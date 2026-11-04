"""Compare visible focused paths using the same ranked map and local source snapshots."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

from common import REPO, SOURCES, git
from map_retrieval import extract, select
from replay_navigation_scope import load

REPOSITORIES = {
    "flask": ("49943b5a94413a530761350f04e896f76e8d620e", r"^src/flask/.+\.py$"),
    "click": ("2247b35ea1c47c727d7a06e51fa280e12a863ff6", r"^src/click/.+\.py$"),
    "packaging": ("78d8673da4d275bb7aee0126a5edc3cf90976af1", r"^src/packaging/.+\.py$"),
}
LIMITS = (500, 2500)
PATH_LINE = re.compile(r'^- ("(?:[^"\\]|\\.)*") \[[^\]\n]+\]', re.MULTILINE)


def visible(text: str) -> set[str]:
    return {json.loads(raw) for raw in PATH_LINE.findall(text)}


def measure(baseline_ref: str, per_repo: int) -> dict:
    revision = git(REPO, "rev-parse", "--verify", baseline_ref + "^{commit}", check=True).strip()
    relative = "skills/compound/scripts/code_map.py"
    previous = subprocess.check_output(["git", "show", f"{revision}:{relative}"], cwd=REPO)
    source = REPO / relative
    sys.path.insert(0, str(source.parent))
    current = load(source, "text_current")
    rows = []
    totals = {str(limit): Counter() for limit in LIMITS}
    with TemporaryDirectory(prefix="compound-text-replay-") as folder:
        scratch = Path(folder)
        baseline = scratch / "baseline.py"
        baseline.write_bytes(previous)
        old = load(baseline, "text_baseline")
        for name, (head, pattern) in REPOSITORIES.items():
            repo = SOURCES / name
            if git(repo, "rev-parse", "HEAD", check=True).strip() != head:
                raise ValueError(f"{name}: source must be at {head}")
            commits = select(repo, pattern, r"(^|/)tests?/", per_repo)
            if len(commits) != per_repo:
                raise ValueError(f"{name}: missing source history")
            for commit in commits:
                with TemporaryDirectory(dir=scratch) as checkout:
                    tree = Path(checkout) / name
                    tree.mkdir()
                    extract(repo, commit["sha"], tree)
                    model, _ = current.build_map(tree, query=commit["query"], no_cache=True)
                    tracked = set(git(tree, "ls-files", check=True).splitlines())
                    touched = set(commit["touched"]) & tracked
                    if not touched:
                        continue
                    row = {"repository": name, "commit": commit["sha"], "query": commit["query"],
                           "touched_paths_at_parent": len(touched), "limits": {}}
                    for limit in LIMITS:
                        before_text = old._text(model, limit, commit["query"])
                        after_text = current._text(model, limit, commit["query"])
                        before, after = visible(before_text), visible(after_text)
                        if len(after_text) > limit or not before <= after:
                            raise ValueError(f"{name}/{commit['sha']}: text budget or visible path regression")
                        metrics = {"before_paths": len(before), "after_paths": len(after),
                                   "before_touched_paths": len(before & touched), "after_touched_paths": len(after & touched)}
                        row["limits"][str(limit)] = metrics
                        totals[str(limit)].update(metrics)
                        totals[str(limit)].update(queries=1, touched_paths_at_parent=len(touched),
                                                   queries_with_more_paths=int(len(after) > len(before)),
                                                   queries_with_more_touched_paths=int(len(after & touched) > len(before & touched)))
                    rows.append(row)
    return {"scope": "Keyless presentation replay on commit parent snapshots. Same ranked map for both renders. "
                     "Measures complete paths visible in the agent summary, not agent reads or model cost.",
            "baseline_ref": revision, "baseline_source_sha256": hashlib.sha256(previous).hexdigest(),
            "candidate_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "source_heads": {name: head for name, (head, _) in REPOSITORIES.items()},
            "queries": rows, "totals": {limit: dict(values) for limit, values in totals.items()}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", required=True)
    parser.add_argument("--per-repo", type=int, default=12)
    args = parser.parse_args()
    if args.per_repo < 1:
        parser.error("--per-repo must be positive")
    print(json.dumps(measure(args.baseline_ref, args.per_repo), indent=2))


if __name__ == "__main__":
    main()
