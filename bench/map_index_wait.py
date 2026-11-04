"""Measure live index-status work for warm map summaries on pinned checkouts."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
from unittest.mock import patch

from common import REPO, SOURCES, git
from map_warm_work import PROBES, SCRIPTS

REPETITIONS = 7


def run_worker(scripts, root, state, query):
    sys.path.insert(0, scripts)
    import map_server

    samples = []
    with patch.dict(os.environ, {"COMPOUND_SKILLS_STATE_DIR": state, "COMPOUND_MAP_PORT": "0"}):
        try:
            expected = map_server.get_text(root, query)
            for _ in range(REPETITIONS):
                started = time.perf_counter()
                with patch.object(map_server, "_request", wraps=map_server._request) as requests:
                    text = map_server.get_text(root, query)
                if text != expected:
                    raise RuntimeError("Warm map output changed")
                samples.append({
                    "status_requests": sum(call.args[2].startswith("/api/status?") for call in requests.call_args_list),
                    "milliseconds": round((time.perf_counter() - started) * 1000, 2),
                })
        finally:
            with contextlib.redirect_stdout(io.StringIO()):
                if map_server.main(["stop"]):
                    raise RuntimeError("Could not stop the isolated map service")
    return {
        "summary_sha256": hashlib.sha256(expected.encode()).hexdigest(),
        "median_ms": statistics.median(row["milliseconds"] for row in samples),
        "samples": samples,
    }


def compare(baseline_ref):
    baseline = git(REPO, "rev-parse", "--verify", baseline_ref + "^{commit}", check=True).strip()
    with TemporaryDirectory(prefix="compound-status-wait-") as folder:
        temp = Path(folder).resolve()
        archive = subprocess.check_output(["git", "archive", baseline, "skills/compound"], cwd=REPO)
        subprocess.run(["tar", "-xf", "-"], cwd=temp, input=archive, check=True)
        rows = []
        for name, (head, subdir, query) in PROBES.items():
            root = SOURCES / name
            if git(root, "rev-parse", "HEAD", check=True).strip() != head or git(root, "status", "--porcelain", check=True).strip():
                raise ValueError(f"{name}: checkout must be clean at {head}")
            arms = []
            for variant, scripts in (("before", temp / SCRIPTS), ("after", REPO / SCRIPTS)):
                args = [str(scripts), str(root / subdir), str(temp / (name + "-" + variant)), query]
                output = subprocess.check_output([sys.executable, "-B", __file__, "--worker", *args], timeout=90)
                arms.append(json.loads(output))
            before, after = arms
            if before["summary_sha256"] != after["summary_sha256"]:
                raise RuntimeError(f"{name}: map summaries differ")
            rows.append({"repository": name, "source_head": head, "query": query, "before": before, "after": after})
    return {
        "scope": "Seven live get_text calls after one warmup per arm on each checkout. Times include local recheck and summary but omit interpreter startup. Zero model calls.",
        "baseline_ref": baseline,
        "candidate_sha256": hashlib.sha256((REPO / SCRIPTS / "map_server.py").read_bytes()).hexdigest(),
        "repositories": rows,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--baseline-ref")
    mode.add_argument("--worker", nargs=4, help=argparse.SUPPRESS)
    args = parser.parse_args()
    print(json.dumps(run_worker(*args.worker) if args.worker else compare(args.baseline_ref), indent=2))
