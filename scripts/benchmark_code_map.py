#!/usr/bin/env python3
"""Bounded offline synthetic benchmark for Compound code maps and symbol lookup.

Creates and removes a local Git fixture outside this checkout. No models, network,
source artifacts, tokenizers, or token-count estimates are used.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

SCHEMA_VERSION = 1
LANGUAGE_FIXTURES: dict[str, tuple[str, str, list[str]]] = {
    "python": (
        ".py", "resolve_python",
        [
            "def resolve_python(value):",
            "    # resolve_python in a comment",
            '    print("resolve_python")',
            "    resolve_python(value)",
            "    return value",
            "# resolve_python_extra is an identifier-boundary near miss",
        ],
    ),
    "javascript": (
        ".js", "resolve_javascript",
        [
            "export function resolve_javascript(value) {",
            "  // resolve_javascript in a comment",
            '  void "resolve_javascript";',
            "  resolve_javascript(value);",
            "  return value;",
            "}",
            "// resolve_javascript_extra is an identifier-boundary near miss",
        ],
    ),
    "typescript": (
        ".ts", "resolve_typescript",
        [
            "export function resolve_typescript(value: string): string {",
            "  // resolve_typescript in a comment",
            '  void "resolve_typescript";',
            "  resolve_typescript(value);",
            "  return value;",
            "}",
            "// resolve_typescript_extra is an identifier-boundary near miss",
        ],
    ),
    "go": (
        ".go", "resolve_go",
        [
            "package fixture",
            'import _ "example.invalid/fixture/dep"',
            "func resolve_go(value string) string {",
            "    // resolve_go in a comment",
            '    println("resolve_go")',
            "    _ = resolve_go(value)",
            "    return value",
            "}",
            "// resolve_go_extra is an identifier-boundary near miss",
        ],
    ),
    "rust": (
        ".rs", "resolve_rust",
        [
            "pub fn resolve_rust(value: &str) -> &str {",
            "    // resolve_rust in a comment",
            '    let _ = "resolve_rust";',
            "    let _ = resolve_rust(value);",
            "    value",
            "}",
            "// resolve_rust_extra is an identifier-boundary near miss",
        ],
    ),
}


class BenchmarkError(RuntimeError):
    pass


def _ratio(correct: int, total: int) -> float | None:
    return round(correct / total, 6) if total else None


def _accuracy(expected: set[tuple[Any, ...]], predicted: set[tuple[Any, ...]]) -> dict[str, Any]:
    correct = expected & predicted
    return {
        "correct": len(correct),
        "total": len(expected),
        "recall": _ratio(len(correct), len(expected)),
        "predicted": len(predicted),
        "precision": _ratio(len(correct), len(predicted)),
        "false_positives": [list(value) for value in sorted(predicted - expected)],
        "missed": [list(value) for value in sorted(expected - predicted)],
    }


def _source_bytes(paths: list[Path]) -> int:
    return sum(len(path.read_bytes()) for path in paths)


def _measure_parser(call: Callable[[], Any], repo: Path, code_map: Any) -> tuple[Any, float, dict[str, Any]]:
    original = code_map._read_parse
    measured: dict[str, Any] = {"bytes_read": 0, "files": []}

    def tracked(info: dict[str, Any], remaining: int) -> Any:
        result = original(info, remaining)
        measured["bytes_read"] += result[1]
        try:
            measured["files"].append(info["absolute"].relative_to(repo).as_posix())
        except (AttributeError, ValueError):
            measured["files"].append(str(info.get("absolute", "")))
        return result

    code_map._read_parse = tracked
    started = time.perf_counter()
    try:
        value = call()
        elapsed = time.perf_counter() - started
    finally:
        code_map._read_parse = original
    measured["files_parsed"] = len(measured["files"])
    measured["files"] = sorted(measured["files"])
    return value, elapsed, measured


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> None:
    process_env = os.environ.copy()
    process_env.update(env or {})
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True,
        check=False, env=process_env, timeout=10,
    )
    if result.returncode:
        raise BenchmarkError(f"local Git command failed ({' '.join(args)}): {result.stderr.strip()}")


def _make_fixture(repo: Path, files_per_language: int) -> tuple[list[Path], list[dict[str, Any]]]:
    repo.mkdir()
    paths: list[Path] = []
    cases: list[dict[str, Any]] = []
    for language, (suffix, symbol, lines) in LANGUAGE_FIXTURES.items():
        directory = repo / "src" / language
        directory.mkdir(parents=True)
        primary = directory / ("primary" + suffix)
        primary.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        paths.append(primary)
        declaration_line = next(index for index, line in enumerate(lines, 1) if symbol in line)
        cases.append({
            "language": language,
            "symbol": symbol,
            "path": primary.relative_to(repo).as_posix(),
            "definition": (primary.relative_to(repo).as_posix(), declaration_line, symbol, "function"),
            # The fixture deliberately places one lexical occurrence on each of
            # consecutive lines: declaration, comment, string, and call.
            "references": {(primary.relative_to(repo).as_posix(), line) for line in range(declaration_line, declaration_line + 4)},
        })
        comment = "#" if language == "python" else "//"
        for index in range(1, files_per_language):
            filler = directory / f"filler_{index:03d}{suffix}"
            header = "package fixture\n" if language == "go" else ""
            rows = [f"{comment} fixture {language} module {index} line {line} preserves bounded search behavior" for line in range(50)]
            filler.write_text(header + "\n".join(rows) + "\n", encoding="utf-8", newline="\n")
            paths.append(filler)

    manifest = repo / "src/go/go.mod"
    manifest.write_text("module example.invalid/fixture\n\ngo 1.22\n", encoding="utf-8")
    go_dependency = repo / "src/go/dep/dep.go"
    go_dependency.parent.mkdir(parents=True)
    go_dependency.write_text("package dep\nvar Value = 1\n", encoding="utf-8")
    rust_root = repo / "src/rust/lib.rs"
    rust_root.write_text("pub mod primary;\n", encoding="utf-8")
    paths.extend((manifest, go_dependency, rust_root))

    _git(repo, "init", "-q")
    _git(repo, "checkout", "-q", "-b", "benchmark")
    _git(repo, "config", "user.name", "Compound benchmark")
    _git(repo, "config", "user.email", "benchmark.invalid@example.invalid")
    _git(repo, "add", "--", ".")
    _git(
        repo, "commit", "-q", "-m", "synthetic benchmark fixture",
        env={"GIT_AUTHOR_DATE": "2000-01-01T00:00:00+00:00", "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+00:00"},
    )
    return paths, cases


def _map_definitions(model: dict[str, Any]) -> set[tuple[Any, ...]]:
    found: set[tuple[Any, ...]] = set()
    for record in model.get("files", []):
        for symbol in record.get("symbols", []):
            if isinstance(symbol, dict) and isinstance(symbol.get("line"), int):
                found.add((record.get("path"), symbol["line"], symbol.get("name"), symbol.get("kind")))
    return found


def _payload_bytes(value: dict[str, Any]) -> int:
    return len(json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode("utf-8"))


def _check_limits(files_per_language: int, repetitions: int) -> None:
    if not 1 <= files_per_language <= 100:
        raise BenchmarkError("--files-per-language must be between 1 and 100")
    if not 1 <= repetitions <= 5:
        raise BenchmarkError("--repetitions must be between 1 and 5")


def run_benchmark(files_per_language: int = 2, repetitions: int = 3) -> dict[str, Any]:
    _check_limits(files_per_language, repetitions)
    checkout = Path(__file__).resolve().parents[1]
    scripts_dir = checkout / "skills" / "compound" / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    sys.dont_write_bytecode = True
    import code_map  # type: ignore[import-not-found]
    import symbol_lookup  # type: ignore[import-not-found]
    from reference_cache import IdentifierPostingsCache

    previous_state = os.environ.get("COMPOUND_SKILLS_STATE_DIR")
    with tempfile.TemporaryDirectory(prefix="compound-code-map-bench-") as temporary:
        temporary_root = Path(temporary).resolve()
        try:
            temporary_root.relative_to(checkout)
        except ValueError:
            pass
        else:
            raise BenchmarkError("temporary fixtures must be outside the checkout")
        repo = temporary_root / "synthetic-code-map"
        state = temporary_root / "compound-state"
        os.environ["COMPOUND_SKILLS_STATE_DIR"] = str(state)
        try:
            source_paths, cases = _make_fixture(repo, files_per_language)
            initial_source_bytes = _source_bytes(source_paths)
            max_files = len(source_paths)

            def build_map() -> tuple[dict[str, Any], str]:
                return code_map.build_map(
                    repo, max_files=max_files, no_cache=False, output_format="json",
                )

            (cold_model, cold_json), cold_seconds, cold_parse = _measure_parser(build_map, repo, code_map)
            warm_samples: list[float] = []
            warm_parses: list[dict[str, Any]] = []
            warm_model: dict[str, Any] = cold_model
            warm_json = cold_json
            for _ in range(repetitions):
                (warm_model, warm_json), elapsed, parsed = _measure_parser(build_map, repo, code_map)
                warm_samples.append(elapsed)
                warm_parses.append(parsed)

            changed_file = next(path for path in source_paths if path.name == "primary.py")
            incremental_addition = b"# incremental cache invalidation probe\n"
            with changed_file.open("ab") as target:
                target.write(incremental_addition)
            changed_file_bytes = len(changed_file.read_bytes())
            (incremental_model, incremental_json), incremental_seconds, incremental_parse = _measure_parser(build_map, repo, code_map)
            final_source_bytes = _source_bytes(source_paths)

            expected_map = {case["definition"] for case in cases}
            map_accuracy = _accuracy(expected_map, _map_definitions(cold_model))
            incremental_accuracy = _accuracy(expected_map, _map_definitions(incremental_model))
            expected_edges = {("src/go/primary.go", "src/go/dep/dep.go"), ("src/rust/lib.rs", "src/rust/primary.rs")}
            def selected_edges(model: dict[str, Any]) -> set[tuple[str, str]]:
                return {(item["path"], dependency) for item in model["files"] if item["path"] in {edge[0] for edge in expected_edges} for dependency in item["dependencies"]}
            edge_accuracy = _accuracy(expected_edges, selected_edges(cold_model))
            incremental_edge_accuracy = _accuracy(expected_edges, selected_edges(incremental_model))

            lookup_cases: list[dict[str, Any]] = []
            all_lookup_expected_definitions: set[tuple[Any, ...]] = set()
            all_lookup_predicted_definitions: set[tuple[Any, ...]] = set()
            all_lookup_expected_references: set[tuple[Any, ...]] = set()
            all_lookup_predicted_references: set[tuple[Any, ...]] = set()
            for case in cases:
                expected_definition = {case["definition"]}
                expected_references = case["references"]

                def lookup(no_cache: bool, cache: Any = None) -> dict[str, Any]:
                    return symbol_lookup.lookup_symbols(
                        repo, case["symbol"], max_files=max_files, max_results=100,
                        max_seconds=3.0, max_file_bytes=1024 * 1024,
                        max_total_bytes=8 * 1024 * 1024, max_output_bytes=64 * 1024,
                        no_cache=no_cache, reference_cache=cache,
                    )

                cold_result, cold_lookup_seconds, cold_lookup_parse = _measure_parser(
                    lambda: lookup(True), repo, code_map,
                )
                cold_reference_bytes = cold_result["coverage"]["references"]["bytes_read"]
                warm_lookup_samples: list[float] = []
                warm_lookup_parses: list[dict[str, Any]] = []
                warm_result = cold_result
                for _ in range(repetitions):
                    warm_result, elapsed, parsed = _measure_parser(
                        lambda: lookup(False), repo, code_map,
                    )
                    warm_lookup_samples.append(elapsed)
                    warm_lookup_parses.append(parsed)
                with IdentifierPostingsCache(max_entries=2000) as postings:
                    primed, prime_seconds, _ = _measure_parser(lambda: lookup(False, postings), repo, code_map)
                    memory_samples = []
                    memory_result = primed
                    for _ in range(repetitions):
                        memory_result, elapsed, _ = _measure_parser(lambda: lookup(False, postings), repo, code_map)
                        memory_samples.append(elapsed)
                    if memory_result["references"] != warm_result["references"]:
                        raise BenchmarkError("memory postings changed lexical occurrence results")
                definitions = {
                    (value.get("path"), value.get("line"), case["symbol"], value.get("kind"))
                    for value in warm_result.get("definitions", [])
                }
                references = {
                    (value.get("path"), value.get("line"))
                    for value in warm_result.get("references", [])
                }
                all_lookup_expected_definitions.update(expected_definition)
                all_lookup_predicted_definitions.update(definitions)
                all_lookup_expected_references.update(expected_references)
                all_lookup_predicted_references.update(references)
                serialized_bytes = _payload_bytes(warm_result)
                reported_bytes = warm_result["coverage"]["output"]["bytes"]
                if serialized_bytes != reported_bytes:
                    raise BenchmarkError("symbol lookup output byte count disagrees with its JSON payload")
                lookup_cases.append({
                    "language": case["language"],
                    "symbol": case["symbol"],
                    "definitions": _accuracy(expected_definition, definitions),
                    "lexical_occurrences": _accuracy(expected_references, references),
                    "cold": {
                        "seconds": round(cold_lookup_seconds, 6),
                        "map_parse_files": cold_lookup_parse["files_parsed"],
                        "map_source_bytes_read": cold_lookup_parse["bytes_read"],
                        "reference_source_bytes_read": cold_reference_bytes,
                        "total_source_bytes_read": cold_lookup_parse["bytes_read"] + cold_reference_bytes,
                        "json_payload_utf8_bytes": _payload_bytes(cold_result),
                    },
                    "warm": {
                        "seconds_median": round(statistics.median(warm_lookup_samples), 6),
                        "seconds_samples": [round(value, 6) for value in warm_lookup_samples],
                        "map_parse_files_median": round(statistics.median(item["files_parsed"] for item in warm_lookup_parses), 6),
                        "map_source_bytes_read_median": round(statistics.median(item["bytes_read"] for item in warm_lookup_parses), 6),
                        "reference_source_bytes_read": warm_result["coverage"]["references"]["bytes_read"],
                        "total_source_bytes_read_median": round(statistics.median(
                            item["bytes_read"] + warm_result["coverage"]["references"]["bytes_read"]
                            for item in warm_lookup_parses
                        ), 6),
                        "json_payload_utf8_bytes": serialized_bytes,
                    },
                    "memory_postings": {
                        "prime_seconds": round(prime_seconds, 6),
                        "seconds_median": round(statistics.median(memory_samples), 6),
                        "seconds_samples": [round(value, 6) for value in memory_samples],
                        "reference_source_bytes_read": memory_result["coverage"]["references"]["bytes_read"],
                        "reference_bytes_considered": memory_result["coverage"]["references"]["bytes_considered"],
                        "cached_files": memory_result["coverage"]["references"]["cached_files"],
                    },
                    "coverage": {
                        "definitions_partial": warm_result["coverage"]["definitions"]["model_complete"] is False
                            or warm_result["coverage"]["definitions"]["semantic_recall_complete"] is False,
                        "lexical_scan_complete": warm_result["coverage"]["references"]["complete"],
                        "reference_files_scanned": warm_result["coverage"]["references"]["files_scanned"],
                        "reference_scan_bytes": warm_result["coverage"]["references"]["bytes_read"],
                    },
                })

            map_json_bytes = len(cold_json.encode("utf-8"))
            map_text_bytes = len(code_map._text(cold_model, code_map.DEFAULT_MAX_CHARS).encode("utf-8"))
            return {
                "schema_version": SCHEMA_VERSION,
                "benchmark": "compound-code-map-synthetic",
                "status": "ok" if map_accuracy["correct"] == map_accuracy["total"] and map_accuracy["precision"] == 1 and incremental_accuracy["correct"] == incremental_accuracy["total"] and incremental_accuracy["precision"] == 1 and edge_accuracy["recall"] == 1 and edge_accuracy["precision"] == 1 and incremental_edge_accuracy["recall"] == 1 and incremental_edge_accuracy["precision"] == 1 and all_lookup_expected_definitions == all_lookup_predicted_definitions and all_lookup_expected_references == all_lookup_predicted_references else "fail",
                "contract": {
                    "offline": True,
                    "environment": {"system": platform.system(), "machine": platform.machine(), "python": platform.python_version(), "logical_cpus": os.cpu_count()},
                    "temporary_repository_outside_checkout": True,
                    "temporary_cache_outside_checkout": True,
                    "fixture_repositories_created": 1,
                    "languages": list(LANGUAGE_FIXTURES),
                    "files_per_language": files_per_language,
                    "fixture_source_files": len(source_paths),
                    "fixture_source_utf8_bytes_before_increment": initial_source_bytes,
                    "fixture_source_utf8_bytes_after_increment": final_source_bytes,
                    "timing_repetitions": repetitions,
                    "ground_truth": "Hand-specified declarations, lexical line locations, and Go/Rust import edges in generated fixtures.",
                    "definitions": "Exact code-map outline matches; fixture-only recall, not semantic/LSP recall.",
                    "lexical_occurrences": "Identifier-boundary lines include declaration, comment, string, and call; not semantic references.",
                    "unscored_capabilities": ["language-server semantic references", "call hierarchy", "cross-language resolution"],
                    "bytes": "Actual UTF-8 source and serialized JSON/text byte lengths; no token estimates.",
                    "network": "No network calls; local temporary Git only.",
                    "fixture_cleanup": "Temporary repository and cache are removed on exit.",
                },
                "code_map": {
                    "accuracy": map_accuracy,
                    "incremental_accuracy": incremental_accuracy,
                    "dependency_edges": edge_accuracy,
                    "incremental_dependency_edges": incremental_edge_accuracy,
                    "cold": {
                        "seconds": round(cold_seconds, 6),
                        "files_parsed": cold_parse["files_parsed"],
                        "source_bytes_read": cold_parse["bytes_read"],
                        "json_payload_utf8_bytes": map_json_bytes,
                        "summary_text_utf8_bytes": map_text_bytes,
                    },
                    "warm": {
                        "seconds_median": round(statistics.median(warm_samples), 6),
                        "seconds_samples": [round(value, 6) for value in warm_samples],
                        "files_parsed_median": round(statistics.median(item["files_parsed"] for item in warm_parses), 6),
                        "source_bytes_read_median": round(statistics.median(item["bytes_read"] for item in warm_parses), 6),
                        "json_payload_utf8_bytes": len(warm_json.encode("utf-8")),
                        "summary_text_utf8_bytes": len(code_map._text(warm_model, code_map.DEFAULT_MAX_CHARS).encode("utf-8")),
                    },
                    "incremental": {
                        "seconds": round(incremental_seconds, 6),
                        "files_parsed": incremental_parse["files_parsed"],
                        "parsed_files": incremental_parse["files"],
                        "source_bytes_read": incremental_parse["bytes_read"],
                        "changed_file_utf8_bytes": changed_file_bytes,
                        "appended_utf8_bytes": len(incremental_addition),
                        "json_payload_utf8_bytes": len(incremental_json.encode("utf-8")),
                    },
                },
                "symbol_lookup": {
                    "per_language": lookup_cases,
                    "definitions_aggregate": _accuracy(
                        all_lookup_expected_definitions, all_lookup_predicted_definitions,
                    ),
                    "lexical_occurrences_aggregate": _accuracy(
                        all_lookup_expected_references, all_lookup_predicted_references,
                    ),
                    "semantics": "Lexical line matches only; optional language-server references are not measured here.",
                },
            }
        finally:
            if previous_state is None:
                os.environ.pop("COMPOUND_SKILLS_STATE_DIR", None)
            else:
                os.environ["COMPOUND_SKILLS_STATE_DIR"] = previous_state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--files-per-language", type=int, default=2, help="fixture source files per language (1-100)")
    parser.add_argument("--repetitions", type=int, default=3, help="warm timing samples (1-5)")
    args = parser.parse_args(argv)
    try:
        result = run_benchmark(args.files_per_language, args.repetitions)
    except (BenchmarkError, ImportError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"schema_version": SCHEMA_VERSION, "benchmark": "compound-code-map-synthetic", "status": "error", "error": str(exc)}, ensure_ascii=True, separators=(",", ":")))
        return 2
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
