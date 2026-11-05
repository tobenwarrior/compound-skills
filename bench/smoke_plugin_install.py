"""Install an archived Compound release and smoke-test it in temporary host homes."""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import threading
from tempfile import TemporaryDirectory
from urllib.parse import urljoin, urlsplit
from urllib.request import ProxyHandler, build_opener

from common import REPO, git

PLUGIN = "compound-skills@compound-skills"
ENTRYPOINTS = {"compound", "map", "setup", "setup-global", "status-global"}


def check_codex_fresh_chat(executable, project, env, cache, routing):
    """Check a fresh native request at a loopback-only, scripted provider."""
    sandbox = shutil.which("sandbox-exec")
    if platform.system() != "Darwin" or sandbox is None:
        raise ValueError("The fresh Codex chat check requires the macOS network sandbox")

    prompt = ("Trace demo from its entry point to its implementation and tests. "
              "Cite file paths and lines. Leave files unchanged.")
    marker = "<!-- compound-skills:global-setup:start -->"
    installed_skills = str(cache / "skills")
    requests = []

    class LocalProvider(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            if self.path != "/v1/responses":
                self.send_error(404)
                return
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(request)
            item = {"id": "msg_offline", "type": "message", "role": "assistant",
                    "status": "completed", "content": [{"type": "output_text",
                    "text": "Offline fixture response.", "annotations": []}]}
            response = {"id": "resp_offline", "object": "response", "status": "completed",
                        "model": request["model"], "output": [item],
                        "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2}}
            events = [
                {"type": "response.created",
                 "response": {**response, "status": "in_progress", "output": []}},
                {"type": "response.output_item.added", "output_index": 0,
                 "item": {**item, "status": "in_progress", "content": []}},
                {"type": "response.output_item.done", "output_index": 0, "item": item},
                {"type": "response.completed", "response": response},
            ]
            data = "".join(f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"
                           for event in events).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    with ThreadingHTTPServer(("127.0.0.1", 0), LocalProvider) as server:
        port = server.server_port
        policy = (
            "(version 1) (allow default) (deny network*) "
            f'(allow network-outbound (remote ip "localhost:{port}"))'
        )
        provider = "model_providers.compound_offline"
        command = [
            sandbox, "-p", policy, executable, "exec", "--json", "--ephemeral",
            "--sandbox", "read-only", "--model", "gpt-5.4",
            "-c", 'model_provider="compound_offline"',
            "-c", f'{provider}.name="Compound offline smoke"',
            "-c", f'{provider}.base_url="http://127.0.0.1:{port}/v1"',
            "-c", f'{provider}.env_key="COMPOUND_SMOKE_KEY"',
            "-c", f'{provider}.wire_api="responses"',
            "-c", f"{provider}.request_max_retries=0",
            "-c", f"{provider}.stream_max_retries=0",
            prompt,
        ]

        def fresh_request():
            start = len(requests)
            subprocess.run(command, cwd=project, env={**env, "COMPOUND_SMOKE_KEY": "offline-placeholder"},
                           input="", text=True, capture_output=True, timeout=40, check=True)
            assert len(requests) == start + 1
            messages = "\n".join(part.get("text", "") for item in requests[-1]["input"]
                                 for part in item.get("content", []))
            assert messages.count(prompt) == 1
            assert installed_skills in messages
            assert all(f"compound-skills:{name}:" in messages for name in ENTRYPOINTS)
            return messages

        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            assert marker not in fresh_request()
            assert routing("enable")["hosts"]["codex"]["configured"]
            saved = (Path(env["CODEX_HOME"]) / "AGENTS.md").read_text()
            _, managed = saved.split(marker)
            rule = next(line for line in managed.splitlines() if line.startswith("Review diff first."))
            enabled = fresh_request()
            assert enabled.count(marker) == 1 and enabled.count(rule) == 1
            core = (cache / "skills/compound/SKILL.md").read_text().split("---", 2)[-1].strip()
            assert core not in enabled
        finally:
            routing("disable")
            server.shutdown()
            thread.join()

    return {"saved_rule_delivery": "pass", "installed_skill_discovery": "pass",
            "disabled_rule_control": "pass", "scripted_provider_requests": len(requests)}


def check_host(host, executable, package, scratch, *, fresh_chat=False):
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
    chat = check_codex_fresh_chat(executable, project, env, cache, routing) if fresh_chat else "not exercised"
    assert retained.read_text() == "Keep this existing instruction.\n"
    return {"host": host, "host_version": version, "installed_version": installed["version"],
            "fresh_chat_activation": chat,
            "skills": sorted(ENTRYPOINTS), "global_enable_status_disable": "pass",
            "read_only_map": "pass", "invalid_state_recovery": "pass", "local_viewer_html_and_css": "pass"}


def smoke(ref, hosts, *, fresh_chat=False):
    if fresh_chat and tuple(hosts) != ("codex",):
        raise ValueError("The fresh chat check supports only Codex")
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
            results.append(check_host(host, executable, package, root / host, fresh_chat=fresh_chat))
    scope = "Local archive, isolated host homes and direct helper calls."
    if fresh_chat:
        scope += " Fresh native Codex chats use a scripted loopback provider."
    return {"scope": scope + " No model calls.", "source_tree": revision,
            "python": platform.python_version(), "results": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--host", choices=("claude", "codex"), action="append")
    parser.add_argument("--fresh-chat", action="store_true", help="Probe native Codex rule delivery offline on macOS")
    args = parser.parse_args()
    if args.fresh_chat and args.host not in (None, ["codex"]):
        parser.error("--fresh-chat supports only Codex")
    print(json.dumps(smoke(args.ref, args.host or (("codex",) if args.fresh_chat else ("codex", "claude")),
                           fresh_chat=args.fresh_chat), indent=2))
