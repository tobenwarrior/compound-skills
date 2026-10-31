#!/usr/bin/env python3
"""Benchmark Compound Skills against other plugin versions, or no plugin, on fixed engineering tasks.

    python3 bench/bench.py setup                       # once: fetch pinned sources, build fixtures, template config
    python3 bench/bench.py tasks                       # list tasks and tags
    python3 bench/bench.py run --label my-change --arms base=ref:main,new=worktree --tasks core --reps 3
    python3 bench/bench.py judge --label my-change     # blind-grade review and investigation answers
    python3 bench/bench.py report --label my-change    # tables and paired tests against the first arm
    python3 bench/bench.py map-speed --plugin worktree
    python3 bench/bench.py map-retrieval --plugin worktree

See bench/README.md for what each part measures and how to add a task.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import RESULTS, SOURCES, TEMPLATE, materialize, parse_arms  # noqa: E402


def setup(args) -> int:
    import fixtures
    import harness
    problems = harness.preflight()
    if problems:
        print("\n".join(f"cannot run: {problem}" for problem in problems))
        return 1
    report = fixtures.build(map_sources=args.map)
    for name, checks in report["fixtures"].items():
        print(f"fixture {name}: {checks['head'][:12]} {'matches the frozen commit' if checks['matches_frozen_commit'] else 'DIFFERS from the frozen commit'}")
    print(f"reference trees: {', '.join(report['refs'])}; mutants: {len(report['mutants'])}")
    if report["problems"]:
        print("\n".join(f"problem: {problem}" for problem in report["problems"]))
        return 1
    if TEMPLATE.is_dir() and not args.template:
        print("template config: kept (use --template to rebuild it)")
    else:
        result = harness.make_template(args.model)
        print(f"template config: {'ok' if result['ok'] else 'FAILED'} (Claude Code {result['claude_code']}, model {result['model']}, "
              f"{result['wall_ms'] / 1000:.0f}s)")
        if not result["ok"]:
            print(result["stderr"])
            return 1
    print("ready")
    return 0


def list_tasks(args) -> int:
    from tasks import TASKS
    for task in TASKS.values():
        print(f"{task['name']:20s} {task['kind']:5s} {','.join(task.get('tags', [])):16s} {task.get('about', '')}")
    print("\ntags: core (the six measured tasks), bugfix, judged, control, all")
    return 0


def run(args) -> int:
    import harness
    import tasks
    problems = harness.preflight()
    if problems:
        print("\n".join(f"cannot run: {problem}" for problem in problems))
        return 1
    return harness.run_matrix(args.label, parse_arms(args.arms), tasks.select(args.tasks), args.models.split(","), args.reps,
                              args.first_rep, args.slots, not args.no_retry, args.max_seven_day, args.pause_five_hour)


def judge(args) -> int:
    import judge as judging
    if args.calibrate:
        judging.calibrate(args.votes, args.model)
        return 0
    return judging.judge_label(args.label, args.votes, args.workers, args.model)


def report(args) -> int:
    import report as reporting
    labels = [args.label, *args.also]
    print(reporting.write(labels, args.baseline, Path(args.out) if args.out else None))
    return 0


def plugin_scripts(spec: str) -> tuple[dict, Path]:
    arm = materialize(parse_arms(f"map={spec}")[0])
    if not arm["plugin"]:
        raise SystemExit("--plugin must be worktree, ref:<revision> or dir:<path>")
    return arm, Path(arm["plugin"]) / "skills" / "compound" / "scripts"


def output_path(name: str, label: str | None) -> Path:
    folder = RESULTS / (label or "map")
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{name}-{datetime.now(timezone.utc):%Y%m%d%H%M%S}.json"


def map_speed(args) -> int:
    import map_speed as speed
    arm, scripts = plugin_scripts(args.plugin)
    speed.use_scripts(scripts)
    results = {"plugin": {k: v for k, v in arm.items() if k != "plugin"}, "machine": speed.machine(), "repos": []}
    for name in args.repos.split(","):
        source = SOURCES / name
        if not source.is_dir():
            raise SystemExit(f"{name} is not fetched: run `python3 bench/bench.py setup --map`")
        result = speed.bench(source, args.reps)
        results["repos"].append(result)
        print(json.dumps({key: result[key] for key in ("repo", "indexed_files", "build_cold_s", "build_unchanged_s",
                                                       "agent_query_cold_s", "agent_query_warm_s")}), flush=True)
    target = output_path("map-speed", args.label)
    target.write_text(json.dumps(results, indent=1))
    print(f"wrote {target}")
    return 0


def map_retrieval(args) -> int:
    import map_retrieval as retrieval
    for name in retrieval.REPOS:
        if not (SOURCES / name).is_dir():
            raise SystemExit(f"{name} is not fetched: run `python3 bench/bench.py setup --map`")
    arm, scripts = plugin_scripts(args.plugin)
    result = retrieval.run(scripts / "code_map.py", args.per_repo)
    result["plugin"] = {k: v for k, v in arm.items() if k != "plugin"}
    result["python"] = platform.python_version()
    target = output_path("map-retrieval", args.label)
    target.write_text(json.dumps(result, indent=1))
    print(json.dumps(result["summary"], indent=1))
    print(f"wrote {target}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("setup", help="fetch pinned sources, build and check fixtures, create the template config")
    p.add_argument("--map", action="store_true", help="also fetch the repositories the map benchmarks read")
    p.add_argument("--template", action="store_true", help="rebuild the template config even if it exists")
    p.add_argument("--model", default="opus", help="model for the one-time template run")
    p.set_defaults(func=setup)
    p = sub.add_parser("tasks", help="list tasks and tags")
    p.set_defaults(func=list_tasks)
    p = sub.add_parser("run", help="run arms side by side on tasks")
    p.add_argument("--label", required=True, help="results folder name; rerunning a label resumes it")
    p.add_argument("--arms", default="without,with",
                   help="comma-separated: without, with (this worktree), rule, or name=none|rule|worktree|ref:<revision>|dir:<path>")
    p.add_argument("--tasks", default="core", help="task names or tags: core, bugfix, judged, control, all")
    p.add_argument("--models", default="opus", help="comma-separated aliases (opus, sonnet, haiku) or model ids")
    p.add_argument("--reps", type=int, default=1)
    p.add_argument("--first-rep", type=int, default=1)
    p.add_argument("--slots", type=int, default=1, help="groups run at once; keep slots x arms within your CPU count")
    p.add_argument("--no-retry", action="store_true", help="do not rerun a group after an API or harness failure")
    p.add_argument("--max-seven-day", type=float, default=0.80, help="stop when seven-day usage reaches this share")
    p.add_argument("--pause-five-hour", type=float, default=0.75, help="wait for the reset when five-hour usage reaches this share")
    p.set_defaults(func=run)
    p = sub.add_parser("judge", help="blind-grade the answers of judged tasks")
    p.add_argument("--label")
    p.add_argument("--votes", type=int, default=3)
    p.add_argument("--workers", type=int, default=3)
    p.add_argument("--model", default="opus")
    p.add_argument("--calibrate", action="store_true", help="grade the frozen perfect and flawed answers instead")
    p.set_defaults(func=judge)
    p = sub.add_parser("report", help="tables and paired tests for one or more labels")
    p.add_argument("--label", required=True)
    p.add_argument("--also", nargs="*", default=[], help="more labels to pool with the first")
    p.add_argument("--baseline", help="arm or comma-separated arms the others are paired against (default: without, else the first arm)")
    p.add_argument("--out", help="summary JSON path (default: results/<label>/summary.json, with a .md next to it)")
    p.set_defaults(func=report)
    p = sub.add_parser("map-speed", help="time map builds and agent queries on pinned repositories")
    p.add_argument("--plugin", default="worktree", help="worktree, ref:<revision> or dir:<path>")
    p.add_argument("--repos", default="django,vue-core,gin,ripgrep")
    p.add_argument("--reps", type=int, default=5)
    p.add_argument("--label")
    p.set_defaults(func=map_speed)
    p = sub.add_parser("map-retrieval", help="does the map find the files real commits touched")
    p.add_argument("--plugin", default="worktree", help="worktree, ref:<revision> or dir:<path>")
    p.add_argument("--per-repo", type=int, default=60)
    p.add_argument("--label")
    p.set_defaults(func=map_retrieval)
    args = parser.parse_args()
    if args.command == "judge" and not args.calibrate and not args.label:
        parser.error("judge needs --label (or --calibrate)")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
