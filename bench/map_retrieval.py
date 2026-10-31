"""Does the code map point at the files a real change touched? No agents involved.

For the most recent qualifying commits of each repository (non-merge, touching 1-3 non-test source files), the tree
at the commit's parent is extracted into a fresh git repository and queried with the commit subject:

- map: `code_map.py --query <subject> --no-cache --format json`, ranked focus list (the agent-facing text shows about
  the first 4 entries within its 2,500-character budget; the JSON lists up to 12).
- word-count search baseline: code files ranked by how many distinct subject terms they contain (ties: total matches, path).
- random baseline: expected recall k / candidate files.

Score: recall of the touched non-test source files at k = 1, 4 and 12. Files are only read as data; nothing from the
repositories is executed.
"""
from __future__ import annotations

import json
import re
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from common import SOURCES, git

REPOS = {
    "flask": (r"^src/flask/.+\.py$", r"(^|/)tests?/"),
    "click": (r"^src/click/.+\.py$", r"(^|/)tests?/"),
    "hono": (r"^src/.+\.tsx?$", r"(\.test\.tsx?$|(^|/)tests?/|\.spec\.tsx?$)"),
}
CODE_EXT = re.compile(r"\.(py|pyi|ts|tsx|js|jsx|mjs|cjs)$")
SKIP_SUBJECT = re.compile(r"(?i)^(merge|release|bump|chore\(deps|chore: release|version|update (dependencies|deps)|revert)")
STOP = set("the and for with from into when that this not are was use using via add adds added fix fixes fixed make makes "
           "allow allows update updates support supports remove removes handle handles correct correctly properly avoid "
           "should can does don't doesn't more less new old also only all any some its it's has have been instead "
           "change changes changed improve improves better issue bug error case cases test tests type types".split())



def clean_subject(subject: str) -> str:
    subject = re.sub(r"\s*\(#\d+\)\s*$", "", subject).strip()
    subject = re.sub(r"^(\w+)\(([^)]*)\)!?:\s*", r"\2: ", subject)
    subject = re.sub(r"^\w+!?:\s*", "", subject)
    return subject


def select(repo: Path, source: str, tests: str, limit: int) -> list[dict]:
    chosen = []
    for line in git(repo, "log", "--no-merges", "--format=%H%x09%s", "-n", "3000").splitlines():
        sha, _, subject = line.partition("\t")
        if SKIP_SUBJECT.search(subject):
            continue
        files = git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", sha).split()
        sources = [f for f in files if re.search(source, f) and not re.search(tests, f)]
        if not 1 <= len(sources) <= 3:
            continue
        query = clean_subject(subject)
        if len(re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", query)) < 2:
            continue
        chosen.append({"sha": sha, "subject": subject, "query": query, "touched": sources, "date": git(repo, "log", "-1", "--format=%cs", sha).strip()})
        if len(chosen) >= limit:
            break
    return chosen


def extract(repo: Path, sha: str, dest: Path) -> None:
    archive = subprocess.run(["git", "-C", str(repo), "archive", f"{sha}^"], capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive, check=True)
    for args in (["init", "-q"], ["add", "-A"], ["-c", "user.name=bench", "-c", "user.email=bench@example.invalid", "commit", "-qm", "parent"]):
        subprocess.run(["git", "-C", str(dest), *args], capture_output=True, check=True)


def map_rank(code_map: Path, tree: Path, query: str, state: Path) -> tuple[list[str], float, int]:
    env = {"PATH": "/usr/bin:/bin", "HOME": str(state), "COMPOUND_SKILLS_STATE_DIR": str(state), "LANG": "C.UTF-8"}
    started = time.perf_counter()
    out = subprocess.run([sys.executable, "-B", str(code_map), "--repo", str(tree), "--query", query, "--no-cache", "--format", "json"],
                         env=env, capture_output=True, text=True, timeout=600)
    seconds = time.perf_counter() - started
    data = json.loads(out.stdout)
    text = subprocess.run([sys.executable, "-B", str(code_map), "--repo", str(tree), "--query", query, "--no-cache"],
                          env=env, capture_output=True, text=True, timeout=600).stdout
    shown = len(re.findall(r'^- "', text, re.M))
    return [f["path"] if isinstance(f, dict) else f for f in data.get("focus", [])], seconds, shown


def terms_of(query: str) -> list[str]:
    words = {w.lower() for w in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", query)}
    return sorted(w for w in words if w not in STOP)


def rg_rank(tree: Path, query: str, candidates: list[str]) -> list[str]:
    terms = terms_of(query)
    score: dict[str, list[int]] = {path: [0, 0] for path in candidates}
    for term in terms:
        out = subprocess.run(["rg", "-c", "-i", "-F", "--no-messages", term, *candidates], cwd=tree, capture_output=True, text=True).stdout
        for line in out.splitlines():
            path, _, count = line.rpartition(":")
            if path in score:
                score[path][0] += 1
                score[path][1] += int(count)
        for path in candidates:
            if term in path.lower() and score[path][0] == 0:
                score[path][0] += 1
    ranked = sorted((path for path in candidates if score[path][0]), key=lambda p: (-score[p][0], -score[p][1], p))
    return ranked


def recall(ranked: list[str], touched: list[str], k: int) -> float:
    return sum(1 for f in touched if f in ranked[:k]) / len(touched)


def run(code_map: Path, per_repo: int) -> dict:
    report = {"commits": [], "summary": {}}
    for name, (source, tests) in REPOS.items():
        repo = SOURCES / name
        commits = select(repo, source, tests, per_repo)
        rows = []
        for commit in commits:
            with tempfile.TemporaryDirectory(prefix="ret-") as folder:
                tree, state = Path(folder) / name, Path(folder) / "state"
                tree.mkdir()
                state.mkdir()
                extract(repo, commit["sha"], tree)
                candidates = [f for f in git(tree, "ls-files").splitlines() if CODE_EXT.search(f)]
                touched = [f for f in commit["touched"] if f in candidates]
                if not touched:
                    continue
                ranked_map, seconds, shown = map_rank(code_map, tree, commit["query"], state)
                ranked_rg = rg_rank(tree, commit["query"], candidates)
                row = {**commit, "repo": name, "touched": touched, "candidates": len(candidates), "map_seconds": round(seconds, 3),
                       "map_text_entries": shown, "map_top": ranked_map[:12], "rg_top": ranked_rg[:12]}
                for k in (1, 4, 12):
                    row[f"map@{k}"] = recall(ranked_map, touched, k)
                    row[f"rg@{k}"] = recall(ranked_rg, touched, k)
                    row[f"random@{k}"] = min(1.0, k / len(candidates))
                rows.append(row)
                print(name, commit["sha"][:9], f"map@4={row['map@4']:.2f} rg@4={row['rg@4']:.2f} map@12={row['map@12']:.2f} rg@12={row['rg@12']:.2f}",
                      commit["query"][:70], flush=True)
        report["commits"] += rows
        summary = {"commits": len(rows), "dates": [rows[-1]["date"], rows[0]["date"]] if rows else None,
                   "candidates_median": statistics.median(r["candidates"] for r in rows) if rows else None,
                   "map_seconds_median": statistics.median(r["map_seconds"] for r in rows) if rows else None,
                   "map_text_entries_median": statistics.median(r["map_text_entries"] for r in rows) if rows else None}
        for k in (1, 4, 12):
            for method in ("map", "rg", "random"):
                summary[f"{method}@{k}"] = round(statistics.mean(r[f"{method}@{k}"] for r in rows), 3) if rows else None
            summary[f"map_vs_rg@{k}"] = {"map_better": sum(r[f"map@{k}"] > r[f"rg@{k}"] for r in rows),
                                        "tie": sum(r[f"map@{k}"] == r[f"rg@{k}"] for r in rows),
                                        "rg_better": sum(r[f"map@{k}"] < r[f"rg@{k}"] for r in rows)}
        report["summary"][name] = summary
        print(name, json.dumps(summary), flush=True)
    return report
