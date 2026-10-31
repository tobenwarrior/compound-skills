"""Grading probe for pytest projects, run inside a copied tree (cwd) with the project's src and test packages importable.

    python3 -B probe_pytest.py list                -> {"ids": [...], "functions": {key: ast dump}, "asserts": {key: n}}
    python3 -B probe_pytest.py run <id> [<id>..]   -> {"<id>": "pass" | "fail" | "error" | "skip"}

A test that raises during its own body fails (real bugs often show as exceptions); one that cannot be collected or
set up errors.
"""
import ast
import contextlib
import io
import json
import sys
from pathlib import Path

import pytest

BASE = ["-q", "-p", "no:cacheprovider", "-p", "no:randomly"]


class Collector:
    def __init__(self):
        self.ids = []

    def pytest_collection_modifyitems(self, items):
        self.ids = [item.nodeid for item in items]


class Recorder:
    def __init__(self):
        self.status = {}

    def pytest_runtest_logreport(self, report):
        if report.when == "setup" and report.failed:
            self.status[report.nodeid] = "error"
        elif report.when == "setup" and report.skipped:
            self.status[report.nodeid] = "skip"
        elif report.when == "call":
            self.status[report.nodeid] = "pass" if report.passed else "fail" if report.failed else "skip"
        elif report.when == "teardown" and report.failed and self.status.get(report.nodeid) == "pass":
            self.status[report.nodeid] = "error"


def is_check(node) -> bool:
    if isinstance(node, ast.Assert):
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        return node.func.attr in ("raises", "warns") or node.func.attr.startswith("assert")
    return False


def functions():
    dumps, asserts = {}, {}
    for path in sorted(Path("tests").rglob("test*.py")):
        try:
            tree = ast.parse(path.read_text())
        except (SyntaxError, UnicodeDecodeError):
            continue
        scopes = [("", tree.body)] + [(f"{node.name}::", node.body) for node in tree.body if isinstance(node, ast.ClassDef)]
        for prefix, body in scopes:
            for item in body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name.startswith("test"):
                    key = f"{path.as_posix()}::{prefix}{item.name}"
                    dumps[key] = ast.dump(item, include_attributes=False)
                    asserts[key] = sum(1 for sub in ast.walk(item) if is_check(sub))
    return dumps, asserts


def main() -> int:
    if sys.argv[1] == "list":
        collector = Collector()
        with contextlib.redirect_stdout(io.StringIO()):
            pytest.main([*BASE, "--collect-only"], plugins=[collector])
        dumps, asserts = functions()
        print(json.dumps({"ids": collector.ids, "functions": dumps, "asserts": asserts}))
        return 0
    ids = sys.argv[2:]
    recorder = Recorder()
    if ids:
        with contextlib.redirect_stdout(io.StringIO()):
            pytest.main([*BASE, *ids], plugins=[recorder])
    print(json.dumps({i: recorder.status.get(i, "error") for i in ids}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
