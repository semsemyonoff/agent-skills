"""Actual local process cancellation and single-attempt claims; no model requests."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock

RUNNER = Path(__file__).with_name("run_evals.py")
FAKE_CLI = r'''
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
root = Path(os.environ["FIXTURE_ROOT"])
with (root / "calls").open("a") as calls:
    calls.write(str(os.getpid()) + "\n")
child_code = """
from pathlib import Path
import signal
import time
import sys
root = Path(sys.argv[1])
signal.signal(signal.SIGTERM, signal.SIG_IGN)
(root / 'child-ready').write_text('ready')
while not (root / 'release').exists():
    time.sleep(0.01)
(root / 'unwanted-effect').write_text('continued after cancellation')
"""
subprocess.Popen([sys.executable, "-c", child_code, str(root)])
signal.signal(signal.SIGTERM, signal.SIG_IGN)
while True:
    time.sleep(0.05)
'''


class EvaluationSupervisorTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        cli = self.bin / "omp"
        cli.write_text(f"#!{sys.executable}\n" + FAKE_CLI)
        cli.chmod(0o755)
        self.session = self.root / "session"
        self.session.mkdir()
        (self.session / "outputs").mkdir()
        (self.session / "session.json").write_text(json.dumps({"adapter": "omp", "plugin": str(self.root)}))
        (self.session / "prompt.txt").write_text("fixture prompt\n")
        initial = {}
        for name in ("plan.md", "evidence.md", "checkpoint.json"):
            data = (name + "\n").encode()
            (self.session / name).write_bytes(data)
            initial[name] = hashlib.sha256(data).hexdigest()
        (self.session / "initial-state.json").write_text(json.dumps({"sha256": initial}))
        self.env = {"PATH": str(self.bin), "HOME": str(self.root), "FIXTURE_ROOT": str(self.root)}
        self.processes = []

    def tearDown(self):
        for process in self.processes:
            if process.poll() is None:
                process.send_signal(signal.SIGTERM)
                try:
                    process.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            for stream in (process.stdout, process.stderr):
                stream.close()
        self.temp.cleanup()

    def start(self, timeout=20):
        process = subprocess.Popen(
            [sys.executable, str(RUNNER), "--run", str(self.session), "--tools", "read", "--timeout", str(timeout)],
            env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.processes.append(process)
        return process

    def ready(self):
        deadline = time.monotonic() + 5
        while not (self.root / "child-ready").exists():
            if time.monotonic() >= deadline:
                self.fail("Synthetic descendant did not reach its readiness boundary")
            time.sleep(0.01)

    def assert_stopped(self, process, status):
        process.wait(timeout=4)
        self.assertNotEqual(process.returncode, 0)
        session = json.loads((self.session / "session.json").read_text())
        self.assertEqual(session["runtime_status"], status)
        self.assertIsNone(session["cleanup_error"])
        (self.root / "release").write_text("release descendant after supervisor completion")
        time.sleep(0.2)
        self.assertFalse((self.root / "unwanted-effect").exists(), "CLI descendant continued after supervisor stop")

    def test_sigterm_and_sigint_cancel_term_ignoring_cli_descendants(self):
        for cancellation in (signal.SIGTERM, signal.SIGINT):
            with self.subTest(cancellation=cancellation):
                if cancellation == signal.SIGINT:
                    # A distinct session is required; the first attempt stays permanently claimed.
                    for name in ("child-ready", "release"):
                        (self.root / name).unlink()
                    self.session = self.root / "second-session"
                    self.session.mkdir()
                    (self.session / "outputs").mkdir()
                    (self.session / "session.json").write_text(json.dumps({"adapter": "omp", "plugin": str(self.root)}))
                    (self.session / "prompt.txt").write_text("fixture prompt\n")
                    initial = {}
                    for name in ("plan.md", "evidence.md", "checkpoint.json"):
                        data = (name + "\n").encode()
                        (self.session / name).write_bytes(data)
                        initial[name] = hashlib.sha256(data).hexdigest()
                    (self.session / "initial-state.json").write_text(json.dumps({"sha256": initial}))
                process = self.start()
                self.ready()
                process.send_signal(cancellation)
                self.assert_stopped(process, "interrupted")

    def test_concurrent_attempt_and_restart_cannot_launch_another_cli_or_overwrite_trace(self):
        first = self.start()
        self.ready()
        original_command = (self.session / "command.json").read_bytes()
        second = self.start()
        second.wait(timeout=4)
        self.assertNotEqual(second.returncode, 0)
        self.assertIn(b"Already attempted", second.stderr.read())
        self.assertEqual((self.session / "command.json").read_bytes(), original_command, "Rejected duplicate overwrote provenance")
        self.assertEqual(len((self.root / "calls").read_text().splitlines()), 1, "Concurrent supervisor launched a duplicate CLI")
        first.send_signal(signal.SIGTERM)
        self.assert_stopped(first, "interrupted")
        # Simulate lost completion artifacts after a crash: the atomic claim still forbids a repeat.
        (self.session / "timing.json").unlink()
        (self.session / "command.json").unlink()
        third = self.start()
        third.wait(timeout=4)
        self.assertNotEqual(third.returncode, 0)
        self.assertIn(b"Already attempted", third.stderr.read())
        self.assertEqual(len((self.root / "calls").read_text().splitlines()), 1, "Restart repeated a consumed attempt")
        self.assertFalse((self.session / "command.json").exists())

    def test_deadline_stops_descendants_and_remains_consumed(self):
        process = self.start(timeout=1)
        self.ready()
        self.assert_stopped(process, "timeout")
        again = self.start()
        again.wait(timeout=4)
        self.assertNotEqual(again.returncode, 0)
        self.assertEqual(len((self.root / "calls").read_text().splitlines()), 1)

    def test_cancellation_during_launch_does_not_lose_child_ownership(self):
        spec = importlib.util.spec_from_file_location("evaluation_launch_boundary", RUNNER)
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        real_popen = subprocess.Popen
        launched = []

        def cancel_before_constructor_returns(*args, **kwargs):
            process = real_popen(*args, **kwargs)
            launched.append(process)
            self.ready()
            os.kill(os.getpid(), signal.SIGTERM)
            return process

        try:
            with mock.patch.dict(os.environ, self.env, clear=True), \
                    mock.patch.object(runner.subprocess, "Popen", cancel_before_constructor_returns):
                with self.assertRaises(SystemExit) as outcome:
                    runner.execute(SimpleNamespace(run=self.session, tools="read", allowed_tools=None, timeout=20))
                self.assertEqual(outcome.exception.code, 1)
            session = json.loads((self.session / "session.json").read_text())
            self.assertEqual(session["runtime_status"], "interrupted")
            (self.root / "release").write_text("release only after supervisor reports cancellation")
            time.sleep(0.2)
            self.assertFalse((self.root / "unwanted-effect").exists(), "Launch cancellation leaked the native child group")
        finally:
            for process in launched:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=4)


if __name__ == "__main__":
    unittest.main()
