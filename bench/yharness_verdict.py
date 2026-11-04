"""Offline completion comparison verdicts for a frozen Y Harness run.

The evaluator consumes a frozen plan and records that have already passed the
runner's raw-meter validation.  It still validates the experiment ledger before
making a cost claim, so an incomplete or mixed schedule can never look cheap.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable


class VerdictError(ValueError):
    """Raised when the plan or record ledger is malformed."""


_COST_FIELDS = ("allowance", "list_cost", "cost")
_ATTEMPT_KINDS = {"initial", "semantic_repair", "interruption_recovery"}


def _decimal(value: Any, field: str, location: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise VerdictError(f"{location}: {field} is not a decimal amount")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise VerdictError(f"{location}: {field} is not a decimal amount") from exc
    if not number.is_finite() or number < 0:
        raise VerdictError(f"{location}: {field} is not a non-negative decimal amount")
    return number


def _expected_schedule(plan: dict[str, Any]) -> dict[int, tuple[int, str]]:
    schedule = plan.get("schedule")
    sequences = plan.get("sequences")
    if not isinstance(schedule, list) or not isinstance(sequences, list) or len(sequences) != 1:
        raise VerdictError("plan must contain one sequence and a schedule")
    sequence = sequences[0]
    tasks = sequence.get("tasks") if isinstance(sequence, dict) else None
    if not isinstance(tasks, list) or not tasks:
        raise VerdictError("plan sequence must contain tasks")

    expected: dict[int, tuple[int, str]] = {}
    for schedule_index, item in enumerate(schedule):
        if not isinstance(item, list) or len(item) != 3:
            raise VerdictError("schedule entry must be [sequence, stage, arm]")
        sequence_index, stage, arm = item
        if type(sequence_index) is not int or sequence_index != 0 or type(stage) is not int or stage < 0 or not isinstance(arm, str):
            raise VerdictError("schedule entry has invalid index, stage, or arm")
        if stage >= len(tasks) or not isinstance(tasks[stage], dict) or not isinstance(tasks[stage].get("name"), str):
            raise VerdictError(f"schedule index {schedule_index} names an unknown stage")
        if arm not in {"without", "with"}:
            raise VerdictError(f"schedule index {schedule_index} names an unsupported arm")
        expected[schedule_index] = (stage, arm)
    expected_pairs = {(stage, arm) for stage, arm in expected.values()}
    required_pairs = {(stage, arm) for stage in range(len(tasks)) for arm in ("without", "with")}
    if expected_pairs != required_pairs or len(expected) != len(required_pairs):
        raise VerdictError("schedule must contain exactly one entry for every stage in both arms")
    for arm in ("without", "with"):
        if [stage for stage, mode in expected.values() if mode == arm] != list(range(len(tasks))):
            raise VerdictError(f"{arm}: stages must run in order")
    return expected


def _record_costs(record: dict[str, Any], location: str) -> dict[str, Decimal]:
    costs = record.get("known_costs")
    if not isinstance(costs, dict):
        raise VerdictError(f"{location}: missing known_costs")
    return {field: _decimal(costs.get(field), field, location) for field in _COST_FIELDS}


def _record_acceptance(record: dict[str, Any], location: str) -> bool:
    grade = record.get("grade")
    if not isinstance(grade, dict) or type(grade.get("success")) is not bool:
        raise VerdictError(f"{location}: missing boolean grade.success")
    if type(record.get("valid_usage")) is not bool:
        raise VerdictError(f"{location}: missing boolean valid_usage")
    expected = bool(grade["success"] and record["valid_usage"])
    if type(record.get("accepted")) is not bool or record["accepted"] != expected:
        raise VerdictError(f"{location}: accepted does not match grade.success and valid_usage")
    return record["accepted"]


def _totals(attempts):
    return {
        field: str(sum((attempt["costs"][field] for attempt in attempts), Decimal(0)))
        for field in _COST_FIELDS
    }


def evaluate(plan: dict[str, Any], records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Return a strict, decimal-exact verdict for a completed two-arm run.

    Every attempt contributes to the arm totals, including failed initial
    attempts and one permitted follow-up.  ``claim`` is true only when both
    arms completed every scheduled stage with accepted artifacts and the
    Compound arm is strictly cheaper in allowance and list price with no cash
    increase.
    """
    expected = _expected_schedule(plan)
    plan_hash = plan.get("plan_sha256")
    by_index: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for ordinal, record in enumerate(records):
        location = f"record {ordinal}"
        if not isinstance(record, dict):
            raise VerdictError(f"{location}: record is not an object")
        index = record.get("index")
        if type(index) is not int or index not in expected:
            raise VerdictError(f"{location}: orphan schedule index")
        stage, arm = expected[index]
        if record.get("stage") != stage or record.get("arm") != arm:
            raise VerdictError(f"{location}: stage or arm does not match schedule index {index}")
        if record.get("task") != plan["sequences"][0]["tasks"][stage]["name"]:
            raise VerdictError(f"{location}: task does not match schedule index {index}")
        if plan_hash is not None and record.get("plan_sha256") != plan_hash:
            raise VerdictError(f"{location}: plan hash does not match frozen plan")
        attempt = record.get("attempt")
        if type(attempt) is not int or attempt < 0 or attempt > 1:
            raise VerdictError(f"{location}: attempt must be zero or one")
        kind = record.get("attempt_kind")
        if kind not in _ATTEMPT_KINDS or (attempt == 0 and kind != "initial") or (attempt == 1 and kind == "initial"):
            raise VerdictError(f"{location}: invalid attempt kind")
        accepted = _record_acceptance(record, location)
        costs = _record_costs(record, location)
        by_index[index].append({"record": record, "accepted": accepted, "costs": costs})

    for index, attempts in by_index.items():
        attempts.sort(key=lambda item: item["record"]["attempt"])
        numbers = [item["record"]["attempt"] for item in attempts]
        if len(numbers) != len(set(numbers)) or sorted(numbers) not in ([0], [0, 1]):
            raise VerdictError(f"schedule index {index}: duplicate or missing attempt sequence")
        if len(attempts) == 2 and attempts[0]["accepted"]:
            raise VerdictError(f"schedule index {index}: follow-up follows an accepted artifact")

    errors = [f"schedule index {index}: missing scheduled task" for index in sorted(set(expected) - set(by_index))]

    arms: dict[str, dict[str, Any]] = {}
    for arm in ("without", "with"):
        arm_attempts = []
        by_stage = {}
        for index, (stage, mode) in expected.items():
            if mode != arm or index not in by_index:
                continue
            attempts = by_index[index]
            arm_attempts.extend(attempts)
            by_stage[str(stage)] = {
                "attempts": len(attempts),
                "accepted": attempts[-1]["accepted"],
                "totals": _totals(attempts),
            }
        stages = sorted(int(stage) for stage in by_stage)
        accepted_stages = sorted(int(stage) for stage, item in by_stage.items() if item["accepted"])
        arms[arm] = {
            "attempts": len(arm_attempts),
            "stages": stages,
            "accepted_stages": accepted_stages,
            "by_stage": by_stage,
            "totals": _totals(arm_attempts),
        }

    expected_by_arm = {
        arm: sorted(stage for stage, scheduled_arm in expected.values() if scheduled_arm == arm)
        for arm in ("without", "with")
    }
    complete = not errors and all(
        arms[arm]["accepted_stages"] == expected_by_arm[arm] and arms[arm]["stages"] == expected_by_arm[arm]
        for arm in ("without", "with")
    )
    if not complete:
        errors.append("both arms must accept every scheduled stage")

    cheaper = False
    if complete:
        without = {field: Decimal(value) for field, value in arms["without"]["totals"].items()}
        with_ = {field: Decimal(value) for field, value in arms["with"]["totals"].items()}
        cheaper = (
            with_["allowance"] < without["allowance"]
            and with_["list_cost"] < without["list_cost"]
            and with_["cost"] <= without["cost"]
        )
        if not cheaper:
            errors.append("Compound is not strictly cheaper in allowance and list cost without a cash increase")

    return {
        "valid": True,
        "claim": cheaper,
        "complete": complete,
        "compound_cheaper": cheaper,
        "errors": errors,
        "arms": arms,
    }
