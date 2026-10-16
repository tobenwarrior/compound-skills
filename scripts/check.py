#!/usr/bin/env python3
"""Read-only checks for the compound-skills package."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


NAME = "compound-skills"
VERSION = "0.8.2"
AUTHOR = "tobenwarrior"
REPOSITORY = "https://github.com/tobenwarrior/compound-skills"
SKILLS = ("compound", "map")
SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
MANIFESTS = {
    "plugin.json": "portable",
    ".codex-plugin/plugin.json": "codex",
    ".cursor-plugin/plugin.json": "cursor",
    ".claude-plugin/plugin.json": "claude",
}
MARKETPLACES = {
    ".agents/plugins/marketplace.json": "codex",
    ".cursor-plugin/marketplace.json": "cursor",
    ".claude-plugin/marketplace.json": "claude",
}
CURSOR_RULES_PATH = "./.cursor-plugin/rules/"
CURSOR_RULE_PATH = ".cursor-plugin/rules/compound-default.mdc"
PRIVATE_PATTERNS = (
    ("private_path", re.compile(r"/(?:Users|home|private/tmp|var/folders)/[^\s'\"`<>]+")),
    ("windows_private_path", re.compile(r"(?i)\b[A-Z]:\\Users\\[^\s'\"`<>]+")),
    ("openai_token", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")),
    ("github_token", re.compile(r"\b(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{16,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{16,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private_key", re.compile(r"-----BEGIN(?: [A-Z]+)? PRIVATE KEY-----")),
    (
        "credential_assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?key|access[_-]?token|secret[_-]?key|password)"
            r"\s*[:=]\s*['\"]?[A-Za-z0-9][^\s'\"]{7,}"
        ),
    ),
)


def add(errors: list[dict[str, str]], code: str, path: str, message: str) -> None:
    item = {"code": code, "path": path, "message": message}
    if item not in errors:
        errors.append(item)


def relative(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def safe_is_symlink(root: Path, path: Path, errors: list[dict[str, str]] | None = None) -> bool:
    try:
        return path.is_symlink()
    except OSError:
        if errors is not None:
            add(errors, "unreadable_content", relative(root, path), "release path could not be inspected")
        return True


def under_symlink(root: Path, path: Path, errors: list[dict[str, str]] | None = None) -> bool:
    """Check a lexical release path without resolving any symlink target."""

    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return False
    current = root
    for part in parts:
        current /= part
        if safe_is_symlink(root, current, errors):
            return True
    return False


def public_files(root: Path, errors: list[dict[str, str]]) -> list[Path]:
    """Use Git's tracked/unignored view, with a small non-Git fallback."""

    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            check=False,
            capture_output=True,
        )
        if result.returncode == 0:
            paths = {
                root / item.decode("utf-8", "surrogateescape")
                for item in result.stdout.split(b"\0")
                if item
            }
            if result.stderr:
                add(errors, "release_inventory", ".", "Git could not read every release path")
            return sorted(paths, key=lambda path: relative(root, path))
    except OSError:
        pass

    ignored = {".git", ".pytest_cache", "__pycache__", ".mypy_cache", ".ruff_cache", "tests", "test"}
    paths = []

    def unreadable(exc: OSError) -> None:
        path = Path(exc.filename) if exc.filename else root
        add(errors, "unreadable_content", relative(root, path), "release directory could not be read")

    for directory, directories, files in os.walk(root, followlinks=False, onerror=unreadable):
        parent = Path(directory)
        directories[:] = [name for name in directories if name not in ignored]
        paths.extend(parent / name for name in files if name not in ignored)
        paths.extend(parent / name for name in directories if safe_is_symlink(root, parent / name, errors))
    return sorted(paths, key=lambda path: relative(root, path))


def read_json(root: Path, path: str, label: str, errors: list[dict[str, str]]) -> dict[str, Any] | None:
    file = root / path
    if under_symlink(root, file, errors):
        add(errors, "release_symlink", path, "release paths may not be symlinks")
        return None
    try:
        is_file = file.is_file()
    except OSError:
        add(errors, "unreadable_content", path, f"{label} could not be inspected")
        return None
    if not is_file:
        add(errors, f"{label}_missing", path, f"{label} file is missing")
        return None
    try:
        value = json.loads(file.read_text(encoding="utf-8"))
    except OSError:
        add(errors, "unreadable_content", path, f"{label} could not be read")
        return None
    except UnicodeDecodeError as exc:
        add(errors, f"{label}_encoding", path, f"{label} is not UTF-8: {exc}")
        return None
    except json.JSONDecodeError as exc:
        code = "manifest_json" if label == "manifest" else "marketplace_json"
        add(errors, code, path, f"{label} is malformed JSON at line {exc.lineno}, column {exc.colno}")
        return None
    if not isinstance(value, dict):
        add(errors, f"{label}_type", path, f"{label} top level must be an object")
        return None
    return value


def check_identity(path: str, value: dict[str, Any], errors: list[dict[str, str]]) -> None:
    for field, expected in (("name", NAME), ("version", VERSION), ("repository", REPOSITORY)):
        if value.get(field) != expected:
            add(errors, "identity_mismatch", path, f"{field} must be {expected!r}")
    author = value.get("author")
    if not isinstance(author, dict) or author.get("name") != AUTHOR:
        add(errors, "identity_mismatch", path, "author.name does not match package identity")


def check_path(
    root: Path,
    value: Any,
    origin: str,
    field: str,
    errors: list[dict[str, str]],
    *,
    directory: bool = False,
) -> None:
    if not isinstance(value, str):
        add(errors, "path_type", origin, f"{field} must contain a string path")
        return
    portable = value.replace("\\", "/")
    if "\\" in value:
        add(errors, "path_separator", origin, f"{field} must use forward slashes")
    if value.startswith("/") or re.match(r"^[A-Za-z]:/", portable):
        add(errors, "path_escape", origin, f"{field} must be relative to the package")
        return
    if not (value.startswith("./") or value == "."):
        add(errors, "path_relative", origin, f"{field} must start with ./")
    if ".." in Path(portable).parts:
        add(errors, "path_escape", origin, f"{field} may not contain ..")
        return
    lexical = root / value
    if under_symlink(root, lexical, errors):
        add(errors, "release_symlink", origin, f"{field} may not traverse a symlink")
        return
    target = lexical.resolve()
    if not inside(target, root):
        add(errors, "path_escape", origin, f"{field} resolves outside the package")
    elif not target.exists():
        add(errors, "path_missing", origin, f"{field} does not resolve to a package path")
    elif directory:
        try:
            is_directory = target.is_dir()
        except OSError:
            add(errors, "unreadable_content", origin, f"{field} could not be inspected")
        else:
            if not is_directory:
                add(errors, "source_directory", origin, f"{field} must resolve to a directory")


def check_manifest(root: Path, path: str, kind: str, errors: list[dict[str, str]]) -> dict[str, Any] | None:
    value = read_json(root, path, "manifest", errors)
    if value is None:
        return None
    check_identity(path, value, errors)
    if kind == "portable" and value.get("$schema") != SCHEMA:
        add(errors, "schema_mismatch", path, "portable manifest uses an unexpected schema")
    if kind == "codex" and value.get("skills") != "./skills/":
        add(errors, "component_path", path, "Codex skills must be ./skills/")
    if kind == "cursor" and value.get("skills") not in (None, "./skills/"):
        add(errors, "component_path", path, "Cursor skills must be ./skills/ when declared")
    if kind in {"codex", "cursor"} and "skills" in value:
        check_path(root, value["skills"], path, "skills", errors)
    if kind == "cursor" and "rules" in value:
        if value["rules"] != CURSOR_RULES_PATH:
            add(errors, "component_path", path, f"Cursor rules must be {CURSOR_RULES_PATH}")
        check_path(root, value["rules"], path, "rules", errors, directory=True)
    return value


def check_marketplace(root: Path, path: str, kind: str, errors: list[dict[str, str]]) -> dict[str, Any] | None:
    value = read_json(root, path, "marketplace", errors)
    if value is None:
        return None
    if value.get("name") != NAME:
        add(errors, "identity_mismatch", path, "marketplace name does not match package identity")
    if kind in {"cursor", "claude"}:
        owner = value.get("owner")
        if not isinstance(owner, dict) or owner.get("name") != AUTHOR:
            add(errors, "identity_mismatch", path, "marketplace owner.name does not match package identity")
    entries = value.get("plugins")
    if not isinstance(entries, list):
        add(errors, "marketplace_plugins", path, "marketplace plugins must be an array")
        return value
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        origin = f"{path}:plugins[{index}]"
        if not isinstance(entry, dict):
            add(errors, "marketplace_entry", origin, "plugin entry must be an object")
            continue
        entry_name = entry.get("name")
        if isinstance(entry_name, str) and entry_name in seen:
            add(errors, "duplicate_identity", origin, f"duplicate plugin name {entry_name!r}")
        if isinstance(entry_name, str):
            seen.add(entry_name)
        if entry_name != NAME:
            add(errors, "identity_mismatch", origin, "plugin entry name does not match package identity")
        source = entry.get("source")
        if kind == "codex":
            if not isinstance(source, dict) or source.get("source") != "local":
                add(errors, "marketplace_source", origin, "Codex source must be a local source object")
            else:
                check_path(root, source.get("path"), origin, "source.path", errors, directory=True)
        elif isinstance(source, str):
            check_path(root, source, origin, "source", errors, directory=True)
        else:
            add(errors, "marketplace_source", origin, "marketplace source must be a relative path")
        if "version" in entry and entry["version"] != VERSION:
            add(errors, "identity_mismatch", origin, f"version must be {VERSION!r}")
    return value


def scalar(value: str) -> str | None:
    """Accept quoted strings and unambiguous plain text, not YAML structures."""
    value = value.strip()
    if value.startswith('"'):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, str) else None
        except json.JSONDecodeError:
            return None
    if value.startswith("'"):
        return value[1:-1].replace("''", "'") if re.fullmatch(r"'(?:[^']|'')*'", value) else None
    if (not value or not (value[0].isalpha() or value[0] == "_")
            or value.lower() in {"true", "false", "null", "yes", "no", "on", "off"}
            or re.search(r":(?:\s|$)|\s#", value)):
        return None
    return value


def parse_skill(path: Path) -> tuple[dict[str, str] | None, str]:
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None, "frontmatter is not valid UTF-8"
    except OSError:
        return None, "frontmatter could not be read"
    if b"\0" in raw:
        return None, "frontmatter contains binary bytes"
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None, "frontmatter must start with ---"
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return None, "frontmatter is missing its closing ---"
    fields: dict[str, str] = {}
    for line in lines[1:end]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = re.match(r"^([A-Za-z0-9_-]+):(?:[ \t]+)?(.*)$", stripped)
        if not match or match.group(1) in fields:
            return None, "frontmatter contains an invalid or duplicate field"
        parsed = scalar(match.group(2))
        if parsed is None:
            return None, f"frontmatter field {match.group(1)!r} has an unterminated or unsupported scalar"
        fields[match.group(1)] = parsed
    if not fields.get("name") or "description" not in fields:
        return None, "frontmatter requires name and description"
    return {"name": fields["name"], "description": fields["description"], "body": "".join(lines[end + 1 :]), "raw": text}, ""


def check_references(root: Path, skill_root: Path, source: Path, text: str, errors: list[dict[str, str]]) -> None:
    targets = [(match.group(1), source.parent, False) for match in re.finditer(r"\]\(\s*<?([^) >]+)", text)]
    for match in re.finditer(r"(?<![\w./])((?:references|scripts)/[A-Za-z0-9_.~/-]+)", text):
        prefix = text[max(0, match.start() - 32) : match.start()]
        if prefix.endswith("<installed-skill-dir>/") or prefix.endswith("${SKILL_DIR}/"):
            continue
        targets.append((match.group(1).rstrip(".,;:)]`"), skill_root, True))
    checked: set[tuple[str, str]] = set()
    for raw, base, fallback in targets:
        if (raw, str(base)) in checked:
            continue
        checked.add((raw, str(base)))
        target = raw.split("#", 1)[0].split("?", 1)[0].strip()
        if not target or target.startswith(("#", "http:", "https:", "mailto:")):
            continue
        if target.startswith("/") or "\\" in target:
            add(errors, "reference_escape", relative(root, source), f"local reference {raw!r} is not portable")
            continue
        candidate = (base / target).resolve()
        if not inside(candidate, root):
            add(errors, "reference_escape", relative(root, source), f"local reference {raw!r} escapes package")
        elif not candidate.exists():
            package_candidate = (root / target).resolve()
            if not fallback or not inside(package_candidate, root) or not package_candidate.exists():
                add(errors, "reference_missing", relative(root, source), f"local reference {raw!r} is missing")


def check_skills(root: Path, errors: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    directory = root / "skills"
    if under_symlink(root, directory, errors):
        return {}
    try:
        is_directory = directory.is_dir()
    except OSError:
        add(errors, "unreadable_content", "skills", "skills directory could not be inspected")
        return {}
    if not is_directory:
        add(errors, "skills_missing", "skills", "skills directory is missing")
        return {}
    paths = []
    try:
        for path in directory.glob("*/SKILL.md"):
            try:
                is_file = path.is_file()
            except OSError:
                add(errors, "unreadable_content", relative(root, path), "skill entrypoint could not be inspected")
                continue
            if is_file and not under_symlink(root, path, errors):
                paths.append(path)
    except OSError:
        add(errors, "unreadable_content", "skills", "skills directory could not be read")
    paths.sort()
    if {path.parent.name for path in paths} != set(SKILLS) or len(paths) != len(SKILLS):
        add(errors, "skill_count", "skills", "expected exactly compound and map skill entrypoints")
    for path in directory.rglob("SKILL.md"):
        if under_symlink(root, path, errors):
            continue
        if path.parent.parent != directory:
            add(errors, "skill_layout", relative(root, path), "skill entrypoints must be immediate children of skills/")
    result: dict[str, dict[str, str]] = {}
    for path in paths:
        parsed, reason = parse_skill(path)
        if parsed is None:
            add(errors, "frontmatter", relative(root, path), reason)
            continue
        name = path.parent.name
        result[name] = parsed
        if parsed["name"] != name:
            add(errors, "skill_identity", relative(root, path), "frontmatter name must match its directory")
        if not parsed["description"]:
            add(errors, "frontmatter", relative(root, path), "skill description must not be empty")
        check_references(root, path.parent, path, parsed["body"], errors)
        for resource in sorted(path.parent.rglob("*.md")):
            if resource != path and not under_symlink(root, resource, errors):
                try:
                    check_references(root, path.parent, resource, resource.read_text(encoding="utf-8"), errors)
                except UnicodeDecodeError:
                    add(errors, "unreadable_content", relative(root, resource), "release file is not valid UTF-8")
                except OSError:
                    add(errors, "unreadable_content", relative(root, resource), "release file could not be read")
    names = [parsed["name"] for parsed in result.values()]
    if len(names) != len(set(names)):
        add(errors, "duplicate_identity", "skills", "skill frontmatter names are duplicated")
    if set(names) != set(SKILLS):
        add(errors, "skill_identity", "skills", "skill frontmatter names are incomplete")
    return result


def stats(raw: bytes) -> dict[str, int]:
    text = raw.decode("utf-8", "replace")
    return {"bytes": len(raw), "words": len(text.split())}


def file_item(root: Path, path: Path) -> dict[str, Any]:
    return {"path": relative(root, path), **stats(path.read_bytes())}


def bundle(files: list[dict[str, Any]], *, source: str | None = None, loading: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "bytes": sum(item["bytes"] for item in files),
        "words": sum(item["words"] for item in files),
        "files": files,
    }
    if source:
        result["source"] = source
    if loading:
        result["loading"] = loading
    return result


def resource_group(root: Path, path: Path) -> str:
    parts = path.relative_to(root).parts
    if path.suffix == ".py":
        return "scripts"
    if len(parts) >= 2 and parts[-2] == "agents" and path.suffix in {".yaml", ".yml"}:
        return "metadata"
    if "skills" in parts and "references" in parts:
        return "references"
    return "other"


def context(
    root: Path,
    manifests: dict[str, Any],
    marketplaces: dict[str, Any],
    skills: dict[str, dict[str, str]],
    public: list[Path],
    host_rules: list[Path],
) -> dict[str, Any]:
    metadata_paths = [root / path for path in (*manifests, *marketplaces)]
    descriptions = []
    for name, value in sorted(skills.items()):
        source = f"{name}\n{value['description']}".encode()
        descriptions.append({"name": name, "description": value["description"], **stats(source)})

    entrypoints = []
    for name, value in sorted(skills.items()):
        entrypoints.append({"skill": name, "path": f"skills/{name}/SKILL.md", **stats(value["body"].encode())})

    resources: dict[str, list[dict[str, Any]]] = {"references": [], "scripts": [], "metadata": [], "other": []}
    host_rule_items = [file_item(root, path) for path in host_rules]
    known = set(manifests) | set(marketplaces) | {item["path"] for item in entrypoints}
    known.update(item["path"] for item in host_rule_items)
    for path in public:
        path_name = relative(root, path)
        if path_name in known:
            continue
        resources[resource_group(root, path)].append(file_item(root, path))

    return {
        "measurement_note": "UTF-8 source bytes and whitespace-separated words only; conditional loading, host framing, and tokenizer costs are unknown.",
        "discovery": {
            "descriptions": {
                **bundle(
                    descriptions,
                    source="skill name and description values only",
                    loading="source_only",
                ),
                "source_only": True,
            },
            "metadata": bundle(
                [file_item(root, path) for path in metadata_paths],
                loading="host discovery metadata",
            ),
        },
        "entrypoints": bundle(entrypoints, source="SKILL.md bodies"),
        "host_rules": bundle(
            host_rule_items,
            source="Cursor compound-default.mdc",
            loading="native Cursor always-loaded rule; applies when enabled",
        ),
        "conditional_resources": {
            "references": bundle(resources["references"], loading="on demand by the selected skill"),
            "scripts": bundle(resources["scripts"], loading="executable storage; not prompt text by default"),
            "metadata": bundle(resources["metadata"], loading="host or UI metadata; loading is host/task dependent"),
            "other": bundle(resources["other"], loading="package files; loading depends on host and task"),
        },
    }


def release_text(path: Path, root: Path, errors: list[dict[str, str]]) -> str | None:
    try:
        raw = path.read_bytes()
    except OSError:
        add(errors, "unreadable_content", relative(root, path), "release file could not be read")
        return None
    if b"\0" in raw:
        add(errors, "unreadable_content", relative(root, path), "release file contains binary bytes")
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        add(errors, "unreadable_content", relative(root, path), "release file is not valid UTF-8")
        return None


def check_cursor_rule(root: Path, errors: list[dict[str, str]]) -> Path | None:
    rule = root / CURSOR_RULE_PATH
    if under_symlink(root, rule, errors):
        add(errors, "release_symlink", CURSOR_RULE_PATH, "release paths may not be symlinks")
        return None
    try:
        is_file = rule.is_file()
    except OSError:
        add(errors, "unreadable_content", CURSOR_RULE_PATH, "Cursor rule could not be inspected")
        return None
    if not is_file:
        add(errors, "cursor_rule_missing", CURSOR_RULE_PATH, "Cursor always-loaded rule is missing")
        return None
    try:
        raw = rule.read_bytes()
    except OSError:
        add(errors, "unreadable_content", CURSOR_RULE_PATH, "Cursor rule could not be read")
        return rule
    if b"\0" in raw:
        add(errors, "unreadable_content", CURSOR_RULE_PATH, "Cursor rule contains binary bytes")
        return rule
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        add(errors, "unreadable_content", CURSOR_RULE_PATH, "Cursor rule is not valid UTF-8")
        return rule
    lines = text.splitlines()
    end = next((index for index in range(1, len(lines)) if lines[index].strip() == "---"), None)
    valid = bool(lines and lines[0].strip() == "---" and end is not None)
    always_apply = False
    if valid:
        for line in lines[1:end]:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            match = re.match(r"^([A-Za-z0-9_-]+):[ \t]*(.*)$", stripped)
            if not match or not match.group(2).strip():
                valid = False
                break
            if match.group(1) == "alwaysApply":
                if always_apply or match.group(2).strip() != "true":
                    valid = False
                    break
                always_apply = True
    if not valid or not always_apply:
        add(errors, "cursor_rule_frontmatter", CURSOR_RULE_PATH, "Cursor rule frontmatter must declare alwaysApply: true")
    return rule


def check_index_worktree(root: Path, errors: list[dict[str, str]]) -> None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "diff", "--name-only", "-z", "--"],
            check=False,
            capture_output=True,
        )
    except OSError:
        return
    if result.returncode != 0:
        return
    for raw_path in result.stdout.split(b"\0"):
        if raw_path:
            path = raw_path.decode("utf-8", "surrogateescape")
            add(errors, "index_mismatch", path, "tracked release content differs between index and worktree")


def check_package(root: Path) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    try:
        root = root.resolve()
    except OSError:
        add(errors, "unreadable_content", ".", "package root could not be resolved")
    public: list[Path] = []
    manifests: dict[str, Any] = {}
    marketplaces: dict[str, Any] = {}
    skills: dict[str, dict[str, str]] = {}
    host_rules: list[Path] = []
    readable: list[Path] = []
    try:
        try:
            root_is_directory = root.is_dir()
        except OSError:
            add(errors, "unreadable_content", ".", "package root could not be inspected")
            root_is_directory = False
        public = public_files(root, errors) if root_is_directory else []
        symlinks = [path for path in public if under_symlink(root, path, errors)]
        for path in symlinks:
            add(errors, "release_symlink", relative(root, path), "release paths may not be symlinks")
        scannable = [path for path in public if not under_symlink(root, path, errors)]
        check_index_worktree(root, errors)
        manifests = {path: value for path, kind in MANIFESTS.items() if (value := check_manifest(root, path, kind, errors)) is not None}
        cursor_manifest = manifests.get(".cursor-plugin/plugin.json")
        if isinstance(cursor_manifest, dict) and "rules" in cursor_manifest:
            if rule := check_cursor_rule(root, errors):
                if rule in public:
                    host_rules.append(rule)
                else:
                    add(errors, "release_inventory", CURSOR_RULE_PATH, "declared Cursor rule is not in release inventory")
        marketplaces = {path: value for path, kind in MARKETPLACES.items() if (value := check_marketplace(root, path, kind, errors)) is not None}
        skills = check_skills(root, errors) if root_is_directory else {}
        for path in scannable:
            path_name = relative(root, path)
            if path_name.startswith(("tests/", "test/")):
                add(errors, "public_development_file", path_name, "tests must remain ignored and outside the public package")
            text = release_text(path, root, errors)
            if text is None:
                continue
            readable.append(path)
            for kind, pattern in PRIVATE_PATTERNS:
                if pattern.search(text):
                    add(errors, "sensitive_content", path_name, f"detected {kind} pattern")
            if path.suffix == ".md" and "skills" not in path.relative_to(root).parts:
                check_references(root, root, path, text, errors)
    except OSError:
        add(errors, "unreadable_content", ".", "package could not be fully inspected")
    try:
        measured_context = context(root, manifests, marketplaces, skills, readable, host_rules)
    except OSError:
        add(errors, "unreadable_content", ".", "package measurements could not be read")
        measured_context = context(root, {}, {}, {}, [], [])
    return {
        "status": "pass" if not errors else "fail",
        "root": str(root),
        "package": {"name": NAME, "version": VERSION},
        "manifests": sorted(manifests),
        "marketplaces": sorted(marketplaces),
        "skills": sorted(skills),
        "public_files": [relative(root, path) for path in public],
        "errors": errors,
        "warnings": [],
        "context": measured_context,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate compound-skills manifests, skills, references, and public-content hygiene.")
    parser.add_argument("root", nargs="?", default=".", help="package root (default: current directory)")
    parser.add_argument("--json", action="store_true", help="emit one machine-readable JSON report")
    args = parser.parse_args(argv)
    result = check_package(Path(args.root))
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['status'].upper()}: {result['root']}")
        for item in result["errors"]:
            print(f"ERROR {item['code']} [{item['path']}]: {item['message']}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
