"""Compare registry replacements for distinct warm CLI queries on pinned checkouts."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from common import REPO, SOURCES, git
from map_warm_work import PROBES, SCRIPTS

QUERIES = {
    "flask": ("request context", "blueprint registration", "session cookie"),
    "django": ("queryset annotations", "model constraints", "URL resolution"),
}


def run_arm(scripts, root, state, viewer_query, queries):
    env = {**os.environ, "COMPOUND_SKILLS_STATE_DIR": str(state), "COMPOUND_MAP_PORT": "0"}
    registry = state / "code-map" / "registry.json"

    def command(script, *args):
        result = subprocess.run([sys.executable, "-B", str(scripts / script), *args], env=env,
                                capture_output=True, check=True, timeout=60)
        if result.stderr:
            raise RuntimeError(result.stderr.decode(errors="replace"))
        return result.stdout

    def snapshot():
        info = registry.stat()
        return info.st_ino, info.st_mtime_ns, registry.read_bytes()

    def open_viewer(query):
        command("map_server.py", "open", "--repo", str(root), "--query", query, "--no-open")

    def summary(query):
        return command("code_map.py", "--repo", str(root), "--query", query)

    try:
        open_viewer(viewer_query)
        summary(viewer_query)
        initial = snapshot()
        rows = []
        previous = initial
        for query in queries:
            output = summary(query)
            current = snapshot()
            rows.append({"summary_sha256": hashlib.sha256(output).hexdigest(), "registry_changed": current != previous})
            previous = current
        retained = initial[2] == previous[2]
        open_viewer("explicit viewer update")
        if json.loads(registry.read_bytes())["projects"][0]["query"] != "explicit viewer update":
            raise RuntimeError("Explicit viewer query was not saved")
        return {"viewer_query_retained": retained, "queries": rows}
    finally:
        command("map_server.py", "stop")


def compare(baseline_ref):
    baseline = git(REPO, "rev-parse", "--verify", baseline_ref + "^{commit}", check=True).strip()
    with TemporaryDirectory(prefix="compound-registry-replay-") as folder:
        temp = Path(folder).resolve()
        archive = subprocess.check_output(["git", "archive", baseline, "skills/compound"], cwd=REPO)
        subprocess.run(["tar", "-xf", "-"], cwd=temp, input=archive, check=True)
        rows = []
        for name, (head, subdir, viewer_query) in PROBES.items():
            root = SOURCES / name
            if git(root, "rev-parse", "HEAD", check=True).strip() != head or git(root, "status", "--porcelain", check=True).strip():
                raise ValueError(f"{name}: checkout must be clean at {head}")
            before = run_arm(temp / SCRIPTS, root / subdir, temp / (name + "-before"), viewer_query, QUERIES[name])
            after = run_arm(REPO / SCRIPTS, root / subdir, temp / (name + "-after"), viewer_query, QUERIES[name])
            if [row["summary_sha256"] for row in before["queries"]] != [row["summary_sha256"] for row in after["queries"]]:
                raise RuntimeError(f"{name}: focused summary changed")
            rows.append({"repository": name, "source_head": head, "queries": QUERIES[name], "before": before, "after": after})
    return {"scope": "Distinct warm CLI text queries after one initial viewer query. Compare registry bytes, inode and modification time. Zero model calls.",
            "baseline_ref": baseline,
            "candidate_sha256": hashlib.sha256((REPO / SCRIPTS / "map_server.py").read_bytes()).hexdigest(),
            "repositories": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", required=True)
    print(json.dumps(compare(parser.parse_args().baseline_ref), indent=2))
