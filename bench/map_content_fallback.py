"""Measure source-only map lookups against pinned local repository snapshots."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

from common import REPO, SOURCES, git
from map_text_coverage import REPOSITORIES, visible
from replay_navigation_scope import load

# Source-only probes exercise the fallback. Controls include a normal symbol
# query and a miss so the normal and worst-case scan costs are visible.
PROBES = {
    "flask": (("pluginmanager", "tests/test_logging.py"), ("Blueprint", "src/flask/blueprints.py")),
    "click": (("multibyte", "tests/test_types/test_File.py"), ("Command", "src/click/core.py")),
    "packaging": (
        ("jsonschema", "tests/test_dependency_groups.py"),
        ("mousebender", "tests/pylock/pylock.spec-example.toml"),
        ("SpecifierSet", "src/packaging/specifiers.py"),
    ),
}

MIXED_PROBES = {
    "flask": (("pytest pluginmanager", "tests/test_logging.py"), ("route handlers", "src/flask/app.py")),
    "click": (("encoding multibyte", "tests/test_types/test_File.py"), ("command completion", "src/click/core.py")),
    "packaging": (("platform mousebender", "tests/pylock/pylock.spec-example.toml"), ("specifier versions", "src/packaging/specifiers.py")),
}


def replay(module, model, root, query, target):
    read = module._content_terms
    counts = {"source_probes": 0, "source_bytes": 0}

    def count(*args, **kwargs):
        terms, used = read(*args, **kwargs)
        counts["source_probes"] += 1
        counts["source_bytes"] += used
        return terms, used

    matches = set()
    with patch.object(module, "_content_terms", side_effect=count):
        ranked = module._rank(model["files"], query, root, query_matches=matches)
    focus = [record["path"] for record in ranked[:12]]
    rendered = module._text(
        {**model, "focus": focus, "query_matches": [path for path in focus if path in matches]},
        2500, query,
    )
    return {**counts, "target_visible": target in visible(rendered), "focus": focus}


def measure(baseline_ref, mixed=False):
    revision = git(REPO, "rev-parse", "--verify", baseline_ref + "^{commit}", check=True).strip()
    relative = "skills/compound/scripts/code_map.py"
    before_bytes = subprocess.check_output(["git", "show", f"{revision}:{relative}"], cwd=REPO)
    source = REPO / relative
    sys.path.insert(0, str(source.parent))
    current = load(source, "content_current")
    rows = []
    title_controls = json.loads((REPO / "bench/diagram_sources/map_text_coverage_v01618.json").read_text())["queries"] if mixed else []
    title_summary = Counter()
    with TemporaryDirectory(prefix="compound-content-replay-") as scratch:
        snapshot = Path(scratch) / "baseline.py"
        snapshot.write_bytes(before_bytes)
        before = load(snapshot, "content_baseline")
        for name, cases in (MIXED_PROBES if mixed else PROBES).items():
            root = SOURCES / name
            expected = REPOSITORIES[name][0]
            head = git(root, "rev-parse", "HEAD", check=True).strip()
            if head != expected or git(root, "status", "--porcelain", check=True).strip():
                raise ValueError(f"{name}: checkout must be clean at {expected}")
            model, _ = current.build_map(root, no_cache=True, max_files=5000)
            miss = "compoundnonexistentfallbackprobe"
            if mixed:
                topic, topic_path = cases[-1]
                probe, target = cases[0]
                cases = (*cases, (topic_path, topic_path), (f"{name} {probe}", target))
                miss = f"{topic.split()[0]} {miss}"
            for query, target in (*cases, (miss, None)):
                previous, candidate = [replay(module, model, root, query, target) for module in (before, current)]
                kind = "miss" if target is None else ("ordinary" if previous["target_visible"] else "source-only")
                if kind == "ordinary":
                    assert previous == candidate
                if kind == "miss":
                    assert previous["focus"] == candidate["focus"]
                if mixed and kind == "source-only":
                    assert candidate["target_visible"]
                    assert previous["focus"][:3] == candidate["focus"][:3]
                rows.append({"repository": name, "source_head": head, "kind": kind,
                             "query": query, "target": target,
                             "focus_preserved": previous["focus"] == candidate["focus"],
                             "before": {k: v for k, v in previous.items() if k != "focus"},
                             "after": {k: v for k, v in candidate.items() if k != "focus"}})
            for title in title_controls:
                if title["repository"] != name:
                    continue
                previous, candidate = [replay(module, model, root, title["query"], None) for module in (before, current)]
                title_summary.update(
                    queries=1,
                    unchanged_reads=int(previous["source_probes"] == candidate["source_probes"]),
                    unchanged_focus=int(previous["focus"] == candidate["focus"]),
                    extra_probes=candidate["source_probes"] - previous["source_probes"],
                )
    result = {"scope": "Selected source-only lookups and controls on pinned local repositories. "
                       "These probes measure visible paths and local reads, with zero model calls.",
              "baseline_ref": revision,
              "baseline_source_sha256": hashlib.sha256(before_bytes).hexdigest(),
              "candidate_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "probes": rows}
    if mixed:
        result["commit_title_controls_on_pinned_trees"] = dict(title_summary)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", required=True)
    parser.add_argument("--mixed", action="store_true", help="run mixed-keyword probes and their controls")
    args = parser.parse_args()
    print(json.dumps(measure(args.baseline_ref, args.mixed), indent=2))
