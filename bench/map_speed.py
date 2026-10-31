"""Time Compound's code map on real repositories, as the agent and the viewer run it.

Per repository (a git copy, so the sources stay untouched; files are read as data, nothing is executed):
- build, cold: in-process builds, each with a fresh state directory
- build, unchanged: rebuilds on a warm cache
- build after a one-file edit: edits of a leaf file and of the most-imported file
- agent query, exactly as the skill runs it: `code_map.py --query` cold (starts the local service and indexes),
  warm (second call), and `--cache-read-only` with no cache (read-only tasks)
"""
from __future__ import annotations

import importlib
import os
import platform
import shutil
import socket
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

_SCRIPTS: list[Path] = []


def use_scripts(path: Path) -> None:
    _SCRIPTS[:] = [path]


def scripts() -> Path:
    return _SCRIPTS[0]


def load_code_map():
    if str(scripts()) not in sys.path:
        sys.path.insert(0, str(scripts()))
    return importlib.import_module("code_map")


QUERY = "how are requests routed to handlers"


def stats(values: list[float]) -> dict:
    return {"median": round(statistics.median(values), 3), "min": round(min(values), 3), "max": round(max(values), 3), "n": len(values)}


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def agent_call(repo: Path, state: Path, port: int, *flags: str) -> tuple[float, int]:
    env = {"PATH": "/usr/bin:/bin", "HOME": str(state), "LANG": "C.UTF-8", "COMPOUND_SKILLS_STATE_DIR": str(state), "COMPOUND_MAP_PORT": str(port)}
    started = time.perf_counter()
    out = subprocess.run([sys.executable, "-B", str(scripts() / "code_map.py"), "--repo", str(repo), "--query", QUERY, *flags],
                         env=env, capture_output=True, text=True, timeout=900)
    return time.perf_counter() - started, len(out.stdout)


def stop_service(state: Path, port: int) -> None:
    env = {"PATH": "/usr/bin:/bin", "HOME": str(state), "LANG": "C.UTF-8", "COMPOUND_SKILLS_STATE_DIR": str(state), "COMPOUND_MAP_PORT": str(port)}
    subprocess.run([sys.executable, "-B", str(scripts() / "map_server.py"), "stop"], env=env, capture_output=True, timeout=120)


def bench(source: Path, reps: int) -> dict:
    with tempfile.TemporaryDirectory(prefix="map-bench-") as folder:
        base = Path(folder)
        repo = base / source.name
        shutil.copytree(source, repo, symlinks=True)
        tracked = subprocess.run(["git", "ls-files"], cwd=repo, capture_output=True, text=True).stdout.splitlines()

        def build(state: Path):
            os.environ["COMPOUND_SKILLS_STATE_DIR"] = str(state)
            started = time.perf_counter()
            model, _ = load_code_map().build_map(repo, max_files=20000, no_cache=False, output_format="json")
            return model, time.perf_counter() - started

        cold = []
        for index in range(reps):
            state = base / f"state-cold-{index}"
            state.mkdir()
            model, seconds = build(state)
            cold.append(seconds)
        warm_state = base / "state-cold-0"
        unchanged = [build(warm_state)[1] for _ in range(reps)]
        files = model["files"]
        importers: dict[str, int] = {}
        for item in files:
            for dep in item.get("dependencies", []):
                target = dep if isinstance(dep, str) else dep.get("path")
                if target:
                    importers[target] = importers.get(target, 0) + 1
        code_files = [item["path"] for item in files if item.get("language") in {"python", "typescript", "javascript", "go", "rust"}]
        hub = max(importers, key=importers.get) if importers else code_files[0]
        leaves = sorted(path for path in code_files if path not in importers)
        leaf = leaves[len(leaves) // 2] if leaves else code_files[0]
        edits = {}
        for label, path in (("leaf", leaf), ("hub", hub)):
            target = repo / path
            times = []
            for index in range(reps):
                with target.open("a", encoding="utf-8") as handle:
                    handle.write(f"\n// bench edit {index}\n" if target.suffix in {".ts", ".js", ".go", ".rs", ".tsx"} else f"\n# bench edit {index}\n")
                times.append(build(warm_state)[1])
            edits[label] = {"path": path, "importers": importers.get(path, 0), **stats(times)}
        subprocess.run(["git", "checkout", "-q", "--", "."], cwd=repo)
        query_cold, query_warm, read_only, chars = [], [], [], 0
        for index in range(reps):
            state, port = base / f"state-agent-{index}", free_port()
            state.mkdir()
            seconds, chars = agent_call(repo, state, port)
            query_cold.append(seconds)
            query_warm.append(agent_call(repo, state, port)[0])
            stop_service(state, port)
            ro_state = base / f"state-ro-{index}"
            ro_state.mkdir()
            read_only.append(agent_call(repo, ro_state, free_port(), "--cache-read-only")[0])
        coverage = model.get("coverage", {})
        return {
            "repo": source.name, "tracked_files": len(tracked), "indexed_files": coverage.get("indexed") or len(files),
            "import_links": sum(len(item.get("dependencies", [])) for item in files), "symbols": sum(len(item.get("symbols", [])) for item in files),
            "build_cold_s": stats(cold), "build_unchanged_s": stats(unchanged), "build_after_edit_s": edits,
            "agent_query_cold_s": stats(query_cold), "agent_query_warm_s": stats(query_warm), "agent_read_only_s": stats(read_only),
            "agent_output_chars": chars, "reps": reps,
        }


def machine() -> dict:
    cpu = ""
    try:
        cpu = next(line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines() if line.startswith("model name"))
    except (OSError, StopIteration):
        pass
    return {"cpu": cpu, "cores": os.cpu_count(), "python": platform.python_version(), "platform": platform.platform()}
