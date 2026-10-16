#!/usr/bin/env python3
"""Build a bounded repository map from Git's current file inventory."""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import json
import os
import posixpath
import re
import stat
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path, PurePosixPath
from typing import Any
try:
    from .onboarding import _reject_symlink_chain, _state_paths
except ImportError:  # direct script execution
    from onboarding import _reject_symlink_chain, _state_paths

DEFAULT_MAX_CHARS = 2500
MAX_CHARS = 12000
DEFAULT_MAX_FILES = 2000
MAX_FILES = 5000
MAX_FILE_BYTES = 128 * 1024
MAX_READ_BYTES = 16 * 1024 * 1024
MAX_SYMBOLS = 24
MAX_DEPS = 24
GIT_TIMEOUT = 5
CACHE_VERSION = 3
SKIP_DIRS = {".git", "vendor", "node_modules", "build", "dist"}
PRIVATE_NAMES = {"credentials", "credential", "secrets", "secret", "keys", "id_rsa", "id_ed25519"}
CONFIG_NAMES = {
    "cargo.toml", "dockerfile", "go.mod", "makefile", "package.json", "pyproject.toml",
    "requirements.txt", "setup.cfg", "setup.py", "tsconfig.json", "vite.config.js", "webpack.config.js",
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
    ".yaml": "yaml", ".yml": "yaml", ".toml": "toml", ".xml": "xml", ".ini": "ini", ".cfg": "ini",
    ".conf": "ini", ".properties": "properties", ".gradle": "groovy", ".proto": "protobuf",
}
JS_IMPORT = re.compile(
    r"(?:\bimport\s+(?:[^'\";]*?\s+from\s+)?|\bexport\s+[^'\";]*?\s+from\s+)['\"]([^'\"]+)['\"]"
)
JS_REQUIRE = re.compile(r"\brequire\s*\(\s*['\"]([^'\"]+)['\"]\s*\)")
JS_SYMBOLS = (
    (re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)"), "function"),
    (re.compile(r"^\s*(?:export\s+)?class\s+([A-Za-z_$][\w$]*)"), "class"),
    (re.compile(r"^\s*(?:export\s+)?interface\s+([A-Za-z_$][\w$]*)"), "interface"),
    (re.compile(r"^\s*(?:export\s+)?(?:type|enum)\s+([A-Za-z_$][\w$]*)"), "type"),
    (re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\("), "function"),
)
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
            ["git", "-C", str(path), *args], capture_output=True, check=False, timeout=GIT_TIMEOUT
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
def _git_context(supplied: Path) -> tuple[Path, str, list[str], list[str]]:
    root_result = _git(supplied, "rev-parse", "--show-toplevel")
    if root_result is None or root_result.returncode != 0:
        return supplied, "", [], ["Git inventory unavailable; use native search to inspect this repository"]
    try:
        root = Path(os.fsdecode(root_result.stdout.strip())).resolve(strict=True)
    except OSError:
        return supplied, "", [], ["Git root unavailable; use native search to inspect this repository"]
    head_result = _git(root, "rev-parse", "HEAD")
    head = os.fsdecode(head_result.stdout.strip()) if head_result and head_result.returncode == 0 else ""
    inventory_result = _git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
    if inventory_result is None or inventory_result.returncode != 0:
        return root, head, [], ["Git inventory unavailable; use native search to inspect this repository"]
    inventory = []
    for raw in inventory_result.stdout.split(b"\0"):
        rel = os.fsdecode(raw) if raw else ""
        if _safe_relative(rel):
            inventory.append(PurePosixPath(rel).as_posix())
    return root, head, sorted(set(inventory)), []
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
def _private(rel: str) -> bool:
    for part in PurePosixPath(rel).parts:
        lower = part.lower()
        if part.startswith(".env") or lower in PRIVATE_NAMES or "credential" in lower or "secret" in lower:
            return True
        if lower.endswith((".pem", ".key", ".p12", ".pfx")) or re.search(r"(?:^|[-_.])key(?:[-_.]|$)", lower):
            return True
    return False
def _skip_dir(rel: str) -> bool:
    return any(part.lower() in SKIP_DIRS for part in PurePosixPath(rel).parts[:-1])
def _language(rel: str) -> str | None:
    name = PurePosixPath(rel).name.lower()
    if name in CONFIG_NAMES:
        return "python" if name.endswith(".py") else "javascript" if name.endswith(".js") else "config"
    if name == "dockerfile" or name.startswith("dockerfile."):
        return "config"
    return LANGUAGES.get(PurePosixPath(rel).suffix.lower())
def _entry_config(rel: str) -> bool:
    name = PurePosixPath(rel).name.lower()
    return name in CONFIG_NAMES or name == "dockerfile" or name.startswith("dockerfile.")
def _candidate(root: Path, rel: str) -> tuple[dict[str, Any] | None, str | None]:
    path = root / rel
    fp = _fingerprint(path)
    if _private(rel) or _skip_dir(rel) or _has_symlink_ancestor(path, root):
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
def _python_outline(text: str) -> tuple[list[dict[str, Any]], list[list[Any]], str | None]:
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, TypeError):
        return [], [], "Python file could not be parsed"
    symbols: list[dict[str, Any]] = []
    imports: list[list[Any]] = []
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
            imports.extend([[node.module or "", int(node.level), alias.name] for alias in node.names])
    return symbols[:MAX_SYMBOLS], imports[: MAX_DEPS * 2], None
def _javascript_outline(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    symbols: list[dict[str, Any]] = []
    for line, source in enumerate(text.splitlines(), 1):
        for expression, kind in JS_SYMBOLS:
            match = expression.search(source)
            if match:
                symbols.append({"name": match.group(1), "kind": kind, "line": line})
                break
        if len(symbols) == MAX_SYMBOLS:
            break
    return symbols, (JS_IMPORT.findall(text) + JS_REQUIRE.findall(text))[: MAX_DEPS * 2]
def _read_parse(info: dict[str, Any], remaining: int) -> tuple[dict[str, Any] | None, int, str | None]:
    fp = info["fingerprint"]
    if fp["size"] > MAX_FILE_BYTES:
        return None, 0, "files over 128 KiB were skipped"
    if fp["size"] > remaining:
        return None, 0, "16 MiB total read budget reached"
    if remaining <= 0:
        return None, 0, "16 MiB total read budget reached"
    limit = min(MAX_FILE_BYTES, remaining)
    try:
        with info["absolute"].open("rb") as source:
            data = source.read(limit + 1)
    except OSError:
        return None, 0, "unreadable files were skipped"
    consumed = len(data)
    if consumed > limit:
        current = _fingerprint(info["absolute"])
        if current and current["size"] > MAX_FILE_BYTES:
            return None, min(consumed, remaining), "files over 128 KiB were skipped"
        return None, min(consumed, remaining), "16 MiB total read budget reached"
    if b"\0" in data:
        return None, consumed, "binary or non-UTF-8 files were skipped"
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None, consumed, "binary or non-UTF-8 files were skipped"
    if _fingerprint(info["absolute"]) != fp:
        return None, consumed, "changing files were skipped after re-stat"
    symbols: list[dict[str, Any]] = []
    imports: list[Any] = []
    note = None
    if info["language"] == "python":
        symbols, imports, note = _python_outline(text)
    elif info["language"] in {"javascript", "typescript"}:
        symbols, imports = _javascript_outline(text)
    return {
        "fingerprint": fp,
        "language": info["language"],
        "symbols": symbols,
        "imports": imports,
    }, consumed, note
def _python_dep(path: str, module: str, level: int, imported: str | None, known: set[str]) -> str | None:
    source = PurePosixPath(path)
    base = source.parent
    for _ in range(max(0, level - 1)):
        base = base.parent
    if level == 0:
        base = PurePosixPath(module.replace(".", "/"))
    elif module:
        base /= module.replace(".", "/")
    candidates = []
    if imported and (module or level):
        candidates += [str(base / imported) + ext for ext in (".py", ".pyw", "/__init__.py")]
    if str(base) not in {"", "."}:
        candidates += [str(base) + ext for ext in (".py", ".pyw", "/__init__.py")]
    for candidate in candidates:
        normalized = PurePosixPath(candidate).as_posix()
        if normalized in known:
            return normalized
    if level == 0:
        suffixes = {PurePosixPath(candidate).as_posix() for candidate in candidates}
        matches = sorted(path for path in known if any(path.endswith("/" + suffix) for suffix in suffixes))
        if len(matches) == 1:
            return matches[0]
    return None
def _javascript_dep(path: str, spec: str, known: set[str]) -> str | None:
    if not spec.startswith("."):
        return None
    base = posixpath.normpath(posixpath.join(PurePosixPath(path).parent.as_posix(), spec))
    if base == ".." or base.startswith("../") or base.startswith("/"):
        return None
    suffix = PurePosixPath(base).suffix.lower()
    extensions = (".ts", ".tsx", ".js", ".jsx", ".mts", ".cts", ".mjs", ".cjs", ".json")
    candidates: list[str] = []
    if suffix:
        stem = base[:-len(suffix)]
        if base in known:
            return base
        if suffix in {".js", ".jsx", ".mjs", ".cjs"}:
            candidates += [stem + ext for ext in extensions if ext != suffix]
        candidates.append(base)
    else:
        candidates += [base + ext for ext in extensions]
    candidates += [f"{base}/index{ext}" for ext in extensions]
    for candidate in candidates:
        if PurePosixPath(candidate).as_posix() in known:
            return PurePosixPath(candidate).as_posix()
    return None
def _record(path: str, entry: dict[str, Any], known: set[str]) -> dict[str, Any]:
    dependencies: list[str] = []
    if entry["language"] == "python":
        for module, level, imported in entry["imports"]:
            dep = _python_dep(path, module, level, imported, known)
            if dep and dep != path and dep not in dependencies:
                dependencies.append(dep)
    elif entry["language"] in {"javascript", "typescript"}:
        for spec in entry["imports"]:
            dep = _javascript_dep(path, spec, known)
            if dep and dep != path and dep not in dependencies:
                dependencies.append(dep)
    return {"path": path, "language": entry["language"], "symbols": entry["symbols"][:MAX_SYMBOLS], "dependencies": dependencies[:MAX_DEPS]}
def _rank(records: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    terms = re.findall(r"[a-z0-9_]+", query.lower())
    by_path = {record["path"]: record for record in records}
    reverse = {path: set() for path in by_path}
    for record in records:
        for dependency in record["dependencies"]:
            if dependency in reverse:
                reverse[dependency].add(record["path"])
    scores: dict[str, int] = {}
    for path, record in by_path.items():
        names = " ".join(symbol["name"] + " " + symbol.get("signature", "") for symbol in record["symbols"]).lower()
        score = sum(5 for term in terms if term in path.lower()) + sum(4 for term in terms if term in names)
        if not terms and _entry_config(path):
            score += 6
        scores[path] = score
    matched = [path for path, score in scores.items() if score]
    for path in matched:
        for neighbor in set(by_path[path]["dependencies"]) | reverse[path]:
            if neighbor in scores:
                scores[neighbor] = max(scores[neighbor], 2)
    return sorted(records, key=lambda record: (-scores[record["path"]], not _entry_config(record["path"]), record["path"]))
def _note(notes: list[str], value: str) -> None:
    if value and value not in notes:
        notes.append(value)
def _valid_fp(value: Any) -> bool:
    return isinstance(value, dict) and all(isinstance(value.get(key), int) and value[key] >= 0 for key in ("ctime_ns", "inode", "size", "mtime_ns"))


def _valid_entry(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) - {"fingerprint", "language", "symbols", "imports"}:
        return False
    if not _valid_fp(value.get("fingerprint")) or not isinstance(value.get("language"), str):
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
    imports = value.get("imports")
    if not isinstance(imports, list) or len(imports) > MAX_DEPS * 2:
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
        _reject_symlink_chain(state, "state parent")
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
        if write:
            state.mkdir(parents=True, exist_ok=True)
            _reject_symlink_chain(state, "state parent")
            directory.mkdir(exist_ok=True)
            _reject_symlink_chain(directory, "code-map cache parent")
        elif not directory.exists():
            return directory, directory / (hashlib.sha256(str(root).encode()).hexdigest() + ".json")
        path = directory / (hashlib.sha256(str(root).encode()).hexdigest() + ".json")
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
        if path.stat().st_size > 8 * 1024 * 1024:
            return {}, "code-map cache is too large"
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {}, f"code-map cache is invalid: {exc}"
    if not isinstance(payload, dict) or payload.get("version") != CACHE_VERSION:
        return {}, "code-map cache has an unsupported shape"
    raw = payload.get("entries")
    if not isinstance(raw, dict):
        return {}, "code-map cache entries are invalid"
    reusable: dict[str, Any] = {}
    for path_name, entry in raw.items():
        current = candidates.get(path_name)
        if isinstance(path_name, str) and current and _valid_entry(entry) and entry["fingerprint"] == current["fingerprint"] and entry["language"] == current["language"]:
            reusable[path_name] = entry
    return reusable, None
def _write_json(root: Path, entries: dict[str, Any]) -> None:
    directory, path = _cache_location(root, True)
    if path.exists() and path.is_symlink():
        raise CodeMapError(f"refusing symlink code-map cache: {path}")
    encoded = json.dumps({"version": CACHE_VERSION, "entries": entries}, ensure_ascii=True, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > 8 * 1024 * 1024:
        raise CodeMapError("code-map cache exceeds 8 MiB")
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
def _build(root: Path, head: str, inventory: list[str], notes: list[str], query: str, max_files: int, use_cache: bool, refresh: bool) -> dict[str, Any]:
    candidates: dict[str, dict[str, Any]] = {}
    skipped = 0
    for rel in inventory:
        candidate, reason = _candidate(root, rel)
        if candidate:
            candidates[rel] = candidate
        else:
            skipped += 1
            _note(notes, reason or "inventory entry skipped")
    cached, cache_note = ({}, None) if (refresh or not use_cache) else _load_entries(root, candidates)
    if cache_note and "invalid" in cache_note.lower():
        _note(notes, "invalid cache entries were reparsed")
    elif cache_note:
        _note(notes, cache_note)
    entries: dict[str, Any] = {}
    remaining = MAX_READ_BYTES
    for rel, info in candidates.items():
        entry = cached.get(rel)
        if entry is None:
            entry, consumed, parse_note = _read_parse(info, remaining)
            remaining = max(0, remaining - consumed)
            if parse_note:
                _note(notes, parse_note)
            if entry is None:
                skipped += 1
                continue
        entries[rel] = entry
    budget_hit = any(note.startswith("16 MiB total read budget") for note in notes)
    if remaining == 0 and len(entries) < len(candidates):
        _note(notes, "16 MiB total read budget reached")
    known = set(entries)
    records = [_record(path, entry, known) for path, entry in entries.items()]
    ranked = _rank(records, query)
    file_cap = len(ranked) > max_files
    truncated = file_cap or budget_hit
    if file_cap:
        skipped += len(ranked) - max_files
        _note(notes, f"file cap reached at {max_files} files")
    if any(info["language"] in {"python", "javascript", "typescript"} for info in candidates.values()):
        _note(notes, "Python and JavaScript/TypeScript import links are heuristic and incomplete; aliases, dynamic imports, and unresolved modules need native search")
    selected = sorted(ranked[:max_files], key=lambda record: record["path"])
    model = {
        "root_name": repository_name(root),
        "generated_at": _now(),
        "head": head,
        "coverage": {"inventory": len(inventory), "indexed": len(selected), "truncated": truncated, "skipped": skipped, "notes": notes[:24]},
        "files": selected,
        "focus": [record["path"] for record in _rank(selected, query)[:12]],
    }
    if use_cache:
        try:
            _write_json(root, entries)
        except CodeMapError as exc:
            _note(model["coverage"]["notes"], f"cache unavailable: {exc}")
    return model


def _text(model: dict[str, Any], limit: int) -> str:
    coverage = model["coverage"]
    partial = coverage["truncated"] or coverage["skipped"] or any(
        note.startswith(("Git inventory unavailable", "Git root unavailable"))
        for note in coverage["notes"]
    )
    lines = [
        f"Code map: {json.dumps(model['root_name'], ensure_ascii=True)}",
        f"Head: {model['head'] or '(unavailable)' }",
        f"Coverage: {coverage['indexed']}/{coverage['inventory']} files indexed; {coverage['skipped']} skipped; {'partial' if partial else 'complete'}",
        "Source confirmation: metadata only; inspect listed files before changing behavior.",
        "Focus:",
    ]
    by_path = {file["path"]: file for file in model["files"]}
    for path in model["focus"]:
        file = by_path.get(path)
        if not file:
            continue
        symbols = ", ".join((symbol.get("signature") or symbol["name"]) + f" ({symbol['kind']}:{symbol['line']})" for symbol in file["symbols"])
        dependencies = ", ".join(json.dumps(dep, ensure_ascii=True) for dep in file["dependencies"])
        line = f"- {json.dumps(path, ensure_ascii=True)} [{file['language']}]"
        if symbols:
            line += " symbols: " + symbols
        if dependencies:
            line += " deps: " + dependencies
        lines.append(line)
    if coverage["notes"]:
        lines.append("Notes: " + "; ".join(coverage["notes"]))
    value = "\n".join(lines)
    if len(value) <= limit:
        return value
    suffix = "\n[output truncated; inspect JSON or the live viewer for the bounded full map]"
    return (value[: max(0, limit - len(suffix))] + suffix)[-limit:]
def build_map(repo: str | os.PathLike[str], *, query: str = "", max_chars: int = DEFAULT_MAX_CHARS, max_files: int = DEFAULT_MAX_FILES, no_cache: bool = False, refresh: bool = False, output_format: str = "text") -> tuple[dict[str, Any], str]:
    if output_format not in {"text", "json"}:
        raise CodeMapError(f"unsupported output format: {output_format}")
    root_input = _repo_path(repo)
    root, head, inventory, notes = _git_context(root_input)
    model = _build(root, head, inventory, notes, query, _clamp(int(max_files), 1, MAX_FILES), not no_cache, refresh)
    max_chars = _clamp(int(max_chars), 500, MAX_CHARS)
    if output_format == "text":
        return model, _text(model, max_chars)
    if output_format == "json":
        return model, json.dumps(model, ensure_ascii=True, separators=(",", ":"))
    raise CodeMapError("unsupported output format")
def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a bounded repository code map")
    parser.add_argument("--repo", required=True, metavar="PATH")
    parser.add_argument("--query", default="", metavar="TEXT")
    parser.add_argument("--format", choices=("text", "json", "html"), default="text")
    parser.add_argument("--no-cache", action="store_true")
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
    try:
        if args.format == "html":
            url = _server_api().open_map(args.repo, query=args.query, open_browser=args.open_html)
            sys.stdout.write(url + "\n")
            return 0
        if args.no_cache:
            model, rendered = build_map(args.repo, query=args.query, max_chars=args.max_chars, max_files=args.max_files, no_cache=True, refresh=args.refresh, output_format=args.format)
        else:
            try:
                model = _server_api().get_model(args.repo, query=args.query, max_files=_clamp(args.max_files, 1, MAX_FILES), refresh=args.refresh)
            except (OSError, ValueError, ImportError) as exc:
                print(f"local viewer unavailable; using an in-process map: {exc}", file=sys.stderr)
                model, _ = build_map(args.repo, query=args.query, max_files=args.max_files, refresh=args.refresh)
            rendered = _text(model, _clamp(args.max_chars, 500, MAX_CHARS)) if args.format == "text" else json.dumps(model, ensure_ascii=True, separators=(",", ":"))
        sys.stdout.write(rendered)
        return 0
    except (CodeMapError, OSError, ValueError, ImportError) as exc:
        print(f"code-map error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
