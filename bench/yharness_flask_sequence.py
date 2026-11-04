"""Prepare and grade two consecutive upstream Flask fixes without model calls."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from common import FIXTURES, REFS, SOURCES, git, tree_hash
from fixtures import PINS, REAL_BUGS, compose, pytest_probe, pytest_suite
from tasks import REAL_PROMPTS, _pytest_changes

TASK_NAMES = ("flask-ipv6-session", "flask-ipv6-run")
FIXTURE = FIXTURES / TASK_NAMES[0]
REFERENCES = REFS / "real"
PYENV = "flask"


def grade(project: Path, stage: int, previous: Path | None = None, *, fixture: Path = FIXTURE) -> dict:
    """Grade stage 1 or 2 against frozen tests and the preceding accepted artifact."""
    if stage not in (1, 2) or (stage == 2) != (previous is not None):
        raise ValueError("Stage 2 requires the accepted stage 1 artifact. Stage 1 uses the frozen fixture.")
    baseline = fixture if previous is None else previous
    if not all((tree / part).is_dir() for tree in (project, baseline) for part in ("src", "tests")):
        return {"success": False, "error": "The current and preceding trees need src and tests."}

    frozen = {}
    for name in TASK_NAMES[:stage]:
        ids = json.loads((REFERENCES / name / "hidden.json").read_text())["ids"]
        if len(ids) != 1:
            raise RuntimeError(f"{name} must have exactly one frozen hidden case")
        frozen[name] = ids[0]

    with TemporaryDirectory(prefix="flask-sequence-grade-") as folder:
        scratch = Path(folder)
        # The later upstream reference includes the earlier test. The candidate supplies only source.
        reference = REFERENCES / TASK_NAMES[stage - 1] / "fix"
        hidden = compose(fixture, project, reference, scratch / "hidden")
        statuses = pytest_probe(hidden, PYENV, "run", *frozen.values())
        checks = {name: statuses.get(case, "error") for name, case in frozen.items()}
        result = {"success": False, "checks": checks}
        if any(status != "pass" for status in checks.values()):
            return result

        final = compose(fixture, project, project, scratch / "final")
        before = compose(fixture, baseline, baseline, scratch / "baseline")
        before_info = pytest_probe(before, PYENV, "list")
        final_info = pytest_probe(final, PYENV, "list")
        if not before_info.get("ids") or not final_info.get("ids"):
            return {**result, "error": "Could not collect tests in both stage snapshots."}
        targets, removed, weakened = _pytest_changes(before_info, final_info)

        original_tests = compose(fixture, project, fixture, scratch / "original-tests")
        suites = {"original": pytest_suite(original_tests, PYENV), "final": pytest_suite(final, PYENV)}
        if previous is not None:
            prior_tests = compose(fixture, project, previous, scratch / "prior-tests")
            suites["previous"] = pytest_suite(prior_tests, PYENV)
        regressions = []
        if targets:
            buggy = compose(fixture, baseline, project, scratch / "without-stage-fix")
            unfixed = pytest_probe(buggy, PYENV, "run", *targets)
            fixed = pytest_probe(final, PYENV, "run", *targets)
            regressions = [test for test in targets if unfixed.get(test) == "fail" and fixed.get(test) == "pass"]
        return {
            **result, "suites": suites, "regression_tests": regressions, "removed_tests": removed,
            "weakened_tests": weakened,
            "success": bool(regressions and not removed and not weakened and all(s["ok"] for s in suites.values())),
        }


def preflight() -> dict:
    """Check the source pins, clean fixture, cumulative grader and negative controls."""
    upstream = SOURCES / PYENV
    pinned = PINS[PYENV][1]
    if git(upstream, "rev-parse", "HEAD", check=True).strip() != pinned:
        raise RuntimeError("The Flask source checkout must match the benchmark pin")
    first, second = (REAL_BUGS[name][1] for name in TASK_NAMES)
    git(upstream, "merge-base", "--is-ancestor", second, pinned, check=True)
    head = git(upstream, "rev-parse", first + "^", check=True).strip()
    if git(upstream, "rev-parse", second + "^", check=True).strip() != first:
        raise RuntimeError("The two Flask fixes must be adjacent upstream commits")
    if (git(FIXTURE, "rev-parse", "HEAD", check=True).strip() != head
            or git(FIXTURE, "status", "--porcelain", "--ignored", check=True)
            or git(FIXTURE, "remote", check=True)
            or git(FIXTURE, "for-each-ref", "--format=%(refname)", check=True).splitlines() != ["refs/heads/main"]
            or any(git(FIXTURE, "cat-file", "-t", fix).strip() for fix in (first, second))):
        raise RuntimeError("The fixture must be the clean first parent with both upstream fixes removed")

    first_fix, both = (REFERENCES / name / "fix" for name in TASK_NAMES)
    with TemporaryDirectory(prefix="flask-sequence-preflight-") as folder:
        scratch = Path(folder)
        later_only = compose(FIXTURE, FIXTURE, FIXTURE, scratch / "later-only")
        for path in ("src/flask/app.py", "tests/test_basic.py"):
            shutil.copy2(both / path, later_only / path)
        missing_test = compose(FIXTURE, both, first_fix, scratch / "missing-second-regression")
        removed_test = compose(FIXTURE, both, both, scratch / "removed-prior-regression")
        shutil.copy2(FIXTURE / "tests/test_testing.py", removed_test / "tests/test_testing.py")
        variants = {
            "unchanged": (FIXTURE, 1, False, ("fail",)),
            "first_fix": (first_fix, 1, True, ("pass",)),
            "first_only_at_second_stage": (first_fix, 2, False, ("pass", "fail")),
            "both_fixes": (both, 2, True, ("pass", "pass")),
            "lost_first_fix": (later_only, 2, False, ("fail", "pass")),
            "missing_second_regression": (missing_test, 2, False, ("pass", "pass")),
            "removed_prior_regression": (removed_test, 2, False, ("pass", "pass")),
        }
        cases = {}
        for name, (project, stage, accepted, statuses) in variants.items():
            result = grade(project, stage, first_fix if stage == 2 else None)
            if result["success"] != accepted or result.get("checks") != dict(zip(TASK_NAMES, statuses)):
                raise RuntimeError(f"Unexpected preflight result for {name}: {result}")
            cases[name] = result
    if cases["missing_second_regression"]["regression_tests"] or not cases["removed_prior_regression"]["removed_tests"]:
        raise RuntimeError("Test retention or stage-local regression control failed")

    return {
        "fixture": TASK_NAMES[0], "fixture_head": head, "fixture_sha256": tree_hash(FIXTURE),
        "upstream_fixes": dict(zip(TASK_NAMES, (first, second))), "cases": cases,
        "tasks": [
            {"name": name, "prompt": REAL_PROMPTS[name].removesuffix(" Please fix it and commit the fix.")
             + " Fix the bug and add a regression test that fails before this change. Preserve existing fixes and tests."}
            for name in TASK_NAMES
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("preflight", help="validate the prepared Flask fixture and reference cases")
    scoring = commands.add_parser("grade", help="grade a candidate from inside a disposable runner")
    scoring.add_argument("stage", type=int, choices=(1, 2))
    scoring.add_argument("project", type=Path)
    scoring.add_argument("--fixture", type=Path, default=FIXTURE, help="the frozen first-stage checkout")
    scoring.add_argument("--previous", type=Path, help="the accepted stage 1 snapshot for stage 2")
    args = parser.parse_args()
    if args.command == "preflight":
        result = preflight()
    else:
        if (args.stage == 2) != (args.previous is not None):
            scoring.error("--previous is required for stage 2 and only accepted for that stage")
        result = grade(args.project, args.stage, args.previous, fixture=args.fixture.resolve())
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
