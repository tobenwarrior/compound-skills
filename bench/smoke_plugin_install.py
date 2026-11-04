"""Install an archived Compound release and smoke-test it in temporary host homes."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from urllib.parse import urljoin, urlsplit
from urllib.request import ProxyHandler, build_opener

from common import REPO, git

PLUGIN = "compound-skills@compound-skills"
ENTRYPOINTS = {"compound", "map", "setup", "setup-global", "status-global"}


def check_host(host, executable, package, scratch):
    home = scratch / "home"
    config = scratch / "host config"
    project = scratch / "example project"
    for directory in (home, config, project):
        directory.mkdir(parents=True)
    env = {
        "PATH": os.environ["PATH"],
        "HOME": str(home),
        "CODEX_HOME": str(config if host == "codex" else home / ".codex"),
        "CLAUDE_CONFIG_DIR": str(config if host == "claude" else home / ".claude"),
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "COMPOUND_SKILLS_STATE_DIR": str(scratch / "state"),
        "COMPOUND_MAP_PORT": "0",
    }

    def run(*args):
        return subprocess.run(args, cwd=project, env=env, capture_output=True, check=True, text=True, timeout=60).stdout.strip()

    version = run(executable, "--version")
    run(executable, "plugin", "marketplace", "add", str(package), "--json")
    if host == "codex":
        installed = json.loads(run(executable, "plugin", "add", PLUGIN, "--json"))
        assert installed["pluginId"] == PLUGIN
        retained = config / "AGENTS.md"
    else:
        run(executable, "plugin", "install", PLUGIN, "--json")
        installed, = [row for row in json.loads(run(executable, "plugin", "list", "--json")) if row["id"] == PLUGIN]
        assert installed["enabled"] and installed["scope"] == "user"
        retained = config / "CLAUDE.md"
    path_field = "installedPath" if host == "codex" else "installPath"
    cache = Path(installed[path_field]).resolve()
    assert cache.is_relative_to(config.resolve())
    assert {path.parent.name for path in (cache / "skills").glob("*/SKILL.md")} == ENTRYPOINTS

    retained.write_text("Keep this existing instruction.\n")
    scripts = cache / "skills" / "compound" / "scripts"

    def routing(action):
        return json.loads(run(sys.executable, "-B", str(scripts / "project_setup.py"),
                              action, "--global"))

    assert not routing("status")["hosts"][host]["configured"]
    assert routing("enable")["hosts"][host]["configured"]
    assert not routing("enable")["changed"]
    status = routing("status")
    assert status["status"] == "enabled" and set(status["hosts"]) == {host}

    run("git", "init", "-q")
    (project / "demo.py").write_text("def demo():\n    return 42\n")
    query = (sys.executable, "-B", str(scripts / "code_map.py"), "--repo", str(project),
             "--format", "json", "--query", "demo.py", "--max-files", "1")
    service = (sys.executable, "-B", str(scripts / "map_server.py"))
    try:
        assert json.loads(run(*query))["focus"] == ["demo.py"]
    finally:
        run(*service, "stop")

    directory = Path(env["COMPOUND_SKILLS_STATE_DIR"]) / "code-map"
    cached, = [path for path in directory.glob("*.json") if path.name != "registry.json"]
    invalid = b'{"version":' + b"9" * 6000 + b"}"
    for path in (cached, directory / "runtime.json", directory / "registry.json"):
        path.write_bytes(invalid)
        path.chmod(0o600)
    model = json.loads(run(*query, "--cache-read-only"))
    assert model["focus"] == ["demo.py"]
    assert "invalid cache entries were reparsed" in model["coverage"]["notes"]
    assert cached.read_bytes() == invalid

    try:
        url = run(*service, "open", "--repo", str(project), "--query", "demo.py", "--no-open")
        assert json.loads(run(*query))["focus"] == ["demo.py"]
        assert cached.read_bytes() != invalid
        assert urlsplit(url).hostname == "127.0.0.1"
        opener = build_opener(ProxyHandler({}))
        with opener.open(url, timeout=5) as response:
            assert response.status == 200 and b'id="graph"' in response.read()
        with opener.open(urljoin(url, "code-map.css"), timeout=5) as response:
            assert response.status == 200 and response.headers.get_content_type() == "text/css"
    finally:
        run(*service, "stop")

    assert not routing("disable")["hosts"][host]["configured"]
    assert not routing("status")["hosts"][host]["configured"]
    assert retained.read_text() == "Keep this existing instruction.\n"
    return {"host": host, "host_version": version, "installed_version": installed["version"],
            "skills": sorted(ENTRYPOINTS), "global_enable_status_disable": "pass",
            "read_only_map": "pass", "invalid_state_recovery": "pass", "local_viewer_html_and_css": "pass"}


def smoke(ref, hosts):
    revision = git(REPO, "rev-parse", "--verify", ref + "^{tree}", check=True).strip()
    with TemporaryDirectory(prefix="compound-install-smoke-") as scratch:
        root = Path(scratch).resolve()
        package = root / "package"
        package.mkdir()
        archive = subprocess.check_output(["git", "archive", revision], cwd=REPO)
        subprocess.run(["tar", "-xf", "-"], cwd=package, input=archive, check=True)
        results = []
        for host in hosts:
            executable = shutil.which(host)
            if executable is None:
                raise ValueError(f"{host} CLI is required for this smoke check")
            results.append(check_host(host, executable, package, root / host))
    return {"scope": "Local archive and isolated host homes. No model calls.", "source_tree": revision,
            "python": platform.python_version(), "results": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--host", choices=("claude", "codex"), action="append")
    args = parser.parse_args()
    print(json.dumps(smoke(args.ref, args.host or ("codex", "claude")), indent=2))
