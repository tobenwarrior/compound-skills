"""Isolated, concurrent runs of headless Claude Code, one per arm, on the same task at the same moment.

Every run executes in its own mount and PID namespace with one neutral layout shared by all arms: the project
at <home>/src/<project>, HOME and CLAUDE_CONFIG_DIR inside a neutral home (a copy of one template config, so
client identity and feature flags match) and a fresh /tmp. The host's /root and /home, the answer keys, other
runs and the results are hidden. Arms differ only by --plugin-dir and the plugin snapshot it mounts, the user
rule (Compound's `setup global`, or the generic habits rule), the map port variable, and, for write tasks in
plugin arms, the one-time repository check-up recorded as completed beforehand.
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import random
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from common import (BENCH, COMPOUND, FIXTURES, GIT_IDENTITY, HABITS_RULE, PYENV_MOUNT, PYENVS, RESULTS, RUNS, SANDBOX_HOME,
                    SCRIPTS_MOUNT, SRC_ROOT, TEMPLATE, TRACE_MOUNT, git, is_compound, materialize, plugin_mount, same_model,
                    sha256_bytes, tree_hash)

sys.path.insert(0, str(BENCH / "shim"))
from devtrace import digest  # noqa: E402

KEEP_ENV = ("HTTPS_PROXY", "https_proxy", "NO_PROXY", "no_proxy", "NODE_EXTRA_CA_CERTS", "SSL_CERT_FILE",
            "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE")
CA_ENV = ("NODE_EXTRA_CA_CERTS", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE")
HIDDEN_ROOTS = ("/root", "/home")
STAGES = ("/mnt", "/media", "/srv")
LOCK = threading.Lock()

# Runs inside `unshare -m -p -f --mount-proc`: stages every host path a run needs, hides /root, /home and /tmp,
# restores the paths to keep, builds the neutral home, optionally records the one-time check-up as completed,
# then runs claude as a child of PID 1, so every process the run starts dies with the namespace.
RUNNER = r'''
set -eu
R="$1"; P="$2"; PLUG="$3"; ONBOARD="$4"; SHIM="$5"; KEEP="$6"; D="$7"; TRACE="$8"; STAGE="$9"; PYENV="${10}"; PYMOUNT="${11}"; M="${12}"
shift 12
NL='
'
mount -t tmpfs -o mode=755 tmpfs "$STAGE"
mkdir "$STAGE/run"
mount --bind "$R" "$STAGE/run"
if [ "$PLUG" != - ]; then mkdir "$STAGE/plug"; mount --bind "$PLUG" "$STAGE/plug"; fi
if [ "$SHIM" != - ]; then mkdir "$STAGE/shim"; mount --bind "$SHIM" "$STAGE/shim"; fi
if [ "$PYENV" != - ]; then mkdir "$STAGE/pyenv"; mount --bind "$PYENV" "$STAGE/pyenv"; fi
n=0; IFS=$NL
for k in $KEEP; do n=$((n+1)); mkdir "$STAGE/k$n"; mount --bind "$k" "$STAGE/k$n"; done
unset IFS
mount -t tmpfs -o mode=700 tmpfs /root
mount -t tmpfs -o mode=755 tmpfs /home
mount -t tmpfs -o mode=1777 tmpfs /tmp
n=0; IFS=$NL
for k in $KEEP; do n=$((n+1)); mkdir -p "$k"; mount --move "$STAGE/k$n" "$k"; mount -o remount,bind,ro "$k"; done
unset IFS
mkdir -p "$D"
mount --bind "$STAGE/run/home" "$D"
mkdir -p "$D/src/$P" "$D/.claude" "$D/.cache/compound-skills"
mount --bind "$STAGE/run/$P" "$D/src/$P"
mount --bind "$STAGE/run/cfg" "$D/.claude"
mount --bind "$STAGE/run/state" "$D/.cache/compound-skills"
if [ "$PLUG" != - ]; then mkdir -p "$M"; mount --bind "$STAGE/plug" "$M"; mount -o remount,bind,ro "$M"; fi
if [ "$SHIM" != - ]; then
  mkdir -p "$D/.local/bin" "$TRACE"
  mount --bind "$STAGE/shim" "$D/.local/bin"
  mount -o remount,bind,ro "$D/.local/bin"
  mount --bind "$STAGE/run/trace" "$TRACE"
fi
if [ "$PYENV" != - ]; then mkdir -p "$PYMOUNT"; mount --bind "$STAGE/pyenv" "$PYMOUNT"; mount -o remount,bind,ro "$PYMOUNT"; fi
umount -R "$STAGE"
cd "$D/src/$P"
if [ "$ONBOARD" = 1 ]; then
  S="$M/skills/compound/scripts"
  CLAIM=$(/usr/bin/python3 -B "$S/onboarding.py" claim --repo "$D/src/$P")
  TOKEN=$(printf '%s' "$CLAIM" | /usr/bin/python3 -c 'import json,sys; print(json.load(sys.stdin).get("token", ""))')
  echo "@@claim $CLAIM" >&2
  echo "@@complete $(/usr/bin/python3 -B "$S/onboarding.py" complete --repo "$D/src/$P" --token "$TOKEN")" >&2
  echo "@@status $(/usr/bin/python3 -B "$S/onboarding.py" status --repo "$D/src/$P")" >&2
fi
echo "@@start" >&2
"$@"
'''

READ_ONLY_BASH = ["git log", "git show", "git diff", "git status", "git ls-files", "git grep", "git blame", "git branch",
                  "git rev-parse", "git rev-list", "git merge-base", "git cat-file", "git ls-tree", "git describe",
                  "git shortlog", "ls", "wc", "cat", "head", "tail", "sed -n", "find", "rg", "grep", "egrep", "tree", "file",
                  "stat", "du", "sort", "uniq", "cut", "awk", "diff", "pwd", "echo", "nl", "cd", "realpath", "readlink",
                  "basename", "dirname", "tr", "column", "printf", "true", "test"]
PLUGIN_HELPERS = ["code_map.py", "symbol_lookup.py", "onboarding.py status"]
NETWORK_DENY = ["Bash(curl:*)", "Bash(wget:*)", "Bash(git fetch:*)", "Bash(git pull:*)", "Bash(git clone:*)",
                "Bash(git push:*)", "Bash(pip install:*)", "Bash(pip3 install:*)", "Bash(python3 -m pip:*)",
                "Bash(uv pip:*)", "Bash(npm install:*)", "Bash(npx:*)"]


# ---------------------------------------------------------------- host environment

def _under_hidden(path: str) -> bool:
    return any(path == root or path.startswith(root + "/") for root in HIDDEN_ROOTS)


def keep_paths() -> list[str]:
    """Host directories a run must still see, read-only: the proxy CA files' folders, BENCH_KEEP, and the
    folders of claude, node and python3 when they live under /root or /home."""
    keep = []
    for key in CA_ENV:
        value = os.environ.get(key)
        if value and os.path.isfile(value):
            keep.append(os.path.dirname(os.path.realpath(value)))
    keep += [item for item in os.environ.get("BENCH_KEEP", "").split(os.pathsep) if item]
    for tool in ("claude", "node", "python3"):
        found = shutil.which(tool)
        for candidate in filter(None, (found, found and os.path.realpath(found))):
            if _under_hidden(candidate):
                keep.append(os.path.dirname(candidate))
    out = []
    for item in keep:
        item = os.path.realpath(item)
        if os.path.isdir(item) and item not in out:
            out.append(item)
    return out


def sandbox_path() -> str:
    folders = [f"{SANDBOX_HOME}/.local/bin"]
    for tool in ("claude", "node"):
        found = shutil.which(tool)
        if found:
            folders.append(os.path.dirname(found))
    folders += ["/usr/local/bin", "/usr/bin", "/bin"]
    return ":".join(dict.fromkeys(folders))


def stage_dir(paths: list[str]) -> str:
    for stage in STAGES:
        if os.path.isdir(stage) and not any(p == stage or p.startswith(stage + "/") for p in paths):
            return stage
    raise SystemExit("no free staging mount point (/mnt, /media or /srv)")


def preflight() -> list[str]:
    """Problems that stop runs before they start."""
    problems = []
    if sys.platform != "linux":
        problems.append("runs need Linux mount and PID namespaces")
    for tool in ("claude", "git", "unshare", "taskset"):
        if not shutil.which(tool):
            problems.append(f"{tool} is not on PATH")
    if not Path("/usr/bin/python3").exists():
        problems.append("the exec shim needs /usr/bin/python3")
    return problems


def unshare_prefix() -> list[str]:
    user = [] if os.geteuid() == 0 else ["--user", "--map-root-user"]
    return ["unshare", *user, "-m", "-p", "-f", "--mount-proc", "--propagation", "private", "--kill-child=SIGKILL"]


def install_shim(folder: Path) -> None:
    """Each run gets its own copy: a shared copy could be replaced under a running sandbox by another benchmark."""
    folder.mkdir(parents=True)
    for name in ("python", "python3", "pytest"):
        shutil.copy2(BENCH / "shim" / "python3", folder / name)
        (folder / name).chmod(0o755)
    shutil.copy2(BENCH / "shim" / "devtrace.py", folder / "devtrace.py")


# ---------------------------------------------------------------- one run

def permission_args(task: dict, arm: dict | None = None) -> list[str]:
    """One policy per task kind, identical in every arm except that a plugin arm may run its own helpers."""
    if task["kind"] == "write":
        return ["--permission-mode", "acceptEdits",
                "--allowedTools", "Bash", "Read", "Edit", "Write", "Grep", "Glob", "Skill", "TodoWrite", "Task",
                "--disallowedTools", "WebFetch", "WebSearch", *NETWORK_DENY]
    # Third-party repositories: read and search freely, edit if the agent chooses (graded), but never execute
    # repository code. Compound's own helpers are part of the treatment and only exist in plugin arms.
    allowed = [f"Bash({command}:*)" for command in READ_ONLY_BASH]
    for helper in PLUGIN_HELPERS:
        for python in ("python3 -B", "python3"):
            allowed.append(f"Bash({python} {SCRIPTS_MOUNT}/{helper}:*)")
    if arm and arm.get("plugin") and not is_compound(arm):
        # Another plugin's helpers are unknown to us, so any command that runs a file from its own folder is allowed.
        mount = plugin_mount(arm)
        allowed += [f"Bash({runner} {mount}/:*)" for runner in ("python3 -B", "python3", "python", "bash", "sh", "node")]
        allowed.append(f"Bash({mount}/:*)")
    return ["--permission-mode", "default",
            "--allowedTools", "Read", "Grep", "Glob", "Edit", "Write", "Skill", "TodoWrite", "Task", *allowed,
            "--disallowedTools", "WebFetch", "WebSearch", *NETWORK_DENY]


def claude_argv(task: dict, arm: dict, model: str) -> list[str]:
    argv = ["claude", "-p", task["prompt"], "--output-format", "stream-json", "--verbose", "--model", model,
            "--no-session-persistence", *permission_args(task, arm)]
    if arm["plugin"]:
        argv += ["--plugin-dir", plugin_mount(arm)]
    return argv


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def port_free(port: int) -> bool:
    with socket.socket() as sock:
        return sock.connect_ex(("127.0.0.1", port)) != 0


def environment(task: dict, arm: dict, port: int | None) -> dict[str, str]:
    env = {key: os.environ[key] for key in KEEP_ENV if key in os.environ}
    env.update({key: os.environ[key] for key in os.environ.get("BENCH_PASS_ENV", "").split(",") if key and key in os.environ})
    env.update(HOME=SANDBOX_HOME, CLAUDE_CONFIG_DIR=f"{SANDBOX_HOME}/.claude", PATH=sandbox_path(), LANG="C.UTF-8",
               TERM="dumb", DISABLE_AUTOUPDATER="1")
    if is_compound(arm) and port:
        env["COMPOUND_MAP_PORT"] = str(port)
    if task.get("pyenv"):
        # The project's test dependencies, read-only, and its src/ as an editable install would provide it.
        env["PYTHONPATH"] = f"{PYENV_MOUNT}:{SRC_ROOT}/{task['fixture']}/src"
    return env


def stat_signature(path: Path) -> str:
    """Cheap fingerprint of a worktree for change timestamps: names, sizes and mtimes outside .git."""
    parts = []
    for folder, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for name in files:
            full = os.path.join(folder, name)
            try:
                info = os.lstat(full)
            except FileNotFoundError:
                continue
            parts.append(f"{full}:{info.st_size}:{info.st_mtime_ns}")
    return sha256_bytes("\n".join(sorted(parts)).encode())


def flags_hash(cfg: Path) -> str | None:
    try:
        data = json.loads((cfg / ".claude.json").read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return sha256_bytes(json.dumps(data.get("cachedGrowthBookFeatures"), sort_keys=True).encode())


def prepare(task: dict, arm: dict, model: str) -> dict:
    if not TEMPLATE.is_dir():
        raise SystemExit("no template config: run `python3 bench/bench.py setup` first")
    run_id = secrets.token_hex(4)
    run = RUNS / run_id
    for name in ("home", "cfg", "state", "trace"):
        (run / name).mkdir(parents=True)
    if task["kind"] == "write":
        install_shim(run / "shim")
    shutil.copytree(TEMPLATE, run / "cfg", dirs_exist_ok=True, symlinks=True)
    project = task["fixture"]
    if not (FIXTURES / project).is_dir():
        raise SystemExit(f"fixture {project} is missing: run `python3 bench/bench.py setup`")
    shutil.copytree(FIXTURES / project, run / project, symlinks=True)
    (run / "home" / ".gitconfig").write_text(
        f"[user]\n\tname = {GIT_IDENTITY[0]}\n\temail = {GIT_IDENTITY[1]}\n[init]\n\tdefaultBranch = main\n"
        "[safe]\n\tdirectory = *\n")
    if task.get("plant_user_work"):
        task["plant_user_work"](run / project)
    compound = is_compound(arm)
    port = free_port() if compound else None
    setup: dict = {}
    if arm["source"] == "rule":
        (run / "cfg" / "rules").mkdir(exist_ok=True)
        (run / "cfg" / "rules" / "engineering.md").write_text(HABITS_RULE)
        setup["rule_sha256"] = sha256_bytes(HABITS_RULE.encode())
    if arm.get("rule_file"):
        text = Path(arm["rule_file"]).read_bytes()
        (run / "cfg" / "rules").mkdir(exist_ok=True)
        (run / "cfg" / "rules" / f"{arm['name']}.md").write_bytes(text)
        setup["extra_rule_sha256"] = sha256_bytes(text)
    if compound:
        out = subprocess.run([sys.executable, "-B", str(Path(arm["plugin"]) / "skills/compound/scripts/project_setup.py"), "enable",
                              "--global", "--host", "claude"],
                             env={"PATH": "/usr/bin:/bin", "HOME": str(run / "home"), "CLAUDE_CONFIG_DIR": str(run / "cfg"),
                                  "LANG": "C.UTF-8"}, capture_output=True, text=True, timeout=60)
        setup["rule_exit"] = out.returncode
        rule = run / "cfg" / "rules" / "compound-skills.md"
        setup["rule_sha256"] = sha256_bytes(rule.read_bytes()) if rule.exists() else None
    onboard = compound and task["kind"] == "write" and not task.get("first_use")
    write = task["kind"] == "write"
    return {"run_id": run_id, "run": run, "task": task, "arm": arm, "model": model, "port": port, "setup": setup,
            "onboard": onboard, "fixture_head": git(run / project, "rev-parse", "HEAD").strip(),
            "digests_pre": (digest(run / project, "src"), digest(run / project, "tests")) if write else None,
            "worktree_hash_pre": tree_hash(run / project) if not write or len(list((run / project).rglob("*"))) < 5000 else None,
            "flags_pre": flags_hash(run / "cfg")}


def execute(prep: dict, cpus: str, label: str, spawn_order: int, start_at: float) -> dict:
    run, task, arm = prep["run"], prep["task"], prep["arm"]
    project = task["fixture"]
    out_dir = RESULTS / label
    out_dir.mkdir(parents=True, exist_ok=True)
    stream_path = out_dir / f"{prep['run_id']}.stream"
    stderr_path = out_dir / f"{prep['run_id']}.stderr"
    keep = keep_paths()
    plugin = arm["plugin"] or "-"
    mount = plugin_mount(arm) if arm["plugin"] else "-"
    shim = str(run / "shim") if task["kind"] == "write" else "-"
    pyenv = str(PYENVS / task["pyenv"]) if task.get("pyenv") else "-"
    stage = stage_dir([str(run), plugin, shim, pyenv, *keep])
    argv = ["taskset", "-c", cpus, *unshare_prefix(), "/bin/sh", "-c", RUNNER, "runner", str(run), project, plugin,
            "1" if prep["onboard"] else "0", shim, "\n".join(keep), SANDBOX_HOME, TRACE_MOUNT, stage, pyenv, PYENV_MOUNT, mount,
            *claude_argv(task, arm, prep["model"])]
    env = environment(task, arm, prep["port"])
    changes: list[tuple[int, str, str]] = []
    stop = threading.Event()
    while time.time() < start_at:
        time.sleep(0.01)
    started = time.monotonic()
    started_wall = time.time()
    started_at = datetime.now(timezone.utc).isoformat()
    with stderr_path.open("w") as err:
        proc = subprocess.Popen(argv, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=err,
                                start_new_session=True)

        def watch() -> None:
            last, state = None, None
            while not stop.is_set():
                try:
                    signature = stat_signature(run / project)
                except OSError:
                    signature = last
                if signature != last:
                    last = signature
                    current = (digest(run / project, "src"), digest(run / project, "tests"))
                    if current != state:
                        changes.append((int((time.monotonic() - started) * 1000), *current))
                        state = current
                stop.wait(0.5)

        watcher = threading.Thread(target=watch, daemon=True) if task["kind"] == "write" else None
        if watcher:
            watcher.start()
        lines = 0
        timed_out = False

        def kill_after_cap() -> None:
            nonlocal timed_out
            if proc.poll() is None:
                timed_out = True
                for sig, pause in ((signal.SIGINT, 10), (signal.SIGTERM, 10), (signal.SIGKILL, 0)):
                    try:
                        os.killpg(proc.pid, sig)
                    except ProcessLookupError:
                        return
                    deadline = time.monotonic() + pause
                    while time.monotonic() < deadline and proc.poll() is None:
                        time.sleep(0.2)
                    if proc.poll() is not None:
                        return

        timer = threading.Timer(task["timeout"], kill_after_cap)
        timer.start()
        with stream_path.open("w") as stream:
            for raw in proc.stdout:
                stamp = int((time.monotonic() - started) * 1000)
                stream.write(f"{stamp}\t{raw.decode('utf-8', 'replace').rstrip()}\n")
                lines += 1
        code = proc.wait()
        timer.cancel()
        stop.set()
        if watcher:
            watcher.join()
    wall_ms = int((time.monotonic() - started) * 1000)
    leftovers = []
    for pid in os.listdir("/proc"):
        if pid.isdigit():
            try:
                if str(run) in Path(f"/proc/{pid}/cmdline").read_bytes().decode("utf-8", "replace"):
                    leftovers.append(int(pid))
            except OSError:
                pass
    for pid in leftovers:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    execs = []
    trace = run / "trace" / "exec.jsonl"
    if trace.exists():
        for line in trace.read_text(errors="replace").splitlines():
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            entry["ms0"], entry["ms1"] = int((entry.pop("t0") - started_wall) * 1000), int((entry.pop("t1") - started_wall) * 1000)
            execs.append(entry)
    return {"argv": claude_argv(task, arm, prep["model"]), "cpus": cpus, "spawn_order": spawn_order, "started_at": started_at,
            "execs": execs, "ended_at": datetime.now(timezone.utc).isoformat(), "exit_code": code, "timed_out": timed_out,
            "wall_ms": wall_ms, "stream_lines": lines, "changes": changes, "leftover_pids": leftovers,
            "port_free_after": port_free(prep["port"]) if prep["port"] else None,
            "stderr_tail": stderr_path.read_text(errors="replace")[-2000:]}


# ---------------------------------------------------------------- stream parsing

def guide_refs(calls: list[dict]) -> list[str]:
    """Compound guides read in a run, by the Read tool or in a shell command, also through a variable like $S/references/x.md."""
    names = {Path(str(c["input"].get("file_path", ""))).name for c in calls
             if c["name"] == "Read" and "/skills/compound/references/" in str(c["input"].get("file_path", ""))}
    for c in calls:
        command = str(c["input"].get("command", "")) if c["name"] == "Bash" else ""
        if "compound" in command:
            names.update(re.findall(r"references/([\w.-]+\.md)", command))
    return sorted(names)


FALLBACK = re.compile(r"local viewer unavailable|another map service|did not become healthy|map service exited|is busy; retry|code-map error")
SKILL = re.compile(r"^(compound-skills:)?(compound|map|setup|setup-global|status-global)$")


def text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(item.get("text", "") if isinstance(item, dict) else str(item) for item in content)
    return json.dumps(content) if content is not None else ""


def parse_stream(path: Path) -> dict:
    events = []
    parse_errors = 0
    for line in path.read_text(errors="replace").splitlines():
        stamp, _, body = line.partition("\t")
        try:
            events.append((int(stamp), json.loads(body)))
        except (ValueError, json.JSONDecodeError):
            parse_errors += 1
    init, result, init_ms = {}, {}, 0
    calls: dict[str, dict] = {}
    order: list[str] = []
    usage_by_message: dict[str, dict] = {}
    message_order: list[str] = []
    rate = None
    texts: list[str] = []
    fallback_events = []
    for stamp, event in events:
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "init" and not init:
            init, init_ms = event, stamp
        elif kind == "system" and event.get("subtype") in ("model_fallback", "api_retry"):
            fallback_events.append(event.get("subtype"))
        elif kind == "rate_limit_event":
            rate = event.get("rate_limit_info")
        elif kind == "assistant":
            message = event.get("message", {})
            sub = event.get("parent_tool_use_id") is not None
            if message.get("id") and message.get("usage"):
                if message["id"] not in usage_by_message:
                    message_order.append(message["id"])
                usage_by_message[message["id"]] = {"usage": message["usage"], "sub": sub}
            for block in message.get("content", []) or []:
                if block.get("type") == "tool_use":
                    calls[block["id"]] = {"name": block.get("name"), "input": block.get("input", {}), "sub": sub,
                                          "ms": stamp, "result_ms": None, "bytes": 0, "error": False, "text": ""}
                    order.append(block["id"])
                elif block.get("type") == "text" and not sub:
                    texts.append(block.get("text", ""))
        elif kind == "user":
            content = event.get("message", {}).get("content")
            for block in content if isinstance(content, list) else []:
                if block.get("type") == "tool_result" and block.get("tool_use_id") in calls:
                    text = text_of(block.get("content"))
                    call = calls[block["tool_use_id"]]
                    call.update(result_ms=stamp, bytes=len(text.encode()), error=bool(block.get("is_error")), text=text)
        elif kind == "result":
            result = event
    return {"events": len(events), "parse_errors": parse_errors, "init": init, "init_ms": init_ms, "result": result,
            "calls": [calls[i] for i in order], "usage": [usage_by_message[i] for i in message_order],
            "rate": rate, "assistant_text": texts, "fallback_events": fallback_events}


FAILURE = re.compile(r"FAILED \(|AssertionError|^=+ .*\b\d+ failed\b", re.M)
FULL_SUITE = r"\bdiscover\b"


def habits(prep: dict, harness: dict, calls: list[dict], final: tuple[str, str]) -> dict:
    """Engineering habits from the exec shim (exact source state at every python run) and the change watcher."""
    if not prep.get("digests_pre"):
        return {}
    orig_src, orig_tests = prep["digests_pre"]
    final_src, final_tests = final
    execs = [e for e in harness.get("execs") or [] if e["ms0"] >= harness.get("init_ms", 0)]
    starts = [ms for ms, src, _ in harness.get("changes") or [] if src != orig_src]
    starts += [e["ms0"] for e in execs if e["src0"] == orig_src and e["src1"] != orig_src]
    src_root = f"{SRC_ROOT}/{prep['task']['fixture']}/src/"
    starts += [c["ms"] for c in calls if c["name"] in ("Edit", "Write", "MultiEdit") and not c["error"]
               and str(c["input"].get("file_path", "")).startswith(src_root)]
    first_src_change = min(starts) if starts else None
    helper = lambda e: any("/claude-plugins/" in str(a) for a in e["argv"])  # noqa: E731
    runs = [e for e in execs if not helper(e) and (e["src0"], e["tests0"]) == (e["src1"], e["tests1"])]
    # pytest counts only where it is installed: elsewhere `python -m pytest` exits 1 without running a test.
    runner = r"unittest|pytest" if prep["task"].get("pyenv") else r"unittest"
    is_test = lambda e: (any(re.search(runner, str(a)) for a in e["argv"])  # noqa: E731
                         or any(re.search(r"(^|/)tests/.+\.py$", str(a)) for a in e["argv"]))
    symptom = re.compile(prep["task"]["symptom"]) if prep["task"].get("symptom") else None
    full_suite = re.compile(prep["task"].get("full_suite", FULL_SUITE))

    def output(entry: dict) -> str:
        for c in calls:
            if c["name"] == "Bash" and c["ms"] - 200 <= entry["ms0"] and entry["ms1"] <= (c["result_ms"] or 10 ** 12) + 200:
                return c["text"]
        return ""

    before = [e for e in runs if e["src0"] == orig_src and (first_src_change is None or e["ms1"] <= first_src_change)]
    return {
        "first_src_change_ms": first_src_change,
        "python_runs": len(runs), "test_runs": sum(1 for e in runs if is_test(e)),
        "ran_before_change": bool(before),
        "reproduced_before_fix": any((symptom and symptom.search(output(e))) or FAILURE.search(output(e)) for e in before),
        "failing_test_on_old_code": any(is_test(e) and e["src0"] == orig_src and e["tests0"] != orig_tests and e["exit"] != 0 for e in runs),
        "final_state_tested": any(is_test(e) and e["exit"] == 0 and e["src0"] == final_src and e["tests0"] == final_tests for e in runs),
        "final_full_suite_ok": any(is_test(e) and e["exit"] == 0 and e["src0"] == final_src and e["tests0"] == final_tests
                                   and full_suite.search(" ".join(map(str, e["argv"]))) for e in runs),
        "src_changed": final_src != orig_src, "tests_changed": final_tests != orig_tests,
    }


def summarize(parsed: dict, prep: dict, harness: dict) -> dict:
    init, result, calls = parsed["init"], parsed["result"], parsed["calls"]
    model_usage = result.get("modelUsage") or {}
    tokens = {"input": 0, "cache_creation": 0, "cache_read": 0, "output": 0, "thinking": 0, "cost_usd": 0.0}
    for usage in model_usage.values():
        tokens["input"] += usage.get("inputTokens", 0)
        tokens["cache_creation"] += usage.get("cacheCreationInputTokens", 0)
        tokens["cache_read"] += usage.get("cacheReadInputTokens", 0)
        tokens["output"] += usage.get("outputTokens", 0)
        tokens["thinking"] += usage.get("thinkingTokens", 0)
        tokens["cost_usd"] += usage.get("costUSD", 0.0)
    tokens["context_total"] = tokens["input"] + tokens["cache_creation"] + tokens["cache_read"]
    first = parsed["usage"][0]["usage"] if parsed["usage"] else {}
    tokens["first_call_context"] = sum(first.get(key, 0) for key in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    per_call = [sum(u["usage"].get(key, 0) for key in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")) for u in parsed["usage"]]
    tokens["peak_call_context"] = max(per_call) if per_call else 0
    tokens["api_calls"] = len(per_call)
    by_name: dict[str, int] = {}
    for call in calls:
        by_name[call["name"]] = by_name.get(call["name"], 0) + 1
    arm = prep["arm"]
    compound = is_compound(arm)
    skill_calls = [c["input"].get("skill") for c in calls if c["name"] == "Skill"]
    compound_skill = [s for s in skill_calls if s and SKILL.match(s)] if compound else []
    # Another plugin's skills are namespaced by its manifest name, as Compound's are by compound-skills.
    plugin_skill = [s for s in skill_calls if s and not compound and arm.get("plugin")
                    and s.startswith(f"{arm.get('plugin_name')}:")]
    references = guide_refs(calls) if compound else []
    map_calls = []
    for c in calls if compound else []:
        command = str(c["input"].get("command", "")) if c["name"] == "Bash" else ""
        script = re.search(r"(code_map|symbol_lookup|lsp_lookup|map_server)\.py", command)
        if script:
            map_calls.append({"script": script.group(1), "query": bool(re.search(r"--query", command)),
                              "cache_read_only": "--cache-read-only" in command, "ms": (c["result_ms"] or c["ms"]) - c["ms"],
                              "out_bytes": c["bytes"], "fallback": bool(FALLBACK.search(c["text"])), "error": c["error"]})
    onboarding_calls = [re.search(r"onboarding\.py\s+(\w+)", str(c["input"].get("command", ""))).group(1)
                        for c in calls if c["name"] == "Bash" and re.search(r"onboarding\.py\s+\w+", str(c["input"].get("command", "")))]
    audit_calls = sum(1 for c in calls if c["name"] == "Bash" and "repo_audit.py" in str(c["input"].get("command", "")))
    skill_loaded = compound and any("Base directory for this skill:" in c["text"] and "/skills/compound" in c["text"]
                                    for c in calls if c["name"] == "Skill")
    activation = "none"
    if compound_skill or skill_loaded:
        activation = "skill" + ("+refs" if references else "") + ("+map" if map_calls else "")
    elif plugin_skill:
        activation = "plugin-skill"
    leak_text = "\n".join(json.dumps(c["input"]) + c["text"] for c in calls) + "\n".join(parsed["assistant_text"])
    control_leak = not prep["arm"]["plugin"] and bool(re.search(r"(?i)compound", leak_text))
    project = prep["run"] / prep["task"]["fixture"]
    final_digests = (digest(project, "src"), digest(project, "tests")) if prep.get("digests_pre") else None
    habit = habits(prep, harness, calls, final_digests) if final_digests else {}
    return {
        "init": {"model": init.get("model"), "cwd": init.get("cwd"), "permission_mode": init.get("permissionMode"),
                 "version": init.get("claude_code_version"), "plugins": [(p.get("name"), p.get("path"), p.get("version")) for p in init.get("plugins", [])],
                 "skills": init.get("skills", []), "tools": init.get("tools", []), "mcp_servers": init.get("mcp_servers"),
                 "effort_per_turn": init.get("per_turn_effort_active"), "fast_mode": init.get("fast_mode_state"),
                 "session_id": init.get("session_id")},
        "result": {"present": bool(result), "subtype": result.get("subtype"), "is_error": result.get("is_error"),
                   "terminal_reason": result.get("terminal_reason"), "api_error_status": result.get("api_error_status"),
                   "num_turns": result.get("num_turns"), "duration_ms": result.get("duration_ms"),
                   "duration_api_ms": result.get("duration_api_ms"), "models": sorted(model_usage),
                   "denials": result.get("permission_denials", []), "subagents": (result.get("subagent_stats") or {}).get("spawned", 0),
                   "subagents_by_type": (result.get("subagent_stats") or {}).get("by_type", {})},
        "tokens": tokens,
        "trace": {"tool_calls": len(calls), "by_name": by_name, "in_subagents": sum(1 for c in calls if c["sub"]),
                  "tool_errors": sum(1 for c in calls if c["error"]), "tool_output_bytes": sum(c["bytes"] for c in calls),
                  "files_read": len({str(c["input"].get("file_path")) for c in calls if c["name"] == "Read"}),
                  "grep_calls": by_name.get("Grep", 0) + sum(1 for c in calls if c["name"] == "Bash" and re.search(r"\b(grep|rg)\b", str(c["input"].get("command", "")))),
                  "bash": [str(c["input"].get("command", ""))[:500] for c in calls if c["name"] == "Bash"],
                  "fallback_events": parsed["fallback_events"]},
        "habits": habit, "digests_pre": prep.get("digests_pre"), "digests_final": final_digests,
        "compound": {"skill_calls": skill_calls, "compound_skill": bool(compound_skill), "skill_loaded": skill_loaded,
                     "plugin_skill_calls": plugin_skill,
                     "references": references, "map_calls": map_calls, "onboarding_calls": onboarding_calls,
                     "audit_calls": audit_calls, "activation": activation, "control_leak": control_leak},
        "final_message": result.get("result") or "",
        "rate": parsed["rate"],
        "parse_errors": parsed["parse_errors"],
    }


def validity(record: dict) -> tuple[bool, list[str], str | None]:
    """Decided from config, init, result and harness fields only, before any grading."""
    reasons, infra = [], None
    init, result, harness, compound = record["init"], record["result"], record["harness"], record["compound"]
    plugin_arm = bool(record["plugin_hash"])
    plugin_name = record.get("plugin_name") or COMPOUND
    compound_arm = is_compound(record)
    if not result["present"]:
        tail = harness.get("stderr_tail", "")
        infra = "api" if re.search(r"(?i)api error|overloaded|rate.?limit|529|5\d\d|ECONNRESET|socket hang up|network", tail) else "harness"
        if harness.get("timed_out"):
            infra = None  # an agent that runs past the cap is a failure, not an infra problem
        reasons.append("no result event")
    elif result.get("api_error_status"):
        infra = "api"
        reasons.append(f"api error {result['api_error_status']}")
    if init.get("model") and not same_model(record["model"], init["model"]):
        reasons.append(f"init model {init['model']}")
    if result["models"] and set(result["models"]) - {init.get("model")}:
        reasons.append(f"other models used: {result['models']}")
    if init.get("cwd") and not str(init["cwd"]).startswith(SRC_ROOT + "/"):
        reasons.append(f"cwd {init['cwd']}")
    # Claude Code's own bundled plugins (cc-plugin-*) load in every arm; any other plugin must be the arm's.
    loaded = {name for name, *_ in init.get("plugins", []) if name and not str(name).startswith("cc-plugin-")}
    has_skill = f"{COMPOUND}:compound" in (init.get("skills") or [])
    if plugin_arm and init and (plugin_name not in loaded or (compound_arm and not has_skill)):
        reasons.append("plugin not loaded")
    if plugin_arm and loaded - {plugin_name}:
        reasons.append(f"other plugins loaded: {sorted(loaded - {plugin_name})}")
    if not plugin_arm and (loaded or has_skill):
        reasons.append("plugin present in control")
    if compound["control_leak"]:
        reasons.append("control saw compound")
    if any(call["fallback"] for call in compound["map_calls"]):
        reasons.append("map fallback")
    if compound_arm and record["setup"].get("rule_sha256") is None:
        reasons.append("rule missing")
    if record.get("extra_rule_sha256") and record["setup"].get("extra_rule_sha256") != record["extra_rule_sha256"]:
        reasons.append("arm rule missing")
    if record.get("onboarding_status") not in (None, "completed"):
        reasons.append(f"onboarding {record.get('onboarding_status')}")
    if plugin_arm and record["onboard"] and (compound["audit_calls"] or "claim" in compound["onboarding_calls"]):
        reasons.append("steady-state run did the first-use check-up")
    if harness.get("port_free_after") is False:
        reasons.append("map port still held")
    if harness.get("leftover_pids"):
        reasons.append("leftover processes")
    if init.get("fast_mode") not in (None, "off"):
        reasons.append("fast mode")
    return (not reasons, reasons, infra)


def onboarding_status(stderr: str) -> str | None:
    match = re.search(r"^@@status (.*)$", stderr, re.M)
    if not match:
        return None
    try:
        return json.loads(match.group(1)).get("status")
    except json.JSONDecodeError:
        return "unparsed"


def one(prep: dict, cpus: str, label: str, spawn_order: int, start_at: float, rep: int, group_id: str) -> dict:
    task, arm = prep["task"], prep["arm"]
    harness = execute(prep, cpus, label, spawn_order, start_at)
    parsed = parse_stream(RESULTS / label / f"{prep['run_id']}.stream")
    harness["init_ms"] = parsed["init_ms"]
    record = {"schema": 3, "run_id": prep["run_id"], "pair_id": group_id, "task": task["name"], "arm": arm["name"],
              "arm_source": arm["source"], "plugin_hash": arm.get("plugin_hash"), "plugin_version": arm.get("plugin_version"),
              "plugin_name": arm.get("plugin_name"), "extra_rule_sha256": arm.get("rule_sha256"),
              "plugin_commit": arm.get("commit"), "model": prep["model"], "rep": rep, "kind": task.get("cell", "measured"),
              "fixture": task["fixture"], "fixture_head": prep["fixture_head"],
              "prompt_sha256": sha256_bytes(task["prompt"].encode()), "setup": prep["setup"], "onboard": prep["onboard"],
              "port": prep["port"], "flags_pre": prep["flags_pre"], "flags_post": flags_hash(prep["run"] / "cfg"),
              "synced": [str(p.relative_to(prep["run"])) for p in (prep["run"] / "cfg").glob("*/synced")],
              "onboarding_status": onboarding_status((RESULTS / label / f"{prep['run_id']}.stderr").read_text(errors="replace")) if prep["onboard"] else None,
              "harness": harness}
    record.update(summarize(parsed, prep, harness))
    record["valid"], record["invalid_reasons"], record["infra_failure"] = validity(record)
    if record["synced"]:
        record["valid"] = False
        record["invalid_reasons"].append("synced skills or plugins")
    project_dir = prep["run"] / task["fixture"]
    record["outcome"] = {"porcelain": git(project_dir, "status", "--porcelain")[:4000],
                         "head_moved": git(project_dir, "rev-parse", "HEAD").strip() != prep["fixture_head"]}
    if prep["worktree_hash_pre"]:
        record["outcome"]["worktree_unchanged"] = tree_hash(project_dir) == prep["worktree_hash_pre"]
    if task.get("grade"):
        try:
            record["outcome"].update(task["grade"](project_dir, record, prep))
        except Exception as error:  # a grader failure is recorded, never hidden
            record["outcome"]["grade_error"] = repr(error)
    record["timed_out"] = harness["timed_out"]
    if task["kind"] == "write":
        subprocess.run(["tar", "-czf", str(RESULTS / label / f"{prep['run_id']}.final.tgz"), "-C", str(project_dir), "src", "tests"],
                       capture_output=True)
    (RESULTS / label / f"{prep['run_id']}.diff").write_text(
        git(project_dir, "log", "-p", "--format=commit %H%nAuthor: %an <%ae>%n%n%B", f"{prep['fixture_head']}..HEAD")
        + "\n=== uncommitted ===\n" + git(project_dir, "diff", "HEAD"))
    (RESULTS / label / f"{prep['run_id']}.json").write_text(json.dumps(record, indent=1, default=str))
    shutil.rmtree(prep["run"], ignore_errors=True)
    with LOCK:
        shown = {k: v for k, v in record["outcome"].items()
                 if k in ("success", "hidden_pass", "regression_valid", "commit_made", "ai_trailer", "worktree_unchanged")}
        print(f"[{datetime.now(timezone.utc):%H:%M:%S}] {label} {task['name']} rep {rep} {arm['name']:8s} {prep['model']}: "
              f"valid={record['valid']} {record['invalid_reasons'] or ''} wall={harness['wall_ms'] / 1000:.0f}s "
              f"cost={record['tokens']['cost_usd']:.3f} act={record['compound']['activation']} "
              f"map={len(record['compound']['map_calls'])} outcome={json.dumps(shown)}", flush=True)
    return record


def group(task: dict, arms: list[dict], model: str, rep: int, label: str, slot: int, first_cpu: int = 0) -> list[dict]:
    """Every arm on the same task at the same moment, each on its own CPU; order and CPUs rotate by repetition."""
    group_id = secrets.token_hex(4)
    count = len(arms)
    shift = rep % count
    order = arms[shift:] + arms[:shift]
    total = os.cpu_count() or 1
    cpus = [str((first_cpu + slot * count + index) % total) for index in range(count)]
    turn = (rep // count) % count
    cpus = cpus[turn:] + cpus[:turn]
    preps = [prepare(task, arm, model) for arm in order]
    start_at = time.time() + 0.5
    with concurrent.futures.ThreadPoolExecutor(count) as pool:
        futures = [pool.submit(one, prep, cpus[i], label, i, start_at + 0.05 * i, rep, group_id) for i, prep in enumerate(preps)]
        return [future.result() for future in futures]


def utilization(label: str) -> tuple[float, float, int]:
    """Latest seven-day and five-hour utilization reported by any run in this label."""
    latest, seven, five, reset = 0.0, 0.0, 0.0, 0
    for path in (RESULTS / label).glob("*.json"):
        if path.name.endswith(".judge.json") or path.name in ("arms.json", "summary.json"):
            continue
        try:
            record = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(record, dict):
            continue
        windows = (record.get("rate") or {}).get("unifiedWindows") or {}
        stamp = path.stat().st_mtime
        if windows and stamp > latest:
            latest = stamp
            seven = windows.get("seven_day", {}).get("utilization", 0.0)
            five = windows.get("five_hour", {}).get("utilization", 0.0)
            reset = windows.get("five_hour", {}).get("resetsAt", 0)
    return seven, five, reset


def load_records(label: str) -> list[dict]:
    records = []
    for path in sorted((RESULTS / label).glob("*.json")):
        if path.name.endswith(".judge.json") or path.name in ("arms.json", "summary.json"):
            continue
        try:
            record = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(record, dict) and "pair_id" in record:
            records.append(record)
    return records


def run_matrix(label: str, arm_specs: list[dict], tasks: list[dict], models: list[str], reps: int, first_rep: int,
               slots: int, retry: bool, max_seven_day: float, pause_five_hour: float, first_cpu: int = 0) -> int:
    out = RESULTS / label
    out.mkdir(parents=True, exist_ok=True)
    arms = [materialize(arm) for arm in arm_specs]
    known = json.loads((out / "arms.json").read_text()) if (out / "arms.json").exists() else {}
    for arm in arms:
        previous = known.get(arm["name"])
        if previous and (previous.get("plugin_hash"), previous.get("rule_sha256")) != (arm.get("plugin_hash"), arm.get("rule_sha256")):
            raise SystemExit(f"arm {arm['name']} in label {label} ran a different plugin or rule ({previous.get('plugin_hash')}); "
                             "use a new label or a new arm name")
        known[arm["name"]] = {k: v for k, v in arm.items() if k != "plugin"}
    (out / "arms.json").write_text(json.dumps(known, indent=1))
    stop_file = out / "STOP"
    stop_file.unlink(missing_ok=True)
    done = {(r["task"], r["model"], r["rep"], r["arm"]) for r in load_records(label) if not r.get("superseded")}
    queue = []
    for rep in range(first_rep, first_rep + reps):
        for model in models:
            order = list(tasks)
            random.Random(f"{label}-{rep}-{model}").shuffle(order)
            for task in order:
                missing = [arm for arm in arms if (task["name"], model, rep, arm["name"]) not in done]
                if missing:
                    queue.append((task, missing, model, rep))
    (out / f"schedule-{datetime.now(timezone.utc):%Y%m%d%H%M%S}.txt").write_text(
        "\n".join(f"{t['name']} {m} rep {r}: {', '.join(a['name'] for a in arms_)}" for t, arms_, m, r in queue) + "\n")
    print(f"{label}: {len(queue)} groups to run, arms {', '.join(a['name'] for a in arms)}", flush=True)
    lock = threading.Lock()
    stop = threading.Event()

    def worker(slot: int) -> None:
        while not stop.is_set():
            with lock:
                if not queue:
                    return
                task, group_arms, model, rep = queue.pop(0)
            if stop_file.exists():
                print("stopping: STOP file", flush=True)
                stop.set()
                return
            seven, five, reset = utilization(label)
            if seven >= max_seven_day:
                print(f"stopping: seven-day utilization {seven}", flush=True)
                stop.set()
                return
            if five >= pause_five_hour and reset:
                wait = max(0, reset - time.time()) + 60
                print(f"pausing {wait:.0f}s for the five-hour window ({five})", flush=True)
                time.sleep(wait)
            records = group(task, group_arms, model, rep, label, slot, first_cpu)
            if any(r["infra_failure"] for r in records) and retry:
                print(f"re-running {task['name']} rep {rep} {model} after an infra failure", flush=True)
                for r in records:
                    path = RESULTS / label / f"{r['run_id']}.json"
                    data = json.loads(path.read_text())
                    data["superseded"] = True
                    path.write_text(json.dumps(data, indent=1, default=str))
                group(task, group_arms, model, rep, label, slot, first_cpu)

    with concurrent.futures.ThreadPoolExecutor(slots) as pool:
        list(pool.map(worker, range(slots)))
    return 0


def make_template(model: str) -> dict:
    """One trivial run in the neutral layout with an empty config, then strip everything run-specific."""
    if TEMPLATE.exists():
        shutil.rmtree(TEMPLATE)
    TEMPLATE.mkdir(parents=True)
    task = {"name": "template", "fixture": "invoicekit", "kind": "write", "prompt": "Reply with the single word OK.", "timeout": 300}
    arm = {"name": "without", "source": "none", "plugin": None}
    prep = prepare(task, arm, model)
    harness = execute(prep, "0", "template", 0, time.time())
    shutil.copytree(prep["run"] / "cfg", TEMPLATE, dirs_exist_ok=True, symlinks=True)
    for name in ("projects", "sessions", "backups", "shell-snapshots", "todos", "statsig", "debug", "file-history", "plans",
                 "paste-cache", "session-env"):
        shutil.rmtree(TEMPLATE / name, ignore_errors=True)
    config = TEMPLATE / ".claude.json"
    if config.exists():
        data = json.loads(config.read_text())
        data.pop("projects", None)
        config.write_text(json.dumps(data, indent=2))
    shutil.rmtree(prep["run"], ignore_errors=True)
    parsed = parse_stream(RESULTS / "template" / f"{prep['run_id']}.stream")
    ok = bool(parsed["result"]) and not parsed["result"].get("is_error") and harness["exit_code"] == 0
    if not ok:
        shutil.rmtree(TEMPLATE, ignore_errors=True)
    return {"ok": ok, "exit": harness["exit_code"], "wall_ms": harness["wall_ms"], "model": parsed["init"].get("model"),
            "claude_code": parsed["init"].get("claude_code_version"), "reply": (parsed["result"] or {}).get("result"),
            "stderr": harness["stderr_tail"][-800:]}


def rescore(label: str) -> int:
    """Recompute habits and guide reads from saved transcripts with the current detectors."""
    from tasks import TASKS
    changed = 0
    for path in sorted((RESULTS / label).glob("*.json")):
        if path.name.endswith(".judge.json") or path.name in ("arms.json", "summary.json"):
            continue
        record = json.loads(path.read_text())
        stream = path.with_suffix(".stream")
        task = TASKS.get(record.get("task"))
        if not isinstance(record, dict) or "pair_id" not in record or not stream.exists() or not task:
            continue
        calls = parse_stream(stream)["calls"]
        before = (record.get("habits"), record["compound"].get("references"))
        record["compound"]["references"] = guide_refs(calls) if is_compound(record) else []
        if record.get("digests_pre") and record.get("digests_final"):
            prep = {"task": task, "digests_pre": record["digests_pre"]}
            record["habits"] = habits(prep, record["harness"], calls, tuple(record["digests_final"]))
        if (record.get("habits"), record["compound"].get("references")) != before:
            changed += 1
            path.write_text(json.dumps(record, indent=1, default=str))
    print(f"{label}: {changed} records rescored")
    return 0

