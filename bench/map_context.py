"""Compare text renderers on identical map metadata; no model calls or cost estimates.

Sources are read as data. The baseline renderer is loaded from a trusted local Git
revision of this repository. Results measure text bytes and complete focus entries,
not navigation accuracy, token usage, or billed savings.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

QUERIES = {
    "flask": ["request routing handler", "session cookie configuration", "template rendering context"],
    "click": ["command option validation", "parameter type conversion", "shell completion"],
    "attrs": ["attribute validator converter", "class fields initialization", "frozen exception"],
    "packaging": ["version specifier parsing", "metadata license validation", "platform tag compatibility"],
    "marshmallow": ["schema field serialization", "validation error messages", "nested field load"],
}


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def complete_entries(text: str, model: dict) -> int:
    # A truncated final row does not count as a usable complete entry.
    lines = text.splitlines()
    if lines and lines[-1].startswith("[output truncated"):
        lines = lines[:-2]
    paths = {json.dumps(path, ensure_ascii=True) for path in model["focus"]}
    return sum(any(line.startswith(f"- {path} [") for path in paths) for line in lines)


def measure(baseline, candidate, model: dict, query: str) -> dict:
    before = copy.deepcopy(model)
    full = [renderer._text(model, 10**9, query) for renderer in (baseline, candidate)]
    capped = [renderer._text(model, 2500, query) for renderer in (baseline, candidate)]
    if model != before:
        raise ValueError("renderer mutated map metadata")
    return {
        "query": query,
        "full_bytes": [len(text.encode("utf-8")) for text in full],
        "capped_bytes": [len(text.encode("utf-8")) for text in capped],
        "complete_focus_entries": [complete_entries(text, model) for text in capped],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", required=True, help="trusted local Git revision of this plugin")
    parser.add_argument("--sources", type=Path, default=Path(__file__).resolve().parent / "work/sources")
    parser.add_argument("--baseline-repo", type=Path, help="local plugin checkout containing the baseline revision")
    args = parser.parse_args()
    from fixtures import PINS

    root = Path(__file__).resolve().parents[1]
    baseline_repo = args.baseline_repo or root
    scripts = root / "skills/compound/scripts"
    sys.path.insert(0, str(scripts))
    sha = subprocess.check_output(["git", "rev-parse", "--verify", f"{args.baseline_ref}^{{commit}}"], cwd=baseline_repo, text=True).strip()
    source = subprocess.check_output(["git", "show", f"{sha}:skills/compound/scripts/code_map.py"], cwd=baseline_repo)
    with tempfile.TemporaryDirectory(prefix="compound-context-") as folder:
        baseline_path = Path(folder) / "baseline.py"
        baseline_path.write_bytes(source)
        baseline = load(baseline_path, "context_baseline")
        candidate = load(scripts / "code_map.py", "context_candidate")
        rows = []
        sources = {}
        for name, queries in QUERIES.items():
            repo = args.sources / name
            sources[name] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
            if sources[name] != PINS[name][1]:
                raise ValueError(f"{name}: checkout differs from bench/fixtures.py pin")
            dirty = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all"], cwd=repo, text=True)
            if dirty.strip():
                raise ValueError(f"{name}: checkout must be clean")
            for query in queries:
                model, _ = candidate.build_map(repo, query=query, no_cache=True, output_format="json")
                rows.append({"repo": name, **measure(baseline, candidate, model, query)})
        totals = [sum(row["full_bytes"][i] for row in rows) for i in range(2)]
        print(json.dumps({"baseline": sha, "sources": sources, "pairs": rows,
                          "summary": {"pairs": len(rows), "full_bytes": totals,
                                      "full_bytes_reduction_pct": round(100 * (1 - totals[1] / totals[0]), 1),
                                      "median_complete_focus_entries": [statistics.median(row["complete_focus_entries"][i] for row in rows) for i in range(2)]}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
