#!/usr/bin/env python3
"""Optional Codex review for the orchestrate skill.

  codex_review.py check
      Exit 0 and print "available", or exit 1 and print "unavailable: <reason>".
      Silent-skip reasons (no codex, CODEX_REVIEW=off) start with "skip:"; a failing
      CODEX_REVIEW_GUARD starts with "guard:" and should be shown to the user.

  codex_review.py run --repo DIR --start SHA --intent-file FILE [--xhigh] [--timeout MIN]
      Re-check availability, then run `codex exec` read-only on everything that changed since
      SHA (commits, staged, unstaged, untracked). Artifacts go to a temp dir printed on stdout:
      review.md (final message), stdout.log, stderr.log, exit-code. Exit code is Codex's, 124 on
      timeout. Nonzero or an empty review.md means the review failed, not "no findings".

Environment: CODEX_REVIEW=off disables; CODEX_REVIEW_GUARD is a shell command that must exit 0;
CODEX_MODEL / CODEX_REASONING_EFFORT override the model / reasoning effort, otherwise Codex's own
config decides.
"""

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

GUARD_TIMEOUT = 10

PROMPT = """You are reviewing changes made by an automated multi-agent run. Do not modify anything.

Intent of the change (from the confirmed plan):
{intent}

Scope — everything that changed since commit {start} in this repository:
- committed: git diff {start} HEAD
- staged and unstaged: git diff HEAD
- untracked files: git ls-files --others --exclude-standard
{dirty}
Review for correctness, regressions and missed edge cases against the intent. Return prioritized
findings (P1 highest), each with path:line, what triggers it, the impact and a suggested fix.
If you could not inspect part of the scope, say so explicitly.
"""


def stop_group(proc: subprocess.Popen, grace: float = 10) -> None:
    """Terminate the whole process group: SIGTERM, grace period, then SIGKILL regardless of
    whether the leader already exited (descendants may ignore SIGTERM)."""
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(proc.pid, sig)
        except ProcessLookupError:
            break
        if sig == signal.SIGTERM:
            try:
                proc.wait(timeout=grace)
            except subprocess.TimeoutExpired:
                pass
    proc.wait()


def availability() -> tuple[bool, str]:
    if shutil.which("codex") is None:
        return False, "skip: codex CLI not installed"
    if os.environ.get("CODEX_REVIEW", "") == "off":
        return False, "skip: CODEX_REVIEW=off"
    guard = os.environ.get("CODEX_REVIEW_GUARD", "")
    if guard:
        proc = subprocess.Popen(["sh", "-c", guard], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, start_new_session=True)
        try:
            stdout, stderr = proc.communicate(timeout=GUARD_TIMEOUT)
        except subprocess.TimeoutExpired:
            stop_group(proc, grace=1)
            return False, f"guard: CODEX_REVIEW_GUARD timed out after {GUARD_TIMEOUT}s"
        if proc.returncode != 0:
            out = (stderr or stdout).strip().splitlines()
            return False, f"guard: {out[-1] if out else f'exit {proc.returncode}'}"
    return True, "available"


def git(repo: str, *args: str) -> str:
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True,
                          check=True).stdout


def run(args: argparse.Namespace) -> int:
    ok, reason = availability()
    if not ok:
        print(f"unavailable: {reason}")
        return 1
    try:
        repo = git(args.repo, "rev-parse", "--show-toplevel").strip()
        start = git(repo, "rev-parse", "--verify", f"{args.start}^{{commit}}").strip()
    except subprocess.CalledProcessError as e:
        print(f"error: {' '.join(e.cmd[3:])}: {e.stderr.strip()}", file=sys.stderr)
        return 2
    intent = Path(args.intent_file).read_text(encoding="utf-8").strip()

    out = Path(tempfile.mkdtemp(prefix="flow-codex-review."))
    cmd = ["codex", "exec", "--cd", repo, "--sandbox", "read-only", "--skip-git-repo-check",
           "--ephemeral", "--color", "never",
           "-c", 'approval_policy="never"', "--output-last-message", str(out / "review.md")]
    if model := os.environ.get("CODEX_MODEL"):
        cmd += ["-c", f'model="{model}"']
    effort = "xhigh" if args.xhigh else os.environ.get("CODEX_REASONING_EFFORT", "")
    if effort:
        cmd += ["-c", f'model_reasoning_effort="{effort}"']
    dirty = ""
    if args.dirty_at_start:
        dirty = f"Note: the working tree already had uncommitted changes before the run:\n{args.dirty_at_start}\n"
    cmd.append(PROMPT.format(intent=intent, start=start, dirty=dirty))

    print(out)
    with open(out / "stdout.log", "w") as so, open(out / "stderr.log", "w") as se:
        proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=so, stderr=se,
                                start_new_session=True)
        try:
            rc = proc.wait(timeout=args.timeout * 60)
            reason = "" if rc == 0 else f"codex exited with {rc}, see stderr.log"
        except subprocess.TimeoutExpired:
            stop_group(proc)
            rc, reason = 124, f"timed out after {args.timeout} min"
    review = out / "review.md"
    if rc == 0 and (not review.exists() or not review.read_text().strip()):
        rc, reason = 1, "codex exited 0 but the final message is empty"
    (out / "exit-code").write_text(f"{rc}\n")
    if reason:
        (out / "error.txt").write_text(reason + "\n")
        print(f"review failed: {reason}", file=sys.stderr)
    return rc


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    r = sub.add_parser("run")
    r.add_argument("--repo", required=True)
    r.add_argument("--start", required=True, help="commit recorded at plan confirmation")
    r.add_argument("--intent-file", required=True, help="file with a one-paragraph summary of the plan")
    r.add_argument("--dirty-at-start", default="", help="`git status --short` at confirmation, if non-empty")
    r.add_argument("--xhigh", action="store_true")
    r.add_argument("--timeout", type=float, default=15, help="minutes")
    args = p.parse_args()
    if args.cmd == "check":
        ok, reason = availability()
        print(reason if ok else f"unavailable: {reason}")
        return 0 if ok else 1
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
