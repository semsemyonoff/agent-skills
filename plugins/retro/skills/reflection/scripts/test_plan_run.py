import collections
import contextlib
import datetime as dt
import io
import json
import os
import tempfile
import unittest
from unittest import mock

import plan_run as P


class PlanRunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = os.path.realpath(self.temp.name)
        self.plan = self.write("docs/plan.md", "### Task 1: First\n- [x] one\n- [ ] two\n### Task 2: Second\n- [ ] three\n## Validation Commands\n- `python3 check.py`\n")
        self.progress = self.write(".ralphex/progress/progress-example.txt", self.log())

    def write(self, path, content):
        path = os.path.join(self.root, path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return path

    def log(self, body=None):
        return (f"Plan: {self.plan}\nBranch: example\nMode: full\nStarted: 2026-10-08 09:00:00\n" +
                (body if body is not None else "starting task execution phase\n--- task iteration 7 ---\n[26-10-08 09:01:00] working\n[26-10-08 09:02:00] Task 1 done\nCompleted: 2026-10-08 09:03:00\n"))

    def args(self, *extra):
        return P.parse_args(["--project-root", self.root, "--tz", "UTC", "--config-dir", os.path.join(self.root, "claude"),
                             "--omp-sessions-dir", os.path.join(self.root, "omp"),
                             "--codex-sessions-dir", os.path.join(self.root, "codex"), *extra])

    def test_plan_counts_size_validation(self):
        plan = P.parse_plan(self.plan)
        self.assertEqual((plan["tasks"][0]["done"], plan["tasks"][0]["total"]), (1, 2))
        self.assertEqual(plan["validation_commands"], ["python3 check.py"])
        self.assertEqual(plan["bytes"], os.path.getsize(self.plan))
        self.assertEqual(plan["lines"], 7)

    def test_success_timezone_and_task_evidence(self):
        run = P.parse_progress(self.progress, "Etc/GMT-3")
        self.assertEqual(run["start"].hour, 6)
        self.assertEqual(run["status"], "Completed")
        self.assertFalse(run["failed"])
        iteration = next(b for b in run["boundaries"] if b["kind"] == "iteration")
        self.assertEqual(iteration["number"], 7)
        self.assertEqual(iteration["task_number"], 1)
        self.assertEqual(iteration["outcome"], "completed")

    def test_failure_restart_repeated_iteration_phase(self):
        self.write(".ralphex/progress/progress-example.txt", self.log(
            "starting task execution phase\n--- task iteration 1 ---\n[26-10-08 09:01:00] token=private-value\n"
            "[26-10-08 09:02:00] ralphex --branch example docs/plan.md\n"
            "[26-10-08 09:02:01] <<<RALPHEX:TASK_FAILED>>>\nFailed: 2026-10-08 09:02:02\n"
            "--- restarted at 2026-10-08 09:04:00 ---\nstarting task execution phase\n--- task iteration 1 ---\n"
            "[26-10-08 09:05:00] Task 2 done\nstarting external review phase\n[26-10-08 09:06:00] review\n"
            "Completed: 2026-10-08 09:07:00\n"))
        run = P.parse_progress(self.progress, "UTC")
        self.assertFalse(run["failed"])
        self.assertEqual(len(run["restarts"]), 1)
        self.assertEqual(len(run["failures"]), 1)
        self.assertNotIn("private-value", json.dumps(run["failures"]))
        self.assertEqual(len(run["resume_lines"]), 1)
        iterations = [b for b in run["boundaries"] if b["kind"] == "iteration"]
        self.assertEqual([b["number"] for b in iterations], [1, 1])
        self.assertIsNone(iterations[0]["task_number"])
        self.assertEqual(iterations[0]["outcome"], "failed")
        self.assertEqual(iterations[1]["end"].minute, 5)

    def test_restart_without_terminal_unknown(self):
        self.write(".ralphex/progress/progress-example.txt", self.log("Failed: 2026-10-08 09:02:00\n--- restarted at 2026-10-08 09:04:00 ---\n"))
        self.assertIsNone(P.parse_progress(self.progress, "UTC")["failed"])

    def test_moved_plan_basename_newest_and_others(self):
        moved = self.write("completed/plan.md", "### Task 1: Moved\n")
        older = self.write(".ralphex/progress/progress-older.txt", self.log())
        os.utime(older, (1, 1))
        run, plan, selection = P.select_inputs(self.args("--plan", moved))
        self.assertEqual(run["path"], self.progress)
        self.assertEqual(selection["matched_by"], "basename")
        self.assertEqual(selection["other_progress"], [older])
        self.assertEqual(plan["path"], moved)

    def test_realpath_preferred_over_newer_basename(self):
        newer = self.write(".ralphex/progress/progress-newer.txt", self.log().replace(self.plan, "/elsewhere/plan.md"))
        os.utime(self.progress, (1, 1))
        run, _, selection = P.select_inputs(self.args("--plan", self.plan))
        self.assertEqual(run["path"], self.progress)
        self.assertEqual(selection["matched_by"], "realpath")
        self.assertIn(newer, selection["other_progress"])

    def test_missing_files_exit_two(self):
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(P.main(["--project-root", self.root, "--progress", "absent"]), 2)
        with self.assertRaises(ValueError):
            P.select_inputs(self.args("--plan", "absent.md"))

    def test_invalid_cli(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                self.args("--planning-days", "-1")
            with self.assertRaises(SystemExit):
                self.args("--tz", "Not/AZone")

    def jsonl(self, path, rows):
        return self.write(path, "".join(json.dumps(row) + "\n" for row in rows))

    def codex(self, name="exec", start="2026-10-08T09:01:05Z", automation=True, patch=None, cwd=None, partial_history=True):
        cwd = cwd or self.root
        rows = [{"timestamp": start, "type": "session_meta", "payload": {
            "id": name, "cwd": cwd, "originator": "codex_exec" if automation else "codex_cli",
            "source": "exec" if automation else "cli", "history_base": "inherited" if automation and partial_history else None}},
            {"timestamp": start, "type": "turn_context", "payload": {"model": "synthetic-model", "effort": "medium"}},
            {"timestamp": start, "type": "token_usage_record", "payload": {
                "usage": {"input_tokens": 12, "cached_input_tokens": 2, "cache_write_input_tokens": 0,
                          "output_tokens": 3, "total_tokens": 15},
                "thread_token_usage": {"input_tokens": 900, "output_tokens": 90, "total_tokens": 990}}}]
        if patch:
            rows.append({"timestamp": start, "type": "response_item", "payload": {
                "type": "custom_tool_call", "name": "apply_patch", "call_id": "patch", "input": patch}})
        return self.jsonl(f"codex/sessions/rollout-{name}.jsonl", rows)

    def claude(self, name="sdk-executor", start="2026-10-08T09:01:05Z", edit=None):
        content = [{"type": "tool_use", "id": "edit", "name": "Write", "input": {"file_path": edit}}] if edit else []
        return self.jsonl(f"claude/projects/project/{name}.jsonl", [{
            "type": "assistant", "uuid": name, "sessionId": name, "cwd": self.root,
            "entrypoint": "sdk-cli" if name.startswith("sdk") else "cli", "timestamp": start,
            "message": {"id": name, "model": "synthetic-claude", "content": content, "usage": {
                "input_tokens": 10, "output_tokens": 3, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}}}])

    def test_codex_window_cost_not_thread_total_and_unknown_metrics(self):
        self.codex()
        report = P.report(self.args())
        iteration = report["tasks"][0]["iterations"][0]
        self.assertEqual(iteration["link_status"], "linked")
        link = iteration["candidates"][0]
        self.assertEqual(link["usage"]["total"], 15)
        self.assertEqual(link["thread_total"]["total"], 990)
        self.assertTrue(link["partial_history"])
        self.assertEqual(report["totals"]["observed_in_run"]["total"], 15)
        self.assertEqual(link["models"][0]["effort"], "medium")
        self.assertIsNone(link["errors"])

    def test_claude_executor_and_missing_sources(self):
        self.claude()
        report = P.report(self.args())
        self.assertEqual(report["tasks"][0]["iterations"][0]["candidates"][0]["source"], "claude")
        self.assertEqual(report["diagnostics"]["sources"]["codex"]["status"], "unavailable")
        self.assertEqual(report["totals"]["completeness"], "partial")

    def test_ambiguous_candidates_kept_separate(self):
        self.codex("one")
        self.codex("two")
        iteration = P.report(self.args())["tasks"][0]["iterations"][0]
        self.assertEqual(iteration["link_status"], "ambiguous")
        self.assertEqual(len(iteration["candidates"]), 2)
        self.assertIsNone(iteration["usage"]["total"])
        self.assertEqual([c["usage"]["total"] for c in iteration["candidates"]], [15, 15])

    def test_unlinked_and_unknown_task_identity(self):
        self.write(".ralphex/progress/progress-example.txt", self.log(
            "--- task iteration 8 ---\n[26-10-08 09:01:00] working\nCompleted: 2026-10-08 09:03:00\n"))
        report = P.report(self.args())
        row = next(t for t in report["tasks"] if t["number"] is None)
        self.assertEqual(row["iterations"][0]["link_status"], "unlinked")
        self.assertIsNone(row["usage"]["total"])
        self.assertEqual(row["iterations"][0]["number"], 8)

    def test_omp_review_low_confidence_and_other_without_phase(self):
        self.write(".ralphex/progress/progress-example.txt", self.log(
            "starting external review phase\n[26-10-08 09:01:00] review\nCompleted: 2026-10-08 09:03:00\n"))
        self.jsonl("omp/project/review.jsonl", [
            {"type": "session", "id": "review", "cwd": self.root, "timestamp": "2026-10-08T09:01:05Z"},
            {"type": "message", "id": "m", "timestamp": "2026-10-08T09:02:00Z",
             "message": {"role": "assistant", "model": "synthetic", "content": [],
                         "usage": {"input": 4, "cacheWrite": 0, "cacheRead": 0, "output": 1, "totalTokens": 5}}}])
        report = P.report(self.args())
        link = report["reviews"][0]["candidates"][0]
        self.assertEqual(link["confidence"], "low")
        self.assertEqual(link["linked_by"], "time-window|cwd")
        self.write(".ralphex/progress/progress-example.txt", self.log(
            "[26-10-08 09:01:00] review\nCompleted: 2026-10-08 09:03:00\n"))
        self.assertEqual(len(P.report(self.args())["other_in_run"]), 1)

    def test_planning_claude_absolute_codex_relative_and_unrelated(self):
        self.claude("interactive", "2026-10-07T09:00:00Z", self.plan)
        self.codex("planning", "2026-10-07T10:00:00Z", False,
                   "*** Begin Patch\n*** Update File: docs/plan.md\n+text\n*** End Patch")
        self.codex("unrelated", "2026-10-07T10:00:00Z", False,
                   "*** Begin Patch\n*** Add File: docs/other.md\n+text\n*** End Patch")
        report = P.report(self.args())
        self.assertEqual(len(report["planning"]["sessions"]), 2)
        self.assertTrue(all(s["linked_by"] == "path|time-window|cwd" for s in report["planning"]["sessions"]))

    def test_old_file_skip_load_once_and_cwd_boundary(self):
        old = self.codex("old")
        os.utime(old, (1, 1))
        self.codex("outside", cwd=self.root + "-neighbor")
        original = P.T.load_sessions
        with mock.patch.object(P.T, "load_sessions", wraps=original) as load:
            report = P.report(self.args())
        self.assertEqual(load.call_count, 3)
        self.assertTrue(all(call.kwargs["min_mtime"] == dt.datetime(2026, 10, 5, 9, tzinfo=P.UTC)
                            for call in load.call_args_list))
        self.assertEqual(report["tasks"][0]["iterations"][0]["link_status"], "unlinked")
        self.assertGreaterEqual(report["diagnostics"]["counts"].get("mtime_skipped", 0), 1)

    def test_full_redaction_json_markdown_and_unknown_duration(self):
        self.write(".ralphex/progress/progress-example.txt", self.log().replace("Branch: example", "Branch: token=private-value"))
        self.codex()
        report = P.report(self.args())
        encoded = json.dumps(report)
        self.assertNotIn("private-value", encoded)
        self.assertEqual(set(("run", "tasks", "reviews", "planning", "totals", "diagnostics")) - report.keys(), set())
        rendered = P.fmt_md(report)
        self.assertIn("## Tasks", rendered)
        self.assertIn("## Planning", rendered)
        self.assertIn("## Diagnostics", rendered)
        self.assertNotIn("private-value", rendered)
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(P.main(["--project-root", self.root, "--tz", "UTC", "--out", "json",
                                     "--config-dir", os.path.join(self.root, "absent"),
                                     "--omp-sessions-dir", os.path.join(self.root, "absent"),
                                     "--codex-sessions-dir", os.path.join(self.root, "absent")]), 0)
        self.assertIn("totals", json.loads(output.getvalue()))

    def test_usage_after_iteration_remains_unlinked(self):
        path = self.codex(start="2026-10-08T09:00:01Z")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"timestamp": "2026-10-08T09:02:30Z", "type": "token_usage_record",
                                 "payload": {"usage": {"input_tokens": 4, "cached_input_tokens": 0,
                                                       "cache_write_input_tokens": 0, "output_tokens": 1,
                                                       "total_tokens": 5}}}) + "\n")
        self.write(".ralphex/progress/progress-example.txt", self.log(
            "starting task execution phase\n--- task iteration 1 ---\n"
            "[26-10-08 09:01:00] Task 1 done\nstarting independent assessment phase\n"
            "[26-10-08 09:02:00] checking\nCompleted: 2026-10-08 09:03:00\n"))
        report = P.report(self.args())
        self.assertEqual(report["tasks"][0]["usage"]["total"], 15)
        self.assertEqual(report["totals"]["unlinked"]["total"], 5)
        self.assertEqual(report["totals"]["observed_in_run"]["total"], 20)
        self.assertAlmostEqual(report["totals"]["unlinked_share"], 0.25)
        self.assertEqual(report["reviews"][0]["name"], "independent assessment")

    def test_missing_usage_unknown_not_zero(self):
        self.jsonl("claude/projects/project/sdk-empty.jsonl", [{
            "type": "assistant", "sessionId": "sdk-empty", "cwd": self.root,
            "timestamp": "2026-10-08T09:01:05Z", "message": {"id": "empty", "content": []}}])
        link = P.report(self.args())["tasks"][0]["iterations"][0]["candidates"][0]
        self.assertIsNone(link["usage"]["total"])
        self.assertEqual(link["usage"]["missing"]["total"], 1)
        self.assertIsNone(link["usage"]["known"]["total"])

    def test_explicit_tool_result_duration_and_errors(self):
        self.jsonl("claude/projects/project/sdk-tools.jsonl", [
            {"type": "assistant", "sessionId": "sdk-tools", "cwd": self.root,
             "timestamp": "2026-10-08T09:01:05Z", "message": {"id": "call", "content": [
                 {"type": "tool_use", "id": "tool", "name": "Bash", "input": {"command": "check token=private-value"}}]}},
            {"type": "user", "sessionId": "sdk-tools", "timestamp": "2026-10-08T09:01:35Z",
             "message": {"content": [{"type": "tool_result", "tool_use_id": "tool", "is_error": True,
                                     "content": "check failed"}]}}])
        link = P.report(self.args())["tasks"][0]["iterations"][0]["candidates"][0]
        self.assertEqual(link["errors"], 1)
        self.assertEqual(link["slowest_commands"][0]["duration_seconds"], 30)
        self.assertNotIn("private-value", json.dumps(link))

    def test_no_progress_and_absent_plan(self):
        args = self.args("--project-root", os.path.join(self.root, "empty"))
        with self.assertRaisesRegex(ValueError, "no matching progress"):
            P.report(args)
        with self.assertRaisesRegex(ValueError, "cannot read"):
            P.report(self.args("--plan", "absent.md", "--progress", self.progress))

    def test_failed_restart_executor_links_stay_distinct(self):
        self.write(".ralphex/progress/progress-example.txt", self.log(
            "starting task execution phase\n--- task iteration 4 ---\n"
            "[26-10-08 09:01:00] Task 2 started\n"
            "[26-10-08 09:02:00] <<<RALPHEX:TASK_FAILED>>>\nFailed: 2026-10-08 09:02:01\n"
            "--- restarted at 2026-10-08 09:04:00 ---\nstarting task execution phase\n"
            "--- task iteration 4 ---\n[26-10-08 09:05:00] Task 2 done\n"
            "Completed: 2026-10-08 09:06:00\n"))
        self.codex("failed", "2026-10-08T09:00:05Z")
        self.codex("retry", "2026-10-08T09:04:05Z")
        report = P.report(self.args())
        task = next(t for t in report["tasks"] if t["number"] == 2)
        self.assertEqual([i["number"] for i in task["iterations"]], [4, 4])
        self.assertEqual([i["outcome"] for i in task["iterations"]], ["failed", "completed"])
        self.assertEqual([i["candidates"][0]["session"] for i in task["iterations"]],
                         ["codex:failed", "codex:retry"])
        self.assertEqual(task["usage"]["total"], 30)
        self.assertEqual(len(task["failure_excerpt"]), 1)
        self.assertFalse(report["run"]["failed"])

    def available_roots(self):
        for path in ("claude/projects", "omp", "codex/sessions"):
            os.makedirs(os.path.join(self.root, path), exist_ok=True)

    def assert_partial_costs(self, report, known):
        iteration = report["tasks"][0]["iterations"][0]
        candidate = iteration["candidates"][0]
        for row in (candidate, iteration, report["tasks"][0]):
            self.assertEqual(row["completeness"], "partial")
            self.assertIsNone(row["usage"]["total"])
            self.assertEqual(row["usage"]["known"]["total"], known)
        self.assertEqual(report["run"]["completeness"], "partial")
        self.assertEqual(report["totals"]["completeness"], "partial")
        for usage in (report["totals"]["observed_in_run"], report["totals"]["by_phase"]["task execution"],
                      report["totals"]["by_task"][0]["usage"]):
            self.assertIsNone(usage["total"])
            self.assertEqual(usage["known"]["total"], known)
        self.assertTrue(all(s["status"] == "available" for s in report["diagnostics"]["sources"].values()))

    def test_fallback_no_pre_window_baseline_propagates_partial(self):
        self.available_roots()
        def snapshot(time, total):
            return {"timestamp": time, "type": "event_msg", "payload": {"type": "token_count", "info": {
                "total_token_usage": {"input_tokens": total, "cached_input_tokens": 0,
                                     "cache_write_input_tokens": 0, "output_tokens": 0, "total_tokens": total}}}}
        self.jsonl("codex/sessions/rollout-fallback.jsonl", [
            {"timestamp": "2026-10-08T09:00:05Z", "type": "session_meta",
             "payload": {"id": "fallback", "cwd": self.root, "source": "exec"}},
            snapshot("2026-10-08T09:01:00Z", 100), snapshot("2026-10-08T09:02:00Z", 150)])
        report = P.report(self.args())
        self.assert_partial_costs(report, 50)
        candidate = report["tasks"][0]["iterations"][0]["candidates"][0]
        self.assertEqual(candidate["thread_total"]["total"], 150)
        self.assertFalse(candidate["partial_history"])
        self.assertEqual(candidate["usage_baseline_time"], "2026-10-08T09:01:00+00:00")
        self.assertEqual(candidate["usage_completeness"], "partial")
        self.assertEqual(report["diagnostics"]["sources"]["codex"]["coverage"], "observed")

    def test_fallback_baseline_before_window_keeps_known_complete_delta(self):
        start = dt.datetime(2026, 10, 8, 9, tzinfo=P.UTC)
        sess = {"id": "codex:baseline", "source": "codex", "records": [], "paths": [], "cwd": self.root,
                "usage_source": "token_count", "usage_baseline_time": "2026-10-08T08:59:00Z"}
        event = {"kind": "usage", "key": "delta", "time": start + dt.timedelta(minutes=1),
                 "usage": {key: 50 if key in ("input", "total") else 0 for key in P.T.METRICS}}
        candidate = P.link_row(sess, [event], start, start + dt.timedelta(minutes=3), "time-window|cwd", "medium")
        self.assertEqual(candidate["usage"]["total"], 50)
        self.assertEqual(candidate["usage_completeness"], "observed")
        self.assertEqual(candidate["completeness"], "observed")

    def test_skipped_zst_source_available_but_coverage_partial(self):
        self.available_roots()
        self.codex(partial_history=False)
        self.write("codex/sessions/rollout-hidden.jsonl.zst", "synthetic compressed placeholder")
        original = __import__
        def unavailable(name, *args, **kwargs):
            if name == "compression" or name.startswith("compression."):
                raise ImportError("synthetic unavailable")
            return original(name, *args, **kwargs)
        with mock.patch("builtins.__import__", side_effect=unavailable):
            report = P.report(self.args())
        self.assert_partial_costs(report, 15)
        source = report["diagnostics"]["sources"]["codex"]
        self.assertEqual(source["coverage"], "partial")
        self.assertEqual(source["evidence_loss"]["zst_skipped"], 1)
        self.assertFalse(report["tasks"][0]["iterations"][0]["candidates"][0]["partial_history"])

    def test_malformed_invalid_header_unreadable_coverage(self):
        self.available_roots()
        path = self.codex(partial_history=False)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("{malformed synthetic record\n")
        self.jsonl("omp/broken.jsonl", [{"type": "not-a-session", "id": "lost", "cwd": self.root}])
        hidden = self.write("claude/projects/project/sdk-hidden.jsonl", "{}\n")
        original = P.T.read_records
        def unreadable(path, diagnostics):
            if path == hidden:
                diagnostics["unreadable_files"] += 1
                return []
            return original(path, diagnostics)
        with mock.patch.object(P.T, "read_records", side_effect=unreadable):
            report = P.report(self.args())
        self.assert_partial_costs(report, 15)
        sources = report["diagnostics"]["sources"]
        for source, loss in (("claude", "unreadable_files"), ("omp", "invalid_headers"), ("codex", "malformed_records")):
            self.assertEqual(sources[source]["coverage"], "partial")
            self.assertEqual(sources[source]["evidence_loss"][loss], 1)

    def test_codex_joined_output_elapsed_and_result_error_time(self):
        self.available_roots()
        path = self.codex(partial_history=False)
        rows = [
            {"timestamp": "2026-10-08T09:01:10Z", "type": "response_item", "payload": {
                "type": "function_call", "name": "exec_command", "call_id": "slow",
                "arguments": json.dumps({"command": "sleep 60"})}},
            {"timestamp": "2026-10-08T09:02:10Z", "type": "response_item", "payload": {
                "type": "function_call_output", "call_id": "slow", "output": {"isError": False, "content": []}}},
            {"timestamp": "2026-10-08T09:02:20Z", "type": "response_item", "payload": {
                "type": "function_call", "name": "exec_command", "call_id": "late-error", "arguments": "{}"}},
            {"timestamp": "2026-10-08T09:04:00Z", "type": "response_item", "payload": {
                "type": "function_call_output", "call_id": "late-error", "output": {"isError": True, "content": []}}}]
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("".join(json.dumps(row) + "\n" for row in rows))
        report = P.report(self.args())
        candidate = report["tasks"][0]["iterations"][0]["candidates"][0]
        slow = next(command for command in candidate["slowest_commands"] if command["command"] == "sleep 60")
        self.assertEqual(slow["duration_seconds"], 60)
        self.assertEqual(slow["duration_source"], "call_to_result_elapsed")
        self.assertEqual(slow["result_time"], "2026-10-08T09:02:10+00:00")
        self.assertEqual(candidate["observed_errors"], 0)
        self.assertEqual(candidate["usage"]["total"], 15)

    def mixed_iteration_report(self, ambiguous=False):
        self.available_roots()
        self.write(".ralphex/progress/progress-example.txt", self.log(
            "starting task execution phase\n--- task iteration 1 ---\n"
            "[26-10-08 09:01:00] Task 1 started\n[26-10-08 09:02:00] working\n"
            "--- task iteration 2 ---\n[26-10-08 09:03:00] Task 1 started\n"
            "[26-10-08 09:04:00] Task 1 done\nCompleted: 2026-10-08 09:05:00\n"))
        self.codex("first", "2026-10-08T09:00:05Z", partial_history=False)
        if ambiguous:
            self.codex("second-a", "2026-10-08T09:02:05Z", partial_history=False)
            self.codex("second-b", "2026-10-08T09:02:10Z", partial_history=False)
        return P.report(self.args())

    def assert_mixed_attribution_partial(self, report, second_status):
        task = report["tasks"][0]
        self.assertEqual([i["link_status"] for i in task["iterations"]], ["linked", second_status])
        self.assertEqual(task["completeness"], "partial")
        summaries = (task["usage"], report["totals"]["by_task"][0]["usage"],
                     report["totals"]["by_phase"]["task execution"])
        for summary in summaries:
            self.assertIsNone(summary["total"])
            self.assertEqual(summary["known"]["total"], 15)
            self.assertEqual(summary["completeness"], "partial")
            self.assertTrue(summary["coverage_missing"])
        self.assertTrue(all(source["status"] == "available" and source["coverage"] == "observed"
                            for source in report["diagnostics"]["sources"].values()))
        first = task["iterations"][0]["candidates"][0]
        self.assertEqual(first["completeness"], "observed")
        self.assertEqual(first["usage"]["total"], 15)
        self.assertFalse(first["partial_history"])
        self.assertEqual(len(report["totals"]["by_task"]), len(report["tasks"]))
        self.assertEqual(list(report["totals"]["by_phase"]), ["task execution"])

    def test_mixed_linked_unlinked_iterations_mark_task_and_phase_metrics_partial(self):
        report = self.mixed_iteration_report()
        self.assert_mixed_attribution_partial(report, "unlinked")
        self.assertEqual(report["tasks"][0]["iterations"][1]["candidates"], [])

    def test_mixed_linked_ambiguous_iterations_keep_candidate_costs_separate(self):
        report = self.mixed_iteration_report(ambiguous=True)
        self.assert_mixed_attribution_partial(report, "ambiguous")
        second = report["tasks"][0]["iterations"][1]
        self.assertIsNone(second["usage"]["total"])
        self.assertEqual([c["usage"]["total"] for c in second["candidates"]], [15, 15])
        self.assertEqual(report["totals"]["observed_in_run"]["total"], 45)
        self.assertEqual(report["totals"]["unlinked"]["total"], 30)

    def test_natural_completions_dominate_other_task_references(self):
        variants = ("Task 1 (First example) is done.", "Task 1 is completed.",
                    "Task 1 is finished and committed.", "Task 1 finished.",
                    "I did Task 1, the first item, and committed it.")
        for completion in variants:
            with self.subTest(completion=completion):
                self.write(".ralphex/progress/progress-example.txt", self.log(
                    "--- task iteration 91 ---\n[26-10-08 09:01:00] Task 2 started\n"
                    "Tasks 2–4 are still open\nMore Task sections remain, starting with Task 2\n"
                    "Task 2 will be completed next\nTask 2 is not done\n"
                    "`Task 2 done`\necho 'Task 2 completed'\n"
                    f"[26-10-08 09:02:00] {completion}\nCompleted: 2026-10-08 09:03:00\n"))
                iteration = P.parse_progress(self.progress, "UTC")["boundaries"][0]
                self.assertEqual(iteration["task_number"], 1)
                self.assertEqual(iteration["outcome"], "completed")
                self.assertEqual([e["status"] for e in iteration["task_evidence"]], ["started", "completed"])

    def test_contradictory_completions_remain_ambiguous(self):
        self.write(".ralphex/progress/progress-example.txt", self.log(
            "--- task iteration 41 ---\n[26-10-08 09:01:00] Task 1 is done\n"
            "[26-10-08 09:02:00] Task 2 (Second) is finished\nCompleted: 2026-10-08 09:03:00\n"))
        iteration = P.parse_progress(self.progress, "UTC")["boundaries"][0]
        self.assertIsNone(iteration["task_number"])
        self.assertEqual(iteration["task_identity"], "ambiguous")
        self.assertEqual(iteration["outcome"], "completed")

    def test_same_line_contradictory_completed_clauses_remain_ambiguous(self):
        self.write(".ralphex/progress/progress-example.txt", self.log(
            "--- task iteration 41 ---\n[26-10-08 09:01:00] Task 1 done. Task 2 is finished.\n"
            "Completed: 2026-10-08 09:03:00\n"))
        iteration = P.parse_progress(self.progress, "UTC")["boundaries"][0]
        self.assertIsNone(iteration["task_number"])
        self.assertEqual(iteration["task_identity"], "ambiguous")
        self.assertEqual([e["task_number"] for e in iteration["task_evidence"]], [1, 2])

    def test_future_negative_quoted_mentions_do_not_identify_task(self):
        self.write(".ralphex/progress/progress-example.txt", self.log(
            "--- task iteration 1 ---\n[26-10-08 09:01:00] Task 1 is not done\n"
            "Task 1 will be completed\nTask 1 done?\nTask 1 done is not true\n"
            "Task 1 done if the checks pass\nTask 1 done\"\n"
            "Run `Task 1 completed`\n' I did Task 1 '\nCompleted: 2026-10-08 09:03:00\n"))
        iteration = P.parse_progress(self.progress, "UTC")["boundaries"][0]
        self.assertIsNone(iteration["task_number"])
        self.assertEqual(iteration["outcome"], "unknown")

    def test_claude_execution_rounds_external_review_and_evaluation(self):
        self.write(".ralphex/progress/progress-example.txt", self.log(
            "starting task execution phase\n--- task iteration 88 ---\n"
            "[26-10-08 09:01:00] Task 1 (First) is completed\n"
            "all tasks completed, starting code review...\n--- claude review 0: all findings ---\n"
            "[26-10-08 09:02:00] first review finished\n--- claude review 1: critical/major ---\n"
            "[26-10-08 09:03:00] second review finished\n--- codex external review ---\n"
            "--- codex iteration 1 ---\n[26-10-08 09:04:00] external result arrived\n"
            "--- claude evaluating codex findings ---\n"
            "[26-10-08 09:05:00] external review found no issues, skipping post-codex Claude review\n"
            "Quality review: no remaining changes\nCompleted: 2026-10-08 09:06:00\n"))
        self.claude("sdk-task", "2026-10-08T09:00:05Z")
        self.claude("sdk-review-zero", "2026-10-08T09:01:05Z")
        self.claude("sdk-review-one", "2026-10-08T09:02:05Z")
        self.codex("external", "2026-10-08T09:03:05Z")
        self.claude("sdk-evaluation", "2026-10-08T09:04:05Z")
        report = P.report(self.args())
        iteration = report["tasks"][0]["iterations"][0]
        self.assertEqual(iteration["task_number"], 1)
        self.assertEqual(iteration["candidates"][0]["session"], "claude:sdk-task")
        reviews = report["reviews"]
        self.assertEqual([r["review_role"] for r in reviews], ["review", "review", "external-review", "evaluation"])
        self.assertEqual([r["review_round"] for r in reviews], [0, 1, 1, None])
        self.assertEqual([r["candidates"][0]["source"] for r in reviews], ["claude", "claude", "codex", "claude"])
        self.assertTrue(all(r["link_status"] == "linked" for r in reviews))
        self.assertEqual(iteration["end"], reviews[0]["start"])
        self.assertTrue(all(left["end"] == right["start"] for left, right in zip(reviews, reviews[1:])))
        self.assertTrue(all(r["time_source"] == "preceding-progress-time" for r in reviews))
        self.assertEqual(report["totals"]["observed_in_run"]["total"], 67)
        self.assertEqual(report["totals"]["by_phase"]["claude review"]["total"], 26)
        self.assertIsNone(report["totals"]["unlinked"]["total"])

    def test_child_artifact_not_executor_and_unique_usage_stays_unlinked(self):
        parent = self.claude("sdk-parent")
        with open(parent, encoding="utf-8") as fh:
            copied = json.loads(fh.readline())
        child = {**copied, "uuid": "child-unique", "timestamp": "2026-10-08T09:01:30Z",
                 "message": {**copied["message"], "id": "child-unique"}}
        self.jsonl("claude/projects/project/sdk-parent/subagents/agent-example.jsonl", [copied, child])
        report = P.report(self.args())
        iteration = report["tasks"][0]["iterations"][0]
        self.assertEqual(iteration["link_status"], "linked")
        self.assertEqual([c["session"] for c in iteration["candidates"]], ["claude:sdk-parent"])
        self.assertEqual(iteration["usage"]["total"], 13)
        self.assertEqual(report["totals"]["observed_in_run"]["total"], 26)
        self.assertEqual(report["totals"]["unlinked"]["total"], 13)
        self.assertGreater(report["diagnostics"]["counts"]["copied_events_skipped"], 0)
        self.assertEqual(len(report["other_in_run"]), 1)

    def test_orphan_child_not_candidate_and_independent_parent_ambiguity_preserved(self):
        self.claude("sdk-one")
        self.claude("sdk-two")
        self.jsonl("claude/projects/project/absent/subagents/agent-orphan.jsonl", [{
            "type": "assistant", "uuid": "orphan", "sessionId": "absent", "cwd": self.root,
            "entrypoint": "sdk-cli", "timestamp": "2026-10-08T09:01:20Z",
            "message": {"id": "orphan", "model": "synthetic", "content": [], "usage": {
                "input_tokens": 2, "output_tokens": 1, "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0}}}])
        report = P.report(self.args())
        iteration = report["tasks"][0]["iterations"][0]
        self.assertEqual(iteration["link_status"], "ambiguous")
        self.assertEqual([c["session"] for c in iteration["candidates"]], ["claude:sdk-one", "claude:sdk-two"])
        self.assertEqual(report["totals"]["unlinked"]["total"], 29)

    def test_generic_and_repeated_review_boundaries_survive_restart(self):
        self.write(".ralphex/progress/progress-example.txt", self.log(
            "starting bespoke analysis phase\n[26-10-08 09:01:00] reviewing\n"
            "--- claude review 0: all findings ---\n[26-10-08 09:02:00] findings\n"
            "--- claude review 1: critical/major ---\nFailed: 2026-10-08 09:03:00\n"
            "--- restarted at 2026-10-08 09:04:00 ---\n"
            "starting task execution phase\n--- task iteration 9 ---\n"
            "[26-10-08 09:05:00] Task 2 is finished\n"
            "--- claude review 0: all findings ---\nCompleted: 2026-10-08 09:06:00\n"))
        run = P.parse_progress(self.progress, "UTC")
        phases = [b for b in run["boundaries"] if b["kind"] == "phase"]
        self.assertEqual(phases[0]["name"], "bespoke analysis")
        self.assertNotIn("review_provider", phases[0])
        self.assertEqual([b["review_round"] for b in phases if "review_round" in b], [0, 1, 0])
        self.assertEqual(run["status"], "Completed")
        iteration = next(b for b in run["boundaries"] if b["kind"] == "iteration")
        self.assertEqual(iteration["task_number"], 2)
        self.assertEqual(iteration["end"].minute, 5)

    def test_review_stage_label_does_not_resolve_independent_primary_ambiguity(self):
        self.write(".ralphex/progress/progress-example.txt", self.log(
            "--- claude review 0: all findings ---\n"
            "[26-10-08 09:02:00] finished\nCompleted: 2026-10-08 09:03:00\n"))
        self.claude("sdk-review")
        self.codex("not-claude", partial_history=False)
        report = P.report(self.args())
        review = report["reviews"][0]
        self.assertEqual(review["link_status"], "ambiguous")
        self.assertEqual({c["source"] for c in review["candidates"]}, {"claude", "codex"})
        self.assertIsNone(review["review_provider"])
        self.assertEqual(report["totals"]["unlinked"]["total"], 28)

    def test_report_conjoined_completed_tasks_have_no_named_task_assignment(self):
        self.write(".ralphex/progress/progress-example.txt", self.log(
            "--- task iteration 73 ---\n[26-10-08 09:02:00] Task 1 is done and Task 2 is finished.\n"
            "Completed: 2026-10-08 09:03:00\n"))
        self.claude()
        report = P.report(self.args())
        self.assertTrue(all(not task["iterations"] for task in report["tasks"] if task["number"] is not None))
        unknown = next(task for task in report["tasks"] if task["number"] is None)
        iteration = unknown["iterations"][0]
        self.assertEqual(iteration["task_identity"], "ambiguous")
        self.assertIsNone(iteration["task_number"])
        self.assertEqual([e["task_number"] for e in iteration["task_evidence"]], [1, 2])
        self.assertEqual(unknown["usage"]["total"], 13)

    def test_report_conditional_question_and_fenced_examples_do_not_complete_tasks(self):
        variants = ("Task 1 is done only if checks pass.", "Task 1 is done, right?",
                    "```text\nTask 1 is done\n```", "~~~text\nTask 1 is finished\n~~~")
        self.claude()
        for text in variants:
            with self.subTest(text=text):
                self.write(".ralphex/progress/progress-example.txt", self.log(
                    f"--- task iteration 73 ---\n[26-10-08 09:02:00] {text}\n"
                    "Completed: 2026-10-08 09:03:00\n"))
                report = P.report(self.args())
                self.assertEqual(report["tasks"][0]["iterations"], [])
                unknown = next(task for task in report["tasks"] if task["number"] is None)
                self.assertEqual(unknown["iterations"][0]["task_identity"], "unknown")
                self.assertEqual(unknown["outcome"], "unknown")
                self.assertEqual(unknown["usage"]["total"], 13)

    def test_report_completion_titles_do_not_change_assertion_framing(self):
        variants = ("Task 1 (Handle not found errors) is done.",
                    "Task 1 (Fix `report` normalization) is done.")
        self.claude()
        for text in variants:
            with self.subTest(text=text):
                self.write(".ralphex/progress/progress-example.txt", self.log(
                    f"--- task iteration 73 ---\n[26-10-08 09:02:00] {text}\n"
                    "Completed: 2026-10-08 09:03:00\n"))
                report = P.report(self.args())
                self.assertEqual(report["tasks"][0]["outcome"], "completed")
                self.assertEqual(report["tasks"][0]["iterations"][0]["task_identity"], "explicit-progress")
                self.assertEqual(report["tasks"][0]["usage"]["total"], 13)
                self.assertFalse(any(task["number"] is None for task in report["tasks"]))

    def test_report_claude_wrapper_variations_count_provider_message_once(self):
        parent = self.claude("sdk-parent")
        with open(parent, encoding="utf-8") as fh:
            message = json.loads(fh.readline())
        copy = {**message, "uuid": "child-wrapper", "isSidechain": True, "agentId": "invented-agent",
                "sessionId": "child-wrapper-session"}
        self.jsonl("claude/projects/project/sdk-parent/subagents/agent-wrapper.jsonl", [copy])
        report = P.report(self.args())
        self.assertEqual(report["tasks"][0]["usage"]["total"], 13)
        self.assertEqual(report["totals"]["observed_in_run"]["total"], 13)
        self.assertIsNone(report["totals"]["unlinked"]["total"])
        self.assertEqual(report["other_in_run"], [])
        self.assertGreater(report["diagnostics"]["counts"]["copied_events_skipped"], 0)

    def test_report_claude_changed_message_payload_and_unrelated_family_not_collapsed(self):
        parent = self.claude("sdk-parent")
        with open(parent, encoding="utf-8") as fh:
            message = json.loads(fh.readline())
        changed = {**message, "isSidechain": True, "agentId": "invented-agent",
                   "message": {**message["message"], "content": [{"type": "text", "text": "Different result"}]}}
        self.jsonl("claude/projects/project/sdk-parent/subagents/agent-changed.jsonl", [changed])
        self.jsonl("claude/projects/project/sdk-independent.jsonl", [
            {**message, "sessionId": "sdk-independent", "uuid": "independent-wrapper"}])
        report = P.report(self.args())
        iteration = report["tasks"][0]["iterations"][0]
        self.assertEqual(iteration["link_status"], "ambiguous")
        self.assertEqual(len(iteration["candidates"]), 2)
        self.assertEqual(report["totals"]["observed_in_run"]["total"], 39)
        self.assertEqual(report["totals"]["unlinked"]["total"], 39)
        self.assertEqual(report["diagnostics"]["counts"].get("copied_events_skipped", 0), 0)

    def test_report_omp_copies_require_identical_persisted_payload(self):
        self.write(".ralphex/progress/progress-example.txt", self.log(
            "starting bespoke review phase\n[26-10-08 09:02:00] finished\n"
            "Completed: 2026-10-08 09:03:00\n"))
        message = {"type": "message", "id": "stable-entry", "timestamp": "2026-10-08T09:01:05Z",
                   "message": {"role": "assistant", "id": "stable-message", "model": "synthetic",
                               "content": [], "usage": {"input": 4, "output": 1, "cacheWrite": 0,
                                                        "cacheRead": 0, "totalTokens": 5}}}
        self.jsonl("omp/project/parent.jsonl", [
            {"type": "session", "id": "parent", "cwd": self.root, "timestamp": "2026-10-08T09:01:00Z"},
            message])
        self.jsonl("omp/project/parent/child.jsonl", [
            {"type": "session", "id": "child", "cwd": self.root, "timestamp": "2026-10-08T09:01:00Z"},
            {**message, "wrapper": "different"}])
        report = P.report(self.args())
        self.assertEqual(report["reviews"][0]["link_status"], "linked")
        self.assertEqual(report["reviews"][0]["usage"]["total"], 5)
        self.assertEqual(report["totals"]["observed_in_run"]["total"], 10)
        self.assertEqual(report["totals"]["unlinked"]["total"], 5)

    def test_report_completed_chains_accept_did_form_after_and_or_comma(self):
        self.claude()
        for separator in (" and ", ", "):
            with self.subTest(separator=separator):
                self.write(".ralphex/progress/progress-example.txt", self.log(
                    f"--- task iteration 73 ---\n[26-10-08 09:02:00] Task 1 is done{separator}I did Task 2.\n"
                    "Completed: 2026-10-08 09:03:00\n"))
                report = P.report(self.args())
                self.assertTrue(all(not task["iterations"] for task in report["tasks"] if task["number"] is not None))
                unknown = next(task for task in report["tasks"] if task["number"] is None)
                iteration = unknown["iterations"][0]
                self.assertEqual(iteration["task_identity"], "ambiguous")
                self.assertEqual([e["task_number"] for e in iteration["task_evidence"]], [1, 2])
                self.assertEqual(unknown["usage"]["total"], 13)

    def test_report_task_references_inside_balanced_title_do_not_split_completion(self):
        self.claude()
        titles = ("Compare Task 2 and Task 3 behavior", "Compare Task 2, Task 3 behavior",
                  "Compare (Task 2 and Task 3) behavior", "Handle `Task 2, Task 3` examples")
        for title in titles:
            with self.subTest(title=title):
                self.write(".ralphex/progress/progress-example.txt", self.log(
                    f"--- task iteration 73 ---\n[26-10-08 09:02:00] Task 1 ({title}) is done.\n"
                    "Completed: 2026-10-08 09:03:00\n"))
                report = P.report(self.args())
                task = report["tasks"][0]
                self.assertEqual(task["outcome"], "completed")
                self.assertEqual(task["iterations"][0]["task_number"], 1)
                self.assertEqual([e["task_number"] for e in task["iterations"][0]["task_evidence"]], [1])
                self.assertEqual(task["usage"]["total"], 13)
                self.assertFalse(any(task["number"] is None for task in report["tasks"]))

    def test_report_completion_chains_after_title_preserve_span_boundaries(self):
        self.claude()
        variants = (
            "Task 1 (Compare Task 2 and Task 3 behavior) is done and I did Task 2.",
            "Task 1 (Compare Task 2, Task 3 behavior) is finished, Task 2 is completed.",
            "Task 1 (Compare (Task 2, Task 3) behavior) is done. I did Task 2.",
        )
        for text in variants:
            with self.subTest(text=text):
                self.write(".ralphex/progress/progress-example.txt", self.log(
                    f"--- task iteration 73 ---\n[26-10-08 09:02:00] {text}\n"
                    "Completed: 2026-10-08 09:03:00\n"))
                report = P.report(self.args())
                unknown = next(task for task in report["tasks"] if task["number"] is None)
                iteration = unknown["iterations"][0]
                self.assertEqual(iteration["task_identity"], "ambiguous")
                self.assertEqual([e["task_number"] for e in iteration["task_evidence"]], [1, 2])
                self.assertEqual(unknown["usage"]["total"], 13)
        self.write(".ralphex/progress/progress-example.txt", self.log(
            "--- task iteration 73 ---\n[26-10-08 09:02:00] Task 1 is done; "
            "the examples say `and I did Task 2` and \"Task 2 done, I did Task 3\".\n"
            "Completed: 2026-10-08 09:03:00\n"))
        report = P.report(self.args())
        self.assertEqual(report["tasks"][0]["iterations"][0]["task_number"], 1)
        self.assertEqual([e["task_number"] for e in report["tasks"][0]["iterations"][0]["task_evidence"]], [1])


    def test_russian_statuses_and_completion_precedence(self):
        self.claude()
        variants = ("Task 2 выполнен", "Task2 выполнена", "Task 2 завершён",
                    "Task2 завершена", "Task 2 завершен", "Task 2 complete")
        for text in variants:
            with self.subTest(text=text):
                self.write(".ralphex/progress/progress-example.txt", self.log(
                    "--- task iteration 99 ---\n[26-10-08 09:01:00] Выбран Task 3: Ошибочный выбор\n"
                    "Выбрана Task2: Исправленный выбор\n" + text +
                    "\nCompleted: 2026-10-08 09:03:00\n"))
                report = P.report(self.args())
                iteration = report["tasks"][1]["iterations"][0]
                self.assertEqual((iteration["task_number"], iteration["outcome"]), (2, "completed"))
                self.assertEqual(iteration["task_identity"], "explicit-progress")

    def test_russian_guards_titles_and_chains(self):
        negatives = ("Task1 остаётся незавершённым", "Task1 не начат",
                     "К Task1 не перехожу", "Task1 будет завершена",
                     "Task1 завершена?", "Task1 завершена только если проверки проходят",
                     "Task1 завершена, когда пройдут проверки", "Task1 завершена не полностью",
                     "«Task1 завершена»", "“Task1 завершена”",
                     "```text\nTask1 завершена\n```", "Выбран Task1 не будет",
                     "Если Task1 завершена, Task2 выполнен")
        self.claude()
        for text in negatives:
            with self.subTest(text=text):
                self.write(".ralphex/progress/progress-example.txt", self.log(
                    "--- task iteration 99 ---\n[26-10-08 09:01:00] " + text +
                    "\nCompleted: 2026-10-08 09:03:00\n"))
                report = P.report(self.args())
                unknown = next(t for t in report["tasks"] if t["number"] is None)
                self.assertEqual(unknown["iterations"][0]["task_identity"], "unknown")
                self.assertEqual(report["run"]["attribution_completeness"], "partial")
        for text in ("Task1 (Исправить не найденные ошибки и Task2) завершён",
                     "Выбрана Task1: Если встречается слово не"):
            with self.subTest(text=text):
                self.assertEqual(P.task_progress(text)["task_number"], 1)
        self.write(".ralphex/progress/progress-example.txt", self.log(
            "--- task iteration 99 ---\n[26-10-08 09:01:00] "
            "Task1 (Сравнить Task2 и Task3) завершён и Task2 выполнена\n"
            "Completed: 2026-10-08 09:03:00\n"))
        unknown = next(t for t in P.report(self.args())["tasks"] if t["number"] is None)
        self.assertEqual(unknown["iterations"][0]["task_identity"], "ambiguous")

    def test_all_tasks_signal_requires_safe_identity_and_never_overrides_failure(self):
        variants = (
            ("Выбрана Task2: Последняя\nTask2 готова к фиксации\n", "", 2, "completed"),
            ("Task2 готова к фиксации\n", "", 2, "completed"),
            ("Выбран Task1: Первый\nВыбран Task2: Второй\n", "", None, "unknown"),
            ("работаю\n", "", None, "unknown"),
            ("Выбран Task2: Последняя\n", "<<<RALPHEX:TASK_FAILED>>>\n", 2, "failed"),
        )
        for evidence, failure, identity, outcome in variants:
            with self.subTest(evidence=evidence, failure=failure):
                self.write(".ralphex/progress/progress-example.txt", self.log(
                    "--- task iteration 99 ---\n[26-10-08 09:01:00] " + evidence +
                    failure + "<<<RALPHEX:ALL_TASKS_DONE>>>\nCompleted: 2026-10-08 09:03:00\n"))
                iteration = next(b for b in P.parse_progress(self.progress, "UTC")["boundaries"]
                                 if b["kind"] == "iteration")
                self.assertEqual((iteration["task_number"], iteration["outcome"]), (identity, outcome))
        self.assertEqual(P.task_progress("Task8 готова к фиксации")["status"], "started")

    def test_legacy_review_links_actual_codex_parent_not_native_children(self):
        self.available_roots()
        self.write(".ralphex/progress/progress-example.txt", self.log(
            "--- claude review 0: all findings ---\n[26-10-08 09:02:00] findings\n"
            "Completed: 2026-10-08 09:03:00\n"))
        self.codex("review-parent", partial_history=False)
        self.jsonl("codex/sessions/rollout-review-child.jsonl", [
            {"timestamp": "2026-10-08T09:01:06Z", "type": "session_meta", "payload": {
                "id": "review-child", "session_id": "root-lineage", "cwd": self.root,
                "originator": "codex_exec", "source": {"subagent": {"thread_spawn": {
                    "parent_thread_id": "review-parent", "depth": 1, "agent_path": "/root/quality",
                    "agent_nickname": "Synthetic", "agent_role": None}}}}},
            {"timestamp": "2026-10-08T09:01:07Z", "type": "token_usage_record", "payload": {
                "usage": {"input_tokens": 4, "cached_input_tokens": 0, "cache_write_input_tokens": 0,
                          "output_tokens": 1, "total_tokens": 5}}}])
        report = P.report(self.args())
        review = report["reviews"][0]
        self.assertEqual((review["link_status"], review["review_provider"]), ("linked", "codex"))
        self.assertEqual(review["review_label"], "claude review 0: all findings")
        self.assertEqual(review["usage"]["total"], 15)
        child = next(c for c in report["other_in_run"] if c["session"] == "codex:review-child")
        self.assertTrue(child["is_subagent"])
        self.assertEqual(child["parent_lineage"], "review-parent")
        self.assertEqual(report["totals"]["unlinked"]["total"], 5)
        self.assertEqual(report["totals"]["attribution_completeness"], "observed")
        self.assertEqual(report["totals"]["observed_in_run"]["total"], 20)

    def test_custom_rounds_restart_and_missing_journal_are_partial_attribution(self):
        self.available_roots()
        self.write(".ralphex/progress/progress-example.txt", self.log(
            "--- custom external review ---\n--- custom review iteration 1 ---\n"
            "[26-10-08 09:01:00] result\n--- claude evaluating codex findings ---\n"
            "[26-10-08 09:02:00] evaluated\n--- custom review iteration 2 ---\n"
            "[26-10-08 09:03:00] result\nFailed: 2026-10-08 09:04:00\n"
            "--- restarted at 2026-10-08 09:05:00 ---\n"
            "--- custom external review ---\n--- custom review iteration 1 ---\n"
            "[26-10-08 09:06:00] result\nCompleted: 2026-10-08 09:07:00\n"))
        self.codex("unrelated-interactive", automation=False, partial_history=False)
        report = P.report(self.args())
        reviews = report["reviews"]
        self.assertEqual([r["review_round"] for r in reviews], [1, None, 2, 1])
        self.assertTrue(all(r["link_status"] == "unlinked" for r in reviews))
        self.assertTrue(all(r["review_provider"] is None and r["usage"]["total"] is None for r in reviews))
        self.assertTrue(all(r["attribution_completeness"] == "partial" for r in reviews))
        self.assertEqual(report["totals"]["unlinked_share"], 1)
        self.assertEqual(report["totals"]["observed_in_run"]["total"], 15)
        self.assertEqual(report["run"]["read_completeness"], "observed")
        self.assertEqual(report["run"]["attribution_completeness"], "partial")
        self.assertEqual(report["run"]["completeness"], "partial")
        self.assertTrue(all(left["end"] <= right["start"] for left, right in zip(reviews, reviews[1:])))

    def test_custom_review_actual_omp_session_has_low_confidence(self):
        self.write(".ralphex/progress/progress-example.txt", self.log(
            "--- custom external review ---\n--- custom review iteration 1 ---\n"
            "[26-10-08 09:02:00] result\nCompleted: 2026-10-08 09:03:00\n"))
        self.jsonl("omp/project/custom.jsonl", [
            {"type": "session", "id": "custom", "cwd": self.root, "timestamp": "2026-10-08T09:01:00Z"},
            {"type": "message", "timestamp": "2026-10-08T09:01:05Z", "message": {
                "role": "assistant", "model": "synthetic-omp", "provider": "synthetic-provider",
                "content": [], "usage": {"input": 3, "output": 2, "totalTokens": 5}}}])
        review = P.report(self.args())["reviews"][0]
        self.assertEqual((review["link_status"], review["review_provider"]), ("linked", "omp"))
        self.assertEqual(review["candidates"][0]["confidence"], "low")

    def test_provider_neutral_external_and_evaluation_labels(self):
        self.write(".ralphex/progress/progress-example.txt", self.log(
            "--- codex external review ---\n--- codex iteration 1 ---\n"
            "[26-10-08 09:01:00] findings\n--- claude evaluating codex findings ---\n"
            "[26-10-08 09:02:00] evaluated\nCompleted: 2026-10-08 09:03:00\n"))
        self.claude("sdk-external", "2026-10-08T09:00:05Z")
        self.codex("evaluation", "2026-10-08T09:01:05Z", partial_history=False)
        reviews = P.report(self.args())["reviews"]
        self.assertEqual([r["review_provider"] for r in reviews], ["claude", "codex"])
        self.assertEqual([r["review_role"] for r in reviews], ["external-review", "evaluation"])

    def test_identified_execution_missing_review_preserves_measured_sum(self):
        self.available_roots()
        self.write(".ralphex/progress/progress-example.txt", self.log(
            "--- task iteration 44 ---\n[26-10-08 09:01:00] Task1 complete\n"
            "--- custom external review ---\n[26-10-08 09:02:00] result\n"
            "Completed: 2026-10-08 09:03:00\n"))
        self.codex("execution", "2026-10-08T09:00:05Z", partial_history=False)
        report = P.report(self.args())
        self.assertEqual(report["tasks"][0]["attribution_completeness"], "observed")
        self.assertEqual(report["totals"]["observed_in_run"]["total"], 15)
        self.assertEqual(report["totals"]["usage_completeness"], "observed")
        self.assertEqual(report["totals"]["read_completeness"], "observed")
        self.assertEqual(report["totals"]["attribution_completeness"], "partial")
        self.assertEqual(report["totals"]["completeness"], "partial")
        self.assertEqual(report["reviews"][0]["usage_completeness"], "unknown")

    def test_last_task_eight_ready_requires_protocol_signal_to_complete(self):
        for signal, outcome in (("", "unknown"), ("<<<RALPHEX:ALL_TASKS_DONE>>>\n", "completed")):
            with self.subTest(signal=signal):
                self.write(".ralphex/progress/progress-example.txt", self.log(
                    "--- task iteration 10 ---\n[26-10-08 09:01:00] Выбрана Task8: Финальная\n"
                    "Task8 готова к фиксации\n" + signal + "Completed: 2026-10-08 09:03:00\n"))
                iteration = next(b for b in P.parse_progress(self.progress, "UTC")["boundaries"]
                                 if b["kind"] == "iteration")
                self.assertEqual((iteration["task_number"], iteration["outcome"]), (8, outcome))


    def test_native_source_exec_without_originator_remains_primary_candidate(self):
        self.write(".ralphex/progress/progress-example.txt", self.log(
            "--- claude review 0: all findings ---\n[26-10-08 09:02:00] findings\n"
            "Completed: 2026-10-08 09:03:00\n"))
        self.jsonl("codex/sessions/rollout-mode-only.jsonl", [
            {"timestamp": "2026-10-08T09:01:00Z", "type": "session_meta", "payload": {
                "id": "mode-only", "cwd": self.root, "source": "exec"}},
            {"timestamp": "2026-10-08T09:01:01Z", "type": "token_usage_record", "payload": {
                "usage": {"input_tokens": 2, "cached_input_tokens": 0, "cache_write_input_tokens": 0,
                          "output_tokens": 1, "total_tokens": 3}}}])
        review = P.report(self.args())["reviews"][0]
        self.assertEqual((review["link_status"], review["review_provider"]), ("linked", "codex"))
        self.assertEqual(review["candidates"][0]["session"], "codex:mode-only")


    def test_russian_selection_title_does_not_invent_completion_chain(self):
        self.write(".ralphex/progress/progress-example.txt", self.log(
            "--- task iteration 10 ---\n[26-10-08 09:01:00] "
            "Выбрана Task1: Проверить если Task2 завершена и Task3 выполнен\n"
            "Completed: 2026-10-08 09:03:00\n"))
        iteration = next(b for b in P.parse_progress(self.progress, "UTC")["boundaries"]
                         if b["kind"] == "iteration")
        self.assertEqual((iteration["task_number"], iteration["outcome"]), (1, "unknown"))
        self.assertEqual([e["task_number"] for e in iteration["task_evidence"]], [1])


    def test_russian_conditional_and_interrogative_particles_do_not_assign_task(self):
        self.available_roots()
        self.claude()
        variants = ("Task2 завершена была бы при успешных проверках", "Task2 завершена ли",
                    "Задача2 завершена была бы при успешных проверках", "Задача2 завершена ли")
        for text in variants:
            with self.subTest(text=text):
                self.write(".ralphex/progress/progress-example.txt", self.log(
                    "--- task iteration 10 ---\n[26-10-08 09:01:00] " + text +
                    "\nCompleted: 2026-10-08 09:03:00\n"))
                report = P.report(self.args())
                unknown = next(t for t in report["tasks"] if t["number"] is None)
                iteration = unknown["iterations"][0]
                self.assertEqual((iteration["task_identity"], iteration["outcome"]), ("unknown", "unknown"))
                self.assertEqual(report["tasks"][1]["iterations"], [])
                self.assertEqual(report["run"]["attribution_completeness"], "partial")
        for text in ("Task2 (Проверить частицы бы и ли) завершена",
                     "Задача2 (Проверить частицы бы и ли) завершена",
                     "Выбрана задача2 (Проверить частицы бы и ли)",
                     "Выбрана задача2: Проверить частицы бы и ли"):
            with self.subTest(title=text):
                self.assertEqual(P.task_progress(text)["task_number"], 2)

    def test_quoted_failure_examples_do_not_block_real_terminal_signal(self):
        self.claude()
        examples = ("```text\n<<<RALPHEX:TASK_FAILED>>>\n```",
                    "~~~text\n<<<RALPHEX:TASK_FAILED>>>\n~~~",
                    "`<<<RALPHEX:TASK_FAILED>>>`", '"<<<RALPHEX:TASK_FAILED>>>"',
                    "«<<<RALPHEX:TASK_FAILED>>>»")
        for example in examples:
            with self.subTest(example=example):
                self.write(".ralphex/progress/progress-example.txt", self.log(
                    "--- task iteration 10 ---\n[26-10-08 09:01:00] Выбрана задача2: Последняя\n" +
                    example + "\n<<<RALPHEX:ALL_TASKS_DONE>>>\nCompleted: 2026-10-08 09:03:00\n"))
                report = P.report(self.args())
                iteration = report["tasks"][1]["iterations"][0]
                self.assertEqual((iteration["task_number"], iteration["outcome"]), (2, "completed"))
                self.assertEqual(iteration["failures"], [])
                self.assertEqual(report["run"]["failures"], [])
        self.write(".ralphex/progress/progress-example.txt", self.log(
            "--- task iteration 10 ---\n[26-10-08 09:01:00] Выбрана задача2: Последняя\n"
            "<<<RALPHEX:TASK_FAILED>>>\n<<<RALPHEX:ALL_TASKS_DONE>>>\nCompleted: 2026-10-08 09:03:00\n"))
        iteration = P.report(self.args())["tasks"][1]["iterations"][0]
        self.assertEqual(iteration["outcome"], "failed")
        self.assertEqual(len(iteration["failures"]), 1)

    def test_singular_russian_task_label_consumer_precedence_and_mixed_chains(self):
        self.claude()
        self.write(".ralphex/progress/progress-example.txt", self.log(
            "--- task iteration 10 ---\n[26-10-08 09:01:00] Выбрана задача1: Ошибочный выбор\n"
            "Задача 2 завершена: Исправленный выбор\nCompleted: 2026-10-08 09:03:00\n"))
        iteration = P.report(self.args())["tasks"][1]["iterations"][0]
        self.assertEqual((iteration["task_number"], iteration["outcome"]), (2, "completed"))
        for text in ("Выбрана задача 7: Синтетическая задача", "Начата задача7",
                     "Задача 7 завершена: Синтетическое завершение",
                     "Задача7 (Сравнить Task2 и задача3) выполнена"):
            with self.subTest(text=text):
                self.assertEqual(P.task_progress(text)["task_number"], 7)
        for chain in ("Задача1 завершена и Task2 complete",
                      "Task1 complete, задача2 выполнена",
                      "Задача1 (Сравнить задачу2 и Task3) завершена; Task2 completed"):
            with self.subTest(chain=chain):
                self.write(".ralphex/progress/progress-example.txt", self.log(
                    "--- task iteration 10 ---\n[26-10-08 09:01:00] " + chain +
                    "\nCompleted: 2026-10-08 09:03:00\n"))
                unknown = next(t for t in P.report(self.args())["tasks"] if t["number"] is None)
                iteration = unknown["iterations"][0]
                self.assertEqual(iteration["task_identity"], "ambiguous")
                self.assertEqual([e["task_number"] for e in iteration["task_evidence"]], [1, 2])

    def test_russian_label_plural_ranges_and_unsafe_contexts_stay_unidentified(self):
        self.claude()
        variants = ("Задачи 1 и 2 завершены", "Задача 1-2 завершена",
                    "Выбрана задача 1-12: Диапазон", "Выбрана задача 1, 2: Список",
                    "Выбраны задачи 1 и 2", "Задача2 будет завершена", "Задача2 не завершена",
                    "Если задача2 завершена, Task1 complete", "«Задача2 завершена»",
                    "```text\nЗадача2 завершена\n```")
        for text in variants:
            with self.subTest(text=text):
                self.write(".ralphex/progress/progress-example.txt", self.log(
                    "--- task iteration 10 ---\n[26-10-08 09:01:00] " + text +
                    "\nCompleted: 2026-10-08 09:03:00\n"))
                unknown = next(t for t in P.report(self.args())["tasks"] if t["number"] is None)
                self.assertEqual(unknown["iterations"][0]["task_identity"], "unknown")


if __name__ == "__main__":
    unittest.main()
