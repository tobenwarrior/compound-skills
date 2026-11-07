"""Count cold and warm Git work for focused map queries on pinned local snapshots."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from common import REPO, SOURCES, git

PROBES = {
    "flask": ("49943b5a94413a530761350f04e896f76e8d620e", "src/flask", "route handlers"),
    "django": ("a05e16a7230fe33d3f43f4a3aaed103cebb42efc", "django/db/models", "model query annotations"),
}
SCRIPTS = Path("skills/compound/scripts")
REPETITIONS = 3


def measure(scripts, nested, query, state):
    state.mkdir()
    trace = state / "git-events.jsonl"
    env = {**os.environ, "COMPOUND_SKILLS_STATE_DIR": str(state), "COMPOUND_MAP_PORT": "0",
           "GIT_TRACE2_EVENT": str(trace)}
    command = [sys.executable, "-B", str(scripts / "code_map.py"), "--repo", str(nested), "--query", query]

    def run_query():
        result = subprocess.run(command, env=env, capture_output=True, check=True, timeout=60)
        if result.stderr:
            raise RuntimeError(result.stderr.decode(errors="replace"))
        return hashlib.sha256(result.stdout).hexdigest()

    def git_work():
        commands = Counter()
        directory_walks = Counter()
        sessions = {}
        for line in trace.read_text().splitlines():
            event = json.loads(line)
            if event["event"] == "start":
                argv = event["argv"]
                if argv[1] != "--no-optional-locks" or "-C" not in argv:
                    raise RuntimeError("Unexpected Git invocation in the map trace")
                args = argv[argv.index("-C") + 2:]
                name = args[1] if args[0] == "--literal-pathspecs" else args[0]
                commands[name] += 1
                sessions[event["sid"]] = name
            elif event["event"] == "region_enter" and event.get("category") == "dir" and event.get("label") == "read_directory":
                directory_walks[sessions[event["sid"]]] += 1
        if not commands:
            raise RuntimeError("No Git commands recorded")
        return {"git_processes": sum(commands.values()), "git_commands": dict(sorted(commands.items())),
                "directory_walks": dict(sorted(directory_walks.items()))}

    try:
        expected = run_query()
        cold = git_work()
        rows = []
        for _ in range(REPETITIONS):
            trace.write_text("")
            if run_query() != expected:
                raise RuntimeError("Query output changed on an unchanged checkout")
            rows.append(git_work())
        return expected, cold, rows
    finally:
        subprocess.run([sys.executable, "-B", str(scripts / "map_server.py"), "stop"],
                       env=env, check=True, stdout=subprocess.DEVNULL, timeout=15)


def compare(baseline_ref):
    baseline = git(REPO, "rev-parse", "--verify", baseline_ref + "^{commit}", check=True).strip()
    with TemporaryDirectory(prefix="compound-warm-work-") as scratch:
        temp = Path(scratch).resolve()
        archive = subprocess.check_output(["git", "archive", baseline, "skills/compound"], cwd=REPO)
        subprocess.run(["tar", "-xf", "-"], cwd=temp, input=archive, check=True)
        rows = []
        for name, (head, subdir, query) in PROBES.items():
            root = SOURCES / name
            if git(root, "rev-parse", "HEAD", check=True).strip() != head or git(root, "status", "--porcelain", check=True).strip():
                raise ValueError(f"{name}: checkout must be clean at {head}")
            before_digest, before_cold, before = measure(temp / SCRIPTS, root / subdir, query, temp / (name + "-before"))
            after_digest, after_cold, after = measure(REPO / SCRIPTS, root / subdir, query, temp / (name + "-after"))
            if before_digest != after_digest:
                raise RuntimeError(f"{name}: focused summaries differ")
            rows.append({"repository": name, "source_head": head, "subdir": subdir, "query": query,
                         "summary_sha256": after_digest, "before_cold": before_cold, "after_cold": after_cold,
                         "before": before, "after": after})
    return {"scope": "Cold and warm focused CLI queries in isolated local services. Zero model calls.",
            "baseline_ref": baseline, "candidate_sha256": {
                name: hashlib.sha256((REPO / SCRIPTS / name).read_bytes()).hexdigest()
                for name in ("code_map.py", "map_server.py")
            }, "warm_queries_per_version_and_repo": REPETITIONS, "repositories": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", required=True)
    print(json.dumps(compare(parser.parse_args().baseline_ref), indent=2))
