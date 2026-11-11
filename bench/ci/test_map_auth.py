"""Exercise the map launch link and its read-only grant against a local fixture."""

from html import unescape
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import monotonic, sleep
import unittest
from urllib.parse import parse_qs, urlsplit
from urllib.request import url2pathname

MAP = Path(__file__).resolve().parents[2] / "skills/map/scripts/map.py"


def request(port, method, route, token=None, body=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if body is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(body)
    connection = HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request(method, route, body, headers)
        response = connection.getresponse()
        return response.status, response.read()
    finally:
        connection.close()


class MapAuthTests(unittest.TestCase):
    def test_private_link_grants_reads_only(self):
        with TemporaryDirectory() as scratch:
            base = Path(scratch).resolve()
            repo = base / "repo"
            repo.mkdir()
            (repo / "demo.py").write_text("def fixture_only():\n    return 42\n", encoding="utf-8")
            env = {
                **os.environ, "COMPOUND_SKILLS_STATE_DIR": str(base / "state"),
                "COMPOUND_MAP_PORT": "0", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
            }

            def run(*args):
                return subprocess.run(args, cwd=repo, env=env, check=True, text=True, capture_output=True, timeout=30).stdout

            run("git", "init", "-q")
            run("git", "add", "demo.py")
            run("git", "-c", "user.name=Compound Fixture", "-c", "user.email=fixture@example.com", "commit", "-qm", "fixture")
            cli = (sys.executable, "-B", str(MAP))
            try:
                link = urlsplit(run(*cli, "open", "--repo", str(repo), "--link").strip())
                self.assertEqual(link.scheme, "file")
                self.assertFalse(link.fragment)
                grant_file = Path(url2pathname(link.path))
                self.assertTrue(grant_file.is_relative_to(base / "state"))
                if os.name == "posix":
                    self.assertEqual(grant_file.stat().st_mode & 0o077, 0)
                html = grant_file.read_text(encoding="utf-8")
                anchor = re.search(r'<a href="([^"]+)"', html)
                self.assertTrue(anchor is not None, "The private launch file has no browser link")
                viewer = urlsplit(unescape(anchor[1]))
                self.assertEqual(viewer.hostname, "127.0.0.1")
                self.assertIsNotNone(viewer.port)
                token, = parse_qs(viewer.fragment)["access"]
                self.check_viewer(viewer.port, viewer.query, token, repo)
            finally:
                run(*cli, "stop")

    def check_viewer(self, port, query, token, repo):
        status, health = request(port, "GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(health)["protocol"], 2)
        status_path = f"/api/status?{query}"
        deadline = monotonic() + 8
        while monotonic() < deadline:
            status, state = request(port, "GET", status_path, token)
            self.assertEqual(status, 200)
            if not json.loads(state)["indexing"]:
                break
            sleep(0.05)
        else:
            self.fail("fixture map did not finish indexing")

        source_path = f"/api/file?{query}&path=demo.py"
        for path in ("/api/projects", status_path, f"/api/map?{query}", f"/api/summary?{query}", source_path):
            with self.subTest(path=path):
                for credential in (None, "invalid"):
                    status, response = request(port, "GET", path, credential)
                    self.assertEqual(status, 401)
                    self.assertNotIn(b"fixture_only", response)
                self.assertEqual(request(port, "GET", path, token)[0], 200)
        self.assertIn(b"fixture_only", request(port, "GET", source_path, token)[1])
        self.assertEqual(request(port, "GET", f"{status_path}&wait=1", token)[0], 401)
        project, = parse_qs(query)["project"]
        for path, body in (("/api/register", {"root": str(repo)}), ("/api/lookup", {"project": project}), ("/api/shutdown", {})):
            with self.subTest(path=path):
                self.assertEqual(request(port, "POST", path, token, body)[0], 401)
