"""Paths, model aliases, sandbox layout and plugin arms shared by the benchmark modules."""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path, PurePosixPath

sys.dont_write_bytecode = True

BENCH = Path(__file__).resolve().parent
REPO = BENCH.parent
DATA = BENCH / "data"
WORK = Path(os.environ.get("BENCH_WORK") or BENCH / "work").resolve()
RESULTS = Path(os.environ.get("BENCH_RESULTS") or BENCH / "results").resolve()
SOURCES = WORK / "sources"
FIXTURES = WORK / "fixtures"
REFS = WORK / "refs"
JUDGE_CONTEXT = WORK / "judge"
TEMPLATE = WORK / "template"
PLUGINS = WORK / "plugins"
RUNS = WORK / "runs"
SHIM = WORK / "shim"

# Aliases resolve to the newest model of each family in the installed Claude Code; full model ids also work.
MODEL_ALIASES = ("opus", "sonnet", "haiku")

# The layout every run sees, whatever the arm. Built from parts so no host path appears in the source.
HOMES = PurePosixPath("/home")
SANDBOX_HOME = str(HOMES / "dev")
SRC_ROOT = f"{SANDBOX_HOME}/src"
PLUGIN_MOUNT = f"{SANDBOX_HOME}/.local/share/claude-plugins/compound-skills"
SCRIPTS_MOUNT = f"{PLUGIN_MOUNT}/skills/compound/scripts"
TRACE_MOUNT = str(HOMES / ".devtrace")
GIT_IDENTITY = ("Alex Morgan", "alex.morgan@example.invalid")

ARM_NAME = re.compile(r"^[a-z][a-z0-9-]{0,30}$")
BUILTIN_ARMS = {"without": "none", "with": "worktree", "rule": "rule"}
# Arm "rule": generic habits as a short user rule, about as long as Compound's always-on rule.
HABITS_RULE = ("Before fixing a reported bug, reproduce it by running the code. Add a regression test and show that it "
               "fails on the unfixed code. Run the full test suite after your last change. Before a refactor, record "
               "current behaviour and compare afterwards. In your final message, list what you ran and what you did "
               "not verify.\n")
# Never copied into a plugin snapshot: answer keys, history, local tests.
SNAPSHOT_EXCLUDE = ("bench", ".git", "tests", "__pycache__")


def git(repo: Path, *args: str, check: bool = False) -> str:
    out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and out.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {out.stderr.strip()}")
    return out.stdout


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tree_hash(path: Path, skip: tuple[str, ...] = (".git", "__pycache__")) -> str:
    digest = hashlib.sha256()
    for item in sorted(path.rglob("*")):
        if any(part in skip for part in item.relative_to(path).parts) or not item.is_file() or item.is_symlink():
            continue
        digest.update(str(item.relative_to(path)).encode() + b"\0" + item.read_bytes() + b"\0")
    return digest.hexdigest()


def same_model(requested: str, served: str | None) -> bool:
    """An alias matches its family; a full id must match exactly."""
    if not served:
        return False
    if requested in MODEL_ALIASES:
        return served.startswith(f"claude-{requested}-")
    return served == requested


# ---------------------------------------------------------------- arms

def parse_arms(spec: str) -> list[dict]:
    """`without,with` or `name=source` items; a source is none, rule, worktree, ref:<git revision> or dir:<path>."""
    arms, seen = [], set()
    for item in filter(None, (part.strip() for part in spec.split(","))):
        name, _, source = item.partition("=")
        if not source:
            if name not in BUILTIN_ARMS:
                raise SystemExit(f"unknown arm {name!r}: use without, with, rule or name=source")
            source = BUILTIN_ARMS[name]
        if not ARM_NAME.match(name):
            raise SystemExit(f"arm name {name!r}: lowercase letters, digits and dashes")
        if source not in ("none", "rule", "worktree") and not source.startswith(("ref:", "dir:")):
            raise SystemExit(f"arm {name}: source must be none, rule, worktree, ref:<revision> or dir:<path>")
        if name in seen:
            raise SystemExit(f"arm {name} given twice")
        seen.add(name)
        arms.append({"name": name, "source": source})
    if not arms:
        raise SystemExit("no arms given")
    return arms


def _excluded(relative: str) -> bool:
    return relative.split("/", 1)[0] in SNAPSHOT_EXCLUDE or "__pycache__" in relative.split("/")


def materialize(arm: dict) -> dict:
    """Copy the plugin an arm runs into an immutable snapshot named by its content hash."""
    source = arm["source"]
    if source in ("none", "rule"):
        return {**arm, "plugin": None}
    PLUGINS.mkdir(parents=True, exist_ok=True)
    staging = PLUGINS / f".staging-{arm['name']}-{os.getpid()}"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir()
    info: dict = {}
    if source == "worktree":
        listing = subprocess.run(["git", "-C", str(REPO), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                                 capture_output=True, check=True).stdout
        for raw in filter(None, listing.split(b"\0")):
            name = raw.decode("utf-8", "surrogateescape")
            path = REPO / name
            if _excluded(name) or not path.is_file() or path.is_symlink():
                continue
            (staging / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, staging / name)
        info = {"commit": git(REPO, "rev-parse", "HEAD").strip(), "dirty": bool(git(REPO, "status", "--porcelain").strip())}
    elif source.startswith("ref:"):
        commit = git(REPO, "rev-parse", "--verify", f"{source[4:]}^{{commit}}", check=True).strip()
        archive = subprocess.run(["git", "-C", str(REPO), "archive", "--format=tar", commit], capture_output=True, check=True).stdout
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            members = [m for m in tar.getmembers() if not _excluded(m.name) and (m.isfile() or m.isdir())]
            tar.extractall(staging, members=members, **({"filter": "data"} if hasattr(tarfile, "data_filter") else {}))
        info = {"commit": commit}
    else:
        origin = Path(source[4:]).expanduser().resolve()
        if not (origin / ".claude-plugin" / "plugin.json").is_file():
            raise SystemExit(f"arm {arm['name']}: {origin} has no .claude-plugin/plugin.json")
        shutil.copytree(origin, staging, dirs_exist_ok=True, symlinks=False,
                        ignore=lambda folder, names: [n for n in names if n in SNAPSHOT_EXCLUDE and Path(folder) == origin or n == "__pycache__"])
    manifest = staging / ".claude-plugin" / "plugin.json"
    if not manifest.is_file():
        shutil.rmtree(staging, ignore_errors=True)
        raise SystemExit(f"arm {arm['name']}: the snapshot has no .claude-plugin/plugin.json")
    digest = tree_hash(staging)[:12]
    final = PLUGINS / f"{arm['name']}-{digest}"
    if final.exists():
        shutil.rmtree(staging)
    else:
        staging.rename(final)
    version = json.loads((final / ".claude-plugin" / "plugin.json").read_text()).get("version")
    return {**arm, **info, "plugin": str(final), "plugin_hash": digest, "plugin_version": version}
