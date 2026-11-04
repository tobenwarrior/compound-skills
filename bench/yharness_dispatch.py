"""Grade the dispatchkit sequence with independent, cumulative checks."""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import json
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

# The isolated grader bundle places benchmark helpers in a sibling bench/ directory.
sys.path.insert(0, str(Path(__file__).resolve().parent / "bench"))
from tasks import _probe, _tree, _unittest


CHECKS = ("test_bug", "test_refactor")


def _test_classes(tree: Path) -> dict[str, ast.ClassDef]:
    """Index original test classes so modifications to shared setup are also visible."""
    classes = {}
    for path in sorted((tree / "tests").glob("test*.py")):
        for node in ast.parse(path.read_text()).body:
            if isinstance(node, ast.ClassDef):
                classes[f"{path.stem}.{node.name}"] = node
    return classes


def _retained_tests(original: Path, project: Path) -> tuple[bool, list[str]]:
    """Require each original test class header and member, allowing added test cases."""
    expected = _test_classes(original)
    actual = _test_classes(project)
    changed = []
    for name, old in expected.items():
        new = actual.get(name)
        if new is None:
            changed.append(name)
            continue
        old_header = [ast.dump(field) for field in old.bases + old.keywords + old.decorator_list]
        new_header = [ast.dump(field) for field in new.bases + new.keywords + new.decorator_list]
        old_members = Counter(ast.dump(member) for member in old.body)
        new_members = Counter(ast.dump(member) for member in new.body)
        if old_header != new_header or old_members - new_members:
            changed.append(name)
    before, after = _probe(original, "list"), _probe(project, "list")
    original_ids = set(before.get("ids", ()))
    final_ids = set(after.get("ids", ()))
    retained = bool(original_ids) and original_ids <= final_ids and not changed and "probe_error" not in after
    return retained, changed + sorted(original_ids - final_ids)


def _regression_test(original: Path, final: Path, scratch: Path) -> bool:
    """Confirm a new agent test passes on the fix and fails on original source."""
    original_ids = set(_probe(original, "list").get("ids", ()))
    added = sorted(set(_probe(final, "list").get("ids", ())) - original_ids)
    if not added:
        return False
    buggy = _tree(original, final, scratch / "buggy")
    before, after = _probe(buggy, "run", *added), _probe(final, "run", *added)
    return any(before.get(case) == "fail" and after.get(case) == "pass" for case in added)


def grade(project: Path, original: Path, hidden: Path, stage: int) -> dict:
    """Check the current task, earlier tasks, and original and final test suites."""
    if not 0 <= stage < len(CHECKS):
        raise ValueError(f"Invalid dispatchkit stage {stage}")
    missing = [name for name in ("src", "tests") if not (project / name).is_dir()]
    if missing:
        return {"success": False, "failure_output": f"Missing required directories: {', '.join(missing)}"}
    with TemporaryDirectory(prefix="dispatch-grade-") as folder:
        scratch = Path(folder)
        final = _tree(project, project, scratch / "final")
        original_tests = _tree(project, original, scratch / "original")
        before = _unittest(original_tests, "discover", "-s", "tests")
        after = _unittest(final, "discover", "-s", "tests")
        try:
            retained, changed = _retained_tests(original, final)
        except SyntaxError:
            retained, changed = False, ["Unparseable test source"]
        checks = {}
        failures = []
        for name in CHECKS[: stage + 1]:
            check = f"_dispatch_{name}"
            shutil.copyfile(hidden / f"{name}.py", final / f"{check}.py")
            result = _unittest(final, check, "-v")
            checks[name] = result["ok"] and result["tests"] > 0
            if not checks[name]:
                failures.append(f"{name}: {result['tail'][-1]}")
        regression_test = checks["test_bug"] and _regression_test(original, final, scratch)
        if not regression_test:
            failures.append("An added regression test must fail on the original source and pass on the changed source.")
        success = all(checks.values()) and regression_test and before["ok"] and after["ok"] and retained
        return {"success": success, "checks": checks, "original_suite": before,
                "own_suite": after, "original_tests_retained": retained,
                "changed_original_tests": changed, "regression_test": regression_test,
                "failure_output": "\n".join(failures)}


def validate(root: Path) -> dict:
    """Verify both tasks before dispatch using independent passing and failing variants."""
    root = root.resolve()
    fixture, hidden, overlays = root / "fixture", root / "hidden", root / "overlays"
    expected = (
        ("unchanged", (), 0, False, {"test_bug": False}),
        ("fixed", ("bug-fix",), 0, True, {"test_bug": True}),
        ("duplication remains", ("bug-fix",), 1, False, {"test_bug": True, "test_refactor": False}),
        ("naive extraction", ("bug-fix", "refactor-naive"), 1, False, {"test_bug": True, "test_refactor": False}),
        ("preserving extraction", ("bug-fix", "refactor-preserving"), 1, True, {"test_bug": True, "test_refactor": True}),
        ("lost earlier fix", ("refactor-preserving",), 1, False, {"test_bug": False, "test_refactor": True}),
    )
    results = {}
    with TemporaryDirectory(prefix="dispatch-validate-") as folder:
        for label, variants, stage, success, checks in expected:
            project = Path(folder) / label
            shutil.copytree(fixture, project)
            for variant in variants:
                shutil.copytree(overlays / variant, project, dirs_exist_ok=True)
            result = grade(project, fixture, hidden, stage)
            assert result["success"] is success and result["checks"] == checks, (label, result)
            assert result["original_suite"]["ok"] and result["own_suite"]["ok"], (label, result)
            results[label] = result["success"]
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", type=int, nargs="?")
    parser.add_argument("--validate", type=Path)
    options = parser.parse_args()
    if options.validate is not None and options.stage is None:
        result = validate(options.validate)
    elif options.stage is not None and options.validate is None:
        result = grade(Path("/input/project"), Path("/input/original"), Path("/grader/hidden"), options.stage)
    else:
        parser.error("pass a stage or --validate")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
