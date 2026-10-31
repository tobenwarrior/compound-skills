#!/usr/bin/env python3
"""Build a bounded repository map from Git's current file inventory."""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import functools
import hashlib
import json
import math
import os
import posixpath
import re
import selectors
import stat
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path, PurePosixPath
from typing import Any
try:
    from .onboarding import _reject_symlink, _state_paths
    from .workspace_imports import MAX_PACKAGE_FILES, load_workspace_packages, resolve_workspace_import
    from .language_outlines import SUPPORTED_LANGUAGES, javascript_exports, javascript_outline, mask_javascript, outline as _language_outline, split_lines
    from .safe_open import open_regular_nofollow
    from .language_imports import extract_language_metadata, build_local_import_index, resolve_go_import, resolve_rust_import, rust_module_dependencies, _sanitize_metadata
except ImportError:  # direct script execution
    from onboarding import _reject_symlink, _state_paths
    from workspace_imports import MAX_PACKAGE_FILES, load_workspace_packages, resolve_workspace_import
    from language_outlines import SUPPORTED_LANGUAGES, javascript_exports, javascript_outline, mask_javascript, outline as _language_outline, split_lines
    from safe_open import open_regular_nofollow
    from language_imports import extract_language_metadata, build_local_import_index, resolve_go_import, resolve_rust_import, rust_module_dependencies, _sanitize_metadata

DEFAULT_MAX_CHARS = 2500
MAX_CHARS = 12000
DEFAULT_MAX_FILES = 2000
MAX_FILES = 20000
MAX_FILE_BYTES = 1024 * 1024
MAX_READ_BYTES = 64 * 1024 * 1024
MAX_SYMBOLS = 512
MAX_DEPS = 256
MAX_IMPORTS = MAX_DEPS * 2
MAX_PARSE_NOTE_CHARS = 160
GIT_TIMEOUT = 5
CACHE_VERSION = 14
ANALYSIS_KINDS = {"python-ast", "javascript-outline", "heuristic-outline", "metadata"}
MAX_ALIAS_CONFIGS = 64
MAX_ALIAS_CONFIG_BYTES = 64 * 1024
MAX_ALIAS_RULES = 2048
MAX_ALIAS_EXTENDS_DEPTH = 16
MAX_ALIAS_READS = 128
MAX_ALIAS_TARGETS = 8
MAX_COCHANGE_COMMITS = 30
MAX_COCHANGE_FILES = 60
MAX_COCHANGE_RESULTS = 6
MAX_GIT_LOG_BYTES = 1024 * 1024
MAX_GIT_INVENTORY_BYTES = 4 * 1024 * 1024
INVENTORY_CAP_NOTE = "Git inventory capped at 4 MiB of paths; later files are not indexed"
MAX_CACHE_BYTES = 8 * 1024 * 1024
SKIP_DIRS = {".git", "vendor", "node_modules"}
BUILD_DIRS = {"build", "dist"}
SKIP_AND_BUILD_DIRS = SKIP_DIRS | BUILD_DIRS
PRIVATE_KEY_PART = re.compile(r"(?:^|[-_.])key(?:[-_.]|$)")
PRIVATE_NAMES = {"credentials", "credential", "secrets", "secret", "keys", "id_rsa", "id_ed25519"}
CONFIG_NAMES = {
    "cargo.toml", "dockerfile", "go.mod", "makefile", "package.json", "pyproject.toml", "procfile",
    "requirements.txt", "setup.cfg", "setup.py", "tsconfig.json", "vite.config.js", "webpack.config.js",
}
NON_CODE_NAMES = {
    ".codeowners", ".cursorignore", ".dockerignore", ".editorconfig", ".gitattributes", ".gitignore",
    ".gitmodules", ".gitkeep", ".npmignore", "authors", "changelog", "copying", "license", "notice", "readme",
    "codeowners", "go.sum", "package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", ".mailmap",
    ".nvmrc", ".node-version", ".python-version", ".ruby-version", ".tool-versions", ".npmrc", ".yarnrc",
    ".prettierrc", ".prettierignore", ".eslintignore", ".flake8", ".coveragerc", ".pylintrc", ".clang-format",
}
NON_CODE_SUFFIXES = {
    ".adoc", ".bmp", ".csv", ".gif", ".ico", ".jpeg", ".jpg", ".lock", ".log", ".map", ".md",
    ".mdc", ".markdown", ".png", ".rst", ".svg", ".text", ".txt", ".webp",
    ".bin", ".jsonl", ".otf", ".ttf", ".woff", ".woff2", ".xls", ".xlsx",
    ".avif", ".class", ".db", ".diff", ".dll", ".dylib", ".eot", ".exe", ".gz", ".jar", ".lockb", ".mov",
    ".mp3", ".mp4", ".parquet", ".patch", ".pdf", ".pkl", ".pyc", ".snap", ".so", ".sqlite", ".tar", ".tgz",
    ".tiff", ".wasm", ".wav", ".zip",
}
LANGUAGES = {
    **dict.fromkeys((".py", ".pyw"), "python"),
    **dict.fromkeys((".js", ".jsx", ".mjs", ".cjs"), "javascript"),
    **dict.fromkeys((".ts", ".tsx", ".mts", ".cts"), "typescript"),
    **dict.fromkeys((".c", ".h"), "c"),
    **dict.fromkeys((".cc", ".cpp", ".cxx", ".hh", ".hpp"), "cpp"),
    ".cs": "csharp", ".go": "go", ".rs": "rust", ".java": "java", ".rb": "ruby",
    ".php": "php", ".swift": "swift", ".kt": "kotlin", ".kts": "kotlin", ".scala": "scala",
    **dict.fromkeys((".sh", ".bash", ".zsh", ".fish"), "shell"),
    ".sql": "sql", ".html": "html", ".htm": "html", ".css": "css", ".scss": "scss",
    ".less": "less", ".vue": "vue", ".svelte": "svelte", ".json": "json", ".jsonc": "json",
    ".yaml": "yaml", ".yml": "yaml", ".toml": "toml", ".xml": "xml", ".plist": "xml",
    ".ini": "ini", ".cfg": "ini", ".service": "ini",
    ".conf": "ini", ".properties": "properties", ".gradle": "groovy", ".proto": "protobuf",
}
STDLIB_MODULES = frozenset(sys.stdlib_module_names)
PYTHON_VERSION = f"{sys.version_info[0]}.{sys.version_info[1]}"
OUTLINED_LANGUAGES = {"python", "javascript", "typescript", *SUPPORTED_LANGUAGES}
# Query words that name no file: English function words and verbs that describe any change.
QUERY_STOP_WORDS = frozenset("""
a about after again all also am an and any are as at be because been before being both but by can could did do does doing
during each for from further had has have having here how if in into is it its itself just more most no nor not now of off
on once only or other our out over own same should so some such than that the their them then there these they this those
through to too under until up very was we were what when where which while who why will with would you your
fix fixes fixed add adds added update updates updated remove removes removed use uses used using support supports allow allows
make makes change changes changed improve improves feat chore refactor perf wip revert bump typo typos minor
""".split())
QUERY_TEST_WORDS = frozenset({"test", "tests", "testing", "spec", "specs"})
TEST_DIRS = frozenset({"test", "tests", "__tests__", "spec", "specs", "e2e"})
TEST_FILE = re.compile(r"^test_.*\.py$|^conftest\.py$|_test\.[a-z0-9]+$|\.(?:test|spec)\.[a-z0-9]+$")
IDENTIFIER = re.compile(r"[A-Za-z0-9_]+")
WORD_PART = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+")
# Focus weights were tuned on recent Flask, click and Hono commits; the README reports other commits.
CONTENT_WEIGHT = 0.5
SIZE_WEIGHT = 0.3
IMPORTER_WEIGHT = 0.3
TEST_FACTOR = 0.5
CONTENT_RANK_FILES = 50
CONTENT_RANK_BYTES = 8 * 1024 * 1024
_COCHANGE_CACHE: dict[tuple[str, str], dict[str, list[dict[str, Any]]]] = {}
class CodeMapError(ValueError):
    pass
def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))
def _repo_path(raw: str | os.PathLike[str]) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    try:
        path = path.resolve(strict=True)
    except OSError as exc:
        raise CodeMapError(f"could not resolve repository: {exc}") from exc
    if not path.is_dir():
        raise CodeMapError(f"repository is not a directory: {path}")
    return path
def _git(path: Path, *args: str) -> subprocess.CompletedProcess[bytes] | None:
    try:
        return subprocess.run(
            ["git", "--no-optional-locks", "-C", str(path), *args], capture_output=True, check=False, timeout=GIT_TIMEOUT
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def _remote_name(value: str) -> str | None:
    remote = value.strip()
    if not remote or any(character.isspace() or ord(character) < 32 or ord(character) == 127 for character in remote):
        return None
    path = ""
    if "://" in remote:
        try:
            parsed = urllib.parse.urlsplit(remote)
            hostname = parsed.hostname
        except ValueError:
            return None
        if parsed.scheme.lower() not in {"http", "https", "ssh", "git", "git+ssh"} or not hostname:
            return None
        path = parsed.path
    else:
        match = re.fullmatch(r"(?:[^@/\s:]+@)?[^/\s:]+:(?P<path>[^?#\s]+)", remote)
        if not match:
            return None
        path = match.group("path")
    candidate = PurePosixPath(path.rstrip("/")).name
    if candidate.lower().endswith(".git"):
        candidate = candidate[:-4]
    if not candidate or candidate in {".", ".."} or any(character in candidate for character in "/\\:@"):
        return None
    if any(ord(character) < 32 or ord(character) == 127 for character in candidate):
        return None
    return candidate


def repository_name(root: Path) -> str:
    """Return a safe display name without changing the canonical repository path."""
    fallback = root.name
    result = _git(root, "remote", "get-url", "origin")
    if result is None or result.returncode != 0:
        return fallback
    try:
        remote = os.fsdecode(result.stdout)
    except (UnicodeDecodeError, ValueError):
        return fallback
    return _remote_name(remote) or fallback


def _safe_relative(value: str) -> bool:
    path = PurePosixPath(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts
def _git_inventory(root: Path) -> tuple[bytes | None, bool]:
    """Return whole NUL-terminated paths within MAX_GIT_INVENTORY_BYTES, tracked first, and whether the cap cut any."""
    tracked = _bounded_git_output(root, ["ls-files", "--cached", "-z"], MAX_GIT_INVENTORY_BYTES, keep_prefix=True)
    if tracked is None:
        return None, False
    # Untracked paths get what tracked ones leave but at least a quarter, so an unignored dependency folder cannot
    # crowd out tracked source and a tracked tree past the cap cannot hide the files just created.
    reserve = max(MAX_GIT_INVENTORY_BYTES - len(tracked), MAX_GIT_INVENTORY_BYTES // 4)
    others = _bounded_git_output(root, ["ls-files", "--others", "--exclude-standard", "-z"], reserve, keep_prefix=True)
    if others is None:
        return None, False
    capped = len(tracked) + len(others) > MAX_GIT_INVENTORY_BYTES
    # Keep the complete entries read so far instead of mapping nothing.
    others = others[:others.rfind(b"\0", 0, reserve) + 1]
    return tracked[:tracked.rfind(b"\0", 0, MAX_GIT_INVENTORY_BYTES - len(others)) + 1] + others, capped
def _git_context(supplied: Path) -> tuple[Path, str, list[str], list[str]]:
    root_result = _git(supplied, "rev-parse", "--show-toplevel")
    if root_result is None or root_result.returncode != 0:
        return supplied, "", [], ["Git inventory unavailable; use native search to inspect this repository"]
    try:
        root = Path(os.fsdecode(root_result.stdout.removesuffix(b"\n"))).resolve(strict=True)  # names may end in spaces
    except OSError:
        return supplied, "", [], ["Git root unavailable; use native search to inspect this repository"]
    head_result = _git(root, "rev-parse", "HEAD")
    head = os.fsdecode(head_result.stdout.strip()) if head_result and head_result.returncode == 0 else ""
    inventory_data, capped = _git_inventory(root)
    if inventory_data is None:
        return root, head, [], ["Git inventory unavailable; inspect with native search"]
    notes = [INVENTORY_CAP_NOTE] if capped else []
    inventory = []
    for raw in inventory_data.split(b"\0"):
        rel = os.fsdecode(raw) if raw else ""
        if _safe_relative(rel):
            inventory.append(PurePosixPath(rel).as_posix())
    return root, head, sorted(set(inventory)), notes


def _git_branch(root: Path) -> str:
    result = _git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    if result is None or result.returncode != 0:
        return ""
    try:
        branch = os.fsdecode(result.stdout).strip()
    except (UnicodeDecodeError, ValueError):
        return ""
    if not branch or any(ord(character) < 32 or ord(character) == 127 for character in branch):
        return ""
    return branch[:256]


def _git_changes_result(root: Path) -> tuple[dict[str, str], str | None]:
    """Return bounded porcelain statuses keyed by the current path.

    The inventory remains authoritative for which files enter the model, so a
    deleted path can never become a metadata-only ghost in the result.
    """
    raw_status = _bounded_git_output(
        root, ["status", "--porcelain=v1", "-z", "--untracked-files=all"], MAX_GIT_LOG_BYTES
    )
    if raw_status is None:
        return {}, "Git status unavailable or exceeded the bounded output limit; changed-file metadata is unavailable"
    changes: dict[str, str] = {}
    parts = raw_status.split(b"\0")
    index = 0
    while index < len(parts):
        raw = parts[index]
        index += 1
        if not raw:
            continue
        try:
            record = os.fsdecode(raw)
        except (UnicodeDecodeError, ValueError):
            continue
        if len(record) < 3:
            continue
        status = record[:2]
        path = PurePosixPath(record[3:]).as_posix()
        if not _safe_relative(path):
            continue
        if "R" in status:
            # In NUL-delimited porcelain output the second path is the old
            # name. The first path is the current destination.
            if index < len(parts):
                index += 1
            kind = "renamed"
        elif "C" in status:
            if index < len(parts):
                index += 1
            kind = "added"
        elif "?" in status:
            kind = "untracked"
        elif "A" in status:
            kind = "added"
        elif "D" in status:
            kind = "deleted"
        elif any(character in status for character in "MTUX"):
            kind = "modified"
        else:
            continue
        changes[path] = kind
    return changes, None


def _git_changes(root: Path) -> dict[str, str]:
    return _git_changes_result(root)[0]


def _git_state(root: Path) -> tuple[str, dict[str, str], str | None]:
    changes, note = _git_changes_result(root)
    return _git_branch(root), changes, note


def _fingerprint(path: Path) -> dict[str, int] | None:
    try:
        value = path.lstat()
    except OSError:
        return None
    return {key: int(getattr(value, attr)) for key, attr in (
        ("ctime_ns", "st_ctime_ns"), ("inode", "st_ino"), ("size", "st_size"), ("mtime_ns", "st_mtime_ns")
    )}
def _has_symlink_ancestor(path: Path, root: Path) -> bool:
    current = path
    try:
        while True:
            if current.is_symlink():
                return True
            if current == root or current.parent == current:
                return False
            current = current.parent
    except OSError:
        return True
# Callers pass normalized POSIX paths, so string splits stand in for PurePosixPath.
def _private(rel: str) -> bool:
    for part in rel.split("/"):
        lower = part.lower()
        if part.startswith(".env") or lower in PRIVATE_NAMES or "credential" in lower or "secret" in lower:
            return True
        if lower.endswith((".pem", ".key", ".p12", ".pfx")) or "key" in lower and PRIVATE_KEY_PART.search(lower):
            return True
    return False
def _skip_dir(rel: str, *, git_inventory: bool = False) -> bool:
    skipped = SKIP_DIRS if git_inventory else SKIP_AND_BUILD_DIRS
    return any(part.lower() in skipped for part in rel.split("/")[:-1])
def _name_and_suffix(rel: str) -> tuple[str, str]:
    name = rel.rpartition("/")[2].lower()
    dot = name.rfind(".")
    return name, name[dot:] if 0 < dot < len(name) - 1 else ""
def _language(rel: str) -> str | None:
    name, suffix = _name_and_suffix(rel)
    if name in CONFIG_NAMES:
        return "python" if name.endswith(".py") else "javascript" if name.endswith(".js") else "config"
    if name == "dockerfile" or name.startswith("dockerfile."):
        return "config"
    return None if name in NON_CODE_NAMES else LANGUAGES.get(suffix)
def _entry_config(rel: str) -> bool:
    name = PurePosixPath(rel).name.lower()
    return name in CONFIG_NAMES or name == "dockerfile" or name.startswith("dockerfile.")


def _non_code_path(rel: str) -> bool:
    name, suffix = _name_and_suffix(rel)
    return name in NON_CODE_NAMES or suffix in NON_CODE_SUFFIXES


def _exclusion_reason(rel: str, reason: str | None) -> str | None:
    if reason == "unsupported format" and _non_code_path(rel):
        return "non-code file"
    if reason == "private or symlink path" and _skip_dir(rel, git_inventory=True) and not _private(rel):
        return "vendored dependency folder"
    if reason in {"private or symlink path", "non-regular path"}:
        return reason
    return None


def _candidate(root: Path, rel: str, *, git_inventory: bool = False) -> tuple[dict[str, Any] | None, str | None]:
    path = root / rel
    fp = _fingerprint(path)
    if _private(rel) or _skip_dir(rel, git_inventory=git_inventory) or _has_symlink_ancestor(path, root):
        return None, "private or symlink path"
    if fp is None:
        return None, "path disappeared"
    try:
        if not stat.S_ISREG(path.lstat().st_mode):
            return None, "non-regular path"
    except OSError:
        return None, "path disappeared"
    language = _language(rel)
    if language is None:
        return None, "unsupported format"
    return {"path": rel, "absolute": path, "language": language, "fingerprint": fp}, None
def _python_outline(text: str) -> tuple[list[dict[str, Any]], list[list[Any]], list[str], str | None]:
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, TypeError, RecursionError, MemoryError):
        # Valid but deeply nested generated code can exhaust the parser's recursion or stack limits.
        return [], [], [], "Python file could not be parsed"
    symbols: list[dict[str, Any]] = []
    imports: list[list[Any]] = []
    extra_names: list[list[Any]] = []
    for node in sorted(ast.walk(tree), key=lambda item: getattr(item, "lineno", 0)):
        line = int(getattr(node, "lineno", 1))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = list(node.args.posonlyargs) + list(node.args.args) + list(node.args.kwonlyargs)
            names = [arg.arg for arg in args]
            if node.args.vararg:
                names.append("*" + node.args.vararg.arg)
            if node.args.kwarg:
                names.append("**" + node.args.kwarg.arg)
            symbols.append({"name": node.name, "kind": "function", "line": line, "signature": f"{node.name}({', '.join(names)})"[:128]})
        elif isinstance(node, ast.ClassDef):
            symbols.append({"name": node.name, "kind": "class", "line": line})
        elif isinstance(node, ast.Import):
            imports.extend([[alias.name, 0, None] for alias in node.names])
        elif isinstance(node, ast.ImportFrom):
            # The first name of each statement comes first, so one long name list cannot crowd out later modules.
            names = [[node.module or "", int(node.level), alias.name] for alias in node.names]
            imports.append(names[0])
            extra_names.extend(names[1:])
    imports += extra_names
    notes = [f"Python symbol outline capped at {MAX_SYMBOLS} entries" if len(symbols) > MAX_SYMBOLS else "",
             f"local import links capped at {MAX_IMPORTS} import entries" if len(imports) > MAX_IMPORTS else ""]
    return symbols[:MAX_SYMBOLS], imports[:MAX_IMPORTS], _python_exports(tree), "; ".join(filter(None, notes)) or None


def _python_exports(tree: ast.Module) -> list[str]:
    explicit: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        if any(isinstance(target, ast.Name) and target.id == "__all__" for target in targets):
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError, SyntaxError):
                value = ()
            if isinstance(value, (list, tuple)):
                explicit = [item for item in value if isinstance(item, str)]
            break
    if explicit:
        return list(dict.fromkeys(explicit))[:MAX_SYMBOLS]
    names = [
        node.name for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and not node.name.startswith("_")
    ]
    return list(dict.fromkeys(names))[:MAX_SYMBOLS]
def _javascript_outline(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Symbols and imports of raw JS/TS text, in the shape Y Harness's vendored tests call."""
    return javascript_outline(mask_javascript(text), MAX_IMPORTS)[:2]


def _open_source(root: Path, relative: str) -> int:
    """Return a read-only descriptor for an indexed file without following symlinks."""
    if os.name == "posix" and hasattr(os, "O_NOFOLLOW") and os.open in getattr(os, "supports_dir_fd", ()):
        return open_regular_nofollow(root, relative)
    return os.open(root / relative, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))


def _read_parse(info: dict[str, Any], remaining: int) -> tuple[dict[str, Any] | None, int, str | None]:
    fp = info["fingerprint"]
    if fp["size"] > MAX_FILE_BYTES:
        return None, 0, "source outline exceeds the 1 MiB file limit; file metadata retained"
    if fp["size"] > remaining:
        return None, 0, "64 MiB total read budget reached; file metadata retained"
    if remaining <= 0:
        return None, 0, "64 MiB total read budget reached; file metadata retained"
    limit = min(MAX_FILE_BYTES, remaining)
    try:
        root = Path(info["absolute"])
        for _ in PurePosixPath(info["path"]).parts:
            root = root.parent
        with os.fdopen(_open_source(root, info["path"]), "rb") as source:
            opened = os.fstat(source.fileno())
            if not stat.S_ISREG(opened.st_mode) or any(
                getattr(opened, attr) != fp[key]
                for key, attr in (("size", "st_size"), ("inode", "st_ino"), ("mtime_ns", "st_mtime_ns"), ("ctime_ns", "st_ctime_ns"))
            ):
                return None, 0, "changing files were skipped after re-stat"
            data = source.read(limit + 1)
    except OSError:
        return None, 0, "unreadable files were skipped"
    consumed = len(data)
    if consumed > limit:
        current = _fingerprint(info["absolute"])
        if current and current["size"] > MAX_FILE_BYTES:
            return None, min(consumed, remaining), "source outline exceeds the 1 MiB file limit; file metadata retained"
        return None, min(consumed, remaining), "64 MiB total read budget reached; file metadata retained"
    if b"\0" in data:
        return None, consumed, "binary or non-UTF-8 files were skipped"
    try:
        # utf-8-sig drops a byte-order mark, which would otherwise hide line-1 declarations.
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None, consumed, "binary or non-UTF-8 files were skipped"
    if _fingerprint(info["absolute"]) != fp:
        return None, consumed, "changing files were skipped after re-stat"
    symbols: list[dict[str, Any]] = []
    imports: list[Any] = []
    note = None
    analysis = "metadata"
    exports: list[str] = []
    try:
        if info["language"] == "python":
            analysis = "python-ast"
            symbols, imports, exports, note = _python_outline(text)
        elif info["language"] in {"javascript", "typescript"}:
            analysis = "javascript-outline"
            code = mask_javascript(text)
            symbols, imports, note = javascript_outline(code, MAX_IMPORTS)
            exports = javascript_exports(code)
        elif info["language"] in SUPPORTED_LANGUAGES:
            analysis = "heuristic-outline"
            symbols, note = _language_outline(text, info["language"], MAX_SYMBOLS)
    except Exception:  # One unusual file must not fail the whole map.
        symbols, imports, exports, note = [], [], [], "file analysis failed; file metadata retained"
    entry = {
        "fingerprint": fp,
        "language": info["language"],
        "symbols": symbols,
        "imports": imports,
        "lines": len(split_lines(text)),
        "analysis": analysis,
        "exports": exports,
    }
    if info["language"] in {"go", "rust"} or PurePosixPath(info["path"]).name == "go.mod":
        entry["native_imports"] = extract_language_metadata(info["path"], text)
    if note:
        entry["parse_note"] = note[:MAX_PARSE_NOTE_CHARS]
    return entry, consumed, note
def _python_modules(known: set[str]) -> dict[str, str | None]:
    modules: dict[str, str | None] = {}
    for path in known:
        if PurePosixPath(path).suffix not in {".py", ".pyw"}:
            continue
        parts = PurePosixPath(path).parts
        for offset in range(len(parts)):
            suffix = "/".join(parts[offset:])
            if suffix in modules and modules[suffix] != path:
                modules[suffix] = None
            else:
                modules[suffix] = path
    return modules


def _python_dep(path: str, module: str, level: int, imported: str | None, known: set[str], modules: dict[str, str | None] | None = None) -> str | None:
    source = PurePosixPath(path)
    base = source.parent
    for _ in range(max(0, level - 1)):
        base = base.parent
    if level == 0:
        base = PurePosixPath(module.replace(".", "/"))
    elif module:
        base /= module.replace(".", "/")
    candidates: list[str] = []
    dotted: list[str] = []  # candidates whose module path has at least two segments
    if imported and (module or level):
        candidates += [PurePosixPath(str(base / imported) + ext).as_posix() for ext in (".py", ".pyw", "/__init__.py")]
        dotted += candidates
    if str(base) not in {"", "."}:
        names = [PurePosixPath(str(base) + ext).as_posix() for ext in (".py", ".pyw", "/__init__.py")]
        candidates += names
        dotted += names if "." in module else []
    for candidate in candidates:
        if candidate in known:
            return candidate
    if level == 0:
        for candidate in candidates:
            if "src/" + candidate in known:
                return "src/" + candidate
        # Unanchored matches would tie stdlib or third-party names such as json or celery to unrelated local files.
        if module.split(".")[0] in STDLIB_MODULES:
            return None
        directory = source.parent
        while directory != directory.parent:
            # Scripts and nested projects import from non-package folders above them (and their src/).
            if (directory / "__init__.py").as_posix() not in known:
                for prefix in (directory, directory / "src"):
                    for candidate in candidates:
                        if (prefix / candidate).as_posix() in known:
                            return (prefix / candidate).as_posix()
            directory = directory.parent
        lookup = _python_modules(known) if modules is None else modules
        for candidate in dotted:
            match = lookup.get(candidate)
            if match:
                return match
    return None


def _config_relative(config_dir: PurePosixPath, value: Any) -> str | None:
    if not isinstance(value, str) or not value or len(value) > 512:
        return None
    candidate = posixpath.normpath(posixpath.join(config_dir.as_posix(), value))
    if candidate == ".." or candidate.startswith("../") or candidate.startswith("/"):
        return None
    return PurePosixPath(candidate).as_posix()


def _strip_jsonc(text: str) -> str:
    """Remove JSONC comments without interpreting config code."""
    output: list[str] = []
    index = 0
    in_string = False
    escaped = False
    while index < len(text):
        character = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if in_string:
            output.append(character)
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            index += 1
            continue
        if character == '"':
            in_string = True
            output.append(character)
            index += 1
        elif character == "/" and following == "/":
            index += 2
            while index < len(text) and text[index] not in "\r\n":
                index += 1
        elif character == "/" and following == "*":
            index += 2
            while index + 1 < len(text) and text[index:index + 2] != "*/":
                if text[index] in "\r\n":
                    output.append(text[index])
                index += 1
            index = min(len(text), index + 2)
        else:
            output.append(character)
            index += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(output))


def _load_alias_configs(root: Path, candidates: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    configs: list[dict[str, Any]] = []
    cache: dict[str, dict[str, Any] | None] = {}
    reads = 0

    def load(rel: str, active: set[str]) -> dict[str, Any] | None:
        nonlocal reads
        if rel in active or len(active) >= MAX_ALIAS_EXTENDS_DEPTH:
            return None
        if rel in cache:
            return cache[rel]
        if rel not in candidates or reads >= MAX_ALIAS_READS:
            return None
        reads += 1
        info = candidates[rel]
        try:
            absolute = info["absolute"]
            if (absolute.resolve() != (root / rel).resolve() or not absolute.resolve().is_relative_to(root.resolve())
                    or info["fingerprint"]["size"] > MAX_ALIAS_CONFIG_BYTES):
                return None
            with absolute.open("rb") as source:
                data = source.read(MAX_ALIAS_CONFIG_BYTES + 1)
            if len(data) > MAX_ALIAS_CONFIG_BYTES or _fingerprint(absolute) != info["fingerprint"]:
                return None
            text = data.decode("utf-8-sig")
            payload = json.loads(_strip_jsonc(text))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, RecursionError, KeyError):
            return None
        if not isinstance(payload, dict):
            return None
        directory = PurePosixPath(rel).parent
        parent = None
        extends = payload.get("extends")
        if isinstance(extends, str) and (extends.startswith("./") or extends.startswith("../")):
            target = _config_relative(directory, extends)
            if target is not None:
                options = [target, target + ".json", posixpath.join(target, "tsconfig.json")]
                for option in options:
                    if option in candidates:
                        parent = load(option, active | {rel})
                        break
        compiler = payload.get("compilerOptions")
        if not isinstance(compiler, dict):
            compiler = {}
        base_url = parent["base_url"] if parent else None
        if "baseUrl" in compiler:
            base_url = _config_relative(directory, compiler["baseUrl"])
        paths = parent["paths"] if parent else []
        if isinstance(compiler.get("paths"), dict):
            paths = []
            paths_base = PurePosixPath(base_url) if base_url is not None else directory
            for pattern, targets in list(compiler["paths"].items())[:MAX_ALIAS_RULES]:
                if not isinstance(pattern, str) or not pattern or len(pattern) > 512 or pattern.count("*") > 1 or not isinstance(targets, list):
                    continue
                normalized = [target for target in (_config_relative(paths_base, value) for value in targets[:MAX_ALIAS_TARGETS]) if target is not None]
                if normalized:
                    paths.append((pattern, normalized))
        result = {"directory": directory.as_posix(), "base_url": base_url, "paths": paths}
        cache[rel] = result
        return result

    names = {"tsconfig.json", "jsconfig.json"}
    ordered = sorted(candidates, key=lambda rel: (len(PurePosixPath(rel).parts), rel))
    unloaded = []
    for rel in ordered:
        if PurePosixPath(rel).name.lower() not in names:
            continue
        if len(configs) >= MAX_ALIAS_CONFIGS or reads >= MAX_ALIAS_READS and rel not in cache:
            # Past the caps, leave imports under this config unresolved rather than apply an ancestor's aliases.
            unloaded.append({"directory": PurePosixPath(rel).parent.as_posix(), "base_url": None, "paths": [], "unloaded": True})
            continue
        config = load(rel, set())
        if config and (config["base_url"] or config["paths"]):
            configs.append(config)
    return configs + unloaded


def _alias_match(spec: str, pattern: str) -> str | None:
    if "*" not in pattern:
        return "" if spec == pattern else None
    prefix, suffix = pattern.split("*", 1)
    if not spec.startswith(prefix) or (suffix and not spec.endswith(suffix)):
        return None
    end = len(spec) - len(suffix) if suffix else len(spec)
    value = spec[len(prefix):end]
    return value if value else None


def _config_applies(config: dict[str, Any], path: str) -> bool:
    directory = config["directory"]
    parent = PurePosixPath(path).parent.as_posix()
    return directory in {"", "."} or parent == directory or parent.startswith(directory + "/")


def _javascript_candidates(base: str, known: set[str]) -> str | None:
    base = posixpath.normpath(base)
    if base == ".." or base.startswith("../") or base.startswith("/"):
        return None
    if base in known:
        return base
    suffix = PurePosixPath(base).suffix.lower()
    extensions = (".ts", ".tsx", ".js", ".jsx", ".mts", ".cts", ".mjs", ".cjs", ".json")
    candidates: list[str] = []
    if suffix in {".js", ".jsx", ".mjs", ".cjs"}:
        candidates += [base[:-len(suffix)] + ext for ext in extensions if ext != suffix]
    if suffix not in extensions:
        # Resolvers append extensions to dotted names such as ./app.module or ./vite.config.
        candidates += [base + ext for ext in extensions]
    candidates += [f"{base}/index{ext}" for ext in extensions]
    for candidate in candidates:
        normalized = PurePosixPath(candidate).as_posix()
        if normalized in known:
            return normalized
    return None


def _javascript_alias_dep(path: str, spec: str, known: set[str], configs: list[dict[str, Any]]) -> str | None:
    applicable = sorted(
        (config for config in configs if _config_applies(config, path)),
        key=lambda config: (len(config["directory"].split("/")), config["directory"]),
        reverse=True,
    )
    for config in applicable[:1]:
        if config.get("unloaded"):
            return None
        rules = sorted(config["paths"], key=lambda item: ("*" not in item[0], len(item[0])), reverse=True)
        for pattern, targets in rules:
            wildcard = _alias_match(spec, pattern)
            if wildcard is None:
                continue
            for target in targets:
                candidate = target.replace("*", wildcard)
                dependency = _javascript_candidates(candidate, known)
                if dependency:
                    return dependency
        if config["base_url"]:
            dependency = _javascript_candidates(posixpath.join(config["base_url"], spec), known)
            if dependency:
                return dependency
    return None


def _javascript_dep(path: str, spec: str, known: set[str], configs: list[dict[str, Any]] | None = None) -> str | None:
    if not spec.startswith("."):
        if configs:
            return _javascript_alias_dep(path, spec, known, configs)
        return None
    spec = spec.split("?", 1)[0].split("#", 1)[0]
    base = posixpath.normpath(posixpath.join(PurePosixPath(path).parent.as_posix(), spec))
    return _javascript_candidates(base, known)


def _python_import_spec(module: str, level: int, imported: str | None) -> str:
    if level:
        return "." * level + (module or "")
    return module or imported or ""


def _bounded_git_output(root: Path, arguments: list[str], max_bytes: int, keep_prefix: bool = False) -> bytes | None:
    """Return Git's output, or None past ``max_bytes`` unless ``keep_prefix`` keeps the first ``max_bytes + 1``."""
    process: subprocess.Popen[bytes] | None = None
    selector: selectors.BaseSelector | None = None
    try:
        process = subprocess.Popen(
            ["git", "--no-optional-locks", "-C", str(root), *arguments],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        assert process.stdout is not None
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        chunks: list[bytes] = []
        size = 0
        deadline = time.monotonic() + GIT_TIMEOUT
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired("git log", GIT_TIMEOUT)
            if not selector.select(remaining):
                raise subprocess.TimeoutExpired("git log", GIT_TIMEOUT)
            block = os.read(process.stdout.fileno(), min(65536, max_bytes + 1 - size))
            if not block:
                break
            chunks.append(block)
            size += len(block)
            if size > max_bytes:
                process.kill()
                process.wait(timeout=1)
                return b"".join(chunks) if keep_prefix else None
        data = b"".join(chunks)
        process.wait(timeout=max(0.0, deadline - time.monotonic()))
        return data if process.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        if process is not None:
            try:
                process.kill()
                process.wait(timeout=1)
            except (OSError, subprocess.TimeoutExpired):
                pass
        return None
    finally:
        if selector is not None:
            selector.close()
        if process is not None and process.stdout is not None:
            process.stdout.close()


def _bounded_git_log(root: Path) -> bytes:
    return _bounded_git_output(
        root,
        ["log", f"-n{MAX_COCHANGE_COMMITS}", "--no-renames", "--name-only", "--format=commit:%H", "-z"],
        MAX_GIT_LOG_BYTES,
    ) or b""


def _cochanges(root: Path, head: str, known: set[str]) -> dict[str, list[dict[str, Any]]]:
    """Return top cochanged paths from a small, HEAD-keyed history cache."""
    if not head:
        return {}
    key = (str(root), head)
    cached = _COCHANGE_CACHE.get(key)
    if cached is not None:
        return _cochanges_for_known(cached, known)
    counts: dict[str, dict[str, int]] = {}
    current: list[str] = []
    commits: list[list[str]] = []
    after_marker = False
    for raw in _bounded_git_log(root).split(b"\0"):
        try:
            token = os.fsdecode(raw)
        except (UnicodeDecodeError, ValueError):
            continue
        if token.startswith("commit:"):
            if current:
                commits.append(current)
            current = []
            after_marker = True
        elif token:
            if after_marker and token.startswith("\n"):
                token = token[1:]
            after_marker = False
            if token:
                current.append(PurePosixPath(token).as_posix())
    if current:
        commits.append(current)
    for changed in commits[:MAX_COCHANGE_COMMITS]:
        paths = sorted({path for path in changed if _safe_relative(path)})
        if len(paths) > MAX_COCHANGE_FILES:
            continue
        paths = [path for path in paths if not _private(path) and not _skip_dir(path, git_inventory=True)]
        for path in paths:
            peers = counts.setdefault(path, {})
            for peer in paths:
                if peer != path:
                    peers[peer] = peers.get(peer, 0) + 1
    result = {
        path: [
            {"path": peer, "count": count}
            for peer, count in sorted(peers.items(), key=lambda item: (-item[1], item[0]))
        ]
        for path, peers in counts.items()
    }
    _COCHANGE_CACHE[key] = result
    while len(_COCHANGE_CACHE) > 8:
        _COCHANGE_CACHE.pop(next(iter(_COCHANGE_CACHE)))
    return _cochanges_for_known(result, known)


def _cochanges_for_known(raw: dict[str, list[dict[str, Any]]], known: set[str]) -> dict[str, list[dict[str, Any]]]:
    return {
        path: [item for item in peers if item.get("path") in known][:MAX_COCHANGE_RESULTS]
        for path, peers in raw.items()
        if path in known
    }


def _record(path: str, entry: dict[str, Any], known: set[str], aliases: list[dict[str, Any]] | None = None, changes: dict[str, str] | None = None, cochanges: dict[str, list[dict[str, Any]]] | None = None, modules: dict[str, str | None] | None = None, packages: dict[str, Any] | None = None, native_index: dict[str, Any] | None = None) -> dict[str, Any]:
    dependencies: list[str] = []
    unresolved: list[str] = []
    native_capped = False
    if entry["language"] == "python":
        for module, level, imported in entry["imports"]:
            dep = _python_dep(path, module, level, imported, known, modules)
            if dep and dep != path and dep not in dependencies:
                dependencies.append(dep)
            elif not dep or dep == path and not level:  # an absolute import of itself names another package
                spec = _python_import_spec(module, level, imported)
                if spec and spec not in unresolved:
                    unresolved.append(spec)
    elif entry["language"] in {"javascript", "typescript"}:
        for spec in entry["imports"]:
            dep = _javascript_dep(path, spec, known, aliases)
            if not dep and packages:
                dep = resolve_workspace_import(spec, known, packages, _javascript_candidates)
            if dep and dep != path and dep not in dependencies:
                dependencies.append(dep)
            elif not dep and spec not in unresolved:
                unresolved.append(spec)
    elif entry["language"] in {"go", "rust"} and native_index:
        metadata = entry.get("native_imports", {})
        specs = metadata.get("go_imports", []) if entry["language"] == "go" else metadata.get("rust_uses", [])
        if entry["language"] == "rust":
            dependencies.extend(rust_module_dependencies(path, native_index))
        seen_dependencies = set(dependencies)
        for spec in specs:
            targets = resolve_go_import(spec, path, native_index) if entry["language"] == "go" else resolve_rust_import(spec, path, native_index)
            if targets:
                for dep in targets:
                    if dep in seen_dependencies:
                        continue
                    if len(dependencies) >= MAX_DEPS:
                        native_capped = True
                        break
                    seen_dependencies.add(dep)
                    dependencies.append(dep)
                if native_capped:
                    break
            elif spec not in unresolved:
                unresolved.append(spec)
    record = {
        "path": path,
        "language": entry["language"],
        "symbols": entry["symbols"][:MAX_SYMBOLS],
        "dependencies": dependencies[:MAX_DEPS],
        "lines": entry["lines"],
        "analysis": entry["analysis"],
        "exports": entry["exports"][:MAX_SYMBOLS],
        "unresolved_imports": unresolved[:MAX_DEPS],
        "changed": (changes or {}).get(path, ""),
        "cochanges": list((cochanges or {}).get(path, ()))[:MAX_COCHANGE_RESULTS],
    }
    if entry.get("parse_note"):
        record["outline_note"] = entry["parse_note"]
    if native_capped or len(dependencies) > MAX_DEPS:
        record["outline_note"] = "; ".join(filter(None, (record.get("outline_note"), f"local import links capped at {MAX_DEPS}")))
    if "source_limit" in entry.get("native_imports", {}).get("diagnostics", ()):
        record["outline_note"] = "; ".join(filter(None, (record.get("outline_note"), "local import links read from the first 256 KiB")))
    return record
def _word_parts(text: str) -> set[str]:
    """Lowercase words of identifiers and prose, split at underscores, digits and case changes."""
    return {part.lower() for token in set(IDENTIFIER.findall(text)) for chunk in token.split("_") for part in WORD_PART.findall(chunk)}


@functools.lru_cache(maxsize=1 << 16)
def _stem(word: str) -> str:
    """Fold common English endings so handler, handles and handling, or cookie and cookies, compare equal."""
    if len(word) <= 3:
        return word
    if word.endswith("ies") and len(word) > 4:
        word = word[:-3] + "i"
    elif word.endswith("sses"):
        word = word[:-2]
    elif word.endswith("s") and not word.endswith(("ss", "us", "is")):
        word = word[:-1]
    if word.endswith("ing") and len(word) > 5:
        word = word[:-3]
    elif word.endswith("ed") and len(word) > 4:
        word = word[:-2]
    if word.endswith("er") and len(word) > 4:
        word = word[:-2]
    if word.endswith("y") and len(word) > 3:
        word = word[:-1] + "i"
    if word.endswith("e") and len(word) > 3:
        word = word[:-1]
    return word


@functools.lru_cache(maxsize=1 << 16)
def _name_terms(name: str) -> frozenset[str]:
    return frozenset(_stem(part) for part in _word_parts(name))


def _query_terms(query: str) -> tuple[list[str], bool]:
    """Return the distinct folded query words that can name a file, and whether the query is about tests."""
    words = [part.lower() for token in IDENTIFIER.findall(query) for chunk in token.split("_") for part in WORD_PART.findall(chunk)]
    terms = [_stem(word) for word in words if len(word) > 1 and word not in QUERY_STOP_WORDS]
    return list(dict.fromkeys(terms)), any(word in QUERY_TEST_WORDS for word in words)


def _is_test(path: str) -> bool:
    parts = path.lower().split("/")
    return any(part in TEST_DIRS or part.endswith(("-tests", "_tests")) for part in parts[:-1]) or bool(TEST_FILE.search(parts[-1]))


def _content_terms(root: Path, relative: str, limit: int, finder: re.Pattern[str], terms: set[str]) -> tuple[set[str], int]:
    """Return which ``terms`` occur in the first ``limit`` bytes of an indexed file, and the bytes read.

    ``finder`` keeps the identifiers that can fold to a term, so other words are never split or folded.
    """
    try:
        with os.fdopen(_open_source(root, relative), "rb") as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                return set(), 0
            data = source.read(limit)
    except OSError:
        return set(), 0
    if b"\0" in data:
        return set(), len(data)
    candidates = filter(finder.search, set(IDENTIFIER.findall(data.decode("utf-8", "replace"))))
    return {term for term in map(_stem, _word_parts(" ".join(candidates))) if term in terms}, len(data)


def _rank_unfocused(records: list[dict[str, Any]], by_path: dict[str, dict[str, Any]], reverse: dict[str, set[str]]) -> list[dict[str, Any]]:
    """Without a query, entry configs, their neighbors, and connected or changed files come first."""
    scores: dict[str, int] = {}
    for path, record in by_path.items():
        degree = len(record.get("dependencies", ())) + len(reverse[path])
        scores[path] = 6 * _entry_config(path) + min(2, (degree + 3) // 4) + (record.get("changed") in {"added", "modified", "untracked", "renamed"})
    for path in [path for path in by_path if _entry_config(path)]:
        for neighbor in set(by_path[path]["dependencies"]) | reverse[path]:
            if neighbor in scores:
                scores[neighbor] = max(scores[neighbor], 2)
        for cochange in by_path[path].get("cochanges", ()):
            neighbor = cochange.get("path") if isinstance(cochange, dict) else None
            if neighbor in scores:
                scores[neighbor] = max(scores[neighbor], 1)
    return sorted(records, key=lambda record: (-scores[record["path"]], not _entry_config(record["path"]), record["path"]))


def _rank(records: list[dict[str, Any]], query: str, root: Path | None = None) -> list[dict[str, Any]]:
    """Order files by query words in paths, symbols and, given ``root``, the text of the leading candidates.

    Rarer words weigh more. Larger code files, widely imported ones, current changes and recent co-changes of
    matches rank higher; tests rank lower unless the query is about tests.
    """
    by_path = {record["path"]: record for record in records}
    reverse: dict[str, set[str]] = {path: set() for path in by_path}
    for record in records:
        for dependency in record["dependencies"]:
            if dependency in reverse:
                reverse[dependency].add(record["path"])
    if not IDENTIFIER.search(query):
        return _rank_unfocused(records, by_path, reverse)
    terms, about_tests = _query_terms(query)
    path_terms = {path: _name_terms(path) for path in by_path}
    symbol_terms = {path: frozenset().union(*(_name_terms(symbol["name"]) for symbol in record["symbols"])) for path, record in by_path.items()}
    weights = {
        term: math.log(1 + len(records) / (1 + sum(term in path_terms[path] or term in symbol_terms[path] for path in by_path)))
        for term in terms
    }
    matched = {path: sum(weight * ((term in path_terms[path]) + (term in symbol_terms[path])) for term, weight in weights.items()) for path in by_path}
    bonus = dict.fromkeys(by_path, 0.0)
    for path, record in by_path.items():
        bonus[path] += IMPORTER_WEIGHT * math.log1p(len(reverse[path])) + (record.get("changed") in {"added", "modified", "untracked", "renamed"})
        if record.get("analysis", "metadata") != "metadata":
            bonus[path] += SIZE_WEIGHT * math.log1p(max(0, record.get("lines", 0)))
    cochanged = {
        cochange.get("path") for path, score in matched.items() if score
        for cochange in by_path[path].get("cochanges", ()) if isinstance(cochange, dict)
    }
    for path in cochanged & bonus.keys():
        bonus[path] += 1

    def score(path: str, word_score: float) -> float:
        value = word_score + bonus[path]
        return value * TEST_FACTOR if not about_tests and _is_test(path) else value

    first = {path: score(path, matched[path]) for path in by_path}
    order = sorted(records, key=lambda record: (-first[record["path"]], not _entry_config(record["path"]), record["path"]))
    if root is None or not terms:
        return order
    # Folding only removes endings or turns a final y into i, so a word that folds to a term contains the term
    # without its final i's.
    finder = re.compile("|".join(sorted({re.escape(term.rstrip("i") or term) for term in terms})), re.IGNORECASE)
    head, budget, wanted, rescored = order[:CONTENT_RANK_FILES], CONTENT_RANK_BYTES, set(terms), {}
    for record in head:
        found, used = _content_terms(root, record["path"], min(MAX_FILE_BYTES, budget), finder, wanted) if budget > 0 else (set(), 0)
        budget -= used
        content = sum(weight for term, weight in weights.items() if term in found)
        rescored[record["path"]] = score(record["path"], matched[record["path"]] + CONTENT_WEIGHT * content)
    head.sort(key=lambda record: (-rescored[record["path"]], not _entry_config(record["path"]), record["path"]))
    return head + order[CONTENT_RANK_FILES:]
def _note(notes: list[str], value: str) -> None:
    if value and value not in notes:
        notes.append(value)
def _valid_fp(value: Any) -> bool:
    return isinstance(value, dict) and all(isinstance(value.get(key), int) and value[key] >= 0 for key in ("ctime_ns", "inode", "size", "mtime_ns"))


def _valid_entry(value: Any, relative: str = "") -> bool:
    if not isinstance(value, dict) or set(value) - {"fingerprint", "language", "symbols", "imports", "parse_note", "lines", "analysis", "exports", "native_imports"}:
        return False
    if not _valid_fp(value.get("fingerprint")) or not isinstance(value.get("language"), str):
        return False
    if not isinstance(value.get("lines"), int) or value["lines"] < 0:
        return False
    native_required = bool(relative) and (value["language"] in {"go", "rust"} or PurePosixPath(relative).name == "go.mod")
    native = value.get("native_imports")
    if native_required and (_sanitize_metadata(relative, native) != native or not isinstance(native, dict)):
        return False
    if not native_required and native is not None:
        return False
    if value.get("analysis") not in ANALYSIS_KINDS:
        return False
    expected_analysis = {
        "python": "python-ast",
        "javascript": "javascript-outline",
        "typescript": "javascript-outline",
    }.get(value["language"], "heuristic-outline" if value["language"] in SUPPORTED_LANGUAGES else "metadata")
    if value["analysis"] != expected_analysis:
        return False
    if "parse_note" in value and (
        not isinstance(value["parse_note"], str)
        or not value["parse_note"]
        or len(value["parse_note"]) > MAX_PARSE_NOTE_CHARS
    ):
        return False
    if not isinstance(value.get("symbols"), list) or len(value["symbols"]) > MAX_SYMBOLS:
        return False
    for symbol in value["symbols"]:
        if not isinstance(symbol, dict) or set(symbol) - {"name", "kind", "line", "signature"}:
            return False
        if not isinstance(symbol.get("name"), str) or not isinstance(symbol.get("kind"), str) or not isinstance(symbol.get("line"), int):
            return False
        if "signature" in symbol and not isinstance(symbol["signature"], str):
            return False
    exports = value.get("exports")
    if not isinstance(exports, list) or len(exports) > MAX_SYMBOLS or not all(isinstance(item, str) for item in exports):
        return False
    imports = value.get("imports")
    if not isinstance(imports, list) or len(imports) > MAX_IMPORTS:
        return False
    if value["language"] == "python":
        return all(isinstance(item, list) and len(item) == 3 and isinstance(item[0], str) and isinstance(item[1], int) and item[1] >= 0 and (item[2] is None or isinstance(item[2], str)) for item in imports)
    return all(isinstance(item, str) for item in imports)
def _cache_location(root: Path, write: bool) -> tuple[Path, Path]:
    try:
        state, _ = _state_paths()
        try:
            resolved_state = state.resolve(strict=False)
        except RuntimeError:
            resolved_state = state
        try:
            resolved_state.relative_to(root)
        except ValueError:
            pass
        else:
            raise CodeMapError(f"refusing code-map cache inside repository: {state}")
        _reject_symlink(state, "state directory")
        if state.exists() and not state.is_dir():
            raise CodeMapError(f"state path is not a directory: {state}")
        directory = state / "code-map"
        try:
            resolved_directory = directory.resolve(strict=False)
        except RuntimeError:
            resolved_directory = directory
        try:
            resolved_directory.relative_to(root)
        except ValueError:
            pass
        else:
            raise CodeMapError(f"refusing code-map cache inside repository: {directory}")
        if directory.exists() and (directory.is_symlink() or not directory.is_dir()):
            raise CodeMapError(f"refusing unsafe code-map cache directory: {directory}")
        # Undecodable path bytes arrive as surrogate escapes, which strict UTF-8 cannot encode.
        path = directory / (hashlib.sha256(str(root).encode("utf-8", "surrogateescape")).hexdigest() + ".json")
        if write:
            state.mkdir(parents=True, exist_ok=True)
            _reject_symlink(state, "state directory")
            directory.mkdir(exist_ok=True)
            _reject_symlink(directory, "code-map cache directory")
        elif not directory.exists():
            return directory, path
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise CodeMapError(f"refusing unsafe code-map cache: {path}")
        return directory, path
    except CodeMapError:
        raise
    except (OSError, ValueError) as exc:
        raise CodeMapError(f"code-map cache unavailable: {exc}") from exc
def _load_entries(root: Path, candidates: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], str | None]:
    try:
        _, path = _cache_location(root, False)
    except CodeMapError as exc:
        return {}, str(exc)
    if not path.exists():
        return {}, None
    try:
        if path.stat().st_size > MAX_CACHE_BYTES:
            return {}, "code-map cache is too large"
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {}, f"code-map cache is invalid: {exc}"
    if not isinstance(payload, dict):
        return {}, "code-map cache has an unsupported shape"
    version = payload.get("version")
    # Python outlines depend on the interpreter that parsed them, so another version re-parses them.
    same_python = payload.get("python") == PYTHON_VERSION
    if version != CACHE_VERSION:
        if isinstance(version, int) and 0 <= version < CACHE_VERSION:
            return {}, "code-map cache requires migration"
        return {}, "code-map cache has an unsupported shape"
    raw = payload.get("entries")
    if not isinstance(raw, dict):
        return {}, "code-map cache entries are invalid"
    reusable: dict[str, Any] = {}
    for path_name, entry in raw.items():
        current = candidates.get(path_name)
        if isinstance(path_name, str) and current and _valid_entry(entry, path_name) and entry["fingerprint"] == current["fingerprint"] and entry["language"] == current["language"] and (same_python or entry["language"] != "python"):
            reusable[path_name] = entry
    return reusable, None
def _write_json(root: Path, entries: dict[str, Any]) -> None:
    directory, path = _cache_location(root, True)
    if path.exists() and path.is_symlink():
        raise CodeMapError(f"refusing symlink code-map cache: {path}")
    # Store the entries that fit, so a large repository keeps most of its cache instead of none.
    parts: list[str] = []
    prefix = f'{{"version":{CACHE_VERSION},"python":"{PYTHON_VERSION}","entries":{{'
    size = len(prefix) + 2
    for name, entry in entries.items():
        part = json.dumps(name, ensure_ascii=True) + ":" + json.dumps(entry, ensure_ascii=True, separators=(",", ":"))
        if size + len(part) + 1 <= MAX_CACHE_BYTES:
            parts.append(part)
            size += len(part) + 1
    encoded = prefix + ",".join(parts) + "}}"
    temporary: Path | None = None
    try:
        if path.exists() and path.stat().st_size == len(encoded) and path.read_bytes() == encoded.encode("utf-8"):
            return
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory, prefix=".code-map-", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        temporary = None
    except OSError as exc:
        raise CodeMapError(f"could not write code-map cache: {exc}") from exc
    finally:
        if temporary:
            try:
                temporary.unlink()
            except OSError:
                pass
def _build(root: Path, head: str, inventory: list[str], notes: list[str], query: str, max_files: int, use_cache: bool, refresh: bool, write_cache: bool = True) -> dict[str, Any]:
    candidates: dict[str, dict[str, Any]] = {}
    skipped = 0
    excluded = 0
    excluded_reasons: dict[str, int] = {}
    for rel in inventory:
        candidate, reason = _candidate(root, rel, git_inventory=True)
        if candidate:
            candidates[rel] = candidate
        else:
            exclusion = _exclusion_reason(rel, reason)
            if exclusion:
                excluded += 1
                excluded_reasons[exclusion] = excluded_reasons.get(exclusion, 0) + 1
            else:
                skipped += 1
                _note(notes, reason or "inventory entry skipped")
    terms, about_tests = _query_terms(query)
    order = sorted(candidates, key=lambda path: (
        -sum(term in _name_terms(path) for term in terms), not _entry_config(path), not about_tests and _is_test(path), path,
    ))
    inventory_capped = len(order) > MAX_FILES
    if inventory_capped:
        skipped += len(order) - MAX_FILES
        _note(notes, f"file inventory cap reached at {MAX_FILES} files")
        order = order[:MAX_FILES]
        candidates = {path: candidates[path] for path in order}
    cached, cache_note = ({}, None) if (refresh or not use_cache) else _load_entries(root, candidates)
    if cache_note and "invalid" in cache_note.lower():
        _note(notes, "invalid cache entries were reparsed")
    elif cache_note and "requires migration" not in cache_note.lower():
        _note(notes, cache_note)
    entries: dict[str, Any] = {}
    reusable: dict[str, Any] = {}
    remaining = MAX_READ_BYTES
    pending = 0
    limited = 0
    for rel in order:
        info = candidates[rel]
        entry = cached.get(rel)
        if entry is None:
            entry, consumed, parse_note = _read_parse(info, remaining)
            remaining = max(0, remaining - consumed)
            bounded = entry is None and bool(parse_note) and ("read budget" in parse_note or "file limit" in parse_note)
            metadata_only = bounded and info["language"] not in OUTLINED_LANGUAGES
            if metadata_only:
                # A size limit costs a metadata-only file nothing but its line count, so only that file says which limit.
                parse_note = "line count not read: " + ("64 MiB total read budget reached" if "read budget" in parse_note else "file exceeds the 1 MiB limit")
            elif bounded:
                pending += int("read budget" in parse_note)
                limited += 1
            if parse_note and not metadata_only:
                _note(notes, parse_note)
            if entry is None:
                if not bounded:
                    skipped += 1
                    continue
                entry = {
                    "fingerprint": info["fingerprint"], "language": info["language"],
                    "symbols": [], "imports": [], "lines": 0, "analysis": "metadata", "exports": [],
                    "parse_note": parse_note,
                }
            else:
                reusable[rel] = entry
        else:
            reusable[rel] = entry
            if entry.get("parse_note"):
                _note(notes, entry["parse_note"])
        entries[rel] = entry
    budget_hit = bool(limited) or inventory_capped or INVENTORY_CAP_NOTE in notes
    known = set(entries)
    aliases = _load_alias_configs(root, candidates)
    if any(config.get("unloaded") for config in aliases):
        _note(notes, f"tsconfig/jsconfig alias limits reached; imports under {sum(bool(config.get('unloaded')) for config in aliases)} configs stay unresolved")
    packages = load_workspace_packages(root, candidates)
    if sum(PurePosixPath(rel).name == "package.json" and "node_modules" not in rel.split("/") for rel in candidates) > MAX_PACKAGE_FILES:
        _note(notes, f"workspace package limit reached at {MAX_PACKAGE_FILES} manifests; some package imports stay unresolved")
    branch, changes, git_state_note = _git_state(root)
    if git_state_note:
        _note(notes, git_state_note)
    cochanges = _cochanges(root, head, known)
    modules = _python_modules(known)
    native_metadata = {path: entry["native_imports"] for path, entry in entries.items() if "native_imports" in entry}
    native_index = build_local_import_index(root, native_metadata, known) if native_metadata else None
    if native_index and native_index.get("partial"):
        _note(notes, "Go/Rust local import resolution is partial; inspect unresolved imports")
    records = [_record(path, entry, known, aliases, changes, cochanges, modules, packages, native_index) for path, entry in entries.items()]
    if any("local import links capped" in record.get("outline_note", "") for record in records):
        _note(notes, "local import link cap reached; some importers may be missing")
    ranked = _rank(records, query, root)
    file_cap = len(ranked) > max_files
    truncated = file_cap or budget_hit
    if file_cap:
        skipped += len(ranked) - max_files
        _note(notes, f"file cap reached at {max_files} files")
    if any(info["language"] in {"python", "javascript", "typescript"} for info in candidates.values()):
        _note(notes, "Python and JavaScript/TypeScript import links are heuristic and incomplete; aliases, dynamic imports, and unresolved modules need native search")
    if any(info["language"] in SUPPORTED_LANGUAGES for info in candidates.values()):
        _note(notes, "Other language symbol outlines and Go/Rust import links are heuristic; verify with native search")
    selected = sorted(ranked[:max_files], key=lambda record: record["path"])
    model = {
        "root_name": repository_name(root),
        "generated_at": _now(),
        "head": head,
        "coverage": {
            "inventory": len(inventory), "indexed": len(selected), "truncated": truncated,
            "skipped": skipped, "excluded": excluded, "excluded_reasons": excluded_reasons,
            "pending": pending, "limited": limited,
            "notes": notes[:24],
        },
        "files": selected,
        "focus": [record["path"] for record in ranked[:min(12, max_files)]],
    }
    if branch:
        model["branch"] = branch
    if use_cache and write_cache:
        try:
            _write_json(root, {path: reusable[path] for path in sorted(reusable)})
        except CodeMapError as exc:
            _note(model["coverage"]["notes"], f"cache unavailable: {exc}")
    return model


def _text(model: dict[str, Any], limit: int, query: str = "") -> str:
    coverage = model["coverage"]
    notes = coverage.get("notes", [])
    if not isinstance(notes, list):
        notes = []
    partial = bool(coverage.get("truncated")) or bool(coverage.get("skipped")) or any(
        "import links are heuristic" not in note for note in notes if isinstance(note, str)
    )
    lines = [
        f"Code map: {json.dumps(model['root_name'], ensure_ascii=True)}",
        f"Head: {model['head'] or '(unavailable)' }",
        f"Coverage: {coverage.get('indexed', 0)}/{coverage.get('inventory', 0)} files indexed; "
        f"{coverage.get('excluded', 0)} excluded; {coverage.get('skipped', 0)} skipped; "
        f"{'partial' if partial else 'complete'}",
        "Source confirmation: metadata only; inspect listed files before changing behavior.",
    ]
    excluded_reasons = coverage.get("excluded_reasons", {})
    if isinstance(excluded_reasons, dict) and excluded_reasons:
        summary = ", ".join(f"{count} {reason}" for reason, count in sorted(excluded_reasons.items()))
        lines.insert(3, "Excluded: " + summary)
    lines.append("Focus:")
    terms = _query_terms(query)[0]
    by_path = {file["path"]: file for file in model["files"]}
    for path in model["focus"]:
        file = by_path.get(path)
        if not file:
            continue
        if terms:
            def relevance(symbol: dict[str, Any]) -> int:
                name = _name_terms(symbol["name"])
                signature = _name_terms(symbol.get("signature", ""))
                return sum(2 * (term in name) + (term in signature) for term in terms)
            symbol_values = sorted(file["symbols"], key=relevance, reverse=True)[:8]
        else:
            symbol_values = file["symbols"][:8]
        symbols = ", ".join((symbol.get("signature") or symbol["name"]) + f" ({symbol['kind']}:{symbol['line']})" for symbol in symbol_values)
        if len(file["symbols"]) > len(symbol_values):
            symbols += f" (+{len(file['symbols']) - len(symbol_values)} more symbols)"
        dependency_values = file["dependencies"][:12]
        dependencies = ", ".join(json.dumps(dep, ensure_ascii=True) for dep in dependency_values)
        if len(file["dependencies"]) > len(dependency_values):
            dependencies += f" (+{len(file['dependencies']) - len(dependency_values)} more deps)"
        line = f"- {json.dumps(path, ensure_ascii=True)} [{file['language']}]"
        if symbols:
            line += " symbols: " + symbols
        if dependencies:
            line += " deps: " + dependencies
        lines.append(line)
    if notes:
        lines.append("Notes: " + "; ".join(notes))
    value = "\n".join(lines)
    if len(value) <= limit:
        return value
    suffix = "\n[output truncated; inspect JSON or the live viewer for the bounded full map]"
    return (value[: max(0, limit - len(suffix))] + suffix)[-limit:]
def build_map(repo: str | os.PathLike[str], *, query: str = "", max_chars: int = DEFAULT_MAX_CHARS, max_files: int = DEFAULT_MAX_FILES, no_cache: bool = False, cache_read_only: bool = False, refresh: bool = False, output_format: str = "text") -> tuple[dict[str, Any], str]:
    if no_cache and cache_read_only:
        raise CodeMapError("--no-cache and --cache-read-only are mutually exclusive")
    if output_format not in {"text", "json"}:
        raise CodeMapError(f"unsupported output format: {output_format}")
    root_input = _repo_path(repo)
    root, head, inventory, notes = _git_context(root_input)
    model = _build(root, head, inventory, notes, query, _clamp(int(max_files), 1, MAX_FILES), not no_cache, refresh, write_cache=not cache_read_only)
    max_chars = _clamp(int(max_chars), 500, MAX_CHARS)
    if output_format == "text":
        return model, _text(model, max_chars, query)
    if output_format == "json":
        return model, json.dumps(model, ensure_ascii=True, separators=(",", ":"))
    raise CodeMapError("unsupported output format")
def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a bounded repository code map")
    parser.add_argument("--repo", required=True, metavar="PATH")
    parser.add_argument("--query", default="", metavar="TEXT")
    parser.add_argument("--format", choices=("text", "json", "html"), default="text")
    cache_options = parser.add_mutually_exclusive_group()
    cache_options.add_argument("--no-cache", action="store_true")
    cache_options.add_argument("--cache-read-only", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--open", action="store_true", dest="open_html")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    return parser
def _server_api():
    try:
        from . import map_server
    except ImportError:
        import map_server
    return map_server


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.format == "html" and args.no_cache:
        print("the live viewer requires a local service and cannot be combined with --no-cache", file=sys.stderr)
        return 2
    if args.format == "html" and args.cache_read_only:
        print("the live viewer requires a local service and cannot be combined with --cache-read-only", file=sys.stderr)
        return 2
    try:
        if args.format == "html":
            url = _server_api().open_map(args.repo, query=args.query, open_browser=args.open_html)
            sys.stdout.write(url + "\n")
            return 0
        if args.no_cache or args.cache_read_only:
            model, rendered = build_map(
                args.repo, query=args.query, max_chars=args.max_chars, max_files=args.max_files,
                no_cache=args.no_cache, cache_read_only=args.cache_read_only, refresh=args.refresh,
                output_format=args.format,
            )
        elif args.format == "text":
            try:
                service = _server_api()
                try:
                    rendered = service.get_text(
                        args.repo, query=args.query, max_files=_clamp(args.max_files, 1, MAX_FILES),
                        max_chars=_clamp(args.max_chars, 500, MAX_CHARS), refresh=args.refresh,
                    )
                except AttributeError:
                    # Older local viewers may not expose the summary endpoint yet.
                    model = service.get_model(args.repo, query=args.query, max_files=_clamp(args.max_files, 1, MAX_FILES), refresh=args.refresh)
                    rendered = _text(model, _clamp(args.max_chars, 500, MAX_CHARS), args.query)
                else:
                    if not isinstance(rendered, str):
                        model = service.get_model(args.repo, query=args.query, max_files=_clamp(args.max_files, 1, MAX_FILES), refresh=args.refresh)
                        rendered = _text(model, _clamp(args.max_chars, 500, MAX_CHARS), args.query)
            except (OSError, ValueError, ImportError) as exc:
                print(f"local viewer unavailable; using an in-process map: {exc}", file=sys.stderr)
                model, _ = build_map(args.repo, query=args.query, max_files=args.max_files, refresh=args.refresh)
                rendered = _text(model, _clamp(args.max_chars, 500, MAX_CHARS), args.query)
        else:
            try:
                model = _server_api().get_model(args.repo, query=args.query, max_files=_clamp(args.max_files, 1, MAX_FILES), refresh=args.refresh)
            except (OSError, ValueError, ImportError) as exc:
                print(f"local viewer unavailable; using an in-process map: {exc}", file=sys.stderr)
                model, _ = build_map(args.repo, query=args.query, max_files=args.max_files, refresh=args.refresh)
            rendered = json.dumps(model, ensure_ascii=True, separators=(",", ":"))
        sys.stdout.write(rendered)
        return 0
    except (CodeMapError, OSError, ValueError, ImportError) as exc:
        print(f"code-map error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
