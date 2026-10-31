"""Grading probe, run inside a copied invoicekit tree (cwd) with PYTHONPATH=src.

    python3 -B probe.py list                 -> {"ids": [...], "functions": {id: ast dump}, "asserts": {id: n}}
    python3 -B probe.py run <id> [<id>..]    -> {"<id>": "pass" | "fail" | "error" | "skip"}
"""
import ast
import json
import sys
import unittest
from pathlib import Path


def iter_tests(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from iter_tests(item)
        else:
            yield item


def functions() -> tuple[dict, dict]:
    dumps, asserts = {}, {}
    for path in sorted(Path("tests").glob("test*.py")):
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name.startswith("test"):
                        key = f"{path.stem}.{node.name}.{item.name}"
                        dumps[key] = ast.dump(item, include_attributes=False)
                        asserts[key] = sum(1 for sub in ast.walk(item) if isinstance(sub, ast.Call)
                                           and isinstance(sub.func, ast.Attribute) and sub.func.attr.startswith(("assert", "fail")))
    return dumps, asserts


class Recorder(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.status = {}

    def addSuccess(self, test):
        self.status[test.id()] = "pass"

    def addFailure(self, test, err):
        self.status[test.id()] = "fail"

    def addError(self, test, err):
        self.status[getattr(test, "id", lambda: str(test))()] = "error"

    def addSkip(self, test, reason):
        self.status[test.id()] = "skip"

    def addExpectedFailure(self, test, err):
        self.status[test.id()] = "pass"

    def addUnexpectedSuccess(self, test):
        self.status[test.id()] = "fail"

    def addSubTest(self, test, subtest, err):
        if err is not None and self.status.get(test.id()) != "error":
            self.status[test.id()] = "fail" if issubclass(err[0], test.failureException) else "error"


def main() -> int:
    sys.path.insert(0, str(Path("tests").resolve()))
    if sys.argv[1] == "list":
        suite = unittest.TestLoader().discover("tests")
        ids = [test.id() for test in iter_tests(suite)]
        dumps, asserts = functions()
        print(json.dumps({"ids": ids, "functions": dumps, "asserts": asserts}))
        return 0
    status = {}
    for test_id in sys.argv[2:]:
        recorder = Recorder()
        try:
            suite = unittest.TestLoader().loadTestsFromName(test_id)
        except Exception:
            status[test_id] = "error"
            continue
        suite.run(recorder)
        status[test_id] = recorder.status.get(test_id, "error" if recorder.errors else "pass" if recorder.wasSuccessful() else "fail")
    print(json.dumps(status))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
