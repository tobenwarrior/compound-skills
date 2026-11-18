"""Exercise bounded Git output on platforms with and without selectable pipes."""

import asyncio
import os
from pathlib import Path
import signal
import subprocess
import sys
import textwrap
import time
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[2] / "skills/compound/scripts"
sys.path.insert(0, str(SCRIPTS))
import map_inventory

FIXTURE_SOURCE = """
import os
import subprocess
import sys
import time

mode = os.environ["COMPOUND_TEST_GIT_MODE"]
if mode == "output":
    sys.stdout.buffer.write(bytes.fromhex(os.environ["COMPOUND_TEST_GIT_OUTPUT"]))
    sys.stdout.flush()
elif mode == "sleep":
    time.sleep(30)
elif mode == "closed":
    sys.stdout.close()
    time.sleep(30)
elif mode == "inherit":
    subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
elif mode == "status":
    raise SystemExit(int(os.environ["COMPOUND_TEST_GIT_STATUS"]))
else:
    raise SystemExit(f"unknown fixture mode: {mode}")
"""


class BoundedGitOutputTests(unittest.TestCase):
    @staticmethod
    def spawn_reader(source, *arguments):
        options = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.DEVNULL,
        }
        if os.name == "nt":
            options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            options["start_new_session"] = True
        return subprocess.Popen([sys.executable, "-c", source, *arguments], **options)

    @staticmethod
    def cleanup_process_group(process):
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait()

    def run_reader(
        self, mode, max_bytes, *, output=b"", status=0, keep_prefix=False, timeout=5, ok_statuses=(0,)
    ):
        env = os.environ.copy()
        env.update({
            "COMPOUND_TEST_GIT_MODE": mode,
            "COMPOUND_TEST_GIT_OUTPUT": output.hex(),
            "COMPOUND_TEST_GIT_STATUS": str(status),
        })
        with TemporaryDirectory() as scratch, patch.object(
            map_inventory, "GIT_READ", (sys.executable, "-c", FIXTURE_SOURCE)
        ):
            return map_inventory._bounded_git_output(
                Path(scratch), ["fixture"], max_bytes, keep_prefix=keep_prefix,
                env=env, ok_statuses=ok_statuses, timeout=timeout,
            )

    @staticmethod
    def run_protocol_reader(source, max_bytes, *, keep_prefix=False, timeout=5, ok_statuses=(0,)):
        loop = asyncio.ProactorEventLoop() if os.name == "nt" else asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                map_inventory._read_windows_command_output(
                    [sys.executable, "-c", source], max_bytes, keep_prefix,
                    env=None, ok_statuses=ok_statuses, deadline=time.monotonic() + timeout,
                )
            )
        finally:
            loop.close()

    def test_portable_reader_preserves_success_and_prefix_cap(self):
        self.assertEqual(self.run_reader("output", 32, output=b"0123456789"), b"0123456789")
        self.assertEqual(
            self.run_reader("output", 3, output=b"0123456789", keep_prefix=True), b"0123"
        )

    def test_portable_reader_reaps_overflowing_child(self):
        self.assertIsNone(self.run_reader("output", 3, output=b"0123456789"))

    def test_portable_reader_reaps_timed_out_child(self):
        self.assertIsNone(self.run_reader("sleep", 32, timeout=0.05))

    def test_git_reader_handles_closed_pipe(self):
        self.assertIsNone(self.run_reader("closed", 32, timeout=0.05))

    def test_portable_reader_deadline_with_inherited_stdout(self):
        source = textwrap.dedent(
            """
            import os
            from pathlib import Path
            import sys
            from tempfile import TemporaryDirectory
            import time

            sys.path.insert(0, sys.argv[1])
            import map_inventory

            fixture_source = sys.argv[2]
            map_inventory.GIT_READ = (sys.executable, "-c", fixture_source)
            env = os.environ.copy()
            env["COMPOUND_TEST_GIT_MODE"] = "inherit"
            env["COMPOUND_TEST_GIT_OUTPUT"] = ""
            env["COMPOUND_TEST_GIT_STATUS"] = "0"
            started = time.monotonic()
            with TemporaryDirectory() as scratch:
                result = map_inventory._bounded_git_output(
                    Path(scratch), ["fixture"], 32, env=env, timeout=0.2,
                )
            print(f"result={result!r} elapsed={time.monotonic() - started:.3f}", flush=True)
            """
        )
        process = self.spawn_reader(source, str(SCRIPTS), FIXTURE_SOURCE)
        try:
            try:
                output, _ = process.communicate(timeout=1)
            except subprocess.TimeoutExpired as error:
                self.cleanup_process_group(process)
                self.fail(f"bounded reader exceeded its supplied deadline: {error}")
            self.assertIn(b"result=None", output)
            elapsed = float(output.decode("utf-8").split("elapsed=", 1)[1].strip())
            self.assertLess(elapsed, 0.8)
        finally:
            self.cleanup_process_group(process)

    def test_portable_reader_rejects_unexpected_status(self):
        self.assertIsNone(self.run_reader("status", 32, status=7))
        self.assertEqual(self.run_reader("status", 32, status=1, ok_statuses=(0, 1)), b"")

    def test_asyncio_protocol_preserves_prefix_and_deadline(self):
        source = "import sys; sys.stdout.buffer.write(b'0123456789'); sys.stdout.flush()"
        self.assertEqual(self.run_protocol_reader(source, 3, keep_prefix=True), b"0123")
        self.assertIsNone(self.run_protocol_reader("import time; time.sleep(30)", 32, timeout=0.05))

    def test_git_reader_returns_real_status_bytes(self):
        with TemporaryDirectory() as scratch:
            root = Path(scratch)
            subprocess.run(["git", "-C", str(root), "init", "-q"], check=True, stdout=subprocess.PIPE)
            (root / "untracked.py").write_text("fixture\n", encoding="utf-8")
            result = map_inventory._bounded_git_output(
                root, ["status", "--porcelain=v1", "-z", "--untracked-files=all"], 1024,
            )
            self.assertIsNotNone(result)
            self.assertIn(b"untracked.py", result or b"")


if __name__ == "__main__":
    unittest.main()
