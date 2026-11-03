"""Paths, model aliases, sandbox layout and plugin arms shared by the benchmark modules."""
from __future__ import annotations

import contextlib
import fcntl
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
PYENVS = WORK / "pyenv"

# Aliases resolve to the newest model of each family in the installed Claude Code; full model ids also work.
MODEL_ALIASES = ("opus", "sonnet", "haiku")

# The layout every run sees, whatever the arm. Built from parts so no host path appears in the source.
HOMES = PurePosixPath("/home")
SANDBOX_HOME = str(HOMES / "dev")
SRC_ROOT = f"{SANDBOX_HOME}/src"
PLUGINS_ROOT = f"{SANDBOX_HOME}/.local/share/claude-plugins"
COMPOUND = "compound-skills"
PLUGIN_MOUNT = f"{PLUGINS_ROOT}/{COMPOUND}"
SCRIPTS_MOUNT = f"{PLUGIN_MOUNT}/skills/compound/scripts"
TRACE_MOUNT = str(HOMES / ".devtrace")
PYENV_MOUNT = str(HOMES / ".bench-python")
GIT_IDENTITY = ("Alex Morgan", "alex.morgan@example.invalid")

ARM_NAME = re.compile(r"^[a-z][a-z0-9-]{0,30}$")
PLUGIN_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
BUILTIN_ARMS = {"without": "none", "with": "worktree", "rule": "rule"}
# Arm "rule": generic habits as a short user rule, about as long as Compound's always-on rule.
HABITS_RULE = ("Before fixing a reported bug, reproduce it by running the code. Add a regression test and show that it "
               "fails on the unfixed code. Run the full test suite after your last change. Before a refactor, record "
               "current behaviour and compare afterwards. In your final message, list what you ran and what you did "
               "not verify.\n")
# Never copied into a plugin snapshot: answer keys, history, local tests.
SNAPSHOT_EXCLUDE = ("bench", ".git", "tests", "__pycache__")


@contextlib.contextmanager
def work_lock(exclusive: bool):
    """Runs share the fixtures; setup rebuilds them, so it waits for no run and no run starts during it."""
    WORK.mkdir(parents=True, exist_ok=True)
    with (WORK / ".lock").open("w") as handle:
        try:
            fcntl.flock(handle, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("another benchmark command is using bench/work: " +
                             ("wait for the running benchmark to finish" if exclusive else "wait for setup to finish")) from None
        yield


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

# Ablations of Compound: exact edits applied to an arm's snapshot before it is hashed, so the arm records the text it ran.
# nomap removes the map query from the skill's startup and from the always-on rule, and keeps everything else.
VARIANTS = {
    "nomap": [
        ("skills/compound/SKILL.md",
         "Read the project's instructions. Then run one map query with the task's terms before any further search, read, or "
         "edit, even if you already know where to look; skip it only when the task names its file or supplies the code:\n\n"
         "- **Edits authorized:** `python3 -B <installed-skill-dir>/scripts/code_map.py --repo <repo-root> --query \"<task terms>\"`. "
         "This starts or reuses the local service and incremental cache.\n"
         "- **Read-only explanation/review:** `python3 -B <installed-skill-dir>/scripts/code_map.py --repo <repo-root> --query "
         "\"<task terms>\" --cache-read-only`. This validates and reuses any existing cache without writing or starting a service; "
         "missing or changed files are scanned in memory. Use `--no-cache` to bypass existing caches entirely.\n",
         "Read the project's instructions.\n", "optional"),
        ("skills/compound/SKILL.md",
         "Read the project's instructions. Use supplied code, named files and current context first. Run one focused map query only to locate unknown files or dependencies; skip it when the relevant files are known or an unchanged map already answers the question:\n\n"
         "- **Edits authorized:** `python3 -B <installed-skill-dir>/scripts/code_map.py --repo <repo-root> --query \"<task terms>\"`. "
         "This starts or reuses the local service and incremental cache.\n"
         "- **Read-only explanation/review:** `python3 -B <installed-skill-dir>/scripts/code_map.py --repo <repo-root> --query "
         "\"<task terms>\" --cache-read-only`. This validates and reuses any existing cache without writing or starting a service; "
         "missing or changed files are scanned in memory. Use `--no-cache` to bypass existing caches entirely.\n",
         "Read the project's instructions.\n", "optional"),
        ("skills/compound/SKILL.md", "See [code maps](references/map.md) for coverage and limits. ", "", "optional"),
        ("skills/compound/SKILL.md", "Map results are navigation candidates, not a reading checklist. Follow only task-relevant links; use [code maps](references/map.md) for limits. ", "", "optional"),
        ("skills/compound/SKILL.md",
         "Run the map query as a single command on its own, with the full script path and no `cd`, `;`, `&&` or shell variables, "
         "so one permission rule can allow it; read references with your file-reading tool, not the shell. ",
         "Read references with your file-reading tool, not the shell. "),
        # Rules before 0.16.0 named the map query; 0.16.0's rule loads the skill only for some tasks and does not.
        ("skills/compound/scripts/project_setup.py", "Run its map query before searching. Reproduce", "Reproduce", "optional"),
    ],
    # 0.16.0 without loading the skill for reviews: the rule and the skill's description leave reviews out.
    "noreview": [
        ("skills/compound/scripts/project_setup.py",
         "lines. For refactors, new features, performance work, reviews and pull requests, first load the installed ",
         "lines. For refactors, new features, performance work and pull requests, first load the installed "),
        ("skills/compound/SKILL.md", "Use for refactors, new features, performance work, reviews and pull requests, or to enable",
         "Use for refactors, new features, performance work and pull requests, or to enable"),
    ],
}


def apply_variant(root: Path, name: str) -> None:
    if name not in VARIANTS:
        raise SystemExit(f"unknown variant {name!r}; known: {', '.join(VARIANTS)}")
    for relative, old, new, *optional in VARIANTS[name]:
        path = root / relative
        text = path.read_text(encoding="utf-8")
        if optional and old not in text:
            continue
        if text.count(old) != 1:
            raise SystemExit(f"variant {name}: {relative} does not contain the edited text exactly once")
        path.write_text(text.replace(old, new), encoding="utf-8")

    if name == "nomap" and "scripts/code_map.py --repo" in (root / "skills/compound/SKILL.md").read_text():
        raise SystemExit("variant nomap: unrecognized map startup instructions")


def parse_arms(spec: str) -> list[dict]:
    """`without,with` or `name=source[+rule:<file>][+prefix:<text>][+variant:<name>]` items; a source is none, rule, worktree,
    ref:<git revision> or dir:<path>. A dir: plugin need not be Compound: its manifest name decides where it is
    mounted. `+rule:<file>` also installs that file as an always-on user rule, as a plugin's own setup step would.
    `+prefix:<text>` starts every prompt with that text, such as the slash command a plugin asks its users to type.
    `+variant:<name>` applies one of VARIANTS to the plugin snapshot, such as nomap to measure Compound without its map."""
    arms, seen = [], set()
    for item in filter(None, (part.strip() for part in spec.split(","))):
        name, _, source = item.partition("=")
        source, _, variant = source.partition("+variant:")
        source, _, prefix = source.partition("+prefix:")
        source, _, rule = source.partition("+rule:")
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
        arm = {"name": name, "source": source}
        if rule:
            if source == "rule":
                raise SystemExit(f"arm {name}: the rule arm already has its rule; use none+rule:<file>")
            path = Path(rule).expanduser().resolve()
            if not path.is_file():
                raise SystemExit(f"arm {name}: rule file {rule} not found")
            arm["rule_file"] = str(path)
        if prefix:
            arm["prompt_prefix"] = prefix.strip()
        if variant:
            if source in ("none", "rule"):
                raise SystemExit(f"arm {name}: a variant needs a plugin source")
            if variant.strip() not in VARIANTS:
                raise SystemExit(f"arm {name}: unknown variant {variant!r}; known: {', '.join(VARIANTS)}")
            arm["variant"] = variant.strip()
        arms.append(arm)
    if not arms:
        raise SystemExit("no arms given")
    return arms


def _excluded(relative: str) -> bool:
    return relative.split("/", 1)[0] in SNAPSHOT_EXCLUDE or "__pycache__" in relative.split("/")


def materialize(arm: dict) -> dict:
    """Copy the plugin an arm runs into an immutable snapshot named by its content hash."""
    source = arm["source"]
    rule = {"rule_sha256": sha256_bytes(Path(arm["rule_file"]).read_bytes())} if arm.get("rule_file") else {}
    if source in ("none", "rule"):
        return {**arm, **rule, "plugin": None}
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
        commit = git(origin, "rev-parse", "HEAD").strip()
        if commit:  # a plugin checked out from Git: record the commit it ran, as ref: arms do
            info = {"commit": commit, "dirty": bool(git(origin, "status", "--porcelain", "--", ".").strip())}
        shutil.copytree(origin, staging, dirs_exist_ok=True, symlinks=False,
                        ignore=lambda folder, names: [n for n in names if n in SNAPSHOT_EXCLUDE and Path(folder) == origin or n == "__pycache__"])
    manifest = staging / ".claude-plugin" / "plugin.json"
    if not manifest.is_file():
        shutil.rmtree(staging, ignore_errors=True)
        raise SystemExit(f"arm {arm['name']}: the snapshot has no .claude-plugin/plugin.json")
    if arm.get("variant"):
        apply_variant(staging, arm["variant"])
    digest = tree_hash(staging)[:12]
    final = PLUGINS / f"{arm['name']}-{digest}"
    if final.exists():
        shutil.rmtree(staging)
    else:
        staging.rename(final)
    manifest = json.loads((final / ".claude-plugin" / "plugin.json").read_text())
    name = manifest.get("name")
    if not isinstance(name, str) or not PLUGIN_NAME.match(name):
        raise SystemExit(f"arm {arm['name']}: plugin name {name!r} is not a plain lowercase name")
    return {**arm, **info, **rule, "plugin": str(final), "plugin_hash": digest, "plugin_version": manifest.get("version"),
            "plugin_name": name}


def is_compound(arm: dict) -> bool:
    """A plugin arm running Compound; records from before third-party arms existed carry no plugin name."""
    return bool(arm.get("plugin_hash")) and (arm.get("plugin_name") or COMPOUND) == COMPOUND


def plugin_mount(arm: dict) -> str:
    """Where a plugin arm's snapshot appears in the sandbox: under its manifest name, as an installed plugin would."""
    return f"{PLUGINS_ROOT}/{arm.get('plugin_name') or COMPOUND}"
