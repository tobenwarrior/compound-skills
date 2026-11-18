"""Exercise bounded Git output on platforms with and without selectable pipes."""

from pathlib import Path
import subprocess
import sys
import threading
import time
from tempfile import TemporaryDirectory
import unittest

SCRIPTS = Path(__file__).resolve().parents[2] / "skills/compound/scripts"
sys.path.insert(0, str(SCRIPTS))
import map_inventory


class BoundedGitOutputTests(unittest.TestCase):
    def run_reader(self, source, max_bytes, *, keep_prefix=False, timeout=5):
        process = subprocess.Popen(
            [sys.executable, "-c", source], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        try:
            result = map_inventory._bounded_process_output(
                process, max_bytes, time.monotonic() + timeout, keep_prefix, (0,),
            )
            self.assertIsNotNone(process.returncode)
            return result
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()
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
        process = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
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
            if process.poll() is None:
                process.kill()
            process.wait()
            self.assertFalse(any(thread.name == "compound-code-map-git-reader" for thread in threading.enumerate()))

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
