#!/usr/bin/env python3
"""Count requests and rejected edits in saved Y Harness events; never run commands.

This audits recorded work. It does not predict which future model calls disappear,
replay a model, execute recorded tools, or turn flagged calls into cost savings.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path


def audit_run(folder: Path) -> dict:
    record_bytes = (folder / 'record.json').read_bytes()
    event_bytes = (folder / 'events.jsonl').read_bytes()
    record = json.loads(record_bytes)
    requests = 0
    calls = {}
    tools = Counter()
    rejected = []
    for line in event_bytes.splitlines():
        event = json.loads(line)
        if event['type'] == 'status' and event.get('phase') == 'step_start':
            requests += 1
        elif event['type'] == 'tool_call':
            call_id = event['callId']
            if call_id in calls:
                raise ValueError('duplicate tool call id')
            calls[call_id] = (event['tool'], requests)
            tools[event['tool']] += 1
        elif event['type'] == 'tool_result':
            tool, step = calls[event['callId']]
            result = event.get('result', '')
            if tool != 'edit' or not isinstance(result, str):
                continue
            for reason in ['file has not been read', 'file changed since it was read']:
                if reason in result:
                    rejected.append(dict(step=step, call_id=event['callId'], reason=reason))
                    break
    if requests != record['requests'] or sum(tools.values()) != record['tool_calls']:
        raise ValueError('record totals do not match saved event counts')
    return dict(run=folder.name, task=record['task'], arm=record['arm'],
                attempt_kind=record.get('attempt_kind', 'unlabeled'), requests=requests,
                tool_calls=sum(tools.values()), tools=dict(sorted(tools.items())),
                edit_precondition_rejections=rejected,
                record_sha256=hashlib.sha256(record_bytes).hexdigest(),
                events_sha256=hashlib.sha256(event_bytes).hexdigest())


def audit(runs: Path) -> dict:
    rows = [audit_run(p.parent) for p in sorted(runs.glob('*/record.json'))]
    if not rows:
        raise ValueError('no saved run records')
    totals = defaultdict(Counter)
    tasks = defaultdict(lambda: defaultdict(Counter))
    for row in rows:
        for destination in [totals[row['arm']], tasks[row['task']][row['arm']]]:
            for key in ['requests', 'tool_calls']:
                destination[key] += row[key]
            destination['edit_precondition_rejections'] += len(row['edit_precondition_rejections'])
    return dict(scope='Saved Y Harness event counts only; no new model calls, projected call savings or cost subtraction.',
                arms={k: dict(v) for k, v in sorted(totals.items())},
                tasks={k: {a: dict(v) for a, v in sorted(arms.items())} for k, arms in sorted(tasks.items())},
                runs=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.runs), indent=2))


if __name__ == '__main__':
    main()
