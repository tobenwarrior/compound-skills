#!/usr/bin/env python3
"""Enable or inspect the bounded Compound Skills project routing block.

The helper edits project-local instruction files only.  It never installs a
skill, reads credentials, changes host settings, or edits an ancestor file.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


START_MARKER = "<!-- compound-skills:project-setup:start -->"
END_MARKER = "<!-- compound-skills:project-setup:end -->"
MARKER_NAMESPACE = "compound-skills:project-setup:"
STATUS_SCOPE = "enabled under default project instruction settings"

BLOCK_LINES = (
    START_MARKER,
    "## Compound Skills default routing",
    "",
    "For engineering tasks, use the installed Compound Skills `compound` skill by default; "
    "load only the references relevant to the task. Respect project-specific guidance and "
    "the user's scope. If the installed skill is missing, report that and follow the "
    "project's conventions.",
    END_MARKER,
)


class SetupError(ValueError):
    """A project setup input cannot be safely processed."""


class UsageError(ValueError):
    """CLI arguments are invalid but can still be reported as JSON."""


class ApplyError(SetupError):
    """A planned write failed after zero or more atomic replacements."""

    def __init__(self, message: str, changed_paths: Sequence[str]) -> None:
        super().__init__(message)
        self.changed_paths = tuple(changed_paths)


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise UsageError(message)


@dataclass(frozen=True)
class MarkerRange:
    start: int
    end: int
    has_trailing_newline: bool


@dataclass(frozen=True)
class TargetState:
    name: str
    path: Path
    text: str | None
    markers: MarkerRange | None

    @property
    def exists(self) -> bool:
        return self.text is not None


@dataclass(frozen=True)
class Context:
    root: Path
    primary: TargetState
    override: TargetState
    fallback: TargetState
    legacy_shadows: tuple[Path, ...]
    warnings: tuple[str, ...]


def _newline(text: str) -> str:
    if "\r\n" in text:
        return "\r\n"
    if "\n" in text:
        return "\n"
    if "\r" in text:
        return "\r"
    return "\n"


def _has_line_ending(text: str) -> bool:
    return text.endswith(("\r\n", "\n", "\r"))


def _marker_lines(text: str, marker: str) -> list[tuple[int, int, str]]:
    matches: list[tuple[int, int, str]] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        if content.strip() == marker:
            matches.append((offset, offset + len(line), line))
        offset += len(line)
    if offset < len(text):  # splitlines() only omits this for an empty string
        content = text[offset:].rstrip("\r\n")
        if content.strip() == marker:
            matches.append((offset, len(text), text[offset:]))
    return matches


def _parse_markers(text: str) -> MarkerRange | None:
    start_lines = _marker_lines(text, START_MARKER)
    end_lines = _marker_lines(text, END_MARKER)
    start_count = text.count(START_MARKER)
    end_count = text.count(END_MARKER)

    if start_count != len(start_lines) or end_count != len(end_lines):
        raise SetupError("managed markers must each occupy their own line")
    if not start_lines and not end_lines:
        if MARKER_NAMESPACE in text:
            raise SetupError("managed marker text is malformed")
        return None
    if len(start_lines) > 1 or len(end_lines) > 1:
        raise SetupError("managed markers are duplicated")
    if len(start_lines) != 1 or len(end_lines) != 1:
        raise SetupError("managed markers are incomplete")

    start, _, _ = start_lines[0]
    end, end_after, end_line = end_lines[0]
    if start >= end:
        raise SetupError("managed markers are out of order")
    return MarkerRange(
        start=start,
        end=end_after,
        has_trailing_newline=_has_line_ending(end_line),
    )


def _read_target(name: str, path: Path) -> TargetState:
    try:
        if path.is_symlink():
            raise SetupError(f"refusing symlink instruction target: {path}")
        if not path.exists():
            return TargetState(name, path, None, None)
        if not path.is_file():
            raise SetupError(f"instruction target is not a regular file: {path}")
        raw = path.read_bytes()
    except OSError as exc:
        raise SetupError(f"could not inspect instruction target {path}: {exc}") from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SetupError(f"instruction target is not UTF-8: {path}") from exc
    return TargetState(name, path, text, _parse_markers(text))


def _validate_fallback_ancestors(root: Path) -> None:
    claude = root / ".claude"
    rules = claude / "rules"
    for path in (claude, rules):
        try:
            if path.is_symlink():
                raise SetupError(f"refusing symlink fallback directory: {path}")
            if path.exists() and not path.is_dir():
                raise SetupError(f"fallback parent is not a directory: {path}")
        except OSError as exc:
            raise SetupError(f"could not inspect fallback directory {path}: {exc}") from exc


def _legacy_shadow_files(root: Path) -> tuple[Path, ...]:
    found: list[Path] = []
    ancestor = root
    user_claude_memory = Path.home() / ".claude" / "CLAUDE.md"
    while True:
        for relative in ("CLAUDE.md", ".claude/CLAUDE.md", "CLAUDE.local.md"):
            candidate = ancestor / relative
            if candidate == user_claude_memory:
                continue
            try:
                if candidate.is_file():
                    found.append(candidate)
            except OSError as exc:
                raise SetupError(f"could not inspect legacy instruction file {candidate}: {exc}") from exc
        parent = ancestor.parent
        if parent == ancestor:
            break
        ancestor = parent
    return tuple(found)


def _warning_list(
    override: TargetState,
    fallback: TargetState,
    shadows: Iterable[Path],
) -> list[str]:
    warnings: list[str] = []
    if override.exists and override.text and override.text.strip() and override.markers is None:
        warnings.append(f"AGENTS.override.md may shadow AGENTS.md without managed routing: {override.path}")
    if shadows and fallback.markers is None:
        for path in shadows:
            warnings.append(f"Claude instruction may shadow AGENTS.md without managed fallback: {path}")
    if fallback.exists and fallback.markers is None:
        warnings.append(f"Claude fallback contains unmanaged content and was left unchanged: {fallback.path}")
    if fallback.exists and not shadows and fallback.markers is not None:
        warnings.append(f"Managed Claude fallback has no current legacy shadow: {fallback.path}")
    return warnings


def _load_context(root: Path) -> Context:
    _validate_fallback_ancestors(root)
    primary_path = root / "AGENTS.md"
    override_path = root / "AGENTS.override.md"
    fallback_path = root / ".claude" / "rules" / "compound.md"

    # Read every candidate before validating any marker or planning a write.
    primary = _read_target("AGENTS.md", primary_path)
    override = _read_target("AGENTS.override.md", override_path)
    fallback = _read_target(".claude/rules/compound.md", fallback_path)
    shadows = _legacy_shadow_files(root)

    warnings = _warning_list(override, fallback, shadows)
    return Context(root, primary, override, fallback, shadows, tuple(warnings))


def _canonical_block(newline: str, trailing: bool) -> str:
    block = newline.join(BLOCK_LINES)
    return block + (newline if trailing else "")


def _append_block(text: str, newline: str) -> str:
    if not text:
        return _canonical_block(newline, False)
    if _has_line_ending(text):
        return text + _canonical_block(newline, True)
    return text + newline + _canonical_block(newline, False)


def _replace_block(text: str, markers: MarkerRange) -> str:
    newline = _newline(text)
    return text[: markers.start] + _canonical_block(newline, markers.has_trailing_newline) + text[markers.end :]


def _remove_block(text: str, markers: MarkerRange) -> str:
    before = text[: markers.start]
    after = text[markers.end :]
    result = before + after
    if not markers.has_trailing_newline and not after and before:
        newline = _newline(before)
        canonical = _canonical_block(newline, False)
        if before.endswith(newline) and text[markers.start : markers.end] == canonical:
            # Enable inserts this separator when the original file had no
            # final newline; remove that separator during the exact round trip.
            result = before[: -len(newline)]
    return result


def _preferred_newline(context: Context) -> str:
    for state in (context.primary, context.override, context.fallback):
        if state.text:
            return _newline(state.text)
    return "\n"


def _planned_enable(context: Context) -> list[tuple[TargetState, str, bool]]:
    preferred = _preferred_newline(context)
    plans: list[tuple[TargetState, str, bool]] = []

    for state in (context.primary, context.override):
        if not state.exists and state is context.override:
            continue
        text = state.text or ""
        if state is context.override and not text.strip() and state.markers is None:
            continue
        new_text = _replace_block(text, state.markers) if state.markers else _append_block(text, preferred)
        if new_text != text:
            plans.append((state, new_text, False))

    if context.legacy_shadows:
        fallback = context.fallback
        if fallback.exists:
            if fallback.markers is None:
                raise SetupError(f"refusing to overwrite unmanaged Claude fallback: {fallback.path}")
            new_text = _replace_block(fallback.text or "", fallback.markers)
        else:
            new_text = _canonical_block(preferred, False)
        if new_text != (fallback.text or ""):
            plans.append((fallback, new_text, False))
    return plans


def _planned_disable(context: Context) -> list[tuple[TargetState, str, bool]]:
    plans: list[tuple[TargetState, str, bool]] = []
    for state in (context.primary, context.override, context.fallback):
        if not state.exists or state.markers is None:
            continue
        new_text = _remove_block(state.text or "", state.markers)
        remove_file = state is context.fallback and new_text == ""
        if remove_file or new_text != (state.text or ""):
            plans.append((state, new_text, remove_file))
    return plans


@dataclass
class StagedPlan:
    state: TargetState
    text: str
    remove_file: bool
    temporary: Path | None = None


def _stage(plans: Iterable[tuple[TargetState, str, bool]]) -> list[StagedPlan]:
    staged: list[StagedPlan] = []
    try:
        for state, text, remove_file in plans:
            item = StagedPlan(state, text, remove_file)
            if not remove_file:
                state.path.parent.mkdir(parents=True, exist_ok=True)
                descriptor, temporary = tempfile.mkstemp(
                    prefix=f".{state.path.name}.compound-setup-",
                    dir=state.path.parent,
                )
                item.temporary = Path(temporary)
                staged.append(item)
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(text.encode("utf-8"))
                    handle.flush()
                    os.fsync(handle.fileno())
                if state.exists:
                    mode = stat.S_IMODE(state.path.stat().st_mode)
                else:
                    mode = 0o644
                os.chmod(item.temporary, mode)
            else:
                staged.append(item)
    except OSError as exc:
        _cleanup_staged(staged)
        raise SetupError(f"could not stage project setup writes: {exc}") from exc
    return staged


def _cleanup_staged(staged: Iterable[StagedPlan]) -> None:
    for item in staged:
        if item.temporary is None:
            continue
        try:
            item.temporary.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass
        item.temporary = None


def _apply(plans: Iterable[tuple[TargetState, str, bool]]) -> tuple[bool, tuple[str, ...]]:
    staged = _stage(plans)
    changed_paths: list[str] = []
    try:
        # Replace all staged files before deleting a managed fallback file.
        for item in staged:
            if item.remove_file:
                continue
            assert item.temporary is not None
            try:
                os.replace(item.temporary, item.state.path)
            except OSError as exc:
                raise ApplyError(f"could not atomically update {item.state.path}: {exc}", changed_paths) from exc
            item.temporary = None
            changed_paths.append(str(item.state.path))
        for item in staged:
            if not item.remove_file:
                continue
            try:
                item.state.path.unlink()
            except OSError as exc:
                raise ApplyError(f"could not remove {item.state.path}: {exc}", changed_paths) from exc
            changed_paths.append(str(item.state.path))
    finally:
        _cleanup_staged(staged)
    return bool(changed_paths), tuple(changed_paths)


def _status_name(context: Context) -> str:
    primary_managed = context.primary.markers is not None
    override_managed = (
        not context.override.exists
        or not (context.override.text or "").strip()
        or context.override.markers is not None
    )
    fallback_managed = not context.legacy_shadows or context.fallback.markers is not None
    any_managed = any(
        state.markers is not None for state in (context.primary, context.override, context.fallback)
    )
    if primary_managed and override_managed and fallback_managed:
        base = "enabled"
    elif any_managed:
        base = "partial"
    else:
        base = "disabled"
    return base + "-with-warnings" if context.warnings else base


def _payload(
    action: str,
    status: str,
    changed: bool,
    path: Path | None,
    warnings: Sequence[str],
    *,
    error: str | None = None,
    changed_paths: Sequence[str] = (),
) -> dict[str, object]:
    value: dict[str, object] = {
        "action": action,
        "status": status,
        "changed": changed,
        "path": str(path) if path is not None else "",
        "warnings": list(warnings),
        "scope": STATUS_SCOPE,
    }
    if error is not None:
        value["error"] = error
    if changed_paths:
        value["changed_paths"] = list(changed_paths)
    return value


def _emit(value: dict[str, object]) -> int:
    print(json.dumps(value, ensure_ascii=False))
    return 0 if value["status"] != "error" else 2


def _resolve_root(raw: str) -> Path:
    lexical = Path(raw)
    if not lexical.is_absolute():
        lexical = Path.cwd() / lexical
    try:
        if lexical.is_symlink():
            raise SetupError(f"project root may not be a symlink: {lexical}")
        root = lexical.resolve(strict=True)
    except SetupError:
        raise
    except OSError as exc:
        raise SetupError(f"could not resolve project root {lexical}: {exc}") from exc
    if not root.is_dir():
        raise SetupError(f"project root is not a directory: {root}")
    return root


def _parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(
        description="Enable, inspect, or disable the project-local Compound Skills routing block."
    )
    parser.add_argument("action", nargs="?", help="enable, status, or disable")
    parser.add_argument("--project-root", metavar="PATH", help="required project root")
    return parser


def _action_hint(argv: Sequence[str] | None) -> str:
    if not argv:
        return ""
    for value in argv:
        if not value.startswith("-"):
            return value
    return ""


def main(argv: Sequence[str] | None = None) -> int:
    argv_list = list(sys.argv[1:] if argv is None else argv)
    try:
        args = _parser().parse_args(argv_list)
    except (UsageError, SystemExit) as exc:
        if isinstance(exc, SystemExit):
            raise
        return _emit(_payload(_action_hint(argv_list), "error", False, None, [], error=str(exc)))

    action = args.action or ""
    if action not in {"enable", "status", "disable"}:
        return _emit(_payload(action, "error", False, None, [], error="action must be enable, status, or disable"))
    if not args.project_root:
        return _emit(_payload(action, "error", False, None, [], error="--project-root is required"))

    try:
        root = _resolve_root(args.project_root)
        context = _load_context(root)
        path = context.primary.path
        if action == "status":
            return _emit(_payload(action, _status_name(context), False, path, context.warnings))
        plans = _planned_enable(context) if action == "enable" else _planned_disable(context)
        changed, changed_paths = _apply(plans)
        after = _load_context(root)
        return _emit(
            _payload(
                action,
                _status_name(after),
                changed,
                path,
                after.warnings,
                changed_paths=changed_paths,
            )
        )
    except ApplyError as exc:
        return _emit(
            _payload(
                action,
                "error",
                bool(exc.changed_paths),
                context.primary.path if "context" in locals() else None,
                context.warnings if "context" in locals() else (),
                error=str(exc),
                changed_paths=exc.changed_paths,
            )
        )
    except SetupError as exc:
        return _emit(_payload(action, "error", False, None, [], error=str(exc)))


if __name__ == "__main__":
    raise SystemExit(main())
