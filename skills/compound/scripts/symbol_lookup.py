#!/usr/bin/env python3
"""Bounded, read-only exact symbol and lexical occurrence lookup for Compound.

Definitions come only from the existing code-map symbol metadata. Occurrences are
plain lexical identifier-boundary matches; they are not semantic references and
may include declarations, comments, and string literals. No source text is
returned.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import stat
import sys
import time
from pathlib import Path
from typing import Any

try:
    from . import code_map
    from .safe_open import open_regular_nofollow as _open_regular_nofollow
    from .reference_cache import SIGIL_SUFFIXES, IdentifierPostingsCache, UnsupportedSymbolError
    from .language_outlines import split_lines
except ImportError:  # direct script execution
    import code_map
    from language_outlines import split_lines
    from safe_open import open_regular_nofollow as _open_regular_nofollow
    from reference_cache import SIGIL_SUFFIXES, IdentifierPostingsCache, UnsupportedSymbolError

DEFAULT_MAX_FILES = 1000
MAX_FILES = 5000
DEFAULT_MAX_RESULTS = 100
MAX_RESULTS = 1000
DEFAULT_TIMEOUT = 3.0
MAX_TIMEOUT = 15.0
DEFAULT_MAX_FILE_BYTES = 256 * 1024
MAX_FILE_BYTES = 1024 * 1024
DEFAULT_MAX_TOTAL_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024
DEFAULT_MAX_OUTPUT_BYTES = 12 * 1024
MIN_OUTPUT_BYTES = 4 * 1024
MAX_OUTPUT_BYTES = 64 * 1024
READ_CHUNK_BYTES = 64 * 1024

# These are data/config formats, not source languages for the lexical scan.
_NON_SOURCE_LANGUAGES = {"config", "json", "yaml", "toml", "xml", "ini", "properties"}


class SymbolLookupError(ValueError):
    """Invalid symbol lookup request or unavailable repository."""


def _bounded_int(value: int, low: int, high: int) -> int:
    return max(low, min(high, int(value)))


def _bounded_timeout(value: float) -> float:
    timeout = float(value)
    if not math.isfinite(timeout):
        raise SymbolLookupError("timeout must be a finite number")
    return max(0.05, min(timeout, MAX_TIMEOUT))


def _valid_symbol(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 256:
        raise SymbolLookupError("symbol must be a non-empty name of at most 256 characters")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise SymbolLookupError("symbol must not contain control characters")
    return value


def _identifier_pattern(symbol: str, sigils: bool = False) -> re.Pattern[str]:
    # `$` is a valid identifier character in JS/TS but a sigil before shell and PHP
    # names; `\w` covers Unicode letters and underscores. Boundaries avoid
    # reporting `needle` inside `needle_more`.
    return re.compile((r"(?<!\w)" if sigils else r"(?<![\w$])") + re.escape(symbol) + r"(?![\w$])")





def _read_reference_text(
    root: Path,
    relative: str,
    fingerprint: dict[str, int],
    *,
    max_file_bytes: int,
    remaining_bytes: int,
    deadline: float,
) -> tuple[str | None, int, str | None]:
    """Read one checked source file, returning text only to the scanner."""
    path = root / relative
    if fingerprint["size"] > max_file_bytes:
        return None, 0, "file byte cap reached"
    if fingerprint["size"] > remaining_bytes:
        return None, 0, "total reference byte cap reached"
    try:
        file_fd = _open_regular_nofollow(root, relative)
        with os.fdopen(file_fd, "rb") as source:
            opened = os.fstat(source.fileno())
            if not stat.S_ISREG(opened.st_mode) or (
                opened.st_size, opened.st_ino, opened.st_mtime_ns, opened.st_ctime_ns
              ) != (
                fingerprint["size"], fingerprint["inode"],
                fingerprint["mtime_ns"], fingerprint["ctime_ns"],
              ):
                return None, 0, "file changed before reference scan"
            chunks: list[bytes] = []
            total = 0
            while total < opened.st_size:
                if time.monotonic() >= deadline:
                    return None, total, "reference scan timed out"
                block = source.read(min(READ_CHUNK_BYTES, opened.st_size - total))
                if not block:
                    return None, total, "file changed during reference scan"
                chunks.append(block)
                total += len(block)
            after_open = os.fstat(source.fileno())
            if (
                after_open.st_size, after_open.st_ino,
                  after_open.st_mtime_ns, after_open.st_ctime_ns,
            ) != (
                opened.st_size, opened.st_ino,
                opened.st_mtime_ns, opened.st_ctime_ns,
            ) or code_map._fingerprint(path) != fingerprint:
                return None, total, "file changed during reference scan"
    except (OSError, ValueError):
        return None, 0, "unsafe or unreadable files were skipped"

    data = b"".join(chunks)
    if b"\0" in data:
        return None, total, "binary files were skipped"
    try:
        return data.decode("utf-8-sig"), total, None
    except UnicodeDecodeError:
        return None, total, "non-UTF-8 files were skipped"


def _budget_exempt(git_root: Path, path: str) -> bool:
    """Whether _build excludes this inventory path, so it needs no file-budget slot."""
    if code_map._private(path) or code_map._skip_dir(path, git_inventory=True):
        return True
    absolute = git_root / path
    try:
        if code_map._has_symlink_ancestor(absolute, git_root) or not stat.S_ISREG(absolute.lstat().st_mode):
            return True  # symlinks, submodules and other non-regular paths
    except OSError:
        return False  # _build reports a missing tracked file as skipped, so it keeps its slot
    return code_map._language(path) is None and code_map._non_code_path(path)


def _coverage_partial(model_coverage: dict[str, Any]) -> bool:
    return bool(
        model_coverage.get("truncated")
        or model_coverage.get("skipped")
        or model_coverage.get("limited")
        or model_coverage.get("pending")
        or model_coverage.get("excluded_source")
        or not model_coverage.get("inventory")
    )


def _serialized_size(result: dict[str, Any]) -> int:
    """Measure JSON including a stable, exact coverage byte count."""
    output = result["coverage"]["output"]
    output["bytes"] = 0
    for _ in range(4):
        size = len(json.dumps(result, ensure_ascii=True, separators=(",", ":")).encode("utf-8"))
        if output["bytes"] == size:
            return size
        output["bytes"] = size
    return len(json.dumps(result, ensure_ascii=True, separators=(",", ":")).encode("utf-8"))


def _fit_output(result: dict[str, Any], byte_limit: int) -> dict[str, Any]:
    """Fit JSON by binary-searching whole result prefixes; never alter paths."""
    coverage = result["coverage"]
    output = {"max_bytes": byte_limit, "bytes": 0, "truncated": False}
    coverage["output"] = output
    if _serialized_size(result) <= byte_limit:
        return result

    original_references = list(result["references"])
    original_definitions = list(result["definitions"])
    output["truncated"] = True
    coverage["partial"] = True

    def candidate(ref_count: int, def_count: int, *, trim_refs: bool, trim_defs: bool) -> dict[str, Any]:
        value = dict(result)
        value["references"] = original_references[:ref_count]
        value["definitions"] = original_definitions[:def_count]
        value_coverage = dict(coverage)
        value["coverage"] = value_coverage
        value_coverage["output"] = dict(output)
        value_coverage["references"] = dict(coverage["references"])
        value_coverage["definitions"] = dict(coverage["definitions"])
        value_coverage["partial"] = True
        if trim_refs:
            value_coverage["references"]["complete"] = False
            value_coverage["references"]["results_truncated"] = True
        if trim_defs:
            value_coverage["definitions"]["model_complete"] = False
            value_coverage["definitions"]["results_truncated"] = True
        _serialized_size(value)
        return value

    def largest_prefix(
        upper: int, *, trim_refs: bool, trim_defs: bool, ref_count: int, def_count: int
    ) -> tuple[int, dict[str, Any] | None]:
        low, high, best = 0, upper, -1
        best_value = None
        while low <= high:
            middle = (low + high) // 2
            candidate_ref_count = middle if trim_refs else ref_count
            candidate_def_count = middle if trim_defs else def_count
            value = candidate(
                candidate_ref_count,
                candidate_def_count,
                trim_refs=trim_refs,
                trim_defs=trim_defs,
            )
            if value["coverage"]["output"]["bytes"] <= byte_limit:
                best = middle
                best_value = value
                low = middle + 1
            else:
                high = middle - 1
        return best, best_value

    current: dict[str, Any]
    if original_references:
        # Search only prefixes shorter than the full list, keeping the truncation
        # flags constant throughout the binary search.
        _, current = largest_prefix(
            len(original_references) - 1,
            trim_refs=True,
            trim_defs=False,
            ref_count=len(original_references),
            def_count=len(original_definitions),
        )
        if current is not None:
            return current
        current = candidate(0, len(original_definitions), trim_refs=True, trim_defs=False)
    else:
        current = candidate(0, len(original_definitions), trim_refs=False, trim_defs=False)

    if current["coverage"]["output"]["bytes"] > byte_limit and original_definitions:
        _, definitions_value = largest_prefix(
            len(original_definitions) - 1,
            trim_refs=bool(original_references),
            trim_defs=True,
            ref_count=0,
            def_count=len(original_definitions),
        )
        if definitions_value is not None:
            return definitions_value
        current = candidate(0, 0, trim_refs=bool(original_references), trim_defs=True)

    while current["coverage"]["output"]["bytes"] > byte_limit:
        ref_notes = current["coverage"]["references"].get("notes", [])
        model_notes = current["coverage"]["definitions"]["model"].get("notes", [])
        if ref_notes:
            current["coverage"]["references"]["notes"] = ref_notes[:-1]
        elif model_notes:
            current["coverage"]["definitions"]["model"]["notes"] = model_notes[:-1]
        else:
            break
        _serialized_size(current)
    if current["coverage"]["output"]["bytes"] > byte_limit:
        compact_coverage = current["coverage"]
        compact_coverage["definitions"].pop("limitations", None)
        compact_coverage["definitions"].pop("analysis_counts", None)
        compact_coverage["definitions"]["model"].pop("notes", None)
        compact_coverage["references"].pop("notes", None)
        compact_coverage["semantics"] = {
            "definitions": "exact code-map name matches; recall is partial",
            "references": "lexical occurrences, not semantic",
        }
        compact_coverage["limits"]["model_timeout"] = "outside reference timeout"
        _serialized_size(current)
    if current["coverage"]["output"]["bytes"] > byte_limit:
        raise SymbolLookupError("fixed lookup metadata exceeds the output byte cap")
    return current


def lookup_symbols(
    repo: str | os.PathLike[str],
    symbol: str,
    *,
    max_files: int = DEFAULT_MAX_FILES,
    max_results: int = DEFAULT_MAX_RESULTS,
    max_seconds: float = DEFAULT_TIMEOUT,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
    no_cache: bool = False,
    reference_cache: IdentifierPostingsCache | None = None,
) -> dict[str, Any]:
    """Return exact code-map definitions and bounded lexical occurrence locations.

    The default reads, but never writes, the existing code-map cache. Set
    ``no_cache=True`` to bypass it entirely. ``max_seconds`` is a deadline for
    the reference scan only; code-map model/cache initialization happens before
    that phase and follows code_map's own bounded Git/file/read limits.
    """
    name = _valid_symbol(symbol)
    file_limit = _bounded_int(max_files, 1, MAX_FILES)
    result_limit = _bounded_int(max_results, 1, MAX_RESULTS)
    file_byte_limit = _bounded_int(max_file_bytes, 1, MAX_FILE_BYTES)
    total_byte_limit = _bounded_int(max_total_bytes, 1, MAX_TOTAL_BYTES)
    output_byte_limit = _bounded_int(max_output_bytes, MIN_OUTPUT_BYTES, MAX_OUTPUT_BYTES)
    timeout = _bounded_timeout(max_seconds)
    patterns = (_identifier_pattern(name), _identifier_pattern(name, sigils=True))

    try:
        root = code_map._repo_path(repo)
        # Reuse the existing, Git-ignore-aware inventory to locate the canonical
        # worktree root. No non-Git filesystem walk is attempted.
        git_root, head, inventory, inventory_notes = code_map._git_context(root)
        excluded = dropped = 0
        # _build never reads source files with private names or in vendored folders.
        unscanned_source = sum(
            1 for path in inventory
            if code_map._language(path) not in _NON_SOURCE_LANGUAGES | {None}
            and (code_map._private(path) or code_map._skip_dir(path, git_inventory=True))
        )
        if len(inventory) > file_limit:
            normalized_name = "".join(character for character in name.casefold() if character.isalnum())
            preferred: list[str] = []
            remaining: list[str] = []
            for path in inventory:
                normalized_path = "".join(character for character in path.casefold() if character.isalnum())
                group = preferred if normalized_name and normalized_name in normalized_path else remaining
                full = len(group) >= file_limit
                # Classify a path only while it could take a budget slot or prove truncation;
                # once a file is dropped, later overflow counts as skipped without a check.
                if (not full or not dropped) and _budget_exempt(git_root, path):
                    excluded += 1
                elif full:
                    dropped += 1
                else:
                    group.append(path)
            bounded_inventory = (preferred + remaining)[:file_limit]
            dropped += len(preferred) + len(remaining) - len(bounded_inventory)
        else:
            bounded_inventory = inventory
        model_notes = list(inventory_notes)
        if dropped:
            model_notes.append(f"symbol lookup inventory capped at {file_limit} files")
        if unscanned_source:
            model_notes.append(f"{unscanned_source} source files with private names or in vendored folders were not scanned")
        # Match build_map's default read-only cache behavior without rendering
        # or serializing the entire model; _build never writes when requested.
        model = code_map._build(
            git_root, head, bounded_inventory, model_notes, name, file_limit,
            use_cache=not no_cache, refresh=False, write_cache=False,
        )
        model["coverage"]["inventory"] = len(inventory)
        model["coverage"]["excluded"] += excluded
        model["coverage"]["excluded_source"] = unscanned_source
        if dropped:
            model["coverage"]["skipped"] += dropped
            model["coverage"]["truncated"] = True
    except (code_map.CodeMapError, OSError, ValueError, ImportError) as exc:
        raise SymbolLookupError(str(exc)) from exc

    model_coverage = model.get("coverage", {})
    model_files = model.get("files", [])
    analysis_counts: dict[str, int] = {}
    metadata_only_files = 0
    heuristic_outline_files = 0
    incomplete_outline_files = 0
    for record in model_files:
        if record.get("language") in _NON_SOURCE_LANGUAGES:
            continue
        analysis = record.get("analysis", "metadata")
        analysis_counts[analysis] = analysis_counts.get(analysis, 0) + 1
        if analysis == "metadata":
            metadata_only_files += 1
        elif analysis != "python-ast":
            heuristic_outline_files += 1
        elif any(note and not note.startswith("local import links capped") for note in record.get("outline_note", "").split("; ")):
            # A failed or capped syntax-tree outline can miss definitions.
            incomplete_outline_files += 1
    definitions: list[dict[str, Any]] = []
    definitions_truncated = False
    for record in model_files:
        path = record.get("path")
        if not isinstance(path, str):
            continue
        symbols = record.get("symbols", [])
        if not isinstance(symbols, list):
            continue
        for item in symbols:
            if not isinstance(item, dict) or item.get("name") != name:
                continue
            definition: dict[str, Any] = {
                "path": path,
                "line": item.get("line"),
                "kind": item.get("kind"),
            }
            if isinstance(item.get("signature"), str):
                definition["signature"] = item["signature"]
            if len(definitions) == result_limit:
                definitions_truncated = True
                break
            definitions.append(definition)
        if definitions_truncated:
            break
    definitions.sort(key=lambda item: (item["path"], item["line"], item["kind"]))

    deadline = time.monotonic() + timeout
    references: list[dict[str, Any]] = []
    scanned_files = 0
    cached_files = 0
    reference_bytes = 0
    reference_considered = 0
    reference_notes: list[str] = []
    references_truncated = False
    reference_timed_out = False
    # Data and config files can name a symbol too (entry points, manifests), so they are scanned after source.
    for record in sorted(model_files[:file_limit], key=lambda item: item.get("language") in _NON_SOURCE_LANGUAGES):
        if time.monotonic() >= deadline:
            reference_timed_out = True
            reference_notes.append("reference scan timed out")
            break
        relative = record.get("path")
        if not isinstance(relative, str):
            continue
        candidate, reason = code_map._candidate(git_root, relative, git_inventory=True)
        if candidate is None:
            if "changed, private, symlink, or unsupported paths were skipped" not in reference_notes:
                reference_notes.append("changed, private, symlink, or unsupported paths were skipped")
            continue
        remaining = total_byte_limit - reference_considered
        fingerprint = candidate["fingerprint"]
        loaded: dict[str, Any] = {}
        lines = None
        if reference_cache is not None and not no_cache and fingerprint["size"] <= file_byte_limit and fingerprint["size"] <= remaining:
            def load_text() -> str:
                text, consumed, note = _read_reference_text(
                    git_root, relative, fingerprint, max_file_bytes=file_byte_limit,
                    remaining_bytes=remaining, deadline=deadline,
                )
                loaded.update(text=text, consumed=consumed, note=note)
                if text is None:
                    raise OSError(note or "source unavailable")
                return text
            try:
                lines = reference_cache.lookup(git_root, relative, fingerprint, load_text, name, deadline=deadline)
            except (UnsupportedSymbolError, OSError):
                pass
        if time.monotonic() >= deadline:
            if loaded:
                reference_bytes += loaded.get("consumed", 0)
                reference_considered += loaded.get("consumed", 0)
            reference_timed_out = True
            reference_notes.append("reference scan timed out")
            break
        if lines is not None:
            consumed = loaded.get("consumed", 0)
            reference_bytes += consumed
            reference_considered += consumed if loaded else fingerprint["size"]
            if code_map._fingerprint(git_root / relative) != fingerprint:
                if "file changed during reference scan" not in reference_notes:
                    reference_notes.append("file changed during reference scan")
                continue
            if not loaded:
                cached_files += 1
            scanned_files += 1
            for line_number in lines:
                if len(references) == result_limit:
                    references_truncated = True
                    break
                references.append({"path": relative, "line": line_number})
            if references_truncated:
                break
            continue
        if time.monotonic() >= deadline:
            reference_timed_out = True
            reference_notes.append("reference scan timed out")
            break
        if loaded:
            text, consumed, note = loaded["text"], loaded["consumed"], loaded["note"]
        else:
            text, consumed, note = _read_reference_text(
                git_root, relative, fingerprint, max_file_bytes=file_byte_limit,
                remaining_bytes=remaining, deadline=deadline,
            )
        reference_bytes += consumed
        reference_considered += consumed
        if note:
            if note == "reference scan timed out":
                reference_timed_out = True
            if note not in reference_notes:
                reference_notes.append(note)
            if reference_timed_out:
                break
            continue
        scanned_files += 1
        assert text is not None
        pattern = patterns[relative.endswith(SIGIL_SUFFIXES)]
        for line_number, line in enumerate(split_lines(text), 1):
            if time.monotonic() >= deadline:
                reference_timed_out = True
                if "reference scan timed out" not in reference_notes:
                    reference_notes.append("reference scan timed out")
                break
            if pattern.search(line):
                if len(references) == result_limit:
                    references_truncated = True
                    break
                references.append({"path": relative, "line": line_number})
        if reference_timed_out or references_truncated:
            break

    model_coverage_partial = (
        _coverage_partial(model_coverage)
        or len(model_files) < model_coverage.get("indexed", len(model_files))
    )
    definitions_partial = (
        model_coverage_partial
        or definitions_truncated
        or metadata_only_files > 0
        or heuristic_outline_files > 0
        or incomplete_outline_files > 0
    )
    references_partial = (
        model_coverage_partial
        or references_truncated
        or reference_timed_out
        or bool(reference_notes)
    )
    result = {
        "query": name,
        "definitions": definitions,
        "references": references,
        "coverage": {
            "partial": definitions_partial or references_partial,
            "definitions": {
                "model_complete": not model_coverage_partial and not definitions_truncated,
                "semantic_recall_complete": False,
                "files_indexed": len(model_files),
                "metadata_only_files": metadata_only_files,
                "heuristic_outline_files": heuristic_outline_files,
                "incomplete_outline_files": incomplete_outline_files,
                "analysis_counts": analysis_counts,
                "results_truncated": definitions_truncated,
                "limitations": [
                    "Definitions are exact-name matches only against available code-map symbols.",
                    "Metadata-only files contribute no definitions; heuristic, failed or capped outlines can miss declarations.",
                    "No semantic/LSP definition-recall guarantee is made.",
                ],
                "model": {
                    "inventory": model_coverage.get("inventory", 0),
                    "indexed": model_coverage.get("indexed", len(model_files)),
                    "skipped": model_coverage.get("skipped", 0),
                    "excluded": model_coverage.get("excluded", 0),
                    "excluded_source": model_coverage.get("excluded_source", 0),
                    "pending": model_coverage.get("pending", 0),
                    "limited": model_coverage.get("limited", 0),
                    "truncated": bool(model_coverage.get("truncated")),
                    "notes": model_coverage.get("notes", []),
                },
            },
            "references": {
                "complete": not references_partial,
                "files_scanned": scanned_files,
                "files_considered": len(model_files),
                "bytes_read": reference_bytes,
                "bytes_considered": reference_considered,
                "cached_files": cached_files,
                "results_truncated": references_truncated,
                "timed_out": reference_timed_out,
                "notes": reference_notes,
            },
            "limits": {
                "max_files": file_limit,
                "max_results_per_kind": result_limit,
                "reference_timeout_seconds": timeout,
                "max_file_bytes": file_byte_limit,
                "max_total_reference_bytes": total_byte_limit,
                "max_output_bytes": output_byte_limit,
                "model_timeout": "code_map's own bounded initialization; not included in reference timeout",
            },
            "semantics": {
                "definitions": "exact symbol-name matches from code-map metadata; availability depends on indexed language outlines",
                "references": "lexical identifier-boundary occurrences, not semantic references; declarations, comments, and strings may match",
            },
        },
    }
    return _fit_output(result, output_byte_limit)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Look up exact code-map definitions and lexical occurrence locations (JSON; no source snippets)."
    )
    parser.add_argument("--repo", required=True, metavar="PATH")
    parser.add_argument("--symbol", required=True, metavar="NAME")
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    parser.add_argument("--max-results", type=int, default=DEFAULT_MAX_RESULTS)
    parser.add_argument(
        "--timeout", type=float, default=DEFAULT_TIMEOUT,
        help="seconds for the reference scan only; model/cache initialization is separate",
    )
    parser.add_argument("--max-file-bytes", type=int, default=DEFAULT_MAX_FILE_BYTES)
    parser.add_argument("--max-total-bytes", type=int, default=DEFAULT_MAX_TOTAL_BYTES)
    parser.add_argument("--max-output-bytes", type=int, default=DEFAULT_MAX_OUTPUT_BYTES)
    cache_options = parser.add_mutually_exclusive_group()
    cache_options.add_argument(
        "--no-cache", action="store_true",
        help="bypass the code-map cache (default is to use it read-only)",
    )
    cache_options.add_argument(
        "--service", action="store_true",
        help="start or reuse the authorized local service and its memory-only postings cache",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        options = {
            "max_files": args.max_files, "max_results": args.max_results,
            "max_seconds": args.timeout, "max_file_bytes": args.max_file_bytes,
            "max_total_bytes": args.max_total_bytes, "max_output_bytes": args.max_output_bytes,
        }
        if args.service:
            try:
                try:
                    from . import map_server
                except ImportError:
                    import map_server
                result = map_server.get_lookup(args.repo, args.symbol, **options)
            except (OSError, ValueError, ImportError) as exc:
                print(f"local lookup service unavailable; using a read-only scan: {exc}", file=sys.stderr)
                result = lookup_symbols(args.repo, args.symbol, **options)
        else:
            result = lookup_symbols(args.repo, args.symbol, no_cache=args.no_cache, **options)
    except (SymbolLookupError, OSError, ValueError) as exc:
        print(f"symbol-lookup error: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(result, ensure_ascii=True, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
