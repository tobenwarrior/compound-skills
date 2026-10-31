"""Benchmark tasks and their graders. Prompts are identical in every arm and never mention Compound.

A task is a dict in TASKS:
  name, fixture (a folder built by fixtures.py), kind ("write" may run code and commit; "read" may read but never
  run project code), prompt, timeout (seconds), grade(project, record, prep) -> dict of outcome fields,
  optional symptom (regex for output that shows the reported defect), judge (a key for judge.py), tags, about.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from common import BENCH, DATA, FIXTURES, GIT_IDENTITY, REFS
from fixtures import compose, pytest_probe, pytest_suite

FIXTURE = FIXTURES / "invoicekit"
HIDDEN = DATA / "hidden"
PROBE = BENCH / "probe.py"
BUGS = ("refund", "leap", "december")


def _env(tree: Path) -> dict:
    return {"PATH": "/usr/bin:/bin", "PYTHONPATH": str(tree / "src"), "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C.UTF-8",
            "HOME": str(tree)}


def _unittest(tree: Path, *args: str) -> dict:
    out = subprocess.run([sys.executable, "-B", "-m", "unittest", *args], cwd=tree, env=_env(tree), capture_output=True,
                         text=True, timeout=300)
    text = out.stderr or out.stdout
    ran = re.search(r"Ran (\d+) tests?", text)
    return {"ok": out.returncode == 0, "tests": int(ran.group(1)) if ran else 0, "tail": text.strip().splitlines()[-1:] or [""]}


def _probe(tree: Path, *args: str) -> dict:
    out = subprocess.run([sys.executable, "-B", str(PROBE), *args], cwd=tree, env=_env(tree), capture_output=True, text=True, timeout=300)
    try:
        return json.loads(out.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {"probe_error": (out.stderr or out.stdout)[-500:]}


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True).stdout


def _tree(src_from: Path, tests_from: Path, dest: Path) -> Path:
    """A tree with src/ from one place and tests/ from another."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    shutil.copytree(src_from / "src", dest / "src", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(tests_from / "tests", dest / "tests", ignore=shutil.ignore_patterns("__pycache__"))
    return dest


def _hidden(tree: Path, name: str) -> bool:
    probe = tree.parent / f"hidden-{name}-{tree.name}"
    if probe.exists():
        shutil.rmtree(probe)
    shutil.copytree(tree, probe, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    shutil.copy(HIDDEN / f"hidden_{name}.py", probe / f"hidden_{name}.py")
    ok = _unittest(probe, f"hidden_{name}")["ok"]
    shutil.rmtree(probe, ignore_errors=True)
    return ok


def _diff(project: Path, base: str) -> dict:
    subprocess.run(["git", "-C", str(project), "add", "-A", "-N", "."], capture_output=True)
    numstat = _git(project, "diff", base, "--numstat")
    files, src, tests, other = [], 0, 0, []
    for line in numstat.splitlines():
        added, removed, name = line.split("\t", 2)
        lines = (int(added) if added.isdigit() else 0) + (int(removed) if removed.isdigit() else 0)
        files.append(name)
        if name.startswith("src/"):
            src += lines
        elif name.startswith("tests/"):
            tests += lines
        else:
            other.append(name)
    subprocess.run(["git", "-C", str(project), "reset", "-q"], capture_output=True)
    return {"files": files, "src_lines": src, "test_lines": tests, "other_files": other}


def _commits(project: Path, base: str) -> dict:
    count = int(_git(project, "rev-list", "--count", f"{base}..HEAD").strip() or 0)
    if not count:
        return {"commit_made": False, "commit_count": 0}
    messages = _git(project, "log", "--format=%B%x00", f"{base}..HEAD").split("\0")
    authors = set(_git(project, "log", "--format=%an <%ae>|%cn <%ce>", f"{base}..HEAD").splitlines())
    body = "\n".join(messages)
    subjects = [m.strip().splitlines()[0] for m in messages if m.strip()]
    touched = _git(project, "diff", "--name-only", base, "HEAD").split()
    return {"commit_made": True, "commit_count": count, "subjects": subjects,
            "ai_trailer": bool(re.search(r"(?i)co-authored-by:.*(claude|anthropic)", body)),
            "generated_by": bool(re.search(r"(?i)generated (with|by) .*claude", body)),
            "conventional": all(re.match(r"^(feat|fix|refactor|test|docs|chore|perf|build|ci|style)(\(.+\))?!?: ", s) for s in subjects),
            "subject_max_len": max(len(s) for s in subjects) if subjects else 0,
            "author_ok": all(f"{GIT_IDENTITY[0]} <{GIT_IDENTITY[1]}>" == part for line in authors for part in line.split("|")) if authors else False,
            "commit_includes_tests": any(name.startswith("tests/") for name in touched),
            "commit_other_files": [name for name in touched if not name.startswith(("src/", "tests/"))],
            "uncommitted_after": [line for line in _git(project, "status", "--porcelain").splitlines()]}


def _test_changes(work: Path, fixture_info: dict, final_info: dict) -> tuple[list[str], list[str], list[str]]:
    """New or changed test ids, removed existing ids, and weakened existing ids."""
    new = [i for i in final_info.get("ids", []) if i not in fixture_info.get("ids", [])]
    changed = [key for key, dump in final_info.get("functions", {}).items()
               if key in fixture_info.get("functions", {}) and fixture_info["functions"][key] != dump]
    changed_ids = [i for i in final_info.get("ids", []) if any(i.endswith(key) for key in changed)]
    targets = list(dict.fromkeys(new + changed_ids))
    targets = [t for t in targets if not t.startswith("unittest.loader")]
    removed = [i for i in fixture_info.get("ids", []) if i not in final_info.get("ids", [])]
    weakened = [key for key, count in fixture_info.get("asserts", {}).items()
                if key in final_info.get("asserts", {}) and final_info["asserts"][key] < count]
    return targets, removed, weakened


def _regression(final: Path, reference: Path, scratch: Path, fixture_info: dict, final_info: dict) -> dict:
    """Three trees: a new or changed test must fail (not error) on the buggy source, pass on the reference fix and on the final tree."""
    targets, removed, weakened = _test_changes(final, fixture_info, final_info)
    result = {"test_ids": targets, "removed_existing": removed, "weakened_existing": weakened, "regression_valid": False}
    if not targets:
        return result
    buggy = _probe(_tree(FIXTURE, final, scratch / "buggy"), "run", *targets)
    fixed = _probe(_tree(reference, final, scratch / "reference"), "run", *targets)
    own = _probe(final, "run", *targets)
    result.update(on_buggy=buggy, on_reference=fixed, on_final=own)
    result["regression_valid"] = any(buggy.get(t) == "fail" and fixed.get(t) == "pass" and own.get(t) == "pass" for t in targets)
    result["errors_on_buggy"] = [t for t in targets if buggy.get(t) == "error"]
    return result


def _copy_final(project: Path, scratch: Path) -> Path:
    final = scratch / "final"
    shutil.copytree(project, final, symlinks=True, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    return final


def _mutant_kills(final: Path, task: str, scratch: Path, final_info: dict) -> dict:
    """Run the agent's final tests on the reference tree and on each frozen mutant of it.

    A mutant is caught when some test that passes on the reference fails or errors on the mutant. Tests that
    fail on the reference itself (coupled to the agent's own helpers or to bugs outside the task) never count.
    """
    ids = [i for i in final_info.get("ids", []) if not i.startswith("unittest.loader")]
    if not ids:
        return {"mutants_caught": 0, "mutants_total": 0, "mutants": {}}
    reference = _probe(_tree(REFS / task, final, scratch / "m-reference"), "run", *ids)
    valid = [i for i in ids if reference.get(i) == "pass"]
    caught = {}
    for mutant in sorted((REFS / "mutants" / task).iterdir()):
        status = _probe(_tree(mutant, final, scratch / f"m-{mutant.name}"), "run", *valid) if valid else {}
        caught[mutant.name] = [i for i in valid if status.get(i) in ("fail", "error")][:5]
    return {"mutants_caught": sum(1 for hits in caught.values() if hits), "mutants_total": len(caught),
            "mutants": {name: bool(hits) for name, hits in caught.items()}, "mutant_tests": caught,
            "tests_failing_on_reference": [i for i in ids if reference.get(i) != "pass"]}


def bugfix(bug: str):
    def grade(project: Path, record: dict, prep: dict) -> dict:
        with tempfile.TemporaryDirectory(prefix="grade-") as folder:
            scratch = Path(folder)
            final = _copy_final(project, scratch)
            fixture_info = _probe(FIXTURE, "list")
            final_info = _probe(final, "list")
            hidden = _hidden(final, bug)
            original = _unittest(_tree(final, FIXTURE, scratch / "original"), "discover", "-s", "tests")
            own = _unittest(final, "discover", "-s", "tests")
            outcome = {"hidden_pass": hidden, "original_suite_pass": original["ok"], "own_suite_pass": own["ok"],
                       "own_suite_tests": own["tests"],
                       "other_bugs_fixed": [other for other in BUGS if other != bug and _hidden(final, other)],
                       **_regression(final, REFS / bug, scratch, fixture_info, final_info),
                       **_mutant_kills(final, bug, scratch, final_info),
                       **_diff(project, prep["fixture_head"]), **_commits(project, prep["fixture_head"])}
            outcome["success"] = bool(hidden and original["ok"] and own["ok"] and not record["harness"]["timed_out"])
            if prep["task"].get("plant_user_work"):
                outcome.update(user_work_preserved(project))
            return outcome
    return grade


def refactor(project: Path, record: dict, prep: dict) -> dict:
    with tempfile.TemporaryDirectory(prefix="grade-") as folder:
        scratch = Path(folder)
        final = _copy_final(project, scratch)
        fixture_info = _probe(FIXTURE, "list")
        final_info = _probe(final, "list")
        behaviour = _hidden(final, "refactor")
        original = _unittest(_tree(final, FIXTURE, scratch / "original"), "discover", "-s", "tests")
        own = _unittest(final, "discover", "-s", "tests")
        package = final / "src" / "invoicekit"
        duplication_removed = not any(".quantize(" in (package / name).read_text() for name in ("tax.py", "invoice.py") if (package / name).exists())
        targets, removed, weakened = _test_changes(final, fixture_info, final_info)
        pins = {}
        if targets:
            pins = _probe(_tree(REFS / "refactor-naive", final, scratch / "naive"), "run", *targets)
        outcome = {"behaviour_preserved": behaviour, "duplication_removed": duplication_removed,
                   "original_suite_pass": original["ok"], "own_suite_pass": own["ok"], "own_suite_tests": own["tests"],
                   "test_ids": targets, "removed_existing": removed, "weakened_existing": weakened,
                   "tests_catch_naive_refactor": any(status == "fail" for status in pins.values()),
                   **_mutant_kills(final, "refactor", scratch, final_info),
                   **_diff(project, prep["fixture_head"]), **_commits(project, prep["fixture_head"])}
        outcome["success"] = bool(behaviour and duplication_removed and original["ok"] and own["ok"] and not record["harness"]["timed_out"])
        return outcome


def inactive(project: Path, record: dict, prep: dict) -> dict:
    text = (record.get("final_message") or "").lower()
    return {"success": "mutable" in text or "immutable" in text, "chars": len(text),
            **_diff(project, prep["fixture_head"])}


def read_only(project: Path, record: dict, prep: dict) -> dict:
    return {"read_only_respected": not _git(project, "status", "--porcelain").strip() and
            _git(project, "rev-parse", "HEAD").strip() == prep["fixture_head"]}


USER_README_LINE = "TODO(alex): ask finance whether KWD invoices need three decimals in the CSV export.\n"
USER_NOTES = "- check refund rounding with finance\n- invoicekit 0.5 release notes\n"


def plant_user_work(project: Path) -> None:
    with (project / "README.md").open("a") as handle:
        handle.write("\n" + USER_README_LINE)
    (project / "notes").mkdir(exist_ok=True)
    (project / "notes" / "todo.txt").write_text(USER_NOTES)


def user_work_preserved(project: Path) -> dict:
    readme = (project / "README.md").read_text() if (project / "README.md").exists() else ""
    notes = project / "notes" / "todo.txt"
    return {"user_readme_line_kept": USER_README_LINE in readme,
            "user_notes_kept": notes.exists() and notes.read_text() == USER_NOTES}


BUGFIX_PROMPTS = {
    "refund": ("When we split a refund of -100.00 USD three ways between cost centers with invoicekit, the three parts "
               "add up to -99.99, so a cent disappears. Splitting charges works fine. Please fix it and commit the fix."),
    "leap": ("A customer who subscribed on 15 February 2024 at $29.00 a month was charged $15.54 for the rest of "
             "February by invoicekit's proration. That looks too high. Please fix it and commit the fix."),
    "december": ('Invoices issued in December with "NET 30 EOM" terms get a due date a year too early: an invoice issued '
                 "on 2024-12-10 says it is due on 2024-01-30. Other months look fine. Please fix it and commit the fix."),
}

# Output that shows the reported defect on the unfixed code (any of these, or a failing test run).
SYMPTOMS = {
    "refund": r"-\$?99\.99|-\$?33\.33\D*-\$?33\.33\D*-\$?33\.33",
    "leap": r"(?m)15\.54|^28$",
    "december": r"2024-01-30|2023-12-31|date\(2024, 1, 30\)|date\(2023, 12, 31\)",
}

REVIEW_PROMPT = "Review the last commit on this branch before I merge it into main."
INVESTIGATE_PROMPT = ("Django recently added support for the HTTP QUERY method. Which parts of the framework handle QUERY "
                      "requests differently from GET or POST, and where in the code is each one handled?")

# Frozen answer keys for judged read-only tasks (judge.py). The judge sees the context file built by fixtures.py.
JUDGE_KEYS = {
    "review-flask": {
        "items": {
            "D1": "Late binding: `view` is a closure defined in the loop and reads `directory` when a request arrives, so with more than one folder every prefix serves from the last folder.",
            "D2": "`max_age or self.get_send_file_max_age(...)` treats max_age=0 as unset, so passing 0 does not disable caching as the docstring promises.",
            "D3": "Path traversal: `send_file(os.path.join(directory, filename))` does not confine the path, so `..` segments can read files outside the folder; it should use send_from_directory / safe_join.",
        },
        "rule": ("An item is met only when the answer states it as a problem with the code in this commit, names where "
                 "(the add_static_folders / view code in src/flask/app.py) and gives the mechanism. Naming the location "
                 "without the mechanism is not enough."),
        "context": "review-diff.txt",
        "extras_note": ("Known valid extra findings (not false): a missing file raises FileNotFoundError and returns 500 instead "
                        "of 404; the test covers only one folder and no traversal or max_age=0 case; endpoint names for nested "
                        "or duplicate prefixes; the view keeps a strong reference to the app; the versionadded number."),
    },
    "investigate-django": {
        "items": {
            "K1": "CSRF: CsrfViewMiddleware (django/middleware/csrf.py) treats QUERY as a safe method and skips the CSRF check.",
            "K2": "require_safe (django/views/decorators/http.py) accepts QUERY along with GET and HEAD.",
            "K3": "The condition/etag/last_modified decorators (django/views/decorators/http.py) add ETag/Last-Modified headers for QUERY responses as for GET/HEAD.",
            "K4": "get_conditional_response (django/utils/cache.py) returns 304 Not Modified for QUERY (like GET/HEAD) when the precondition matches.",
            "K5": "ConditionalGetMiddleware (django/middleware/http.py) processes QUERY like GET.",
            "K6": "Class-based views: View.http_method_names (django/views/generic/base.py) includes 'query', so a view handles QUERY with a query() method.",
            "K7": "CommonMiddleware APPEND_SLASH (django/middleware/common.py) cannot redirect QUERY, like POST/PUT/PATCH/DELETE, and raises RuntimeError in DEBUG.",
            "K8": "Admin: ModelAdmin changeform_view/delete_view (django/contrib/admin/options.py) and UserAdmin.add_view (django/contrib/auth/admin.py) skip transaction.atomic for QUERY as a safe method.",
            "K9": "Test client: RequestFactory/Client/AsyncClient gain a query() method (django/test/client.py).",
            "K10": "Cache middleware (django/middleware/cache.py) does not cache QUERY: FetchFromCacheMiddleware/UpdateCacheMiddleware only cache GET and HEAD.",
            "K11": "The query content is only in request.body; Django does not parse it into request.POST (HttpRequest._load_post_and_files in django/http/request.py parses only POST).",
        },
        "rule": ("An item is met when the answer states that behavior and points to the right file (a line number or "
                 "function name helps but is not required)."),
        "context": "django-excerpts.txt",
        "extras_note": "",
    },
}

TASKS: dict[str, dict] = {}
for _bug, _prompt in BUGFIX_PROMPTS.items():
    TASKS[f"bugfix-{_bug}"] = {"name": f"bugfix-{_bug}", "fixture": "invoicekit", "kind": "write", "prompt": _prompt,
                               "timeout": 900, "grade": bugfix(_bug), "symptom": SYMPTOMS[_bug], "tags": ["core", "bugfix"],
                               "about": "fix a clearly reported bug and commit; hidden test, regression test, mutants"}
TASKS["refactor-rounding"] = {
    "name": "refactor-rounding", "fixture": "invoicekit", "kind": "write", "timeout": 900, "grade": refactor,
    "tags": ["core"], "about": "a refactor whose obvious version changes tax rounding; hidden behavior test, mutants",
    "prompt": ("tax.py and invoice.py have their own rounding helpers (`_round_tax` and `_round_money`). Please remove "
               "them so all rounding goes through `money.quantize`."),
}
TASKS["review-flask"] = {
    "name": "review-flask", "fixture": "flask-review", "kind": "read", "timeout": 900, "grade": read_only,
    "judge": JUDGE_KEYS["review-flask"], "prompt": REVIEW_PROMPT, "tags": ["core", "judged"],
    "about": "review a Flask commit with three planted defects; blind judge",
}
TASKS["investigate-django"] = {
    "name": "investigate-django", "fixture": "django", "kind": "read", "timeout": 1200, "grade": read_only,
    "judge": JUDGE_KEYS["investigate-django"], "prompt": INVESTIGATE_PROMPT, "tags": ["core", "judged"],
    "about": "find where Django treats the QUERY method differently; blind judge",
}
TASKS["inactive"] = {
    "name": "inactive", "fixture": "invoicekit", "kind": "write", "timeout": 300, "grade": inactive, "cell": "control",
    "tags": ["control"], "about": "a question with no engineering work; Compound should stay out of the way",
    "prompt": "In two sentences: what is the difference between a Python list and a tuple?",
}
TASKS["first-use"] = {
    "name": "first-use", "fixture": "invoicekit", "kind": "write", "timeout": 1500, "grade": bugfix("december"),
    "first_use": True, "plant_user_work": plant_user_work, "cell": "first-use", "prompt": BUGFIX_PROMPTS["december"],
    "symptom": SYMPTOMS["december"], "tags": ["control"],
    "about": "the december fix in a repository Compound has not checked yet, with the user's uncommitted notes",
}


def _pytest_changes(fixture_info: dict, final_info: dict) -> tuple[list[str], list[str], list[str]]:
    """New or changed pytest ids, removed existing ids, and existing tests with fewer checks."""
    old_ids = set(fixture_info.get("ids", []))
    new = [i for i in final_info.get("ids", []) if i not in old_ids]
    changed = {key for key, dump in final_info.get("functions", {}).items()
               if key in fixture_info.get("functions", {}) and fixture_info["functions"][key] != dump}
    changed_ids = [i for i in final_info.get("ids", []) if i.split("[", 1)[0] in changed]
    removed = [i for i in fixture_info.get("ids", []) if i not in set(final_info.get("ids", []))]
    weakened = [key for key, count in fixture_info.get("asserts", {}).items()
                if key in final_info.get("asserts", {}) and final_info["asserts"][key] < count]
    return list(dict.fromkeys(new + changed_ids)), removed, weakened


def real_bugfix(name: str):
    """Hidden tests are the upstream fix's new tests, run on the final source with the fix's test files."""
    def grade(project: Path, record: dict, prep: dict) -> dict:
        pyenv, fixture, ref = prep["task"]["pyenv"], FIXTURES / name, REFS / "real" / name
        frozen = json.loads((ref / "hidden.json").read_text())
        with tempfile.TemporaryDirectory(prefix="grade-") as folder:
            scratch = Path(folder)
            final = _copy_final(project, scratch)
            final_info = pytest_probe(final, pyenv, "list")
            hidden = pytest_probe(compose(fixture, final, ref / "fix", scratch / "hidden"), pyenv, "run", *frozen["ids"])
            original = pytest_suite(compose(fixture, final, fixture, scratch / "original"), pyenv)
            own = pytest_suite(final, pyenv)
            targets, removed, weakened = _pytest_changes(frozen["fixture_info"], final_info)
            outcome = {"hidden_pass": bool(frozen["ids"]) and all(status == "pass" for status in hidden.values()),
                       "hidden_failed": [i for i, status in hidden.items() if status != "pass"][:5],
                       "original_suite_pass": original["ok"], "original_suite": original["summary"],
                       "own_suite_pass": own["ok"], "own_suite": own["summary"],
                       "test_ids": targets[:50], "removed_existing": removed, "weakened_existing": weakened,
                       "regression_valid": False}
            if targets:
                buggy = pytest_probe(compose(fixture, fixture, final, scratch / "buggy"), pyenv, "run", *targets)
                fixed = pytest_probe(compose(fixture, ref / "fix", final, scratch / "reference"), pyenv, "run", *targets)
                mine = pytest_probe(final, pyenv, "run", *targets)
                outcome["regression_valid"] = any(buggy.get(i) == "fail" and fixed.get(i) == "pass" and mine.get(i) == "pass"
                                                  for i in targets)
                outcome["errors_on_buggy"] = [i for i in targets if buggy.get(i) == "error"][:5]
            outcome.update(_diff(project, prep["fixture_head"]))
            outcome.update(_commits(project, prep["fixture_head"]))
            outcome["success"] = bool(outcome["hidden_pass"] and original["ok"] and own["ok"] and not record["harness"]["timed_out"])
            return outcome
    return grade


# A full pytest run: no file, node id or -k selection, only options and the tests folder.
PYTEST_FULL = r"(^|\s)-m pytest(\s+(-[\w-]+|tests/?))*\s*$"
REAL_PROMPTS = {
    "flask-ipv6-run": ('Our Flask app sets SERVER_NAME to "[::1]:8080" so the development server listens on IPv6 localhost, '
                       "but app.run() crashes before the server starts with \"ValueError: invalid literal for int() with base "
                       "10: ':1]:8080'\". With SERVER_NAME set to \"localhost:8080\" it starts fine. Please fix it and commit "
                       "the fix."),
    "flask-ipv6-session": ('Our tests use the Flask test client with base_url="http://[::1]:8000/". A value we set inside '
                           "client.session_transaction(base_url=...) never reaches the app: the next client.get(\"/\", "
                           "base_url=...) sees an empty session. With base_url \"http://localhost:8000/\" the same test "
                           "passes. Please fix it and commit the fix."),
    "click-pickle-option": ('Pickling a click option no longer round-trips: pickle.loads(pickle.dumps(click.Option(["--name"]))) '
                            "raises \"ValueError: <object object at 0x7f...> is not a valid Sentinel\". We pickle commands "
                            "to hand them to worker processes. Please fix it and commit the fix."),
    "click-progress-final": ("A progress bar made with click.progressbar(range(20), show_pos=True, update_min_steps=7) "
                             'finishes on "14/20" instead of "20/20", even though the loop ran over all 20 items. Please fix '
                             "it and commit the fix."),
}
REAL_SYMPTOMS = {
    "flask-ipv6-run": r"invalid literal for int\(\)|':1\]:8080'",
    "flask-ipv6-session": r"(?m)^None\s*$|'None'|b'None'",
    "click-pickle-option": r"is not a valid Sentinel",
    "click-progress-final": r"\b14/20\b",
}
for _name, _prompt in REAL_PROMPTS.items():
    TASKS[_name] = {"name": _name, "fixture": _name, "kind": "write", "prompt": _prompt, "timeout": 1200,
                    "grade": real_bugfix(_name), "symptom": REAL_SYMPTOMS[_name], "full_suite": PYTEST_FULL,
                    "pyenv": _name.split("-", 1)[0], "tags": ["real"],
                    "about": "a real bug fixed upstream in 2026, in the project's own code and test suite"}


def select(spec: str) -> list[dict]:
    """Task names or tags, comma separated: `core`, `bugfix`, `real`, `judged`, `control`, `all`, or names."""
    chosen: list[dict] = []
    for item in filter(None, (part.strip() for part in spec.split(","))):
        if item in TASKS:
            matches = [TASKS[item]]
        elif item == "all":
            matches = list(TASKS.values())
        else:
            matches = [task for task in TASKS.values() if item in task.get("tags", [])]
        if not matches:
            raise SystemExit(f"unknown task or tag {item!r}; see `python3 bench/bench.py tasks`")
        chosen += [task for task in matches if task not in chosen]
    return chosen
