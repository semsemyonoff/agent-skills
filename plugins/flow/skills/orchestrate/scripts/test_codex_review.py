import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("codex_review.py")


class CheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        fake = Path(self.tmp.name) / "codex"
        fake.write_text("#!/bin/sh\nexit 0\n")
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        self.path_with_codex = f"{self.tmp.name}:/usr/bin:/bin"

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, path, **env):
        e = {"PATH": path, **env}
        r = subprocess.run([sys.executable, str(SCRIPT), "check"], env=e, capture_output=True, text=True)
        return r.returncode, r.stdout.strip()

    def test_available(self):
        self.assertEqual(self.check(self.path_with_codex), (0, "available"))

    def test_no_codex(self):
        rc, out = self.check("/nonexistent")
        self.assertEqual(rc, 1)
        self.assertIn("skip: codex CLI not installed", out)

    def test_disabled(self):
        rc, out = self.check(self.path_with_codex, CODEX_REVIEW="off")
        self.assertEqual((rc, out), (1, "unavailable: skip: CODEX_REVIEW=off"))

    def test_guard_refuses_with_reason(self):
        rc, out = self.check(self.path_with_codex, CODEX_REVIEW_GUARD="echo work mode >&2; exit 1")
        self.assertEqual((rc, out), (1, "unavailable: guard: work mode"))

    def test_guard_passes(self):
        self.assertEqual(self.check(self.path_with_codex, CODEX_REVIEW_GUARD="true"), (0, "available"))

    def test_guard_not_run_when_disabled(self):
        marker = Path(self.tmp.name) / "ran"
        self.check(self.path_with_codex, CODEX_REVIEW="off", CODEX_REVIEW_GUARD=f"touch {marker}")
        self.assertFalse(marker.exists())


def alive(pid: int) -> bool:
    """A killed orphan stays a zombie where PID 1 does not reap (CI containers); count it as dead."""
    stat = Path(f"/proc/{pid}/stat")
    if Path("/proc/self/stat").exists():
        try:
            return stat.read_text().rsplit(")", 1)[1].split()[0] not in ("Z", "X")
        except FileNotFoundError:
            return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


class RunTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.bin, self.repo = t / "bin", t / "repo"
        self.bin.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "--allow-empty", "-m", "init"], check=True)
        self.intent = t / "intent.txt"
        self.intent.write_text("test intent")

    def tearDown(self):
        self.tmp.cleanup()

    def fake_codex(self, body: str):
        f = self.bin / "codex"
        f.write_text("#!/bin/sh\n" + body)
        f.chmod(f.stat().st_mode | stat.S_IXUSR)

    def run_review(self, *extra, **env):
        e = {"PATH": f"{self.bin}:/usr/bin:/bin", **env}
        return subprocess.run([sys.executable, str(SCRIPT), "run", "--repo", str(self.repo), "--start", "HEAD",
                               "--intent-file", str(self.intent), *extra], env=e, capture_output=True, text=True)

    def test_timeout_kills_term_ignoring_descendants(self):
        pidfile = Path(self.tmp.name) / "child.pid"
        self.fake_codex(f'sh -c \'trap "" TERM; echo $$ > {pidfile}; sleep 300\' &\nsleep 300\n')
        r = self.run_review("--timeout", "0.03")
        self.assertEqual(r.returncode, 124)
        out = Path(r.stdout.strip())
        self.assertEqual((out / "exit-code").read_text().strip(), "124")
        self.assertFalse(alive(int(pidfile.read_text())))

    def test_empty_final_message_is_failure(self):
        self.fake_codex("exit 0\n")
        r = self.run_review()
        self.assertEqual(r.returncode, 1)
        out = Path(r.stdout.strip())
        self.assertEqual((out / "exit-code").read_text().strip(), "1")
        self.assertIn("final message is empty", (out / "error.txt").read_text())

    def test_bad_start_ref(self):
        self.fake_codex("exit 0\n")
        r = subprocess.run([sys.executable, str(SCRIPT), "run", "--repo", str(self.repo), "--start", "nope",
                            "--intent-file", str(self.intent)], env={"PATH": f"{self.bin}:/usr/bin:/bin"},
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)

    def test_rejected_native_route_is_failure_without_retry(self):
        attempts = Path(self.tmp.name) / "attempts"
        self.fake_codex(f'''
if [ -e "{attempts}" ]; then
  while [ "$#" -gt 0 ]; do
    if [ "$1" = "--output-last-message" ]; then
      shift
      printf 'unexpected fallback succeeded\\n' > "$1"
      exit 0
    fi
    shift
  done
fi
printf 'attempt\\n' >> "{attempts}"
printf 'configured model or effort rejected\\n' >&2
exit 42
''')
        for overrides in ({"CODEX_MODEL": "unsupported-model"},
                          {"CODEX_REASONING_EFFORT": "unsupported-effort"}):
            with self.subTest(overrides=overrides):
                attempts.unlink(missing_ok=True)
                r = self.run_review(**overrides)
                self.assertEqual(r.returncode, 42)
                out = Path(r.stdout.strip())
                self.assertEqual((out / "exit-code").read_text().strip(), "42")
                self.assertIn("rejected", (out / "stderr.log").read_text())
                self.assertIn("codex exited with 42", (out / "error.txt").read_text())
                self.assertFalse((out / "review.md").exists())
                self.assertEqual(attempts.read_text().splitlines(), ["attempt"])

    def test_guard_timeout_kills_its_children(self):
        pidfile = Path(self.tmp.name) / "guard.pid"
        self.fake_codex("exit 0\n")
        e = {"PATH": f"{self.bin}:/usr/bin:/bin", "CODEX_REVIEW_GUARD": f"sh -c 'echo $$ > {pidfile}; sleep 300'"}
        r = subprocess.run([sys.executable, str(SCRIPT), "check"], env=e, capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("timed out", r.stdout)
        self.assertFalse(alive(int(pidfile.read_text())))


if __name__ == "__main__":
    unittest.main()
