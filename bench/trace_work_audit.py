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
import math
from pathlib import Path


def audit_run(folder: Path, include_steps: bool = False) -> dict:
    record_bytes = (folder / 'record.json').read_bytes()
    event_bytes = (folder / 'events.jsonl').read_bytes()
    record = json.loads(record_bytes)
    requests = 0
    terminal_reasons = []
    calls = {}
    tools = Counter()
    rejected = []
    step_tools = defaultdict(list)
    for line in event_bytes.splitlines():
        event = json.loads(line)
        if event['type'] == 'status' and event.get('phase') == 'step_start':
            requests += 1
        elif event['type'] == 'status' and event.get('phase') == 'turn_end':
            terminal_reasons.append(event['reason']['kind'])
        elif event['type'] == 'tool_call':
            call_id = event['callId']
            if call_id in calls:
                raise ValueError('duplicate tool call id')
            calls[call_id] = (event['tool'], requests)
            tools[event['tool']] += 1
            step_tools[requests].append(event['tool'])
        elif event['type'] == 'tool_result':
            tool, step = calls[event['callId']]
            result = event.get('result', '')
            if tool != 'edit' or not isinstance(result, str):
                continue
            for reason in ['file has not been read', 'file changed since it was read']:
                if reason in result:
                    rejected.append(dict(step=step, call_id=event['callId'], reason=reason))
                    break
    recorded = record['requests']
    meter_path = folder / 'requests.jsonl'
    meter_events = []
    if include_steps or (requests != recorded and meter_path.is_file()):
        meter_events = [json.loads(line) for line in meter_path.read_bytes().splitlines()]
    blocked = 0
    if requests == recorded + 1 and not step_tools[requests] and meter_events:
        stop = meter_events[-1]
        starts = [event['number'] for event in meter_events if event['event'] == 'request_started']
        if (stop['event'] == 'budget_stop' and type(stop.get('calls')) is int
                and stop['calls'] == recorded and starts == list(range(1, recorded + 1))):
            # A host step can start before the allowance guard rejects its request.
            requests -= 1
            blocked = 1
    if requests != recorded or sum(tools.values()) != record['tool_calls']:
        raise ValueError('record totals do not match saved event counts')
    result = dict(run=folder.name, task=record['task'], arm=record['arm'],
                attempt_kind=record.get('attempt_kind', 'unlabeled'), requests=requests,
                budget_blocked_steps=blocked, tool_calls=sum(tools.values()), tools=dict(sorted(tools.items())),
                edit_precondition_rejections=rejected,
                record_sha256=hashlib.sha256(record_bytes).hexdigest(),
                events_sha256=hashlib.sha256(event_bytes).hexdigest())
    if include_steps:
        result['terminal_reasons'] = terminal_reasons
        meter = {}
        for response in meter_events:
            if response.get('event') != 'request':
                continue
            number = response['number']
            if number in meter or number < 1 or number > requests:
                raise ValueError('duplicate or out-of-range meter response')
            meter[number] = response
        result['steps'] = []
        for number in range(1, requests + 1):
            response = meter.get(number, {})
            usage = response.get('usage', {}) if response.get('complete') else {}
            allowance = usage.get('allowance')
            if allowance is not None and (type(allowance) not in (int, float) or not math.isfinite(allowance) or allowance < 0):
                raise ValueError('invalid meter usage allowance')
            completion = usage.get('completion_tokens')
            reasoning = usage.get('completion_tokens_details', {}).get('reasoning_tokens')
            for name, count in [('completion', completion), ('reasoning', reasoning)]:
                if count is not None and (type(count) is not int or count < 0):
                    raise ValueError(f'invalid meter {name} token count')
            if reasoning is not None and completion is not None and reasoning > completion:
                raise ValueError('reasoning token count exceeds completion tokens')
            result['steps'].append(dict(request=number, tools=step_tools[number],
                                        allowance_usd=str(allowance) if allowance is not None else None,
                                        completion_tokens=completion, reasoning_tokens=reasoning))
    return result


def audit(runs: Path, include_steps: bool = False) -> dict:
    rows = [audit_run(p.parent, include_steps) for p in sorted(runs.glob('*/record.json'))]
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
    parser.add_argument('--steps', action='store_true', help='Include tool names, recorded usage, reasoning tokens and stop reasons; requires saved request meters')
    args = parser.parse_args()
    print(json.dumps(audit(args.runs, args.steps), indent=2))


if __name__ == '__main__':
    main()
