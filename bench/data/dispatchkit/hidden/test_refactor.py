import ast
from pathlib import Path
import unittest

from dispatchkit.publish import publish
from dispatchkit.replay import replay


PACKAGE = Path("src/dispatchkit")


class CallerPolicyTests(unittest.TestCase):
    def test_live_and_replay_keep_their_policies(self) -> None:
        class Capture:
            def __init__(self) -> None:
                self.items = []

            def send(self, envelope):
                self.items.append(envelope)
                return envelope

        transport = Capture()
        publish({"topic": "orders", "payload": {"id": "1"}, "attempt": 9}, transport)
        replay({"topic": "orders", "payload": {"id": "1"}, "attempt": 4}, transport)
        replay({"topic": "orders", "payload": {"id": "2"}}, transport)

        self.assertEqual(transport.items[0], {
            "topic": "orders", "payload": {"id": "1"}, "attempt": 1, "mode": "live"
        })
        self.assertEqual(transport.items[1], {
            "topic": "orders", "payload": {"id": "1"}, "attempt": 4, "mode": "replay"
        })
        self.assertEqual(transport.items[2], {
            "topic": "orders", "payload": {"id": "2"}, "attempt": 0, "mode": "replay"
        })

    def test_callers_keep_their_error_ownership(self) -> None:
        with self.assertRaisesRegex(ValueError, "publish topic required"):
            publish({"payload": {}}, object())
        with self.assertRaisesRegex(ValueError, "replay topic required"):
            replay({"payload": {}}, object())

    def test_shared_operation_replaces_both_old_helpers(self) -> None:
        packaging = PACKAGE / "packaging.py"
        self.assertTrue(packaging.exists())
        module = ast.parse(packaging.read_text())
        functions = {node.name for node in module.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertIn("package_event", functions)
        self.assertNotIn("_make_envelope", functions)
        self.assertNotIn("_replay_envelope", functions)

        for name in ("publish.py", "replay.py"):
            source = (PACKAGE / name).read_text()
            tree = ast.parse(source)
            self.assertNotIn("_make_envelope", {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)})
            self.assertNotIn("_replay_envelope", {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)})
            call_names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module in {"packaging", "dispatchkit.packaging"}:
                        call_names.update(alias.asname or alias.name for alias in node.names if alias.name == "package_event")
                    elif node.module in {None, "dispatchkit"}:
                        call_names.update(f"{alias.asname or alias.name}.package_event" for alias in node.names
                                          if alias.name == "packaging")
                elif isinstance(node, ast.Import):
                    call_names.update(f"{alias.asname or alias.name}.package_event" for alias in node.names
                                      if alias.name == "dispatchkit.packaging")
            self.assertTrue(any(isinstance(node, ast.Call) and ast.unparse(node.func) in call_names
                                for node in ast.walk(tree)))
