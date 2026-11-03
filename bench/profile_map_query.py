#!/usr/bin/env python3
"""Profile local query ranking; no model calls, source execution or cache writes.

Run separately against two script directories and compare result_sha256 before
interpreting timings. This measures in-process ranking, not CLI startup, agent
navigation, correctness of a coding task, or model cost.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
from unittest import mock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--scripts', type=Path, default=Path(__file__).resolve().parents[1] / 'skills/compound/scripts')
    parser.add_argument('--query', action='append', required=True)
    parser.add_argument('--repetitions', type=int, default=31)
    args = parser.parse_args()
    if not 5 <= args.repetitions <= 1000:
        parser.error('--repetitions must be between 5 and 1000')
    scripts, root = args.scripts.resolve(), args.repo.resolve()
    sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location('profiled_code_map', scripts / 'code_map.py')
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    model, _ = engine.build_map(root, no_cache=True)
    records = model['files']
    results = []
    for query in args.query:
        for _ in range(3):
            engine._rank(records, query, root)
        samples, cpu_samples = [], []
        digests = set()
        for _ in range(args.repetitions):
            start = time.perf_counter()
            cpu_start = time.process_time()
            ranked = engine._rank(records, query, root)
            samples.append((time.perf_counter() - start) * 1000)
            cpu_samples.append((time.process_time() - cpu_start) * 1000)
            digests.add(hashlib.sha256(json.dumps([r['path'] for r in ranked]).encode()).hexdigest())
        if len(digests) != 1:
            raise RuntimeError('Ranking changed during timing; discard this measurement')
        original_open = engine.os.open
        counts = {'open_calls': 0, 'root_walks': 0}
        def counted(path, flags, *rest, **kwargs):
            counts['open_calls'] += 1
            counts['root_walks'] += str(path) == root.anchor
            return original_open(path, flags, *rest, **kwargs)
        with mock.patch.object(engine.os, 'open', side_effect=counted) as opened, mock.patch.object(engine.os, 'supports_dir_fd', {opened}):
            engine._rank(records, query, root)
        results.append(dict(query=query, median_ms=statistics.median(samples), median_cpu_ms=statistics.median(cpu_samples), min_ms=min(samples),
                            p95_ms=sorted(samples)[math.ceil(len(samples)*.95)-1],
                            result_sha256=next(iter(digests)), **counts))
    revision = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], check=True, capture_output=True, text=True).stdout.strip()
    sources = {name: hashlib.sha256((scripts / name).read_bytes()).hexdigest() for name in ['code_map.py', 'safe_open.py']}
    print(json.dumps(dict(repository=root.name, revision=revision, files=len(records),
                         platform=platform.system()+' '+platform.machine(), python=platform.python_version(),
                         repetitions=args.repetitions, warmups=3, source_sha256=sources, results=results), indent=2))


if __name__ == '__main__':
    main()
