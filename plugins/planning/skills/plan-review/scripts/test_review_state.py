"""Consumer-visible snapshot/validation boundaries; no provider calls."""

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).with_name("review_state.py")
SPEC = importlib.util.spec_from_file_location("bundled_review_state", SCRIPT)
review_state = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review_state)


class ReviewStateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.plan = self.root / "план.md"
        self.plan.write_bytes("# План\r\n\r\nKeep original bytes.\r\n".encode("utf-8"))
        self.env = {"PATH": os.defpath, "HOME": str(self.root)}

    def tearDown(self):
        self.tmp.cleanup()

    def command(self, *args, script=SCRIPT):
        return [sys.executable, str(script), *map(str, args)]

    def run_state(self, *args, data="", script=SCRIPT):
        return subprocess.run(self.command(*args, script=script), input=data, text=True,
                              capture_output=True, cwd=self.root, env=self.env, timeout=5)

    def collect(self):
        process = self.run_state("snapshot", self.plan)
        self.assertEqual(process.returncode, 0, process.stderr)
        return json.loads(process.stdout)

    def report(self, **fields):
        result = self.collect()
        result.pop("plan_text")
        result.update(verdict="APPROVE", findings=[], unknowns=[])
        result.update(fields)
        return result

    def check(self, report, version=None):
        return self.run_state("validate", self.plan, "--version", version or report["plan_version"],
                              data=json.dumps(report, ensure_ascii=False))

    def assert_rejected(self, process):
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(process.stdout, "", "Failure must not emit an accepted review")
        self.assertTrue(process.stderr.strip())

    def test_snapshot_preserves_exact_unicode_crlf_bom_and_digest(self):
        for data in (self.plan.read_bytes(), b"\xef\xbb\xbf# BOM\n", b"", b"last line without newline"):
            with self.subTest(data=data):
                self.plan.write_bytes(data)
                result = self.collect()
                self.assertEqual(result["plan_text"].encode("utf-8"), data)
                self.assertEqual(result["plan_version"], hashlib.sha256(data).hexdigest())
                self.assertEqual(result["plan_path"], str(self.plan))
                self.assertEqual(self.plan.read_bytes(), data)

    def test_current_approval_and_nonblocking_notes_are_accepted_unchanged(self):
        report = self.report(findings=[{"severity": "nonblocking", "section": "Checks",
                                       "evidence": "Only existing unit checks are listed",
                                       "impact": "An extra integration check would be useful",
                                       "fix": "Optional integration scenario"}],
                             unknowns=[{"blocking": False, "detail": "Live CLI was not exercised"}])
        process = self.check(report)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout), report)

    def test_closed_regular_file_reaches_eof_and_validates_current_report(self):
        report = self.report()
        packet = self.root / "review.json"
        packet.write_text(json.dumps(report), encoding="utf-8")
        with packet.open("rb") as source:
            process = subprocess.run(
                self.command("validate", self.plan, "--version", report["plan_version"]),
                stdin=source, capture_output=True, cwd=self.root, env=self.env, timeout=5,
            )
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout), report)

    def test_revision_requires_real_blocker_or_blocking_unknown(self):
        finding = {"severity": "blocker", "section": "Rollback", "evidence": "No rollback step",
                   "impact": "Cannot restore after failed cutover", "fix": "Define restore procedure"}
        for fields in ({"findings": [finding]},
                       {"unknowns": [{"blocking": True, "detail": "User grant unavailable"}]}):
            with self.subTest(fields=fields):
                report = self.report(verdict="NEEDS REVISION", **fields)
                process = self.check(report)
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertEqual(json.loads(process.stdout), report)
                report["verdict"] = "APPROVE"
                self.assert_rejected(self.check(report))
        self.assert_rejected(self.check(self.report(verdict="NEEDS REVISION")))
        self.assert_rejected(self.check(self.report(verdict="NEEDS REVISION", unknowns=[
            {"blocking": False, "detail": "A purely optional concern"}])))

    def test_changed_plan_cannot_reuse_prior_approval(self):
        report = self.report()
        self.plan.write_bytes(self.plan.read_bytes() + b"\nMaterial new scope\n")
        self.assert_rejected(self.check(report))
        fresh = self.collect()
        self.assert_rejected(self.check(report, fresh["plan_version"]))
        report["plan_version"] = fresh["plan_version"]
        self.assertEqual(self.check(report).returncode, 0)

    def test_stdin_wait_does_not_freeze_current_snapshot_before_edits(self):
        report = self.report()
        process = subprocess.Popen(self.command("validate", self.plan, "--version", report["plan_version"]),
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   env=self.env, cwd=self.root)
        try:
            process.stdin.write(json.dumps(report).encode("utf-8"))
            process.stdin.flush()
            self.plan.write_bytes(b"Entirely changed after reviewer output, before EOF\n")
            process.stdin.close()
            process.wait(timeout=5)
            self.assertNotEqual(process.returncode, 0)
            self.assertEqual(process.stdout.read(), b"")
            self.assertIn(b"stale", process.stderr.read())
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            for stream in (process.stdin, process.stdout, process.stderr):
                stream.close()

    def test_exact_path_rejects_same_content_other_file_and_symlink_alias(self):
        report = self.report()
        other = self.root / "other.md"
        other.write_bytes(self.plan.read_bytes())
        alias = self.root / "alias.md"
        alias.symlink_to(self.plan)
        for path in (other, alias, Path(self.plan.name)):
            with self.subTest(path=path):
                report["plan_path"] = str(path)
                self.assert_rejected(self.check(report))
        process = self.run_state("snapshot", alias)
        self.assertEqual(json.loads(process.stdout)["plan_path"], str(alias))

    def test_schema_refuses_missing_extra_and_wrong_typed_fields(self):
        original = self.report()
        cases = []
        for key in original:
            data = dict(original)
            del data[key]
            cases.append(data)
        cases.extend([dict(original, extra="not canonical"), dict(original, verdict="approve"),
                      dict(original, findings={}), dict(original, unknowns=None),
                      dict(original, plan_version=42), dict(original, plan_path=True),
                      dict(original, findings=[{"severity": "blocker"}]),
                      dict(original, unknowns=[{"blocking": 1, "detail": "not boolean"}]),
                      dict(original, unknowns=[{"blocking": False, "detail": "  "}]),
                      dict(original, unknowns=[{"blocking": False, "detail": "x", "extra": 0}])])
        finding = {"severity": "nonblocking", "section": "Checks", "evidence": "Missing optional case",
                   "impact": "Lower confidence", "fix": "Optional test"}
        for key in finding:
            bad = dict(finding, **{key: "  "})
            cases.append(dict(original, findings=[bad]))
        for data in cases:
            with self.subTest(data=data):
                self.assert_rejected(self.check(data, original["plan_version"]))

    def test_duplicate_keys_fences_nonfinite_and_truncation_are_not_repaired(self):
        report = self.report()
        text = json.dumps(report)
        nested = dict(report, unknowns=[{"blocking": False, "detail": "Unobserved"}])
        cases = [text.replace('"verdict": "APPROVE"', '"verdict":"NEEDS REVISION","verdict":"APPROVE"'),
                 json.dumps(nested).replace('"blocking": false', '"blocking":true,"blocking":false'),
                 json.dumps(nested).replace('"detail": "Unobserved"', '"detail":"x","detail":"Unobserved"'),
                 "```json\n" + text + "\n```", text[:-1], "[]", "", "null",
                 text.replace('"unknowns": []', '"unknowns": [NaN]')]
        for data in cases:
            with self.subTest(data=data):
                process = self.run_state("validate", self.plan, "--version", report["plan_version"], data=data)
                self.assert_rejected(process)
        for version in (report["plan_version"].upper(), "0" * 63, "not-a-hash"):
            self.assert_rejected(self.check(report, version))

    def test_unavailable_invalid_utf8_and_nonregular_plan_are_errors(self):
        report = self.report()
        self.plan.unlink()
        self.assert_rejected(self.check(report))
        self.plan.write_bytes(b"\xff")
        self.assert_rejected(self.run_state("snapshot", self.plan))
        self.plan.unlink()
        self.plan.mkdir()
        self.assert_rejected(self.run_state("snapshot", self.plan))
        if hasattr(os, "mkfifo"):
            fifo = self.root / "fifo"
            os.mkfifo(fifo)
            self.assert_rejected(self.run_state("snapshot", fifo))

    def test_permission_failure_has_no_accepted_output(self):
        output, errors = io.StringIO(), io.StringIO()
        with mock.patch.object(review_state.os, "open", side_effect=PermissionError(13, "Denied")):
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                code = review_state.main(["snapshot", str(self.plan)])
        self.assertEqual(code, 1)
        self.assertEqual(output.getvalue(), "")
        self.assertTrue(errors.getvalue())

    def test_open_stdin_deadline_and_invalid_utf8_are_errors(self):
        reader, writer = os.pipe()
        try:
            with os.fdopen(reader, "rb") as source:
                with mock.patch.object(review_state, "INPUT_TIMEOUT", 0.02):
                    with self.assertRaisesRegex(review_state.InvalidReview, "EOF"):
                        review_state.read_result(source)
        finally:
            os.close(writer)
        report = self.report()
        process = subprocess.run(self.command("validate", self.plan, "--version", report["plan_version"]),
                                 input=b"\xff", capture_output=True, env=self.env, timeout=5)
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(process.stdout, b"")

    def make_packet(self, brief="Review against the original task.", env=None):
        return subprocess.run(self.command("packet", self.plan), input=brief, text=True,
                              capture_output=True, cwd=self.root, env=env or self.env, timeout=5)

    def test_packet_writes_private_exact_snapshot_and_brief(self):
        env = dict(self.env, TMPDIR=str(self.root))
        process = self.make_packet("Задача:\n  keep  spacing\t", env)
        self.assertEqual(process.returncode, 0, process.stderr)
        result = json.loads(process.stdout)
        packet = Path(result["packet_path"])
        self.assertEqual(packet.parent.parent, self.root)
        self.assertEqual(os.stat(packet.parent).st_mode & 0o777, 0o700)
        self.assertEqual(os.stat(packet).st_mode & 0o777, 0o600)
        content = json.loads(packet.read_text(encoding="utf-8"))
        self.assertRegex(content["request_id"], r"^[0-9a-f]{16}$")
        self.assertEqual(content, dict(self.collect(), brief="Задача:\n  keep  spacing\t",
                                       request_id=content["request_id"]))
        self.assertEqual({key: result[key] for key in ("request_id", "plan_path", "plan_version")},
                         {key: content[key] for key in ("request_id", "plan_path", "plan_version")})
        second = json.loads(self.make_packet(env=env).stdout)
        self.assertNotEqual(second["packet_path"], str(packet))
        self.assertNotEqual(second["request_id"], content["request_id"])
        self.assertEqual(json.loads(packet.read_text(encoding="utf-8"))["brief"], content["brief"])

    def test_packet_refuses_empty_brief_whitespace_tmpdir_and_cleans_failures(self):
        spaced = self.root / "tmp  dir"
        spaced.mkdir()
        self.assert_rejected(self.make_packet("  \n", dict(self.env, TMPDIR=str(self.root))))
        self.assert_rejected(self.make_packet(env=dict(self.env, TMPDIR=str(spaced))))
        self.assertEqual(list(spaced.iterdir()), [])
        holder = self.root / "holder"
        holder.mkdir()
        output, errors = io.StringIO(), io.StringIO()
        real_open = os.open
        def failing_open(path, flags, *args):
            if os.fspath(path).endswith("packet.json"):
                raise PermissionError(13, "Denied")
            return real_open(path, flags, *args)
        with mock.patch.object(review_state.tempfile, "tempdir", str(holder)), \
                mock.patch.object(review_state.os, "open", side_effect=failing_open), \
                mock.patch.object(review_state, "read_result", return_value="brief"):
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                code = review_state.main(["packet", str(self.plan)])
        self.assertEqual(code, 1)
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(list(holder.iterdir()), [])

    def test_peer_reply_escaping_survives_whitespace_collapse(self):
        folder = self.root / "dir  with   runs"
        folder.mkdir()
        self.plan = folder / "plan.md"
        self.plan.write_bytes(b"# Plan\n")
        evidence = "code:  x\t= 1\nnext   line  end"
        report = self.report(verdict="NEEDS REVISION", findings=[{
            "severity": "blocker", "section": "Steps", "evidence": evidence,
            "impact": "Exact quote matters", "fix": "Keep  it"}])
        collapse = lambda text: " ".join(text.split())  # what peer-chat delivers

        naive = collapse(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
        self.assert_rejected(self.check(json.loads(naive)))

        def peer_escape(value):
            # The rule from runtime.md: JSON-escape newlines/tabs, non-ASCII whitespace,
            # and each space in a run of two or more spaces.
            text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            text = "".join(f"\\u{ord(c):04x}" if c.isspace() and c != " " else c for c in text)
            return re.sub(r" {2,}", lambda run: "\\u0020" * len(run.group()), text)

        delivered = collapse(peer_escape(report))
        process = self.run_state("validate", self.plan, "--version", report["plan_version"],
                                 data=delivered)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout), report)

    def test_peer_reply_must_carry_pending_request_id(self):
        report = self.report()
        text = json.dumps(report, separators=(",", ":"))
        pending = "3f9a1c0d5e7b2a46"
        validate = lambda data, request_id=pending: self.run_state(
            "validate", self.plan, "--version", report["plan_version"], "--request-id", request_id,
            data=data)
        process = validate(f"{pending} {text}")
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout), report)
        for data in (f"c0ffee0000000000 {text}", text, f"{pending}{text}", f" {pending} {text}"):
            with self.subTest(data=data):
                self.assert_rejected(validate(data))
        self.assert_rejected(validate(f"{pending} {text}", "NOT-HEX"))

    def test_cold_cached_execution_needs_only_bundled_script(self):
        cached = self.root / "cache" / "skill" / "scripts" / SCRIPT.name
        cached.parent.mkdir(parents=True)
        shutil.copyfile(SCRIPT, cached)
        report = self.report()
        process = self.run_state("snapshot", self.plan, script=cached)
        self.assertEqual(process.returncode, 0, process.stderr)
        process = self.run_state("validate", self.plan, "--version", report["plan_version"],
                                 data=json.dumps(report), script=cached)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout), report)


if __name__ == "__main__":
    unittest.main()
