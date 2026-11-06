"""Check saved three-arm correctness and usage without launching agents."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from codex_receipts import USAGE_FIELDS, audit_rollouts, reconcile_receipts
from cost_audit import RESULTS, read_records
from cost_comparison import compare
from yharness_verdict import evaluate, strictly_cheaper, summarize_attempts


ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / 'diagram_sources'
LAST_GOOD = '3ab9db8a2e159a91a24aad006dee5e96c627c98a'
ROLES = ('stock', 'last-good', 'candidate')
WORKLOADS = ('small-edit', 'upstream-fix', 'refactor', 'review', 'navigation')
COST_FIELDS = ('allowance', 'list_cost', 'cost')
NATIVE_PROVIDER = 'codex-chatgpt'
FOLLOWUP_PROMPTS = {'semantic_repair': 'repair_prompt_sha256', 'interruption_recovery': 'recovery_prompt_sha256'}


def _digest(value, lengths=(64,)):
    return isinstance(value, str) and len(value) in lengths and re.fullmatch(r'[0-9a-f]+', value)


def _candidate(candidate):
    if not _digest(candidate, (40, 64)) or candidate == LAST_GOOD:
        raise ValueError('candidate must identify a frozen commit or tree distinct from last-good')


def _validate_plan(plan, candidate):
    expected = {'stock': 'none', 'last-good': LAST_GOOD, 'candidate': candidate}
    if plan['builds'] != expected:
        raise ValueError('stock, pinned last-good and frozen candidate builds must match')
    protocol = plan['protocol']
    provider = protocol['provider']
    if provider not in ('opencode-go', NATIVE_PROVIDER) or any(
        not isinstance(protocol[key], str) or not protocol[key].strip()
        for key in ('runtime', 'model', 'reasoning_effort')
    ):
        raise ValueError('expected a supported provider with frozen model, runtime and reasoning setting')
    if type(protocol['repair_limit']) is not int or protocol['repair_limit'] != 1:
        raise ValueError('expected one repair opportunity per task')
    if provider == NATIVE_PROVIDER:
        timeout = protocol['wall_timeout_seconds']
        guard = protocol['weekly_allowance_guard_percent']
        if type(timeout) is not int or timeout < 1 or type(guard) is not int or not 1 <= guard <= 100:
            raise ValueError('expected a positive Codex attempt timeout and weekly allowance guard')
    else:
        if any(type(protocol[key]) is not int or protocol[key] < 1 for key in ('output_cap', 'request_cap')):
            raise ValueError('output and request caps must be positive integers')
        if not isinstance(protocol['allowance_guard'], str):
            raise ValueError('allowance guard must be a decimal string')
        allowance = Decimal(protocol['allowance_guard'])
        if not allowance.is_finite() or allowance <= 0:
            raise ValueError('expected a positive allowance guard')
    sequences = plan['sequences']
    if len(sequences) != 1 or not sequences[0]['tasks']:
        raise ValueError('expected one nonempty task sequence per workload')
    tasks = sequences[0]['tasks']
    names = [task['name'] for task in tasks]
    hashes = ('fixture_sha256', 'prompt_sha256', 'grader_sha256')
    if provider == NATIVE_PROVIDER:
        hashes += tuple(FOLLOWUP_PROMPTS.values())
    if (any(not isinstance(name, str) or not name.strip() for name in names)
            or len(set(names)) != len(names) or any(
                not _digest(task[key]) for task in tasks
                for key in hashes
            )):
        raise ValueError('each named task needs unique identity and frozen fixture, prompt and grader hashes')
    expected_schedule = {(0, stage, arm) for stage in range(len(tasks)) for arm in ROLES}
    schedule = plan['schedule']
    if len(schedule) != len(expected_schedule) or {tuple(row) for row in schedule} != expected_schedule:
        raise ValueError('schedule must include each task once for each arm')
    if any(type(row[0]) is not int or type(row[1]) is not int for row in schedule):
        raise ValueError('schedule sequence and stage indices must be integers')
    return _hash(plan)


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _pair(plan, attempts, baseline, digest, native):
    aliases = {baseline: 'without', 'candidate': 'with'}
    indices = {}
    schedule = []
    for index, (sequence, stage, arm) in enumerate(plan['schedule']):
        if arm in aliases:
            indices[index] = len(schedule)
            schedule.append([sequence, stage, aliases[arm]])
    pair = {'sequences': plan['sequences'], 'schedule': schedule, 'plan_sha256': digest}
    rows = ({**row, 'index': indices[row['index']], 'arm': aliases[row['arm']]}
            for row in attempts if row['arm'] in aliases)
    if native:
        return summarize_attempts(pair, rows, measure=lambda row, _: row['usage'], fields=USAGE_FIELDS)
    return evaluate(pair, ({**row, 'known_costs': row['costs']} for row in rows))


def _attempt_counts(attempts):
    return {
        'requests': sum(row['requests'] for row in attempts),
        'repairs': sum(row['attempt_kind'] == 'semantic_repair' for row in attempts),
        'recoveries': sum(row['attempt_kind'] == 'interruption_recovery' for row in attempts),
        'usage_complete': bool(attempts) and all(row['valid_usage'] for row in attempts),
    }


def check_workload(document, candidate, *, seen_responses=None):
    """Evaluate one frozen workload with all three arms and every attempt."""
    _candidate(candidate)
    if document['workload'] not in WORKLOADS:
        raise ValueError('unknown workload')
    plan = document['plan']
    digest = _validate_plan(plan, candidate)
    native = plan['protocol']['provider'] == NATIVE_PROVIDER
    if seen_responses is None:
        seen_responses = set()
    rows = document['attempts']
    thread_totals = {}
    if native:
        rows = sorted(rows, key=lambda row: (row['index'], row['attempt']))
    attempts = []
    for row in rows:
        arm = row['arm']
        index = row['index']
        model = row['served_model']
        model_unverified = native and model is None and row['valid_usage'] is False
        if (arm not in ROLES or type(index) is not int or not 0 <= index < len(plan['schedule'])
                or plan['schedule'][index][2] != arm or row['build'] != plan['builds'][arm]
                or (model != plan['protocol']['model'] and not model_unverified) or row['plan_sha256'] != digest):
            raise ValueError('attempt does not match the frozen schedule, build, model or plan')
        stage = plan['schedule'][index][1]
        task = plan['sequences'][0]['tasks'][stage]
        prompt = FOLLOWUP_PROMPTS.get(row['attempt_kind'], 'prompt_sha256') if native else 'prompt_sha256'
        if (row['prompt_sha256'] != task[prompt]
                or any(row[key] != task[key] for key in ('fixture_sha256', 'grader_sha256'))):
            raise ValueError('attempt inputs differ from the frozen task')
        if type(row['requests']) is not int or row['requests'] < (0 if native else 1) or not _digest(row['meter_sha256']):
            raise ValueError('every attempt needs a valid request count and a meter digest')
        if native:
            if row['model_rerouted'] is not False:
                raise ValueError('Codex rerouted the requested model')
            if _hash(row['meter']) != row['meter_sha256']:
                raise ValueError('saved receipt meter digest does not match')
            row = {**row, 'usage': reconcile_receipts(row, seen_responses, thread_totals)}
        attempts.append(row)

    arms = {}
    regressions = []
    blockers = []
    compared_fields = ('total_tokens',) if native else COST_FIELDS
    for baseline in ROLES[:-1]:
        result = _pair(plan, attempts, baseline, digest, native)
        arms[baseline] = result['arms']['without']
        arms['candidate'] = result['arms']['with']
        if not result['complete']:
            blockers.extend(f'{baseline}: {error}' for error in result['errors'])
        elif any(Decimal(arms['candidate']['totals'][key]) > Decimal(arms[baseline]['totals'][key])
                 for key in compared_fields):
            metric = 'total token usage' if native else 'completion cost'
            regressions.append(f'candidate {metric} exceeds {baseline}')
    for arm in ROLES:
        rows = [row for row in attempts if row['arm'] == arm]
        arms[arm].update(_attempt_counts(rows))
        if not native and arms[arm]['requests'] > plan['protocol']['request_cap']:
            raise ValueError(f'{arm}: recorded requests exceed the frozen cap')
    final = {}
    for row in sorted(attempts, key=lambda row: row['attempt']):
        if row['arm'] == 'candidate':
            final[row['stage']] = row
    for row in final.values():
        if row['valid_usage'] and not row['grade']['success'] and not row['grade'].get('infrastructure_error'):
            regressions.append(f"candidate failed {row['task']}")
    status = 'fail' if regressions else 'blocked' if blockers else 'pass'
    return {'status': status, 'complete': not blockers, 'arms': arms,
            'issues': regressions + blockers, 'plan_sha256': digest}


def evaluate_gate(documents, candidate=None, *, codex_rollouts=None):
    """Report independent workload regressions and strict aggregate savings.

    A tie can pass. A usage or cost claim requires every workload to pass
    and strict aggregate improvement against both controls.
    """
    if candidate is not None:
        _candidate(candidate)
    if set(documents) - set(WORKLOADS):
        raise ValueError('unknown workload evidence')
    protocols = [document['plan']['protocol'] for document in documents.values()]
    providers = {protocol['provider'] for protocol in protocols}
    if len(providers) > 1:
        raise ValueError('all workload evidence must use the same provider')
    native = NATIVE_PROVIDER in providers
    if codex_rollouts is not None and not native:
        raise ValueError('Codex rollouts require native Codex workload evidence')
    if native and any(
        protocols[0][key] != protocol[key]
        for protocol in protocols[1:]
        for key in ('model', 'runtime', 'reasoning_effort')
    ):
        raise ValueError('all Codex workloads must use the same model, runtime and reasoning setting')
    workloads = {}
    seen_responses = set()
    for name in WORKLOADS:
        if name not in documents:
            workloads[name] = {'status': 'blocked', 'issues': ['missing matched three-arm evidence']}
        else:
            if documents[name]['workload'] != name:
                raise ValueError(f'{name}: workload label does not match its file')
            workloads[name] = check_workload(documents[name], candidate, seen_responses=seen_responses)
    raw_digest = audit_rollouts(documents, codex_rollouts, ROLES) if codex_rollouts is not None else None
    raw_verified = raw_digest is not None
    statuses = {result['status'] for result in workloads.values()}
    status = 'fail' if 'fail' in statuses else 'blocked' if 'blocked' in statuses else 'pass'
    if native and status == 'pass' and not raw_verified:
        status = 'blocked'
    complete = all(result.get('complete') for result in workloads.values())
    comparisons = dict.fromkeys(ROLES[:-1])
    if native:
        available = [result['arms'] for result in workloads.values() if 'arms' in result]
        known_usage = {
            arm: {field: sum(arms[arm]['totals'][field] for arms in available) for field in USAGE_FIELDS}
            for arm in ROLES
        }
        if complete and raw_verified:
            comparisons = {
                baseline: known_usage['candidate']['total_tokens'] < known_usage[baseline]['total_tokens']
                for baseline in ROLES[:-1]
            }
    elif complete:
        totals = {
            arm: {
                field: sum((Decimal(result['arms'][arm]['totals'][field]) for result in workloads.values()), Decimal(0))
                for field in COST_FIELDS
            }
            for arm in ROLES
        }
        comparisons = {baseline: strictly_cheaper(totals['candidate'], totals[baseline]) for baseline in ROLES[:-1]}
    report = {'status': status, 'builds': {'stock': 'none', 'last-good': LAST_GOOD, 'candidate': candidate},
              'workloads': workloads}
    ready = status == 'pass' and all(comparisons.values())
    if native:
        issues = [] if raw_verified else ['complete Codex rollouts are required to verify native usage']
        return {**report, 'known_usage': known_usage, 'raw_receipts_verified': raw_verified,
                'raw_rollouts_sha256': raw_digest, 'issues': issues,
                'candidate_strictly_lower_usage_at_equal_correctness': comparisons,
                'usage_claim_ready': ready, 'savings_claim_ready': False}
    return {**report, 'candidate_strictly_cheaper_at_equal_correctness': comparisons,
            'savings_claim_ready': ready}


def _saved_comparison(filename):
    data = json.loads((SOURCES / filename).read_text())
    sequences = data['sequences'] if 'sequences' in data else [
        {'tasks': [{'name': task['id']} for task in data['tasks']]}
    ]
    attempts = [
        {**row, 'requests': row.get('requests', row.get('started')), 'known_costs': row['costs']}
        for row in data['attempts']
    ]
    summary = evaluate({'sequences': sequences, 'schedule': data['schedule']}, attempts)
    for mode, arm in summary['arms'].items():
        rows = [row for row in attempts if row['arm'] == mode]
        arm.update(_attempt_counts(rows))
        for stage, outcome in arm['by_stage'].items():
            outcome.update(_attempt_counts([row for row in rows if row['stage'] == int(stage)]))
    return {'source': filename, 'model': data['model'], 'version': data['compound_version'],
            'complete': summary['complete'], 'arms': summary['arms']}


def saved_evidence():
    """Reconcile historical comparisons separately from the release verdict."""
    upstream = _saved_comparison('comparison_flask_v01645.json')
    dispatch = _saved_comparison('comparison_dispatch_v01631.json')
    navigation = _saved_comparison('comparison_navigation_v01657.json')
    result = {'upstream-fix': [upstream], 'navigation': [navigation]}
    if (SOURCES / 'comparison_pstack_flask_v01674.json').is_file():
        pstack = _saved_comparison('comparison_pstack_flask_v01674.json')
        result['upstream-fix'].append({**pstack, 'without_arm': 'pstack'})
    for stage, name in enumerate(('small-edit', 'refactor')):
        result[name] = [{**dispatch, 'stage': stage + 1, 'arms': {
            mode: arm['by_stage'][str(stage)] for mode, arm in dispatch['arms'].items()
        }}]
    try:
        records = read_records('v016b')
    except ValueError:
        result['review'] = [{'source': 'v016b', 'status': 'local saved review records unavailable'}]
        return result
    reviews = [row for row in records if row['task'] == 'review-flask' and row['arm'] in ('without', 'final')]
    for row in reviews:
        path = RESULTS / 'v016b' / f"{row['run_id']}.judge.json"
        if path.is_file():
            grade = json.loads(path.read_text())
            row['outcome']['success'] = (grade['score'] == grade['of'] and grade['incorrect_claims_median'] == 0
                                         and row['outcome']['read_only_respected'])
    result['review'] = [{'source': 'v016b', **compare(reviews, 'without', 'final', {'review-flask'})}]
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, help='directory containing one saved JSON ledger per workload')
    parser.add_argument('--codex-rollouts', type=Path, help='complete native Codex session logs by arm')
    parser.add_argument('--candidate', help='frozen candidate commit or tree hash')
    parser.add_argument('--historical', action='store_true', help='include a separate saved-evidence audit')
    args = parser.parse_args(argv)
    if args.evidence is not None and args.candidate is None:
        parser.error('--evidence requires --candidate')
    try:
        documents = {}
        if args.evidence is not None:
            if not args.evidence.is_dir():
                raise ValueError('evidence directory does not exist')
            for name in WORKLOADS:
                ledger = args.evidence / f'{name}.json'
                if ledger.is_file():
                    documents[name] = json.loads(ledger.read_text())
        report = evaluate_gate(documents, args.candidate, codex_rollouts=args.codex_rollouts)
        if args.historical:
            report['historical'] = saved_evidence()
    except (KeyError, TypeError, ValueError, OSError, InvalidOperation) as exc:
        print(json.dumps({'status': 'blocked', 'issues': [str(exc)]}, indent=2))
        return 2
    print(json.dumps(report, indent=2))
    return {'pass': 0, 'fail': 1, 'blocked': 2}[report['status']]


if __name__ == '__main__':
    raise SystemExit(main())
