"""Compare exact-path focus with the same index on pinned local repositories."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from common import REPO, SOURCES, git
from replay_navigation_scope import load

SNAPSHOTS = {
    "flask": ("49943b5a94413a530761350f04e896f76e8d620e", "src/flask/__init__.py", "route handlers"),
    "django": ("a05e16a7230fe33d3f43f4a3aaed103cebb42efc", "django/urls/base.py", "model query annotations"),
}
SOURCE = Path("skills/compound/scripts/code_map.py")
SAMPLE_SIZE = 24


def ranked(module, records, root, query):
    return [row["path"] for row in module._rank(records, query, root)]


def compare(baseline_ref):
    revision = git(REPO, "rev-parse", "--verify", baseline_ref + "^{commit}", check=True).strip()
    before = subprocess.check_output(["git", "show", f"{revision}:{SOURCE.as_posix()}"], cwd=REPO)
    sys.path.insert(0, str((REPO / SOURCE).parent))
    candidate = load(REPO / SOURCE, "exact_path_candidate")
    rows = []
    with TemporaryDirectory(prefix="compound-exact-path-") as scratch:
        snapshot = Path(scratch) / "before.py"
        snapshot.write_bytes(before)
        baseline = load(snapshot, "exact_path_baseline")
        for name, (head, example, topic) in SNAPSHOTS.items():
            root = SOURCES / name
            if git(root, "rev-parse", "HEAD", check=True).strip() != head or git(root, "status", "--porcelain", check=True).strip():
                raise ValueError(f"{name}: checkout must be clean at {head}")
            model, _ = candidate.build_map(root, max_files=5000, no_cache=True)
            records = model["files"]
            paths = sorted(row["path"] for row in records if row["language"] == "python")
            sample = [paths[index * len(paths) // SAMPLE_SIZE] for index in range(SAMPLE_SIZE)]
            sample = list(dict.fromkeys([*sample, example]))
            queries = []
            for path in sample:
                old = ranked(baseline, records, root, path)
                new = ranked(candidate, records, root, path)
                if new[0] != path:
                    raise RuntimeError(f"{name}: exact path not first: {path}")
                queries.append({"path": path, "before_rank": old.index(path) + 1, "after_rank": 1})
            if ranked(baseline, records, root, topic) != ranked(candidate, records, root, topic):
                raise RuntimeError(f"{name}: topic control ranking changed")
            rows.append({"repository": name, "head": head, "indexed_python_files": len(paths),
                         "example": example, "topic_control": topic, "topic_order_unchanged": True,
                         "queries": queries})
    return {"scope": "Evenly spaced Python paths from each sorted index plus the reported example, deduplicated. "
                     "Both rankers use the same indexed metadata and read the same checkout. Zero model calls.",
            "baseline_ref": revision, "baseline_source_sha256": hashlib.sha256(before).hexdigest(),
            "candidate_source_sha256": hashlib.sha256((REPO / SOURCE).read_bytes()).hexdigest(),
            "repositories": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", required=True)
    print(json.dumps(compare(parser.parse_args().baseline_ref), indent=2))
