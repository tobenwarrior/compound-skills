"""Exercise bounded Git output on platforms with and without selectable pipes."""

import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import textwrap
import time
from tempfile import TemporaryDirectory
import unittest

SCRIPTS = Path(__file__).resolve().parents[2] / "skills/compound/scripts"
sys.path.insert(0, str(SCRIPTS))
import map_inventory


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

    def run_reader(self, source, max_bytes, *, keep_prefix=False, timeout=5):
        process = self.spawn_reader(source)
        try:
            result = map_inventory._bounded_process_output(
                process, max_bytes, time.monotonic() + timeout, keep_prefix, (0,),
            )
            self.assertIsNotNone(process.returncode)
            return result
        finally:
            self.cleanup_process_group(process)
            self.assertFalse(any(thread.name == "compound-code-map-git-reader" for thread in threading.enumerate()))

    def test_portable_reader_preserves_success_and_prefix_cap(self):
        source = "import sys; sys.stdout.buffer.write(b'0123456789'); sys.stdout.flush()"
        self.assertEqual(self.run_reader(source, 32), b"0123456789")
        self.assertEqual(self.run_reader(source, 3, keep_prefix=True), b"0123")

    def test_portable_reader_reaps_overflowing_child(self):
        source = "import sys; sys.stdout.buffer.write(b'0123456789'); sys.stdout.flush()"
        self.assertIsNone(self.run_reader(source, 3))

    def test_portable_reader_reaps_timed_out_child(self):
        self.assertIsNone(self.run_reader("import time; time.sleep(30)", 32, timeout=0.05))

    def test_portable_reader_handles_a_closed_pipe(self):
        process = self.spawn_reader("import time; time.sleep(30)")
        assert process.stdout is not None
        process.stdout.close()
        try:
            self.assertIsNone(
                map_inventory._bounded_process_output(
                    process, 32, time.monotonic() + 1, False, (0,),
                )
            )
            self.assertIsNotNone(process.returncode)
        finally:
            self.cleanup_process_group(process)
            self.assertFalse(any(thread.name == "compound-code-map-git-reader" for thread in threading.enumerate()))

    def test_portable_reader_deadline_with_inherited_stdout(self):
        source = textwrap.dedent(
            """
            import subprocess
            import sys
            import time

            sys.path.insert(0, sys.argv[1])
            import map_inventory

            owner_source = "import subprocess, sys; subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])"
            owner = subprocess.Popen(
                [sys.executable, "-c", owner_source], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            )
            started = time.monotonic()
            result = map_inventory._bounded_process_output(
                owner, 32, started + 0.2, False, (0,),
            )
            print(f"result={result!r} elapsed={time.monotonic() - started:.3f}", flush=True)
            """
        )
        process = self.spawn_reader(source, str(SCRIPTS))
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
