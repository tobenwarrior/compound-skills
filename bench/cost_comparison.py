"""Compare saved, matched cohorts and calculate an explicit recovery-cost scenario.

The scenario uses the observed failure rates as assumptions. It does not predict
future failures or measure correction sessions, human time, or lifetime savings.
"""
from __future__ import annotations

from collections import defaultdict

from cost_audit import summarize


def compare(records: list[dict], baseline: str, candidate: str, tasks: set[str]) -> dict:
    """Compare the same task repetitions, settings and served models in one label."""
    if baseline == candidate:
        raise ValueError('baseline and candidate must differ')
    selected = [r for r in records if r['task'] in tasks and r['arm'] in (baseline, candidate)]
    by_model = defaultdict(list)
    for record in selected:
        by_model[record['model']].append(record)
    if not by_model:
        raise ValueError('no matching saved records')
    models = []
    for model, rows in sorted(by_model.items()):
        active = {}
        for arm in (baseline, candidate):
            attempts = [r for r in rows if r['arm'] == arm and not r.get('superseded')]
            keys = [(r['task'], r['rep']) for r in attempts]
            if len(set(keys)) != len(keys):
                raise ValueError(f'{model}/{arm}: duplicate active task repetition')
            active[arm] = dict(zip(keys, attempts))
        if not active[baseline] or active[baseline].keys() != active[candidate].keys():
            raise ValueError(f'{model}: arms must contain the same active task repetitions')
        if {key[0] for key in active[baseline]} != tasks:
            raise ValueError(f'{model}: requested tasks are missing')
        for record in rows:
            if (record['task'], record['rep']) not in active[record['arm']]:
                raise ValueError(f'{model}: superseded attempt has no matching active task repetition')
        for key, first in active[baseline].items():
            second = active[candidate][key]
            for field in ('pair_id', 'fixture_head', 'prompt_sha256', 'permissions'):
                if first.get(field) is None or first[field] != second.get(field):
                    raise ValueError(f'{model}/{key}: unmatched {field}')
            served = first.get('result', {}).get('models')
            if not served or served != second.get('result', {}).get('models'):
                raise ValueError(f'{model}/{key}: unmatched served models')
        totals = {}
        for arm in (baseline, candidate):
            audited = summarize([r for r in rows if r['arm'] == arm])['groups']
            current = list(active[arm].values())
            n = len(current)
            accepted = sum(r.get('valid') and r.get('outcome', {}).get('success') is True for r in current)
            ungraded = sum(not isinstance(r.get('outcome', {}).get('success'), bool) for r in current)
            missing = sum(g['missing_cost_records'] for g in audited)
            spend = sum(g['recorded_spend_usd'] for g in audited)
            complete = not missing and not ungraded and all(r.get('valid') for r in current)
            totals[arm] = {
                'tasks': len({r['task'] for r in current}), 'active_attempts': n,
                'recorded_attempts': sum(g['attempts'] for g in audited),
                'accepted': accepted, 'ungraded': ungraded,
                'invalid': sum(g['invalid'] for g in audited),
                'superseded': sum(g['superseded'] for g in audited),
                'missing_cost_records': missing, 'recorded_spend_usd': spend,
                'spend_per_task_usd': spend / n if not missing else None,
                'spend_per_accepted_usd': spend / accepted if accepted and complete else None,
                'failure_rate': 1 - accepted / n if complete else None,
                'mutants_caught': sum(r.get('outcome', {}).get('mutants_caught', 0) for r in current if r.get('valid')),
                'mutants_total': sum(r.get('outcome', {}).get('mutants_total', 0) for r in current if r.get('valid')),
            }
        before, after = totals[baseline], totals[candidate]
        cost_before, cost_after = before['spend_per_task_usd'], after['spend_per_task_usd']
        rates = (before['failure_rate'], after['failure_rate'])
        break_even = None
        if cost_before is not None and cost_after is not None and None not in rates and rates[0] > rates[1]:
            break_even = max(0, (cost_after - cost_before) / (rates[0] - rates[1]))
        models.append({'model': model, 'arms': totals,
                       'recorded_spend_ratio': cost_after / cost_before if cost_before and cost_after is not None else None,
                       'recovery_scenario': {
                           'break_even_usd_per_avoided_failure': break_even,
                           'formula': '(candidate cost per task - baseline cost per task) / (baseline failure rate - candidate failure rate)',
                           'assumptions': 'Observed rates recur; each failure adds the same recovery cost; no recovery spend was measured.',
                       }})
    return {'baseline': baseline, 'candidate': candidate, 'tasks': sorted({r['task'] for r in selected}),
            'cost_basis': 'recorded API list-price estimates; all saved attempts in the selected cohort, including invalid and superseded',
            'scope': 'matched first-attempt cohorts; recovery figures are scenarios, not measured long-term savings',
            'models': models}
