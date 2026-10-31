"""Blind grading of read-only answers against frozen keys, several votes per answer, verbatim quotes checked.

The judge sees the question, the key items (shuffled per vote), supporting code, and one redacted answer:
sentences that mention tooling are deleted and absolute project paths are made relative in every arm. It has no
tools, runs in an empty directory with the template config (no plugin, no rule), and never sees the arm, the
run id or any other answer.
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import random
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from common import DATA, JUDGE_CONTEXT, RESULTS, SRC_ROOT, TEMPLATE
from harness import KEEP_ENV, load_records
from tasks import TASKS

SCHEMA = {
    "type": "object",
    "properties": {
        "items": {"type": "object", "additionalProperties": {
            "type": "object", "properties": {"met": {"type": "boolean"}, "quote": {"type": "string"}}, "required": ["met", "quote"]}},
        "incorrect_claims": {"type": "array", "items": {"type": "object", "properties": {"quote": {"type": "string"}, "why": {"type": "string"}},
                                                         "required": ["quote", "why"]}},
        "extra_findings": {"type": "array", "items": {"type": "object", "properties": {"quote": {"type": "string"}, "valid": {"type": "boolean"}},
                                                       "required": ["quote", "valid"]}},
    },
    "required": ["items", "incorrect_claims", "extra_findings"],
}

TOOLING = re.compile(r"(?i)compound|code[_ ]?map|symbol[_ ]lookup|onboarding\.py|references/[\w.-]+\.md|\bskill\b|/claude-plugins/")


def redact(answer: str, project: str) -> str:
    text = answer.replace(f"{SRC_ROOT}/{project}/", "").replace(f"{SRC_ROOT}/{project}", ".")
    kept = []
    for line in text.splitlines():
        if TOOLING.search(line):
            sentences = re.split(r"(?<=[.!?])\s+", line)
            line = " ".join(s for s in sentences if not TOOLING.search(s))
        kept.append(line)
    return "\n".join(kept)


def prompt_for(task: dict, answer: str, seed: int) -> str:
    key = task["judge"]
    names = list(key["items"])
    random.Random(seed).shuffle(names)
    items = "\n".join(f"{name}: {key['items'][name]}" for name in names)
    context = (JUDGE_CONTEXT / key["context"]).read_text()
    return (
        "You grade one answer to a software engineering question against a fixed key. Be strict and literal. "
        "For each key item, set met=true only if the answer clearly states it; quote the exact sentence or phrase from "
        "the answer that shows it (copy it verbatim, at most 300 characters), or use an empty quote when not met. "
        f"{key['rule']} Do not reward length, structure, confidence or hedging. Then list statements in the answer that "
        "are factually wrong about the code shown below (quote them verbatim and say why), and, for reviews, list other "
        "problems the answer reports beyond the key, each with valid=true only if the code below shows it is a real "
        f"problem. {key['extras_note']}\n\nQuestion asked:\n{task['prompt']}\n\nKey items:\n{items}\n\n"
        f"Code for reference:\n<<<\n{context}\n>>>\n\nAnswer to grade:\n<<<\n{answer}\n>>>"
    )


def judge_once(prompt: str, model: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="judge-") as folder:
        base = Path(folder)
        shutil.copytree(TEMPLATE, base / "cfg", symlinks=True)
        (base / "home").mkdir()
        (base / "cwd").mkdir()
        env = {key: os.environ[key] for key in KEEP_ENV if key in os.environ}
        env.update({key: os.environ[key] for key in os.environ.get("BENCH_PASS_ENV", "").split(",") if key and key in os.environ})
        claude = shutil.which("claude") or "claude"
        env.update(HOME=str(base / "home"), CLAUDE_CONFIG_DIR=str(base / "cfg"),
                   PATH=":".join(dict.fromkeys([os.path.dirname(claude), "/usr/bin", "/bin"])),
                   LANG="C.UTF-8", TERM="dumb", DISABLE_AUTOUPDATER="1")
        out = subprocess.run([claude, "-p", prompt, "--output-format", "json", "--model", model, "--no-session-persistence",
                              "--tools", "", "--json-schema", json.dumps(SCHEMA)],
                             cwd=base / "cwd", env=env, capture_output=True, text=True, timeout=900)
    try:
        data = json.loads(out.stdout)
    except json.JSONDecodeError:
        return {"error": (out.stdout or out.stderr)[-500:]}
    verdict = data.get("structured_output")
    if verdict is None:
        match = re.search(r"\{.*\}", data.get("result", ""), re.S)
        verdict = json.loads(match.group(0)) if match else {"error": data.get("result", "")[:500]}
    verdict["cost_usd"] = data.get("total_cost_usd")
    verdict["models"] = sorted((data.get("modelUsage") or {}).keys())
    return verdict


def check_quotes(verdict: dict, answer: str) -> dict:
    flat = re.sub(r"\s+", " ", answer)
    for item in (verdict.get("items") or {}).values():
        quote = re.sub(r"\s+", " ", item.get("quote", "")).strip().strip('"').strip("…").strip()
        item["quote_ok"] = bool(quote) and quote[:120] in flat
        if item.get("met") and not item["quote_ok"]:
            item["met_raw"], item["met"] = True, False
    return verdict


def grade(task: dict, answer: str, votes: int, seed: int, model: str) -> dict:
    results = [check_quotes(judge_once(prompt_for(task, answer, seed + vote), model), answer) for vote in range(votes)]
    names = list(task["judge"]["items"])
    met = {name: sum(1 for r in results if (r.get("items") or {}).get(name, {}).get("met")) for name in names}
    majority = {name: count * 2 > votes for name, count in met.items()}
    return {"items": majority, "score": sum(majority.values()), "of": len(names),
            "split_items": [name for name, count in met.items() if 0 < count < votes],
            "incorrect_claims_median": sorted(len(r.get("incorrect_claims") or []) for r in results)[votes // 2],
            "extra_valid_median": sorted(sum(1 for e in r.get("extra_findings") or [] if e.get("valid")) for r in results)[votes // 2],
            "votes": results}


def calibrate(votes: int, model: str) -> list[tuple]:
    """Grade the frozen perfect and flawed answers; a sound judge scores perfect at the top and flawed lower."""
    rows = []
    for name, answers in json.loads((DATA / "judge" / "calibration.json").read_text()).items():
        for kind, answer in answers.items():
            result = grade(TASKS[name], answer, votes, 7, model)
            rows.append((name, kind, result["score"], result["of"], result["incorrect_claims_median"]))
            print(name, kind, f"{result['score']}/{result['of']}", "incorrect:", result["incorrect_claims_median"], flush=True)
    return rows


def judge_label(label: str, votes: int, workers: int, model: str, arms: list[str] | None = None) -> int:
    jobs = []
    for record in load_records(label):
        task = TASKS.get(record["task"])
        if not task or not task.get("judge") or record.get("superseded") or (arms and record["arm"] not in arms):
            continue
        out = RESULTS / label / f"{record['run_id']}.judge.json"
        if not out.exists():
            jobs.append((out, record, task))
    random.Random(11).shuffle(jobs)

    def work(job):
        out, record, task = job
        answer = redact(record.get("final_message") or "", record["fixture"])
        result = grade(task, answer, votes, int(record["run_id"], 16) % 10_000, model)
        result["redacted_chars"] = len(answer)
        out.write_text(json.dumps(result, indent=1))
        return out.name, result["score"], result["of"], result["split_items"]

    print(f"{label}: {len(jobs)} answers to judge", flush=True)
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        for name, score, of, split in pool.map(work, jobs):
            print(name, f"{score}/{of}", "split:", split, flush=True)
    return 0
