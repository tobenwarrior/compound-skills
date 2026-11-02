"""Re-render saved agent map queries on their clean, frozen fixtures; no model calls.

Only this repository's trusted baseline renderer executes. Fixture source is read
as data. This measures emitted context, not future agent actions or billed cost.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def saved_queries(results: Path, arm: str) -> list[dict]:
    queries = []
    for path in sorted(results.glob('*.json')):
        record = json.loads(path.read_text())
        if not isinstance(record, dict) or record.get('arm') != arm or 'pair_id' not in record:
            continue
        if record.get('superseded') or not record.get('valid'):
            continue
        for command in record.get('trace', {}).get('bash', []):
            if 'code_map.py' not in command:
                continue
            tokens = shlex.split(command)
            if '--query' not in tokens:
                continue
            # Parse recorded arguments, never execute a saved shell command.
            query = tokens[tokens.index('--query') + 1]
            limit = int(tokens[tokens.index('--max-chars') + 1]) if '--max-chars' in tokens else 2500
            queries.append({'task': record['task'], 'model': record['model'],
                            'run_id': record['run_id'], 'fixture': record['fixture'],
                            'fixture_head': record['fixture_head'], 'query': query, 'max_chars': limit})
    if not queries:
        raise ValueError('no saved map queries in this arm')
    return queries


def measure(baseline, candidate, model: dict, query: str, limit: int) -> dict:
    original = copy.deepcopy(model)
    before = baseline._text(model, limit, query)
    after = candidate._text(model, limit, query)
    full = candidate._text(model, 10**9, query)
    # The complete ordered focus list, every matching symbol up to the existing
    # per-file cap, and all import hints remain; only unrelated outlines disappear.
    if model != original:
        raise ValueError('renderer changed shared map metadata')
    from map_context import complete_entries
    if complete_entries(after, model) < complete_entries(before, model):
        raise ValueError('candidate exposes fewer complete focus entries')
    for path in model['focus']:
        if json.dumps(path, ensure_ascii=True) not in full:
            raise ValueError('candidate dropped a ranked path')
    terms = candidate._query_terms(query)[0]
    for file in model['files']:
        if file['path'] not in model['focus']:
            continue
        prefix = f"- {json.dumps(file['path'], ensure_ascii=True)} ["
        before_row = next((line for line in before.splitlines() if line.startswith(prefix)), '')
        after_row = next((line for line in after.splitlines() if line.startswith(prefix)), '')
        for symbol in file['symbols']:
            names = candidate._name_terms(symbol['name'])
            signature = candidate._name_terms(symbol.get('signature', ''))
            if not any(term in names or term in signature for term in terms):
                continue
            declaration = (symbol.get('signature') or symbol['name']) + f" ({symbol['kind']}:{symbol['line']})"
            if declaration in before_row and declaration not in after_row:
                raise ValueError('candidate lost a visible matching declaration')
    return {'before_bytes': len(before.encode()), 'after_bytes': len(after.encode()),
            'before_complete_entries': complete_entries(before, model),
            'after_complete_entries': complete_entries(after, model)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', required=True, type=Path)
    parser.add_argument('--fixtures', required=True, type=Path)
    parser.add_argument('--arm', default='final')
    parser.add_argument('--baseline-ref', required=True)
    parser.add_argument('--baseline-repo', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    scripts = Path(__file__).resolve().parents[1] / 'skills/compound/scripts'
    sys.path.insert(0, str(scripts))
    queries = saved_queries(args.results, args.arm)
    revision = subprocess.check_output(['git', 'rev-parse', '--verify', f'{args.baseline_ref}^{{commit}}'], cwd=args.baseline_repo, text=True).strip()
    source = subprocess.check_output(['git', 'show', f'{revision}:skills/compound/scripts/code_map.py'], cwd=args.baseline_repo)
    with tempfile.TemporaryDirectory(prefix='compound-query-replay-') as directory:
        file = Path(directory)/'baseline.py';file.write_bytes(source)
        baseline = load(file, 'saved_query_baseline')
        candidate = load(scripts/'code_map.py', 'saved_query_candidate')
        rows = []
        for item in queries:
            name = Path(item['fixture'])
            if name.is_absolute() or len(name.parts) != 1 or name.name in ('.', '..'):
                raise ValueError('fixture must name one local directory')
            fixture = args.fixtures/name
            head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=fixture, text=True).strip()
            dirty = subprocess.check_output(['git', 'status', '--porcelain'], cwd=fixture, text=True).strip()
            if head != item['fixture_head'] or dirty:
                raise ValueError('fixture differs from the clean saved revision')
            model, _ = baseline.build_map(fixture, query=item['query'], no_cache=True, output_format='json')
            limit = baseline._clamp(item['max_chars'], 500, baseline.MAX_CHARS)
            rows.append({**item, **measure(baseline, candidate, model, item['query'], limit)})
        before = sum(row['before_bytes'] for row in rows)
        after = sum(row['after_bytes'] for row in rows)
        print(json.dumps({'baseline':revision, 'scope':'offline rendering of saved queries; no model actions or billed savings measured',
                          'queries':rows, 'total_before_bytes':before, 'total_after_bytes':after,
                          'output_reduction_pct':round(100*(1-after/before),1)},indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
