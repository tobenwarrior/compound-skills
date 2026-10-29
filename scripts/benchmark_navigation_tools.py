#!/usr/bin/env python3
"""Offline paired benchmark: native rg versus Compound lexical symbol lookup."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


LANGUAGES = ("python", "rust", "typescript")


def load_fixture_module(checkout: Path) -> Any:
    source = checkout / "scripts" / "benchmark_code_map.py"
    spec = importlib.util.spec_from_file_location("compound_fixture_benchmark", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load fixture generator: {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_command(command: list[str], *, env: dict[str, str], cwd: Path) -> tuple[str, float]:
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    elapsed = time.perf_counter() - started
    if completed.returncode:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"stdout={completed.stdout[-1000:]}\nstderr={completed.stderr[-1000:]}"
        )
    return completed.stdout, elapsed


def parse_rg(output: str) -> set[tuple[str, int]]:
    found: set[tuple[str, int]] = set()
    for line in output.splitlines():
        match = re.match(r"^(.+?):([0-9]+):", line)
        if match is None:
            raise RuntimeError(f"unexpected rg output: {line!r}")
        path = match.group(1)
        if path.startswith("./"):
            path = path[2:]
        found.add((path, int(match.group(2))))
    return found


def parse_compound(output: str, symbol: str, task_kind: str) -> set[tuple[str, int]]:
    payload = json.loads(output)
    if payload.get("error"):
        raise RuntimeError(f"Compound lookup error: {payload['error']}")
    definitions = {(item["path"], item["line"]) for item in payload["definitions"]}
    references = {(item["path"], item["line"]) for item in payload["references"]}
    if payload["coverage"]["references"]["complete"] is not True:
        raise RuntimeError(f"incomplete Compound references for {symbol}")
    return definitions if task_kind == "definition" else references


def expected_for_case(case: dict[str, Any]) -> set[tuple[str, int]]:
    return set(case["references"])


def definition_pattern(case: dict[str, Any]) -> str:
    patterns = {
        "python": rf"^[[:space:]]*def[[:space:]]+{re.escape(case['symbol'])}\b",
        "typescript": rf"^[[:space:]]*export[[:space:]]+function[[:space:]]+{re.escape(case['symbol'])}\b",
        "rust": rf"^[[:space:]]*pub[[:space:]]+fn[[:space:]]+{re.escape(case['symbol'])}\b",
    }
    return patterns[case["language"]]


def git_output(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--checkout",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--files-per-language", type=int, default=20)
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()
    if args.repetitions < 3:
        raise SystemExit("--repetitions must be at least 3")
    rg = shutil.which("rg")
    if rg is None:
        raise SystemExit("rg is required")
    checkout = args.checkout.resolve()
    fixture_module = load_fixture_module(checkout)
    lookup_script = checkout / "skills" / "compound" / "scripts" / "symbol_lookup.py"
    map_script = checkout / "skills" / "compound" / "scripts" / "code_map.py"
    with tempfile.TemporaryDirectory(prefix="compound-tool-ab-") as holder:
        root = Path(holder) / "fixture"
        source_paths, cases = fixture_module._make_fixture(root, args.files_per_language)
        selected = [case for case in cases if case["language"] in LANGUAGES]
        env = os.environ.copy()
        env["COMPOUND_SKILLS_STATE_DIR"] = str(Path(holder) / "state")
        max_files = len(source_paths)
        max_results = 100
        reference_timeout = 3
        max_total_bytes = 32 * 1024 * 1024
        max_output_bytes = 64 * 1024
        max_chars = 12000
        map_generation: list[dict[str, Any]] = []
        for repetition in range(args.repetitions):
            output, elapsed = run_command(
                [
                    sys.executable,
                    "-B",
                    str(map_script),
                    "--repo",
                    str(root),
                    "--format",
                    "json",
                    "--no-cache",
                    "--max-files",
                    str(max_files),
                    "--max-chars",
                    str(max_chars),
                ],
                env=env,
                cwd=root,
            )
            payload = json.loads(output)
            expected_definitions = {
                case["definition"] for case in cases
            }
            observed_definitions = {
                (record["path"], symbol["line"], symbol["name"], symbol["kind"])
                for record in payload["files"]
                for symbol in record.get("symbols", [])
                if isinstance(symbol, dict) and isinstance(symbol.get("line"), int)
            }
            map_generation.append({
                "repetition": repetition + 1,
                "seconds": round(elapsed, 6),
                "files_indexed": payload["coverage"]["indexed"],
                "definitions_correct": observed_definitions == expected_definitions,
            })
        task_results: list[dict[str, Any]] = []
        for case in selected:
            for task_kind in ("definition", "references"):
                symbol = case["symbol"]
                expected = (
                    {(case["path"], case["definition"][1])}
                    if task_kind == "definition"
                    else expected_for_case(case)
                )
                rg_command = [
                    rg,
                    "--line-number",
                    "--no-heading",
                    "--color",
                    "never",
                    "--regexp" if task_kind == "definition" else "--word-regexp",
                    definition_pattern(case) if task_kind == "definition" else symbol,
                    ".",
                ]
                compound_command = [
                    sys.executable,
                    "-B",
                    str(lookup_script),
                    "--repo",
                    str(root),
                    "--symbol",
                    symbol,
                    "--max-files",
                    str(max_files),
                    "--max-results",
                    str(max_results),
                    "--timeout",
                    str(reference_timeout),
                    "--max-total-bytes",
                    str(max_total_bytes),
                    "--max-output-bytes",
                    str(max_output_bytes),
                    "--no-cache",
                ]
                runs: list[dict[str, Any]] = []
                for repetition in range(args.repetitions):
                    ordered_commands = (
                        (("without_compound", rg_command), ("with_compound", compound_command))
                        if repetition % 2 == 0
                        else (("with_compound", compound_command), ("without_compound", rg_command))
                    )
                    for mode, command in ordered_commands:
                        output, elapsed = run_command(command, env=env, cwd=root)
                        observed = parse_rg(output) if mode == "without_compound" else parse_compound(output, symbol, task_kind)
                        runs.append({
                            "repetition": repetition + 1,
                            "mode": mode,
                            "seconds": round(elapsed, 6),
                            "correct": observed == expected,
                            "observed_count": len(observed),
                            "expected_count": len(expected),
                        })
                task_results.append({
                    "language": case["language"],
                    "symbol": symbol,
                    "task_kind": task_kind,
                    "expected_locations": sorted([list(value) for value in expected]),
                    "runs": runs,
                    "summary": {
                        mode: {
                            "seconds_median": round(statistics.median(item["seconds"] for item in runs if item["mode"] == mode), 6),
                            "seconds_samples": [item["seconds"] for item in runs if item["mode"] == mode],
                            "all_correct": all(item["correct"] for item in runs if item["mode"] == mode),
                        }
                        for mode in ("without_compound", "with_compound")
                    },
                })
        result = {
            "benchmark": "compound-tool-navigation-ab",
            "status": "ok",
            "method": {
                "target_checkout_commit": git_output(checkout, "rev-parse", "HEAD"),
                "benchmark_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "fixture_generator": "scripts/benchmark_code_map.py",
                "fixture_files_per_language": args.files_per_language,
                "fixture_source_files": len(source_paths),
                "fixture_commit": git_output(root, "rev-parse", "HEAD"),
                "fixture_source_bytes": sum(path.stat().st_size for path in source_paths),
                "languages": list(LANGUAGES),
                "task_kinds": ["definition", "references"],
                "repetitions_per_mode_and_task": args.repetitions,
                "without_compound": "rg full-fixture scan; anchored definition regex or word-regexp lexical locations",
                "with_compound": "symbol_lookup.py --no-cache; definitions or lexical references",
                "baseline_commands": {
                    "definition": "rg --line-number --no-heading --color never --regexp LANGUAGE_DEFINITION_PATTERN .",
                    "references": "rg --line-number --no-heading --color never --word-regexp SYMBOL .",
                },
                "compound_command": f"python -B symbol_lookup.py --repo FIXTURE --symbol SYMBOL --max-files {max_files} --max-results {max_results} --timeout {reference_timeout} --max-total-bytes {max_total_bytes} --max-output-bytes {max_output_bytes} --no-cache",
                "map_generation_command": f"python -B code_map.py --repo FIXTURE --format json --no-cache --max-files {max_files} --max-chars {max_chars}",
                "same_fixture": True,
                "same_task_symbols": True,
                "compound_limits": {
                    "max_files": max_files,
                    "max_results": max_results,
                    "reference_timeout_seconds": reference_timeout,
                    "max_total_bytes": max_total_bytes,
                    "max_output_bytes": max_output_bytes,
                },
                "network": "none",
                "correctness": "exact path/line set against fixture's hand-specified lexical locations",
                "scope": "tool-level timing and recall only; not an agent/model benchmark",
                "grader": "every mode/task/repetition must match that task's hand-specified path/line locations exactly",
                "no_map_check": "rg output normalized to path/line sets; definition tasks use anchored language-specific patterns",
                "map_check": "symbol_lookup definitions or lexical references normalized to path/line sets",
            },
            "environment": {
                "python": sys.version.split()[0],
                "platform": sys.platform,
                "machine": __import__("platform").machine(),
                "rg": subprocess.run([rg, "--version"], capture_output=True, text=True, check=True).stdout.splitlines()[0],
            },
            "map_generation": {
                "command": f"code_map.py --format json --no-cache --max-files {max_files} --max-chars {max_chars}",
                "runs": map_generation,
                "seconds_median": round(statistics.median(item["seconds"] for item in map_generation), 6),
                "all_correct": all(item["definitions_correct"] for item in map_generation),
            },
            "tasks": task_results,
        }
        all_runs = [run for task in task_results for run in task["runs"]]
        result["comparison"] = {
            mode: {
                "seconds_median_across_runs": round(statistics.median(
                    run["seconds"] for run in all_runs if run["mode"] == mode
                ), 6),
                "all_correct": all(run["correct"] for run in all_runs if run["mode"] == mode),
            }
            for mode in ("without_compound", "with_compound")
        }
        result["status"] = "ok" if (
            result["map_generation"]["all_correct"]
            and all(
                task["summary"][mode]["all_correct"]
                for task in task_results
                for mode in ("without_compound", "with_compound")
            )
        ) else "fail"
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
