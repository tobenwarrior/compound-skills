"""Verify the rule delivered by the public setup command in isolated profiles."""

import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from scripts.check import check_package

ROOT = Path(__file__).resolve().parents[2]
RULE = Path("skills/compound/references/default-routing.md")
CURSOR = Path(".cursor-plugin/rules/compound-default.mdc")
SETUP = ROOT / "skills/compound/scripts/project_setup.py"
START = "<!-- compound-skills:global-setup:start -->"
END = "<!-- compound-skills:global-setup:end -->"


class RoutingTests(unittest.TestCase):
    def test_global_refresh_delivers_the_canonical_rule_to_both_hosts(self):
        canonical = (ROOT / RULE).read_text(encoding="utf-8").strip()
        cursor = (ROOT / CURSOR).read_text(encoding="utf-8").split("---", 2)[2].strip()
        self.assertEqual(cursor, canonical)
        self.assertLessEqual(len(canonical.split()), 100)
        self.assertLessEqual(len(canonical.encode("utf-8")), 1024)

        with TemporaryDirectory() as scratch:
            base = Path(scratch).resolve()
            codex, claude = base / "codex", base / "claude"
            (claude / "rules").mkdir(parents=True)
            codex.mkdir()
            env = {**os.environ, "CODEX_HOME": str(codex), "CLAUDE_CONFIG_DIR": str(claude)}
            previous = f"Keep this user guidance.\n{START}\nOld rule.\n{END}\nKeep this too.\n"
            for host, path in (("codex", codex / "AGENTS.md"), ("claude", claude / "rules/compound-skills.md")):
                with self.subTest(host=host):
                    path.write_text(previous, encoding="utf-8")
                    command = [sys.executable, "-B", str(SETUP), "refresh", "--global", "--host", host]
                    first = subprocess.run(command, cwd=base, env=env, capture_output=True, text=True, check=True)
                    self.assertTrue(json.loads(first.stdout)["changed"])
                    installed = path.read_text(encoding="utf-8")
                    before, managed = installed.split(START)
                    body, after = managed.split(END)
                    self.assertEqual(body.strip().split("\n\n", 1)[1], canonical)
                    self.assertEqual(before + after, previous.split(START)[0] + previous.split(END)[1])
                    second = subprocess.run(command, cwd=base, env=env, capture_output=True, text=True, check=True)
                    self.assertFalse(json.loads(second.stdout)["changed"])
                    self.assertEqual(path.read_text(encoding="utf-8"), installed)

    def test_package_check_rejects_rule_drift_and_both_size_limits(self):
        with TemporaryDirectory() as scratch:
            root = Path(scratch)
            (root / RULE).parent.mkdir(parents=True)
            (root / CURSOR).parent.mkdir(parents=True)
            header = "---\ndescription: Default routing\nalwaysApply: true\n---\n\n"
            for label, rule, cursor, expected in (
                ("drift", "Canonical rule.", "Edited copy.", "routing_rule_drift"),
                ("word budget", "word " * 101, "word " * 101, "routing_rule_budget"),
                ("byte budget", "é" * 513, "é" * 513, "routing_rule_budget"),
            ):
                with self.subTest(label=label):
                    (root / RULE).write_text(rule.strip() + "\n", encoding="utf-8")
                    (root / CURSOR).write_text(header + cursor.strip() + "\n", encoding="utf-8")
                    report = check_package(root)
                    self.assertIn(expected, {item["code"] for item in report["errors"]})
