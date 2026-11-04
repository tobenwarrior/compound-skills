"""Replay and prepare source-graded navigation tasks on pinned Flask and Django checkouts."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

from common import REPO, SOURCES, git
from fixtures import PINS
from map_retrieval import terms_of


CASES = (
    {
        "id": "django-disconnect",
        "repo": "django",
        "prompt": (
            "After Django has read the ASGI request body, a client disconnects. Trace what signals the disconnect, "
            "how request completion differs depending on whether a response exists, and what receives the "
            "completion signal to clean up database connections. Cite a file and symbol for each step."
        ),
        "query": "ASGI disconnect response close request finished database connections",
        "steps": (
            "The condition that detects the disconnect message.",
            "The condition that separates completion with and without a response.",
            "The completion signal send in response closure.",
            "The call that checks whether an initialized database connection should close.",
        ),
        "hops": (
            ("django/core/handlers/asgi.py", "ASGIHandler.listen_for_disconnect", 'if message["type"] == "http.disconnect":',
             "A disconnect raises RequestAborted in the task group, cancelling request processing."),
            ("django/core/handlers/asgi.py", "ASGIHandler.handle", "if response is None:",
             "No response means the handler emits request_finished directly. Otherwise it closes the response."),
            ("django/http/response.py", "HttpResponseBase.close", "signals.request_finished.send(sender=self._handler_class)",
             "Response close calls the registered closers and emits request_finished."),
            ("django/db/__init__.py", "close_old_connections", "conn.close_if_unusable_or_obsolete()",
             "The completion receiver checks initialized connections and closes unusable or obsolete ones."),
        ),
    },
    {
        "id": "django-row-locks",
        "repo": "django",
        "prompt": (
            "On a backend that supports row locks and transactions, evaluating select_for_update() outside an "
            "explicit transaction raises in production but may work in TestCase. Trace how the ORM records the "
            "lock, when it raises, and why the test behaves differently. Cite a file and symbol for each step."
        ),
        "query": "select_for_update outside transaction autocommit TestCase",
        "steps": (
            "The assignment recording the lock request on the query.",
            "The exception message for a lock outside a transaction.",
            "The creation of an atomic block for a TestCase database.",
        ),
        "hops": (
            ("django/db/models/query.py", "QuerySet.select_for_update", "obj.query.select_for_update = True",
             "QuerySet cloning records the lock request and marks the queryset for writes. This does not execute SQL."),
            ("django/db/models/sql/compiler.py", "SQLCompiler.as_sql", "select_for_update cannot be used outside of a transaction.",
             "SQL compilation raises TransactionManagementError when the backend supports transactions and autocommit is on."),
            ("django/test/testcases.py", "TestCase._enter_atomics", "atomic = transaction.atomic(using=db_name)",
             "TestCase enters atomic blocks, so the compiler sees a transaction even without an explicit block in the test."),
        ),
    },
    {
        "id": "flask-streaming",
        "repo": "flask",
        "prompt": (
            "A Flask view streams a generator that needs the current request after the view returns. Trace where "
            "normal request handling releases the context, how stream_with_context keeps it alive, and when "
            "request teardown runs. Cite a file and symbol for each step."
        ),
        "query": "stream_with_context streaming request teardown context",
        "steps": (
            "The call that pops the context at the end of WSGI request handling.",
            "The call that advances the wrapped generator to its sentinel.",
            "The call that runs request teardown when the context pops.",
        ),
        "hops": (
            ("src/flask/app.py", "Flask.wsgi_app", "ctx.pop(error)",
             "The WSGI entry point pops its context in finally after returning the response iterable."),
            ("src/flask/helpers.py", "stream_with_context", "next(wrapped_g)",
             "The wrapper advances to a sentinel to hold the context across iteration, and closes the wrapped iterator."),
            ("src/flask/ctx.py", "AppContext.pop", "self.app.do_teardown_request(self, exc)",
             "Only the outermost pop performs teardown, so the retained context delays cleanup until the stream releases it."),
        ),
    },
)

MAP = REPO / "skills" / "compound" / "scripts" / "code_map.py"
TEXT_PATH = re.compile(r'^- ("(?:[^"\\]|\\.)*") \[', re.MULTILINE)
SHORTLIST = 4


def pinned_source(repo: str, root: Path | None = None) -> Path:
    """Use exactly the checked-in source pin without fetching or modifying it."""
    if root is None:
        root = SOURCES / repo
    if git(root, "rev-parse", "HEAD", check=True).strip() != PINS[repo][1]:
        raise ValueError(f"{repo}: checkout must be at the benchmark pin")
    if git(root, "status", "--porcelain", "--untracked-files=all", check=True).strip():
        raise ValueError(f"{repo}: checkout must be clean")
    return root


def without_compound(root: Path, query: str) -> list[str]:
    """Rank Python files by distinct literal terms in path or source, then hit count."""
    paths = git(root, "ls-files", "-z", "--", "*.py", check=True).rstrip("\0").split("\0")
    scores = {path: [0, 0] for path in paths if path}
    for term in terms_of(query):
        match = subprocess.run(
            ["git", "grep", "-c", "-i", "-F", "-e", term, "--", "*.py"],
            cwd=root, text=True, capture_output=True, timeout=30,
        )
        if match.returncode not in (0, 1):
            raise RuntimeError(f"git grep failed for {term!r}")
        counts = {}
        for row in match.stdout.splitlines():
            path, _, count = row.rpartition(":")
            counts[path] = int(count)
        for path, score in scores.items():
            count = counts.get(path, 0)
            score[0] += bool(count or term in path.lower())
            score[1] += count
    return sorted((path for path, score in scores.items() if score[0]),
                  key=lambda path: (path.split("/", 1)[0] in {"test", "tests"},
                                    -scores[path][0], -scores[path][1], path))[:SHORTLIST]


def map_summary(root: Path, query: str) -> str:
    """Return the normal bounded map summary without writing a cache."""
    return subprocess.check_output(
        [sys.executable, "-B", MAP, "--repo", root, "--query", query, "--no-cache"],
        text=True, timeout=120,
    )


def with_compound(root: Path, query: str) -> list[str]:
    """Read complete file paths from the actual default 2,500-character summary."""
    return [json.loads(path) for path in TEXT_PATH.findall(map_summary(root, query))][:SHORTLIST]


def source_hops(root: Path, hops: tuple[tuple[str, str, str, str], ...]) -> list[dict]:
    """Verify rubric anchors at the pin and return their source locations."""
    rows = []
    for path, symbol, anchor, fact in hops:
        source = (root / path).read_text(encoding="utf-8")
        nodes = [ast.parse(source, filename=path)]
        for name in symbol.split("."):
            nodes = [child for node in nodes for child in node.body
                     if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name]
        lines = source.splitlines()
        matches = [number for node in nodes for number in range(node.lineno, node.end_lineno + 1)
                   if anchor in lines[number - 1]]
        if len(matches) != 1:
            raise ValueError(f"{path}: expected one source anchor for {symbol}, got {len(matches)}")
        rows.append({"path": path, "symbol": symbol, "line": matches[0], "fact": fact})
    return rows


def run() -> dict:
    """Evaluate both first-look tools on the same pinned source and query."""
    roots = {repo: pinned_source(repo) for repo in dict.fromkeys(case["repo"] for case in CASES)}
    rows = []
    for case in CASES:
        root = roots[case["repo"]]
        hops = source_hops(root, case["hops"])
        targets = {hop["path"] for hop in hops}
        row = {key: case[key] for key in ("id", "repo", "prompt", "query")}
        row.update(source_revision=PINS[case["repo"]][1], rubric=hops)
        for mode, lookup in (("without_compound", without_compound), ("with_compound", with_compound)):
            paths = lookup(root, case["query"])
            row[mode] = {"paths": paths, "found": len(targets.intersection(paths)), "expected": len(targets)}
        rows.append(row)
    return {
        "scope": "First shortlist only. No agent, task-completion, timing or model-cost measurement.",
        "map_script_sha256": hashlib.sha256(MAP.read_bytes()).hexdigest(),
        "cases": rows,
    }


def prepare() -> dict:
    """Freeze a common prompt and treatment context, keeping answer keys separate."""
    roots = {repo: pinned_source(repo) for repo in dict.fromkeys(case["repo"] for case in CASES)}
    tasks = []
    for case in CASES:
        root = roots[case["repo"]]
        source_hops(root, case["hops"])
        steps = "\n".join(f"{index}. {step}" for index, step in enumerate(case["steps"], 1))
        prompt = (
            f'{case["prompt"]} Suggested search terms are {case["query"]}.\n\n'
            "Return only a JSON array in the order below. Each entry must have path, symbol and line. "
            "Use a repository-relative path, the function name or Class.method, and the one-based line "
            "that contains the requested statement. Inspect the source before giving your citations.\n\n"
            f"{steps}"
        )
        summary = map_summary(root, case["query"])
        tasks.append({
            "id": case["id"],
            "repo": case["repo"],
            "source_revision": PINS[case["repo"]][1],
            "prompt": prompt,
            "orientation": {"without_compound": "", "with_compound": summary},
            "map_sha256": hashlib.sha256(summary.encode()).hexdigest(),
        })
    return {
        "schema": "compound-map-navigation-1",
        "compound_version": json.loads((REPO / "plugin.json").read_text(encoding="utf-8"))["version"],
        "map_script_sha256": hashlib.sha256(MAP.read_bytes()).hexdigest(),
        "tasks": tasks,
    }


def grade(case: dict, answer: object, *, root: Path | None = None) -> dict:
    """Check ordered source citations against the private rubric at the source pin."""
    root = pinned_source(case["repo"], root)
    expected = source_hops(root, case["hops"])
    if not isinstance(answer, list) or len(answer) != len(expected):
        return {"success": False, "checks": [False] * len(expected)}
    checks = [
        isinstance(entry, dict)
        and type(entry.get("line")) is int
        and all(entry.get(field) == witness[field] for field in ("path", "symbol", "line"))
        for entry, witness in zip(answer, expected)
    ]
    return {"success": all(checks), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prepare", action="store_true", help="generate common prompts and map treatment context")
    mode.add_argument("--grade", nargs=2, metavar=("CASE", "ANSWER"), help="grade a JSON answer file against the source pin")
    args = parser.parse_args()
    if args.grade:
        name, path = args.grade
        case = next((case for case in CASES if case["id"] == name), None)
        if case is None:
            parser.error(f"unknown case {name!r}")
        try:
            answer = json.loads(Path(path).read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError, RecursionError):
            answer = None
        result = grade(case, answer)
        print(json.dumps(result, indent=2))
        return 0 if result["success"] else 1
    print(json.dumps(prepare() if args.prepare else run(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
