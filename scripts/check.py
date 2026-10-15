#!/usr/bin/env python3
"""Read-only checks for the compound-skills package."""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from pathlib import Path
from typing import Any


NAME = "compound-skills"
VERSION = "0.1.0"
AUTHOR = "tobenwarrior"
REPOSITORY = "https://github.com/tobenwarrior/compound-skills"
SKILLS = ("compound", "compound-integrate")
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
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def public_files(root: Path) -> list[Path]:
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
            return sorted(
                (path for path in paths if path.is_file() and not path.is_symlink()),
                key=lambda path: relative(root, path),
            )
    except OSError:
        pass

    ignored = {".git", ".pytest_cache", "__pycache__", ".mypy_cache", ".ruff_cache", "tests", "test"}
    return sorted(
        (
            path
            for path in root.rglob("*")
            if path.is_file()
            and not path.is_symlink()
            and not any(part in ignored for part in path.relative_to(root).parts)
        ),
        key=lambda path: relative(root, path),
    )


def read_json(root: Path, path: str, label: str, errors: list[dict[str, str]]) -> dict[str, Any] | None:
    file = root / path
    if not file.is_file():
        add(errors, f"{label}_missing", path, f"{label} file is missing")
        return None
    try:
        value = json.loads(file.read_text(encoding="utf-8"))
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


def check_path(root: Path, value: Any, origin: str, field: str, errors: list[dict[str, str]]) -> None:
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
    target = (root / value).resolve()
    if not inside(target, root):
        add(errors, "path_escape", origin, f"{field} resolves outside the package")
    elif not target.exists():
        add(errors, "path_missing", origin, f"{field} does not resolve to a package path")


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
                check_path(root, source.get("path"), origin, "source.path", errors)
        elif isinstance(source, str):
            check_path(root, source, origin, "source", errors)
        else:
            add(errors, "marketplace_source", origin, "marketplace source must be a relative path")
        if "version" in entry and entry["version"] != VERSION:
            add(errors, "identity_mismatch", origin, f"version must be {VERSION!r}")
    return value


def scalar(value: str) -> str:
    value = value.strip()
    if len(value) > 1 and value[0] == value[-1] and value[0] in {'"', "'"}:
        try:
            parsed = ast.literal_eval(value)
            return parsed if isinstance(parsed, str) else value[1:-1]
        except (SyntaxError, ValueError):
            return value[1:-1]
    return value


def parse_skill(path: Path) -> dict[str, str] | None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return None
    fields: dict[str, str] = {}
    for line in lines[1:end]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = re.match(r"^([A-Za-z0-9_-]+):(?:[ \t]+)?(.*)$", stripped)
        if not match or match.group(1) in fields:
            return None
        fields[match.group(1)] = scalar(match.group(2))
    if not fields.get("name") or "description" not in fields:
        return None
    return {"name": fields["name"], "description": fields["description"], "body": "".join(lines[end + 1 :]), "raw": text}


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
    if not directory.is_dir():
        add(errors, "skills_missing", "skills", "skills directory is missing")
        return {}
    paths = sorted(path for path in directory.glob("*/SKILL.md") if path.is_file())
    if {path.parent.name for path in paths} != set(SKILLS) or len(paths) != len(SKILLS):
        add(errors, "skill_count", "skills", "expected exactly two skill entrypoints")
    for path in directory.rglob("SKILL.md"):
        if path.parent.parent != directory:
            add(errors, "skill_layout", relative(root, path), "skill entrypoints must be immediate children of skills/")
    result: dict[str, dict[str, str]] = {}
    for path in paths:
        parsed = parse_skill(path)
        if parsed is None:
            add(errors, "frontmatter", relative(root, path), "skill frontmatter is malformed")
            continue
        name = path.parent.name
        result[name] = parsed
        if parsed["name"] != name:
            add(errors, "skill_identity", relative(root, path), "frontmatter name must match its directory")
        if not parsed["description"]:
            add(errors, "frontmatter", relative(root, path), "skill description must not be empty")
        check_references(root, path.parent, path, parsed["body"], errors)
        for resource in sorted(path.parent.rglob("*.md")):
            if resource != path:
                try:
                    check_references(root, path.parent, resource, resource.read_text(encoding="utf-8"), errors)
                except (OSError, UnicodeDecodeError):
                    pass
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


def context(root: Path, manifests: dict[str, Any], marketplaces: dict[str, Any], skills: dict[str, dict[str, str]], public: list[Path]) -> dict[str, Any]:
    metadata_paths = [root / path for path in (*manifests, *marketplaces) if (root / path).is_file()]
    descriptions = []
    for name, value in sorted(skills.items()):
        source = f"{name}\n{value['description']}".encode()
        descriptions.append({"name": name, "description": value["description"], **stats(source)})

    entrypoints = []
    for name, value in sorted(skills.items()):
        entrypoints.append({"skill": name, "path": f"skills/{name}/SKILL.md", **stats(value["body"].encode())})

    resources: dict[str, list[dict[str, Any]]] = {"references": [], "scripts": [], "metadata": [], "other": []}
    known = set(manifests) | set(marketplaces) | {item["path"] for item in entrypoints}
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
        "conditional_resources": {
            "references": bundle(resources["references"], loading="on demand by the selected skill"),
            "scripts": bundle(resources["scripts"], loading="executable storage; not prompt text by default"),
            "metadata": bundle(resources["metadata"], loading="host or UI metadata; not prompt text"),
            "other": bundle(resources["other"], loading="storage only"),
        },
    }


def check_package(root: Path) -> dict[str, Any]:
    root = root.resolve()
    errors: list[dict[str, str]] = []
    public = public_files(root) if root.is_dir() else []
    manifests = {path: value for path, kind in MANIFESTS.items() if (value := check_manifest(root, path, kind, errors)) is not None}
    marketplaces = {path: value for path, kind in MARKETPLACES.items() if (value := check_marketplace(root, path, kind, errors)) is not None}
    skills = check_skills(root, errors) if root.is_dir() else {}
    for path in public:
        path_name = relative(root, path)
        if path_name.startswith(("tests/", "test/")):
            add(errors, "public_development_file", path_name, "tests must remain ignored and outside the public package")
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for kind, pattern in PRIVATE_PATTERNS:
            if pattern.search(text):
                add(errors, "sensitive_content", path_name, f"detected {kind} pattern")
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
        "context": context(root, manifests, marketplaces, skills, public),
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
