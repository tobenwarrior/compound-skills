"""Validate the saved Codex response receipts for one benchmark attempt."""
from __future__ import annotations


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
