"""Reconcile saved Codex response receipts with benchmark attempts and rollouts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


TOKEN_FIELDS = (
    "input_tokens", "cached_input_tokens", "cache_write_input_tokens",
    "output_tokens", "reasoning_output_tokens", "total_tokens",
)
USAGE_FIELDS = (*TOKEN_FIELDS, "uncached_input_tokens")


def _counters(value):
    if not isinstance(value, dict) or any(
        type(value.get(field)) is not int or value[field] < 0 for field in TOKEN_FIELDS
    ):
        raise ValueError("receipt counters must be nonnegative integers")
    if (value["input_tokens"] + value["output_tokens"] != value["total_tokens"]
            or value["cached_input_tokens"] > value["input_tokens"]
            or value["reasoning_output_tokens"] > value["output_tokens"]):
        raise ValueError("receipt token counters do not reconcile")
    return {field: value[field] for field in TOKEN_FIELDS}


def reconcile_receipts(attempt, seen_responses, thread_totals):
    """Derive known usage, retaining partial receipts and rejecting duplicates."""
    meter = attempt["meter"]
    receipts = meter["receipts"]
    if not isinstance(receipts, list) or len(receipts) != attempt["requests"]:
        raise ValueError("request count must match saved receipts")
    if receipts and any(
        not isinstance(attempt[key], str) or not attempt[key].strip() for key in ("session_id", "turn_id")
    ):
        raise ValueError("receipts need an identified session and turn")

    totals = dict.fromkeys(TOKEN_FIELDS, 0)
    session = (attempt["arm"], attempt.get("session_id"))
    previous_thread = thread_totals.get(session, totals.copy())
    for receipt in receipts:
        if any(receipt[key] != attempt[key] for key in ("session_id", "turn_id")):
            raise ValueError("receipt belongs to a different session or turn")
        response_id = receipt["response_id"]
        if not isinstance(response_id, str) or not response_id.strip():
            raise ValueError("receipt needs a response identity")
        if response_id in seen_responses:
            raise ValueError("duplicate response receipt")
        seen_responses.add(response_id)
        usage = _counters(receipt["usage"])
        if usage["total_tokens"] == 0:
            raise ValueError("response receipt must account for token usage")
        thread = _counters(receipt["thread_token_usage"])
        for field in TOKEN_FIELDS:
            totals[field] += usage[field]
        if (_counters(receipt["turn_token_usage"]) != totals
                or any(thread[field] < totals[field] for field in TOKEN_FIELDS)
                or (previous_thread is not None and any(
                    thread[field] - previous_thread[field] != usage[field] for field in TOKEN_FIELDS
                ))):
            raise ValueError("receipt does not match cumulative turn and thread usage")
        previous_thread = thread

    if attempt["valid_usage"]:
        terminal = meter["terminal_usage"]
        required = {"input_tokens", "cached_input_tokens", "output_tokens"}
        if (not receipts or not isinstance(terminal, dict) or not required <= terminal.keys()
                or any(type(terminal[field]) is not int or terminal[field] != previous_thread[field]
                       for field in TOKEN_FIELDS if field in terminal)):
            raise ValueError("complete usage needs receipts matching terminal usage")
    if session[1] is not None:
        thread_totals[session] = previous_thread if attempt["valid_usage"] else None
    return {**totals, "uncached_input_tokens": totals["input_tokens"] - totals["cached_input_tokens"]}



def _skill_entries(text):
    return {
        line.rpartition(" (file: ")[0] for line in text.splitlines()
        if line.startswith("- ") and " (file: " in line and line.endswith("/SKILL.md)")
    }


def _activation_markers(role, text):
    lines = text.splitlines()
    if role == "developer":
        entries = {
            entry.partition(": ")[0] for entry in _skill_entries(text)
            if entry.startswith("- compound-skills:")
        }
        if "- compound-skills:compound" in entries:
            return {"plugin", "core"}
        return {"plugin"} if entries else set()
    if role != "user" or not lines or not (
        lines[0] == "# AGENTS.md instructions" or lines[0].startswith("# AGENTS.md instructions for ")
    ):
        return set()
    start = "<!-- compound-skills:global-setup:start -->"
    end = "<!-- compound-skills:global-setup:end -->"
    markers = {"rule"} if start in lines or end in lines else set()
    if lines.count(start) == lines.count(end) == 1:
        if any(line.strip() for line in lines[lines.index(start) + 1:lines.index(end)]):
            markers.add("complete-rule")
    return markers


def _audit_rollout(path, pending, arm, catalogues):
    session = None
    cli_version = None
    turn = None
    attempt = None
    receipt_count = prompt_count = context_count = completed = 0
    activation = set()
    activation_checked = False
    default_skills = frozenset()
    receipt_fields = ("response_id", "session_id", "turn_id", "usage", "turn_token_usage", "thread_token_usage")

    def finish_turn():
        if attempt is None:
            return
        if receipt_count != len(attempt["meter"]["receipts"]):
            raise ValueError(f"{arm}: saved rollout is missing a ledger receipt")
        if attempt["valid_usage"]:
            if completed != 1:
                raise ValueError(f"{arm}: saved rollout needs one completed turn event")
            if prompt_count != 1:
                raise ValueError(f"{arm}: saved rollout does not match the delivered prompt")
            if context_count != 1:
                raise ValueError(f"{arm}: saved rollout needs one served model context")

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for line in handle:
            digest.update(line)
            if not line.strip():
                continue
            event = json.loads(line)
            if (not isinstance(event, dict) or not isinstance(event.get("type"), str)
                    or not isinstance(event.get("payload"), dict)):
                raise ValueError(f"{arm}: invalid saved rollout event")
            kind, payload = event["type"], event["payload"]
            if kind == "session_meta":
                if session is not None or not isinstance(payload["id"], str) or not payload["id"]:
                    raise ValueError(f"{arm}: invalid rollout session identity")
                session, cli_version = payload["id"], payload["cli_version"]
            elif kind == "event_msg" and payload["type"] == "task_started":
                finish_turn()
                turn = payload["turn_id"]
                if (session, turn) not in pending:
                    raise ValueError(f"{arm}: saved rollout contains an unrecorded turn")
                attempt, protocol, task = pending.pop((session, turn))
                if f"Codex CLI {cli_version}" != protocol["runtime"]:
                    raise ValueError(f"{arm}: saved rollout does not match the frozen runtime")
                receipt_count = prompt_count = context_count = completed = 0
            elif kind == "token_usage_record":
                receipt = {key: payload[key] for key in receipt_fields}
                if (attempt is None or receipt_count >= len(attempt["meter"]["receipts"])
                        or receipt != attempt["meter"]["receipts"][receipt_count]):
                    raise ValueError(f"{arm}: saved rollout receipt does not match the ledger")
                if not activation_checked and arm != "stock" and not {"core", "complete-rule"} <= activation:
                    raise ValueError(f"{arm}: missing Compound activation in startup context")
                if catalogues.setdefault(task, default_skills) != default_skills:
                    raise ValueError(f"{arm}: default skill catalogue changed for {attempt['task']}")
                activation_checked = True
                receipt_count += 1
            elif kind == "turn_context":
                if (attempt is None or payload["turn_id"] != turn or payload["model"] != protocol["model"]
                        or payload["effort"] != protocol["reasoning_effort"]):
                    raise ValueError(f"{arm}: saved rollout does not match the served model and reasoning setting")
                context_count += 1
            elif kind == "event_msg" and payload["type"] == "task_complete":
                if attempt is None or payload["turn_id"] != turn:
                    raise ValueError(f"{arm}: saved rollout has an unrecorded completed turn")
                completed += 1
            elif kind == "event_msg" and "rerout" in payload["type"]:
                raise ValueError(f"{arm}: saved rollout contains a model reroute")
            elif attempt is not None and kind == "response_item" and payload.get("type") == "message":
                role = payload.get("role")
                for part in payload["content"]:
                    if (not isinstance(part, dict) or part.get("type") != "input_text"
                            or not isinstance(part.get("text"), str)):
                        continue
                    text = part["text"]
                    if role == "developer" and (entries := _skill_entries(text)):
                        default_skills = frozenset(entry for entry in entries if not entry.startswith("- compound-skills:"))
                    if role == "user" and hashlib.sha256(text.encode()).hexdigest() == attempt["prompt_sha256"]:
                        prompt_count += 1
                    elif arm == "stock":
                        if _activation_markers(role, text):
                            raise ValueError(f"{arm}: Compound activation found in stock context")
                    elif not activation_checked and prompt_count == 0:
                        activation.update(_activation_markers(role, text))
    finish_turn()
    return digest.hexdigest()


def audit_rollouts(documents, root, roles):
    """Match all native turn starts and receipts from isolated arm profiles to the ledgers."""
    pending = {arm: {} for arm in roles}
    for document in documents.values():
        for attempt in document["attempts"]:
            session, turn = attempt.get("session_id"), attempt.get("turn_id")
            if not session or not turn:
                continue
            turns = pending[attempt["arm"]]
            if (session, turn) in turns:
                raise ValueError("multiple ledger attempts name the same Codex turn")
            plan = document["plan"]
            sequence, stage, _ = plan["schedule"][attempt["index"]]
            task = document["workload"], sequence, stage
            turns[session, turn] = attempt, plan["protocol"], task

    directories = {arm: (Path(root) / arm).resolve() for arm in roles}
    if len(set(directories.values())) != len(directories):
        raise ValueError("Codex rollouts need a separate directory for each arm")
    files = {}
    catalogues = {}
    for arm, directory in directories.items():
        if not directory.is_dir():
            raise ValueError(f"{arm}: missing Codex rollout directory")
        files[arm] = sorted(_audit_rollout(path, pending[arm], arm, catalogues)
                            for path in sorted(directory.rglob("rollout-*.jsonl")))
        if pending[arm]:
            raise ValueError(f"{arm}: saved rollouts are missing a ledger turn")
    return hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
