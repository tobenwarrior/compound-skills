"""Read saved benchmark costs without launching an agent or a judge.

Spend includes invalid and superseded attempts when their cost was recorded.
Acceptance is the existing task grader's success field, not a new quality score.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict

from common import RESULTS


def summarize(records: list[dict]) -> dict:
    """Group recorded spend and accepted outcomes by task, model and arm.

    Missing costs make cost per acceptance unknown. These records do not contain
    linked correction sessions, so no retry or lifetime savings are inferred.
    """
    groups = defaultdict(list)
    for record in records:
        groups[(record['task'], record['model'], record['arm'])].append(record)
    rows = []
    for (task, model, arm), attempts in sorted(groups.items()):
        costs = []
        missing = 0
        for record in attempts:
            cost = record.get('tokens', {}).get('cost_usd')
            if cost is not None and (isinstance(cost, bool) or not isinstance(cost, (int, float))
                                     or not math.isfinite(cost) or cost < 0):
                raise ValueError(f'invalid recorded cost for {task}/{model}/{arm}')
            if cost is None or record.get('result', {}).get('present') is False:
                missing += 1
            if cost is not None:
                costs.append(cost)
        active = [r for r in attempts if r.get('valid') and not r.get('superseded')]
        accepted = sum(r.get('outcome', {}).get('success') is True for r in active)
        rows.append({
            'task': task, 'model': model, 'arm': arm, 'attempts': len(attempts),
            'accepted': accepted,
            'unresolved': sum(r.get('outcome', {}).get('success') is False for r in active),
            'ungraded': sum(r.get('outcome', {}).get('success') is None for r in active),
            'invalid': sum(not r.get('valid') for r in attempts),
            'superseded': sum(bool(r.get('superseded')) for r in attempts),
            'recorded_spend_usd': sum(costs), 'missing_cost_records': missing,
            'spend_per_accepted_usd': sum(costs) / accepted if accepted and not missing else None,
            'tokens': {key: sum(r.get('tokens', {}).get(key, 0) for r in attempts)
                       for key in ('input', 'cache_creation', 'cache_read', 'output')},
            'tool_calls': sum(r.get('trace', {}).get('tool_calls', 0) for r in attempts),
            'map_calls': sum(len(r.get('compound', {}).get('map_calls', [])) for r in attempts),
        })
    return {'scope': 'saved first-attempt batches; no correction or lifetime-cost inference',
            'cost_basis': 'recorded Claude Code list-price estimates, including invalid and superseded attempts',
            'groups': rows}


def read_label(label: str) -> dict:
    """Read a results label, including superseded attempts omitted by outcome reports."""
    folder = RESULTS / label
    if not folder.is_dir():
        raise ValueError(f'no saved results for {label}')
    records = []
    for path in sorted(folder.glob('*.json')):
        if path.name.endswith('.judge.json'):
            continue
        value = json.loads(path.read_text())
        if isinstance(value, dict) and 'pair_id' in value:
            records.append(value)
    if not records:
        raise ValueError(f'no run records for {label}')
    result = summarize(records)
    result['label'] = label
    return result
