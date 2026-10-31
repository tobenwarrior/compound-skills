"""Compare arms run on the same tasks: per-arm rates and medians, and paired tests of each arm against a baseline.

Runs pair up by group (the arms that ran a task side by side). Binary habits use an exact McNemar test on the
pairs; mutants caught and judge scores use an exact or sampled sign-flip test on the paired differences; cost,
tokens and time are paired log ratios with every task weighted equally and a bootstrap 95% interval. P-values are
unadjusted: correct for the number of comparisons you look at.
"""
from __future__ import annotations

import itertools
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path

from common import RESULTS
from harness import load_records

BUGFIX = ("bugfix-refund", "bugfix-leap", "bugfix-december")
WRITE = BUGFIX + ("refactor-rounding",)
HABITS = [  # (key, label, source)
    ("reproduced_before_fix", "Reproduced the bug before changing code", "habits"),
    ("failing_test_on_old_code", "Showed a new test failing on the old code", "habits"),
    ("final_full_suite_ok", "Ran the full suite on the final code", "habits"),
    ("hidden_pass", "Fix passes the hidden test", "outcome"),
    ("regression_valid", "Left a valid regression test", "outcome"),
    ("success", "Finished correctly (hidden test and both suites pass)", "outcome"),
    ("commit_made", "Committed", "outcome"),
    ("ai_trailer", "Commit has an AI co-author trailer", "outcome"),
]
REFACTOR = [
    ("behaviour_preserved", "Kept behavior (hidden test)"),
    ("duplication_removed", "Removed the duplicated rounding"),
    ("success", "Finished correctly"),
    ("tests_catch_naive_refactor", "Tests catch the naive refactor"),
]


def load(labels: list[str]) -> list[dict]:
    records = []
    for label in labels:
        for record in load_records(label):
            if record.get("superseded"):
                continue
            judge = RESULTS / label / f"{record['run_id']}.judge.json"
            if judge.exists():
                record["judge"] = json.loads(judge.read_text())
            record["label"] = label
            records.append(record)
    return records


def value(record: dict, key: str, source: str):
    return (record.get(source) or {}).get(key)


def kn(runs: list[dict], test) -> str:
    return f"{sum(1 for r in runs if test(r))}/{len(runs)}"


def median(values: list[float]):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def sign_flip_p(diffs: list[float], seed: int = 1) -> float:
    diffs = [d for d in diffs if d != 0]
    if not diffs:
        return 1.0
    observed = abs(sum(diffs))
    if len(diffs) <= 20:
        hits = sum(abs(sum(s * d for s, d in zip(signs, diffs))) >= observed - 1e-12
                   for signs in itertools.product((1, -1), repeat=len(diffs)))
        return hits / 2 ** len(diffs)
    rng = random.Random(seed)
    hits = sum(abs(sum(d if rng.random() < 0.5 else -d for d in diffs)) >= observed - 1e-12 for _ in range(100_000))
    return (hits + 1) / 100_001


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def geo_ratio(per_task: dict[str, list[float]], seed: int = 2) -> dict:
    """Mean over tasks of the mean paired log ratio; bootstrap pairs within tasks."""
    tasks = [t for t, logs in per_task.items() if logs]
    if not tasks:
        return {}
    point = statistics.mean(statistics.mean(per_task[t]) for t in tasks)
    rng = random.Random(seed)
    samples = sorted(statistics.mean(statistics.mean(rng.choices(per_task[t], k=len(per_task[t]))) for t in tasks)
                     for _ in range(10_000))
    pooled = [x for t in tasks for x in per_task[t]]
    return {"ratio": math.exp(point), "ci95": [math.exp(samples[249]), math.exp(samples[9749])],
            "p": sign_flip_p(pooled), "pairs": len(pooled)}


def pairs(records: list[dict], task_names, model: str, arm: str, base: str) -> list[tuple[dict, dict]]:
    groups: dict = defaultdict(dict)
    for r in records:
        if r["task"] in task_names and r["model"] == model and r["valid"]:
            groups[(r["label"], r["pair_id"])][r["arm"]] = r
    return [(g[arm], g[base]) for g in groups.values() if arm in g and base in g]


def mutant_fraction(record: dict) -> float:
    return record["outcome"].get("mutants_caught", 0) / max(1, record["outcome"].get("mutants_total", 0))


def describe(records: list[dict], model: str, arms: list[str]) -> dict:
    runs = lambda task_names, arm: [r for r in records if r["model"] == model and r["arm"] == arm  # noqa: E731
                                    and r["task"] in task_names and r["valid"]]
    out: dict = {"bugfix": {}, "refactor": {}, "judged": {}, "cost": {}, "control": {}}
    for arm in arms:
        fixes = runs(BUGFIX, arm)
        row = {key: kn(fixes, lambda r, k=key, s=source: value(r, k, s)) for key, _, source in HABITS}
        row["mutants_caught"] = f"{sum(r['outcome'].get('mutants_caught', 0) for r in fixes)}/{sum(r['outcome'].get('mutants_total', 0) for r in fixes)}"
        out["bugfix"][arm] = row
        refactors = runs(("refactor-rounding",), arm)
        out["refactor"][arm] = {key: kn(refactors, lambda r, k=key: r["outcome"].get(k)) for key, _ in REFACTOR}
        out["refactor"][arm]["mutants_caught"] = f"{sum(r['outcome'].get('mutants_caught', 0) for r in refactors)}/{sum(r['outcome'].get('mutants_total', 0) for r in refactors)}"
        for task in sorted({r["task"] for r in records if r.get("judge")}):
            judged = [r for r in runs((task,), arm) if r.get("judge")]
            if judged:
                out["judged"].setdefault(task, {})[arm] = {
                    "n": len(judged), "score_median": median([r["judge"]["score"] for r in judged]), "of": judged[0]["judge"]["of"],
                    "incorrect_claims_median": median([r["judge"]["incorrect_claims_median"] for r in judged]),
                    "read_only_respected": kn(judged, lambda r: r["outcome"].get("read_only_respected"))}
        for task in sorted({r["task"] for r in records if r["model"] == model}):
            done = runs((task,), arm)
            if done:
                out["cost"].setdefault(task, {})[arm] = {
                    "n": len(done), "invalid": sum(1 for r in records if r["task"] == task and r["model"] == model
                                                   and r["arm"] == arm and not r["valid"]),
                    "cost_usd": median([r["tokens"]["cost_usd"] for r in done]),
                    "wall_s": median([r["harness"]["wall_ms"] / 1000 for r in done]),
                    "output_tokens": median([r["tokens"]["output"] for r in done]),
                    "tool_calls": median([r["trace"]["tool_calls"] for r in done]),
                    "skill_used": kn(done, lambda r: r["compound"]["compound_skill"]),
                    "map_used": kn(done, lambda r: r["compound"]["map_calls"]),
                    "timeouts": sum(1 for r in done if r["timed_out"])}
        control = runs(("inactive",), arm)
        if control:
            out["control"][arm] = {"answered": kn(control, lambda r: r["outcome"].get("success")),
                                   "skill_used": kn(control, lambda r: r["compound"]["compound_skill"]),
                                   "files_changed": kn(control, lambda r: r["outcome"].get("files")),
                                   "cost_usd": median([r["tokens"]["cost_usd"] for r in control])}
    return out


def compare(records: list[dict], model: str, arm: str, base: str) -> dict:
    out: dict = {}
    for key, _, source in HABITS:
        b = c = 0
        found = pairs(records, BUGFIX, model, arm, base)
        for a, z in found:
            b += bool(value(a, key, source) and not value(z, key, source))
            c += bool(value(z, key, source) and not value(a, key, source))
        out[key] = {"arm_only": b, "base_only": c, "pairs": len(found), "p": mcnemar_exact(b, c)}
    found = pairs(records, ("refactor-rounding",), model, arm, base)
    for key, _ in REFACTOR:
        b = sum(1 for a, z in found if a["outcome"].get(key) and not z["outcome"].get(key))
        c = sum(1 for a, z in found if z["outcome"].get(key) and not a["outcome"].get(key))
        out[f"refactor_{key}"] = {"arm_only": b, "base_only": c, "pairs": len(found), "p": mcnemar_exact(b, c)}
    diffs = [mutant_fraction(a) - mutant_fraction(z) for a, z in pairs(records, WRITE, model, arm, base)]
    out["mutants_fraction"] = {"mean_diff": statistics.mean(diffs) if diffs else None, "pairs": len(diffs), "p": sign_flip_p(diffs)}
    judged = [(a, z) for a, z in pairs(records, {r["task"] for r in records if r.get("judge")}, model, arm, base)
              if a.get("judge") and z.get("judge")]
    diffs = [a["judge"]["score"] - z["judge"]["score"] for a, z in judged]
    out["judge_score"] = {"mean_diff": statistics.mean(diffs) if diffs else None, "pairs": len(diffs), "p": sign_flip_p(diffs)}
    tasks = sorted({r["task"] for r in records if r["model"] == model and r["task"] != "inactive"})
    for metric, get in (("cost", lambda r: r["tokens"]["cost_usd"]), ("context_tokens", lambda r: r["tokens"]["context_total"]),
                        ("wall_time", lambda r: r["harness"]["wall_ms"])):
        per_task = {task: [math.log(get(a) / get(z)) for a, z in pairs(records, (task,), model, arm, base) if get(a) and get(z)]
                    for task in tasks}
        out[f"{metric}_ratio"] = geo_ratio(per_task)
    return out


def fmt(value) -> str:
    if value is None:
        return "–"
    if isinstance(value, float):
        return f"{value:.3g}" if abs(value) < 1000 else f"{value:,.0f}"
    return str(value)


def table(header: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(fmt(cell) for cell in row) + " |" for row in rows]
    return "\n".join(lines)


def build(labels: list[str], baseline: str | None) -> tuple[dict, str]:
    """baseline: one arm or several, comma separated; every other arm is paired against each."""
    records = load(labels)
    if not records:
        raise SystemExit(f"no runs in {', '.join(labels)}")
    arm_info: dict = {}
    for label in labels:
        path = RESULTS / label / "arms.json"
        if path.exists():
            arm_info.update(json.loads(path.read_text()))
    arms = [name for name in arm_info if any(r["arm"] == name for r in records)] or sorted({r["arm"] for r in records})
    bases = [name for name in (baseline or "").split(",") if name] or ["without" if "without" in arms else arms[0]]
    for name in bases:
        if name not in arms:
            raise SystemExit(f"baseline {name} is not an arm in {', '.join(labels)}: {', '.join(arms)}")
    models = sorted({r["model"] for r in records})
    summary: dict = {"labels": labels, "arms": arm_info, "baselines": bases, "runs": len(records),
                     "invalid": [(r["task"], r["arm"], r["model"], r["invalid_reasons"]) for r in records if not r["valid"]],
                     "served_models": sorted({r["init"].get("model") or "?" for r in records}),
                     "claude_code": sorted({r["init"].get("version") or "?" for r in records}), "models": {}}
    text = [f"# Benchmark: {', '.join(labels)}", ""]
    for name in arms:
        info = arm_info.get(name, {})
        detail = ", ".join(str(x) for x in (info.get("source"), info.get("plugin_version"), info.get("plugin_hash"),
                                             (info.get("commit") or "")[:12] or None) if x)
        text.append(f"- **{name}**: {detail or 'see records'}")
    text += ["", f"{len(records)} runs, {len(summary['invalid'])} invalid. Claude Code {', '.join(summary['claude_code'])}; "
             f"models served: {', '.join(summary['served_models'])}. Paired tests against: **{', '.join(bases)}**.", ""]
    for model in models:
        described = describe(records, model, arms)
        compared = {base: {arm: compare(records, model, arm, base) for arm in arms if arm != base} for base in bases}
        summary["models"][model] = {"describe": described, "compare": compared}
        text += [f"## {model}", ""]
        has = lambda names: any(r["model"] == model and r["task"] in names and r["valid"] for r in records)  # noqa: E731
        if has(BUGFIX):
            text += ["### Bug fixes (all three bugs pooled)", ""]
            rows = [[label] + [described["bugfix"][arm][key] for arm in arms] for key, label, _ in HABITS]
            rows.append(["Mutants caught by the tests left behind"] + [described["bugfix"][arm]["mutants_caught"] for arm in arms])
            text += [table(["", *arms], rows), ""]
        if has(("refactor-rounding",)):
            text += ["### Refactor", ""]
            rows = [[label] + [described["refactor"][arm][key] for arm in arms] for key, label in REFACTOR]
            rows.append(["Mutants caught"] + [described["refactor"][arm]["mutants_caught"] for arm in arms])
            text += [table(["", *arms], rows), ""]
        if described["judged"]:
            text += ["### Judged answers (median key items found, median incorrect claims)", ""]
            rows = [[task] + [(f"{d['score_median']}/{d['of']}, {fmt(d['incorrect_claims_median'])} wrong (n={d['n']})"
                               if (d := described["judged"][task].get(arm)) else "–") for arm in arms]
                    for task in described["judged"]]
            text += [table(["task", *arms], rows), ""]
        text += ["### Median cost (USD) and time (s) per run", ""]
        rows = [[task] + [(f"${d['cost_usd']:.2f}, {d['wall_s']:.0f}s (n={d['n']}{', ' + str(d['invalid']) + ' invalid' if d['invalid'] else ''})"
                           if (d := described["cost"][task].get(arm)) else "–") for arm in arms]
                for task in described["cost"]]
        text += [table(["task", *arms], rows), ""]
        if described["control"]:
            text += ["### Inactive control (a plain question)", ""]
            rows = [[key] + [described["control"].get(arm, {}).get(key) for arm in arms] for key in ("answered", "skill_used", "files_changed", "cost_usd")]
            text += [table(["", *arms], rows), ""]
        for base, against in compared.items():
            if not against:
                continue
            text += [f"### Paired against {base}", ""]
            rows = []
            for arm, comparison in against.items():
                for key, label, _ in HABITS[:3]:
                    item = comparison[key]
                    rows.append([arm, label, f"{item['arm_only']} vs {item['base_only']} of {item['pairs']} pairs", f"p={item['p']:.3g}"])
                item = comparison["refactor_success"]
                rows.append([arm, "Refactor finished correctly", f"{item['arm_only']} vs {item['base_only']} of {item['pairs']} pairs", f"p={item['p']:.3g}"])
                for key, label in (("mutants_fraction", "Mutants caught (mean difference in share)"), ("judge_score", "Judge score (mean difference)")):
                    item = comparison[key]
                    rows.append([arm, label, f"{fmt(item['mean_diff'])} over {item['pairs']} pairs", f"p={item['p']:.3g}"])
                for key, label in (("cost_ratio", "Cost"), ("context_tokens_ratio", "Context tokens"), ("wall_time_ratio", "Wall time")):
                    item = comparison[key]
                    if item:
                        rows.append([arm, f"{label} ratio (tasks weighted equally)",
                                     f"{item['ratio']:.2f}× (95% CI {item['ci95'][0]:.2f}–{item['ci95'][1]:.2f}), {item['pairs']} pairs", f"p={item['p']:.3g}"])
            text += [table(["arm", "measure", f"arm vs {base}", "p"], rows), ""]
    if summary["invalid"]:
        text += ["### Invalid runs", ""] + [f"- {task} {arm} {model}: {', '.join(reasons)}" for task, arm, model, reasons in summary["invalid"]] + [""]
    return summary, "\n".join(text)


def write(labels: list[str], baseline: str | None, out: Path | None) -> str:
    summary, text = build(labels, baseline)
    target = out or (RESULTS / labels[0] / "summary.json")
    target.write_text(json.dumps(summary, indent=1, default=str))
    (target.with_suffix(".md")).write_text(text)
    return text
