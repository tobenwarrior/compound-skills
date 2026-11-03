#!/usr/bin/env python3
"""Replay saved map-query inputs locally; never execute saved tools or call models."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def load(path, name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--events',type=Path,required=True)
    parser.add_argument('--fixture',type=Path,required=True)
    parser.add_argument('--fixture-head',required=True)
    parser.add_argument('--baseline-ref',required=True)
    args=parser.parse_args()
    def git(*argv,cwd=ROOT):
        return subprocess.check_output(['git',*argv],cwd=cwd,text=True).strip()
    if git('rev-parse','HEAD',cwd=args.fixture)!=args.fixture_head or git('status','--porcelain',cwd=args.fixture):
        raise ValueError('fixture must be clean at the saved revision')
    queries=[]
    events=args.events.read_bytes()
    for line in events.splitlines():
        event=json.loads(line)
        if event['type']!='tool_call' or event['tool']!='bash':continue
        tokens=shlex.split(event['input'].get('command',''))
        if any(Path(token).name=='code_map.py' for token in tokens) and '--query' in tokens:
            queries.append(tokens[tokens.index('--query')+1])
    if not queries:raise ValueError('no recorded map queries')
    revision=git('rev-parse','--verify',args.baseline_ref+'^{commit}')
    source=subprocess.check_output(['git','show',revision+':skills/compound/scripts/code_map.py'],cwd=ROOT)
    scripts=ROOT/'skills/compound/scripts';sys.path.insert(0,str(scripts))
    current=load(scripts/'code_map.py','scope_current')
    rows=[]
    with tempfile.TemporaryDirectory(prefix='compound-navigation-replay-') as folder:
        baseline_file=Path(folder)/'baseline.py';baseline_file.write_bytes(source)
        baseline=load(baseline_file,'scope_baseline')
        for query in queries:
            before,before_text=baseline.build_map(args.fixture,query=query,no_cache=True)
            after,after_text=current.build_map(args.fixture,query=query,no_cache=True)
            if before['files']!=after['files'] or before['focus']!=after['focus']:
                raise ValueError('full ranked index changed; not a presentation-only comparison')
            shown=after['query_matches']
            for path in shown:
                if json.dumps(path) not in after_text:raise ValueError('matching candidate truncated')
            rows.append(dict(query=query,before_candidates=len(before['focus']),after_candidates=len(shown),
                             retained=shown,omitted_unmatched=[p for p in before['focus'] if p not in shown],
                             full_index_sha256=hashlib.sha256(json.dumps(after['files'],sort_keys=True).encode()).hexdigest(),
                             before_summary_bytes=len(before_text.encode()),after_summary_bytes=len(after_text.encode())))
    print(json.dumps(dict(scope='Offline replay of saved Y Harness query inputs; unchanged full JSON index and ranking. No agent actions, model calls or cost savings measured.',
                         baseline=revision,fixture_head=args.fixture_head,events_sha256=hashlib.sha256(events).hexdigest(),queries=rows),indent=2))


if __name__=='__main__':main()
