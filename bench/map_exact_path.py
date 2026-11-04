"""Compare exact-path focus with the same index on pinned local repositories."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

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


def summary(service, engine, project, query):
    probes = source_bytes = 0
    read = engine._content_terms

    def count(*args, **kwargs):
        nonlocal probes, source_bytes
        terms, used = read(*args, **kwargs)
        probes += 1
        source_bytes += used
        return terms, used

    with patch.object(service, "_refresh"), patch.object(engine, "_content_terms", side_effect=count):
        model, body = service.summary_response(project, 2000, query, 2500)
    text = json.loads(body)["text"]
    return model, text, {
        "source_probes": probes, "source_bytes": source_bytes, "text_bytes": len(text.encode()),
        "file_rows": sum(line.startswith('- "') for line in text.splitlines()),
    }


def compare_summaries(old_server, server, root, model, paths, topic):
    modules = old_server, server
    services = [module.MapService("benchmark", 0, {}) for module in modules]
    projects = [module.Project("benchmark", root.name, root, "", 5000, model=model) for module in modules]
    pairs = list(zip(services, (module.engine for module in modules), projects))
    rows = []
    for path in paths:
        (before, before_text, old), (after, after_text, new) = [
            summary(service, engine, project, path) for service, engine, project in pairs
        ]
        old_target = next(file for file in before["files"] if file["path"] == path)
        if (before["focus"][0] != path or after["focus"] != [path] or after["files"] != [old_target]
                or new["file_rows"] != 1 or new["source_probes"] or ('- ' + json.dumps(path)) not in after_text):
            raise RuntimeError(f"Exact-file summary lost its target or ranked source: {path}")
        declarations = [
            (symbol.get("signature") or symbol["name"]) + f" ({symbol['kind']}:{symbol['line']})"
            for symbol in old_target["symbols"]
        ]
        before_visible = {declaration for declaration in declarations if declaration in before_text}
        after_visible = {declaration for declaration in declarations if declaration in after_text}
        if not before_visible <= after_visible or (declarations and not after_visible):
            raise RuntimeError(f"Exact-file summary lost its outline: {path}")
        rows.append({"path": path, "before": old, "after": new,
                     "before_declarations": len(before_visible), "after_declarations": len(after_visible)})
    controls = [topic, "unknowncompoundsymbolzz"]
    for query in controls:
        (_, old_text, old), (_, new_text, new) = [
            summary(service, engine, project, query) for service, engine, project in pairs
        ]
        if old != new or old_text != new_text:
            raise RuntimeError(f"Ordinary summary changed: {query}")
    return {"queries": rows, "unchanged_controls": controls}



def compare_symbol_summaries(old_server, server, root, model, example, topic):
    definitions = {}
    for file in model["files"]:
        for symbol in file["symbols"]:
            name = symbol["name"]
            if name.isidentifier() and server.engine._literal_query_names(name):
                definitions.setdefault(name.casefold(), {}).setdefault(file["path"], []).append(symbol)
    unique = {name: next(iter(files.items())) for name, files in definitions.items() if len(files) == 1}
    candidates = sorted(name for name, (path, _) in unique.items()
                        if path.endswith(".py") and not server.engine._is_test(path) and not name.startswith("_"))
    sample = list(dict.fromkeys([*(candidates[i * len(candidates) // 12] for i in range(12)), example]))

    modules = old_server, server
    pairs = [(module.MapService("benchmark", 0, {}), module.engine,
              module.Project("benchmark", root.name, root, "", 5000, model=model)) for module in modules]
    rows = []
    for key in sample:
        path, symbols = unique[key]
        name = symbols[0]["name"]
        (_, before_text, before), (after, after_text, new) = [
            summary(service, engine, project, name) for service, engine, project in pairs
        ]
        declarations = [
            (symbol.get("signature") or symbol["name"]) + f" ({symbol['kind']}:{symbol['line']})"
            for symbol in symbols[:8]
        ]
        before_visible = {declaration for declaration in declarations if declaration in before_text}
        after_visible = {declaration for declaration in declarations if declaration in after_text}
        if (after["focus"] != [path] or new["file_rows"] != 1 or new["source_probes"]
                or not after_visible or not before_visible <= after_visible):
            raise RuntimeError(f"Exact-symbol summary lost its target or ranked source: {name}")
        rows.append({"query": name, "path": path, "before": before, "after": new,
                     "before_declarations": len(before_visible), "after_declarations": len(after_visible)})

    ambiguous = next(next(iter(files.values()))[0]["name"] for name, files in sorted(definitions.items())
                     if len(files) > 1 and not name.startswith("_"))
    controls = [topic, f"{example} {topic}", ambiguous, "unknown_compound_symbol_zz"]
    for query in controls:
        old, new = [summary(service, engine, project, query) for service, engine, project in pairs]
        if old != new:
            raise RuntimeError(f"Ordinary or ambiguous summary changed: {query}")
    return {"queries": rows, "unchanged_controls": controls}


def load_server(path):
    spec = importlib.util.spec_from_file_location("exact_path_baseline_server", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def compare(baseline_ref, summaries=False, symbols=False):
    revision = git(REPO, "rev-parse", "--verify", baseline_ref + "^{commit}", check=True).strip()
    before = subprocess.check_output(["git", "show", f"{revision}:{SOURCE.as_posix()}"], cwd=REPO)
    sys.path.insert(0, str((REPO / SOURCE).parent))
    candidate = load(REPO / SOURCE, "exact_path_candidate")
    rows = []
    with TemporaryDirectory(prefix="compound-exact-path-") as scratch:
        snapshot = Path(scratch) / "before.py"
        snapshot.write_bytes(before)
        baseline = load(snapshot, "exact_path_baseline")
        if summaries or symbols:
            import map_server as server

            server_source = SOURCE.with_name("map_server.py")
            snapshot = Path(scratch) / "baseline_server.py"
            snapshot.write_bytes(subprocess.check_output(
                ["git", "show", f"{revision}:{server_source.as_posix()}"], cwd=REPO))
            old_server = load_server(snapshot)
            old_server.engine = baseline
        for name, (head, example, topic) in SNAPSHOTS.items():
            root = SOURCES / name
            if git(root, "rev-parse", "HEAD", check=True).strip() != head or git(root, "status", "--porcelain", check=True).strip():
                raise ValueError(f"{name}: checkout must be clean at {head}")
            model, _ = candidate.build_map(root, max_files=5000, no_cache=True)
            records = model["files"]
            paths = sorted(row["path"] for row in records if row["language"] == "python")
            sample = [paths[index * len(paths) // SAMPLE_SIZE] for index in range(SAMPLE_SIZE)]
            sample = list(dict.fromkeys([*sample, example]))
            if symbols:
                symbol = {"flask": "stream_with_context", "django": "select_for_update"}[name]
                rows.append({"repository": name, "head": head,
                             **compare_symbol_summaries(old_server, server, root, model, symbol, topic)})
                continue
            if summaries:
                rows.append({"repository": name, "head": head,
                             **compare_summaries(old_server, server, root, model, sample, topic)})
                continue
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
    if summaries or symbols:
        return {"scope": "Warm indexed text responses on the same metadata. Counts exclude Git and indexing. Zero model calls.",
                "baseline_ref": revision, "repositories": rows}
    return {"scope": "Evenly spaced Python paths from each sorted index plus the reported example, deduplicated. "
                     "Both rankers use the same indexed metadata and read the same checkout. Zero model calls.",
            "baseline_ref": revision, "baseline_source_sha256": hashlib.sha256(before).hexdigest(),
            "candidate_source_sha256": hashlib.sha256((REPO / SOURCE).read_bytes()).hexdigest(),
            "repositories": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--summary", action="store_true", help="count ranking reads and text bytes for exact file paths")
    mode.add_argument("--symbols", action="store_true", help="count ranking reads and text bytes for exact symbol names")
    args = parser.parse_args()
    print(json.dumps(compare(args.baseline_ref, args.summary, args.symbols), indent=2))
