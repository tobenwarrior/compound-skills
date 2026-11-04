"""Compare the first navigation shortlist on pinned, real request and transaction paths."""
from __future__ import annotations

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


def pinned_source(repo: str) -> Path:
    """Use exactly the checked-in source pin without fetching or modifying it."""
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


def with_compound(root: Path, query: str) -> list[str]:
    """Read complete file paths from the actual default 2,500-character summary."""
    text = subprocess.check_output(
        [sys.executable, "-B", MAP, "--repo", root, "--query", query, "--no-cache"],
        text=True, timeout=120,
    )
    return [json.loads(path) for path in TEXT_PATH.findall(text)][:SHORTLIST]


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


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
