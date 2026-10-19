"""Consumer-level CI tests: real read-only HTTP fixture, no forge credentials needed."""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ci_wait
import ship

SHA = "a" * 40
NEXT_SHA = "b" * 40
TOKEN = "fixture-token-DoNotExpose"
RUN_URL = "https://forge.example/owner/repo/actions/runs/42"


def run(state="success", ident=901, sha=SHA, workflow="ci.yml", ref="main", number=42):
    return {"id": ident, "index_in_repo": number, "commit_sha": sha, "status": state,
            "workflow_id": workflow, "prettyref": ref,
            "html_url": RUN_URL.rsplit("/", 1)[0] + "/" + str(number)}


def status(state="success", ident=1, context="ci", created="2026-10-19T10:00:00Z", target=RUN_URL):
    return {"id": ident, "context": context, "status": state, "created_at": created,
            "target_url": target, "description": "check " + state}


def pr(sha=SHA, base="main", state="open", merged=False):
    return {"state": state, "merged": merged, "head": {"sha": sha}, "base": {"ref": base}}


class Clock:
    def __init__(self):
        self.now = 0.0
        self.pauses = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.pauses.append(seconds)
        self.now += seconds


class Fixture(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.runs = []
        self.statuses = []
        self.pull = pr()
        self.route = self.default_route
        self.response_writer = None
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urllib.parse.urlsplit(self.path)
                params = urllib.parse.parse_qs(parsed.query)
                outer.requests.append({"method": self.command, "path": parsed.path,
                                       "params": params, "auth": self.headers.get("Authorization")})
                if outer.response_writer is not None:
                    try:
                        outer.response_writer(self.connection)
                    except OSError:
                        pass  # The deadline supervisor deliberately closes this connection.
                    return
                code, body, headers = outer.route(parsed.path, params)
                raw = body if isinstance(body, bytes) else json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                for name, value in headers.items():
                    self.send_header(name, value)
                self.end_headers()
                self.wfile.write(raw)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.url = "http://127.0.0.1:" + str(self.server.server_port)
        self.env = {"FORGEJO_URL": self.url, "FORGEJO_TOKEN": TOKEN}
        self.clock = Clock()

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def default_route(self, path, params):
        if path.endswith("/pulls/7"):
            return 200, self.pull, {}
        start = (int(params.get("page", [1])[0]) - 1) * 50
        if path.endswith("/actions/runs"):
            return 200, {"workflow_runs": self.runs[start:start + 50], "total_count": len(self.runs)}, {}
        if "/statuses/" in path:
            return 200, self.statuses[start:start + 50], {"X-Total-Count": str(len(self.statuses))}
        return 404, {"message": "unexpected request"}, {}

    def args(self, *flags, workflow=False):
        mode = ["--sha", SHA, "--ref", "main", "--workflow", "deploy.yml"] if workflow else ["--pr", "7", "--base", "main"]
        return ship.build_parser().parse_args(["wait-ci", "--owner", "owner", "--repo", "repo", *mode, *flags])

    def wait(self, *flags, workflow=False):
        return ci_wait.wait_ci(self.args(*flags, workflow=workflow), self.env, self.clock, self.clock.sleep)


class TestGate(Fixture):
    def test_requires_both_sources_and_exact_sha(self):
        self.runs = [run("success"), run("failure", 902, sha=NEXT_SHA, number=43)]
        self.statuses = [status("pending")]
        result = self.wait("--once")
        self.assertEqual(result["status"], "pending")
        self.assertNotIn("accepted_head", result)
        self.statuses = [status("success")]
        result = self.wait("--once")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["accepted_head"], SHA)
        self.assertEqual(result["checked_sha"], SHA)
        self.assertEqual(len(result["evidence"]["runs"]), 1)
        self.assertTrue(all(r["method"] == "GET" for r in self.requests))
        self.assertTrue(all(r["auth"] == "token " + TOKEN for r in self.requests))
        self.assertEqual(self.requests[1]["params"]["head_sha"], [SHA])
        self.assertTrue(any(r["path"].endswith("/statuses/" + SHA) for r in self.requests))

    def test_one_source_can_be_empty_but_not_both(self):
        self.statuses = [status()]
        self.assertEqual(self.wait("--once")["status"], "success")
        self.statuses = []
        self.runs = [run("skipped")]
        self.assertEqual(self.wait("--once")["status"], "success")
        self.runs = []
        result = self.wait("--once")
        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["checks_guard"]["state"], "waiting")
        self.assertNotIn("accepted_head", result)

    def test_all_run_failures_count_separate_success_does_not_replace(self):
        self.runs = [run("failure"), run("success", 902, number=43)]
        result = self.wait()
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["evidence"]["runs"][0]["id"], 901)
        self.assertEqual(result["evidence"]["runs"][0]["index_in_repo"], 42)
        self.runs[0]["status"] = "cancelled"
        self.assertEqual(self.wait()["status"], "fail")

    def test_pending_and_unknown_states_never_pass(self):
        for state in ("waiting", "running", "blocked", "unknown", "future-status"):
            with self.subTest(run_state=state):
                self.runs = [run(state)]
                self.assertEqual(self.wait("--once")["status"], "pending")
        self.runs = [run()]
        for state in ("pending", "future-state"):
            self.statuses = [status(state)]
            self.assertEqual(self.wait("--once")["status"], "pending")
        for state in ("failure", "warning", "error"):
            self.statuses = [status(state)]
            self.assertEqual(self.wait("--once")["status"], "fail")

    def test_latest_created_status_wins_not_id_or_list_order(self):
        self.statuses = [status("failure", 999), status("success", 2, created="2026-10-19T10:00:01Z")]
        result = self.wait("--once")
        self.assertEqual(result["status"], "success")
        self.assertEqual([s["id"] for s in result["evidence"]["statuses"]], [2])
        self.statuses.reverse()
        self.assertEqual(self.wait("--once")["status"], "success")
        self.statuses.append(status("pending", 3, context="external"))
        self.assertEqual(self.wait("--once")["status"], "pending")

    def test_timestamp_compares_offsets_and_preserves_fractional_precision(self):
        self.statuses = [status("failure", 1, created="2026-10-19T12:00:00+02:00"),
                         status("success", 2, created="2026-10-19T10:00:00.100Z")]
        self.assertEqual(self.wait("--once")["status"], "success")

    def test_same_second_needs_matching_terminal_web_run(self):
        self.runs = [run()]
        self.statuses = [status("pending", 1), status("success", 2)]
        self.assertEqual(self.wait("--once")["status"], "success")
        # Database ID 901 is not the web run number 42.
        for target in (RUN_URL.replace("42", "901"), RUN_URL.replace("forge.example", "other.example"),
                       "https://external.example/build/42", None):
            self.statuses[1]["target_url"] = target
            self.assertEqual(self.wait("--once")["status"], "pending", target)
        self.statuses[1]["target_url"] = RUN_URL + "/jobs/0"
        self.assertEqual(self.wait("--once")["status"], "success")
        self.statuses[1]["target_url"] = "/owner/repo/actions/runs/42/jobs/0"
        self.assertEqual(self.wait("--once")["status"], "success")
        self.statuses[1]["target_url"] = RUN_URL
        self.runs[0]["status"] = "running"
        self.assertEqual(self.wait("--once")["status"], "pending")

    def test_failure_beats_success_ties_and_unlinked_failure_cannot_disappear(self):
        self.runs = [run()]
        self.statuses = [status("success", 1), status("failure", 2)]
        self.assertEqual(self.wait("--once")["status"], "fail")
        self.statuses.append(status("pending", 3))
        self.assertEqual(self.wait("--once")["status"], "fail")
        self.statuses[1]["target_url"] = "https://external.example/build/1"
        self.assertNotEqual(self.wait("--once")["status"], "success")

    def test_pending_then_success_uses_backoff(self):
        default = self.default_route

        def route(path, params):
            self.runs = [run("running" if self.clock.now < 75 else "success")]
            return default(path, params)

        self.route = route
        result = self.wait()
        self.assertEqual(result["status"], "success")
        self.assertEqual(self.clock.pauses, [30, 45])
        self.assertEqual(result["elapsed"], 75)

    def test_timeout_caps_sleep_and_interval(self):
        self.runs = [run("running")]
        result = self.wait("--timeout", "500", "--interval", "100")
        self.assertEqual(result["status"], "timeout")
        self.assertEqual(self.clock.pauses, [100, 120, 120, 120, 40])
        self.assertEqual(result["elapsed"], 500)
        self.assertNotIn("accepted_head", result)

    def test_no_checks_returns_original_guard_not_acceptance(self):
        result = self.wait()
        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["reason"], "no-checks")
        self.assertEqual(result["checks_guard"], {"state": "no-checks", "elapsed": 60, "seconds": 60})
        self.assertEqual(result["checked_sha"], SHA)
        self.assertEqual(self.clock.pauses, [30, 30])
        self.assertNotIn("accepted_head", result)

    def test_total_deadline_beats_empty_guard(self):
        result = self.wait("--timeout", "40")
        self.assertEqual(result["status"], "timeout")
        self.assertEqual(result["elapsed"], 40)
        self.assertNotIn("accepted_head", result)

    def test_guard_only_detects_even_failed_checks_without_ci_acceptance(self):
        self.runs = [run("failure")]
        result = self.wait("--guard-only")
        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["reason"], "checks-detected")
        self.assertEqual(result["checks_guard"]["state"], "checks-detected")
        self.assertEqual(result["checked_sha"], SHA)
        self.assertNotIn("accepted_head", result)
        self.assertEqual(self.clock.pauses, [])
        self.runs = []
        self.assertEqual(self.wait("--guard-only")["checks_guard"]["state"], "no-checks")


class TestPagination(Fixture):
    def test_both_sources_fully_page_before_reduction(self):
        self.runs = [run(ident=i, number=i) for i in range(1, 52)]
        self.statuses = [status(ident=i, context="c" + str(i)) for i in range(1, 52)]
        self.statuses[-1]["status"] = "failure"
        result = self.wait("--once")
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["sources"]["runs"]["pages"], 2)
        self.assertEqual(result["sources"]["statuses"]["pages"], 2)
        self.assertEqual(len(result["evidence"]["runs"]), 51)
        self.assertEqual(len(result["evidence"]["statuses"]), 51)

    def test_failed_late_page_discards_even_visible_failure(self):
        self.runs = [run("failure", i, number=i) for i in range(1, 51)]
        default = self.default_route

        def route(path, params):
            if path.endswith("/actions/runs") and params["page"] == ["2"]:
                return 500, {"message": TOKEN}, {}
            return default(path, params)

        self.route = route
        result = self.wait("--once")
        self.assertEqual(result["status"], "pending")
        self.assertFalse(result["sources"]["runs"]["complete"])
        self.assertEqual(result["evidence"]["runs"], [])
        self.assertNotIn(TOKEN, json.dumps(result))
        self.assertNotIn("checked_sha", result)

    def test_status_page_error_prevents_success(self):
        self.runs = [run()]
        self.statuses = [status(ident=i) for i in range(1, 51)]
        default = self.default_route

        def route(path, params):
            if "/statuses/" in path and params["page"] == ["2"]:
                return 502, b"not JSON " + TOKEN.encode(), {}
            return default(path, params)

        self.route = route
        result = self.wait("--once")
        self.assertEqual(result["status"], "pending")
        self.assertFalse(result["sources"]["statuses"]["complete"])
        self.assertNotIn("accepted_head", result)

    def test_late_page_error_can_recover_only_on_a_new_complete_snapshot(self):
        self.runs = [run(ident=i, number=i) for i in range(1, 52)]
        default = self.default_route

        def route(path, params):
            if path.endswith("/actions/runs") and params["page"] == ["2"] and self.clock.now < 30:
                return 503, {"message": TOKEN}, {}
            return default(path, params)

        self.route = route
        result = self.wait()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["elapsed"], 30)
        self.assertEqual(result["sources"]["runs"]["count"], 51)
        self.assertEqual(len(result["evidence"]["runs"]), 51)
        self.assertEqual(result["accepted_head"], SHA)

    def test_server_capped_pages_use_total_and_next_without_following_link(self):
        items = [run(ident=i, number=i) for i in range(1, 4)]
        default = self.default_route

        def route(path, params):
            if path.endswith("/actions/runs"):
                page = int(params["page"][0])
                if page == 1:
                    return 200, {"workflow_runs": items[:2], "total_count": 3}, {
                        "Link": '<https://evil.invalid/stolen>; rel="next"'}
                return 200, {"workflow_runs": items[2:], "total_count": 3}, {}
            return default(path, params)

        self.route = route
        result = self.wait("--once")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["sources"]["runs"]["pages"], 2)
        self.assertTrue(all(r["path"].startswith("/api/v1/repos/owner/repo/") for r in self.requests))

    def test_duplicate_pages_or_truncated_total_never_pass(self):
        default = self.default_route
        for batch in ([run()], []):
            def route(path, params):
                if path.endswith("/actions/runs"):
                    rows = [run()] if params["page"] == ["1"] else batch
                    return 200, {"workflow_runs": rows, "total_count": 2}, {}
                return default(path, params)
            self.route = route
            result = self.wait("--once")
            self.assertEqual(result["status"], "pending")
            self.assertFalse(result["sources"]["runs"]["complete"])

    def test_malformed_identity_timestamp_and_envelope_are_pending(self):
        for broken in ({"commit_sha": None}, {"commit_sha": "a" * 7}, {"status": {"bad": "shape"}}):
            self.runs = [{**run(), **broken}]
            self.assertEqual(self.wait("--once")["status"], "pending")
        self.runs = [run()]
        self.statuses = [status(created="not-a-date")]
        self.assertEqual(self.wait("--once")["status"], "pending")
        self.statuses = [status(created="2026-10-19T10:00:00")]
        self.assertEqual(self.wait("--once")["status"], "pending")
        self.statuses = [{**status(), "status": {"bad": "shape"}}]
        self.assertEqual(self.wait("--once")["status"], "pending")
        default = self.default_route
        self.route = lambda path, params: (200, [], {}) if path.endswith("/actions/runs") else default(path, params)
        self.assertEqual(self.wait("--once")["status"], "pending")


class TestPRLifecycle(Fixture):
    def test_head_change_after_pass_discards_old_acceptance_and_reevaluates(self):
        self.runs = [run(), run("failure", 902, sha=NEXT_SHA, number=43)]
        default = self.default_route
        reads = 0

        def route(path, params):
            nonlocal reads
            if path.endswith("/pulls/7"):
                reads += 1
                return 200, pr(SHA if reads == 1 else NEXT_SHA), {}
            return default(path, params)

        self.route = route
        result = self.wait()
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["sha"], NEXT_SHA)
        self.assertNotIn("accepted_head", result)
        self.assertEqual(result["head_changes"], [{"from": SHA, "to": NEXT_SHA, "elapsed": 0}])
        self.assertEqual(result["evidence"]["runs"][0]["id"], 902)
        queried = [r["params"]["head_sha"][0] for r in self.requests if r["path"].endswith("/actions/runs")]
        self.assertEqual(queried, [SHA, NEXT_SHA])

    def test_once_changed_head_never_returns_old_evidence_or_checked_sha(self):
        self.runs = [run()]
        default = self.default_route
        reads = 0

        def route(path, params):
            nonlocal reads
            if path.endswith("/pulls/7"):
                reads += 1
                return 200, pr(SHA if reads == 1 else NEXT_SHA), {}
            return default(path, params)

        self.route = route
        result = self.wait("--once")
        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["sha"], NEXT_SHA)
        self.assertEqual(result["evidence"]["runs"], [])
        self.assertNotIn("checked_sha", result)
        self.assertNotIn("accepted_head", result)

    def test_head_changes_reset_empty_guard_not_total_deadline(self):
        default = self.default_route

        def route(path, params):
            self.pull = pr(SHA if self.clock.now < 30 else NEXT_SHA)
            return default(path, params)

        self.route = route
        result = self.wait("--timeout", "80")
        self.assertEqual(result["status"], "timeout")
        self.assertEqual(result["elapsed"], 80)
        self.assertEqual(result["head_changes"][0]["elapsed"], 30)
        self.assertNotIn("accepted_head", result)

    def test_head_moving_forever_cannot_extend_deadline(self):
        self.runs = [run("running"), run("running", 902, sha=NEXT_SHA)]
        default = self.default_route
        reads = 0

        def route(path, params):
            nonlocal reads
            self.clock.now += 1
            if path.endswith("/pulls/7"):
                reads += 1
                return 200, pr(SHA if reads % 2 else NEXT_SHA), {}
            return default(path, params)

        self.route = route
        result = self.wait("--timeout", "10")
        self.assertEqual(result["status"], "timeout")
        self.assertLessEqual(result["elapsed"], 10)
        self.assertNotIn("accepted_head", result)

    def test_closed_merged_retargeted_or_unknown_pr_does_not_pass(self):
        self.runs = [run()]
        for pull in (pr(state="closed"), pr(merged=True), pr(base="release")):
            self.pull = pull
            self.assertEqual(self.wait("--once")["status"], "fail")
        self.pull = pr(state="future")
        self.assertEqual(self.wait("--once")["status"], "pending")

    def test_final_pr_error_blocks_pass_and_guard_handoff(self):
        self.runs = [run()]
        default = self.default_route
        reads = 0

        def route(path, params):
            nonlocal reads
            if path.endswith("/pulls/7"):
                reads += 1
                if reads % 2 == 0:
                    return 503, {"message": TOKEN}, {}
            return default(path, params)

        self.route = route
        result = self.wait("--once")
        self.assertEqual(result["status"], "pending")
        self.assertFalse(result["sources"]["pr"]["complete"])
        self.assertNotIn("checked_sha", result)
        self.assertNotIn("accepted_head", result)

    def test_deadline_includes_source_fetching_not_just_sleeps(self):
        self.runs = [run()]
        default = self.default_route

        def route(path, params):
            self.clock.now += 3
            return default(path, params)

        self.route = route
        result = self.wait("--timeout", "5")
        self.assertEqual(result["status"], "timeout")
        self.assertNotIn("accepted_head", result)
        self.assertEqual(self.clock.pauses, [])

    def test_stable_new_head_can_pass_without_reusing_old_sha(self):
        self.runs = [run(), run(ident=902, sha=NEXT_SHA, number=43)]
        default = self.default_route
        reads = 0

        def route(path, params):
            nonlocal reads
            if path.endswith("/pulls/7"):
                reads += 1
                return 200, pr(SHA if reads == 1 else NEXT_SHA), {}
            return default(path, params)

        self.route = route
        result = self.wait()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["accepted_head"], NEXT_SHA)
        self.assertEqual(result["checked_sha"], NEXT_SHA)
        self.assertEqual([r["id"] for r in result["evidence"]["runs"]], [902])


class TestSelectedWorkflows(Fixture):
    def test_only_selected_workflows_exact_sha_and_ref_count_no_statuses(self):
        self.runs = [run(workflow="deploy.yml"), run("failure", 902, workflow="ci.yml"),
                     run("failure", 903, sha=NEXT_SHA, workflow="deploy.yml"),
                     run("failure", 904, ref="other", workflow="deploy.yml")]
        self.statuses = [status("failure")]
        result = self.wait(workflow=True)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["reason"], "selected workflows completed")
        self.assertEqual([r["id"] for r in result["evidence"]["runs"]], [901])
        self.assertEqual(self.requests[0]["params"]["ref"], ["refs/heads/main"])
        self.assertTrue(all(r["path"].endswith("/actions/runs") for r in self.requests))
        self.assertNotIn("accepted_head", result)

    def test_every_selector_required_and_missing_waits_to_deadline(self):
        self.runs = [run(workflow="deploy.yml")]
        result = self.wait("--workflow", "publish.yaml", "--timeout", "40", workflow=True)
        self.assertEqual(result["status"], "timeout")
        self.assertEqual(result["evidence"]["missing_workflows"], ["publish.yaml"])
        self.assertNotIn("checks_guard", result)
        self.clock = Clock()
        self.runs.append(run(ident=902, workflow="publish.yaml"))
        self.assertEqual(self.wait("--workflow", "publish.yaml", workflow=True)["status"], "success")

    def test_selected_skipped_cancelled_failure_and_failed_separate_run_fail(self):
        for state in ("skipped", "failure", "cancelled"):
            self.runs = [run(state, workflow="deploy.yml"), run(ident=902, workflow="deploy.yml")]
            result = self.wait(workflow=True)
            self.assertEqual(result["status"], "fail", state)
        self.runs = [run("running", workflow="deploy.yml")]
        self.assertEqual(self.wait("--once", workflow=True)["status"], "pending")

    def test_display_titles_do_not_match_file_selector(self):
        self.runs = [{**run(workflow="other.yml"), "title": "deploy.yml"}]
        result = self.wait("--once", workflow=True)
        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["evidence"]["missing_workflows"], ["deploy.yml"])

    def test_non_main_full_branch_ref_and_pagination(self):
        self.runs = [run(ident=i, number=i, workflow="deploy.yml", ref="release/v2") for i in range(1, 52)]
        self.runs[-1]["status"] = "failure"
        result = self.wait("--ref", "refs/heads/release/v2", workflow=True)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["ref"], "refs/heads/release/v2")
        self.assertEqual(result["sources"]["runs"]["pages"], 2)
        self.assertEqual(self.requests[0]["params"]["ref"], ["refs/heads/release/v2"])


class TestSecurityAndCLI(Fixture):
    def cli(self, *flags, workflow=False, env=None):
        args = self.args(*flags, workflow=workflow)
        command = [sys.executable, str(HERE / "ship.py"), "wait-ci", "--owner", args.owner, "--repo", args.repo]
        if workflow:
            command += ["--sha", args.sha, "--ref", args.ref]
            for selector in args.workflow:
                command += ["--workflow", selector]
        else:
            command += ["--pr", str(args.pr), "--base", args.base]
        command += ["--once", "--timeout", str(args.timeout)]
        clean_env = {"PATH": "", **(self.env if env is None else env)}
        with tempfile.TemporaryDirectory() as cwd:
            return subprocess.run(command, cwd=cwd, env=clean_env, text=True, capture_output=True, timeout=10)

    def test_cli_outside_git_without_git_and_main_is_valid(self):
        self.runs = [run(workflow="deploy.yml")]
        result = self.cli(workflow=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "success")
        self.runs = [run()]
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["accepted_head"], SHA)

    def test_missing_credentials_and_auth_errors_exit_two_without_secrets(self):
        for env in ({}, {"FORGEJO_URL": self.url}, {"FORGEJO_TOKEN": TOKEN}):
            result = self.cli(env=env)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn(TOKEN, result.stderr + result.stdout)
        self.route = lambda path, params: (401, {"message": TOKEN}, {})
        result = self.cli()
        self.assertEqual(result.returncode, 2)
        self.assertIn("401", result.stderr)
        self.assertNotIn(TOKEN, result.stderr + result.stdout)
        self.assertEqual(result.stdout, "")

    def test_reflected_token_and_url_credentials_never_appear(self):
        self.statuses = [{**status("failure"), "description": "server echoed " + TOKEN,
                          "target_url": "https://user:" + TOKEN + "@forge.example/build/1?token=" + TOKEN + "#" + TOKEN}]
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(TOKEN, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["evidence"]["statuses"][0]["target_url"], "https://forge.example/build/1")
        self.assertIn("[REDACTED]", payload["evidence"]["statuses"][0]["description"])

    def test_all_redirects_rejected_without_forwarding_auth_or_echoing_location(self):
        for destination in (self.url + "/stolen?secret=" + TOKEN, "https://other.invalid/stolen?secret=" + TOKEN):
            self.requests.clear()
            self.route = lambda path, params: (302, {"message": TOKEN}, {"Location": destination})
            result = self.wait("--once")
            self.assertEqual(result["status"], "pending")
            self.assertEqual(len(self.requests), 1)
            self.assertNotIn(TOKEN, json.dumps(result))
            self.assertIn("redirect rejected", result["sources"]["pr"]["error"])

    def test_invalid_json_and_network_failure_are_diagnostic_not_acceptance(self):
        self.route = lambda path, params: (200, b"invalid json " + TOKEN.encode(), {})
        result = self.wait("--once")
        self.assertEqual(result["status"], "pending")
        self.assertNotIn(TOKEN, json.dumps(result))
        self.assertIn("invalid JSON", result["sources"]["pr"]["error"])
        # An invalid TLS handshake against the HTTP fixture exercises real transport failure.
        self.env["FORGEJO_URL"] = self.url.replace("http:", "https:")
        result = self.wait("--once")
        self.assertEqual(result["status"], "pending")
        self.assertIn("network/TLS", result["sources"]["pr"]["error"])

    def test_invalid_urls_paths_and_nonfinite_numbers_rejected_before_request(self):
        for url in ("http://forge.example", "https://user:" + TOKEN + "@forge.example", "https://forge.example?token=" + TOKEN,
                    "https://forge.example/#secret", "https://forge.example/../x", "https://forge.example/%2e%2e", "file:///tmp/x",
                    "https://forge.example\\@other.example", "https://forge.example:wrong", "https://forge.example\nother"):
            with self.subTest(url=url), self.assertRaises(ci_wait.UsageError):
                ci_wait.wait_ci(self.args("--once"), {**self.env, "FORGEJO_URL": url}, self.clock, self.clock.sleep)
        for flags in (("--owner", ".."), ("--repo", "a/b"), ("--repo", "%2e%2e"), ("--base", "main..other"),
                      ("--interval", "nan"), ("--timeout", "inf"), ("--interval", "0"), ("--timeout", "-1")):
            with self.subTest(flags=flags), self.assertRaises(ci_wait.UsageError):
                self.wait(*flags)
        for flags in (("--workflow", "Deploy"), ("--workflow", "../deploy.yml"), ("--guard-only",)):
            with self.subTest(flags=flags), self.assertRaises(ci_wait.UsageError):
                self.wait(*flags, workflow=True)
        self.assertEqual(self.requests, [])

    def test_environment_errors_do_not_discover_git_or_user_config(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(ship, "find_root", side_effect=AssertionError("git discovery")):
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = ship.main(["wait-ci", "--owner", "owner", "--repo", "repo", "--pr", "7", "--base", "main", "--once"])
        self.assertEqual(code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("FORGEJO_URL", stderr.getvalue())


class TestAbsoluteDeadline(Fixture):
    # Fresh interpreter/CLI imports are part of the deadline. Leave startup
    # room, but keep the injected 9–11s stalls well beyond the 4s wall bound.
    WAIT_TIMEOUT = 2.0
    WALL_LIMIT = 4.0
    BLOCK_SECONDS = 10.0
    TRICKLE_STEPS = 60
    TRICKLE_GAP = 0.15

    def bounded_wait(self):
        children = []
        original = subprocess.Popen

        def launch(*args, **kwargs):
            child = original(*args, **kwargs)
            children.append(child)
            return child

        started = time.monotonic()
        with patch.object(ci_wait.subprocess, "Popen", side_effect=launch):
            result = ci_wait.wait_ci(self.args("--timeout", str(self.WAIT_TIMEOUT), "--once"), self.env)
        elapsed = time.monotonic() - started
        self.assertEqual(result["status"], "timeout")
        self.assertNotIn("accepted_head", result)
        self.assertNotIn(TOKEN, json.dumps(result))
        self.assertLess(elapsed, self.WALL_LIMIT, "HTTP transport exceeded the absolute deadline")
        self.assertIn("absolute HTTP deadline", result["sources"]["pr"]["error"])
        self.assertTrue(children)
        for child in children:
            self.assertIsNotNone(child.poll(), "transport process must be reaped")
            self.assertTrue(child.stdin.closed)
            self.assertTrue(child.stdout.closed)
            self.assertNotIn(TOKEN, repr(child.args))
        return result

    def trickled_response(self, style):
        raw = json.dumps(pr()).encode()

        def write(connection):
            if style == "status":
                for byte in b"HTTP/1.1 200 " + b"O" * self.TRICKLE_STEPS + b"\r\n":
                    connection.sendall(bytes([byte]))
                    time.sleep(self.TRICKLE_GAP)
            else:
                connection.sendall(b"HTTP/1.1 200 OK\r\n")
            if style == "headers":
                for _ in range(self.TRICKLE_STEPS):
                    connection.sendall(b"X-Wait: " + TOKEN.encode() + b"\r\n")
                    time.sleep(self.TRICKLE_GAP)
            if style == "chunk":
                connection.sendall(b"Transfer-Encoding: chunked\r\n\r\n")
                for _ in range(self.TRICKLE_STEPS):
                    connection.sendall(b"0")
                    time.sleep(self.TRICKLE_GAP)
                connection.sendall(("%x\r\n" % len(raw)).encode() + raw + b"\r\n0\r\n\r\n")
            else:
                connection.sendall(("Content-Length: %d\r\n\r\n" % len(raw)).encode() + raw)

        self.response_writer = write

    def test_trickled_headers_cannot_extend_deadline(self):
        self.trickled_response("headers")
        self.bounded_wait()
        self.assertTrue(self.requests, "the worker must reach the slow HTTP peer")

    def test_trickled_status_line_cannot_extend_deadline(self):
        self.trickled_response("status")
        self.bounded_wait()
        self.assertTrue(self.requests, "the worker must reach the slow HTTP peer")

    def test_trickled_chunk_metadata_cannot_extend_deadline(self):
        self.trickled_response("chunk")
        self.bounded_wait()
        self.assertTrue(self.requests, "the worker must reach the slow HTTP peer")

    def blocked_transport(self, target):
        # Patch the actual socket/connect/TLS primitive inside the isolated
        # interpreter, not a production fallback or a parent-only mock.
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "entered-blocking-call"
            code = ("import http.client, socket, ssl, sys, time\n"
                    "from pathlib import Path\n"
                    "sys.path.insert(0, " + repr(str(HERE)) + ")\n"
                    "import ci_wait\n"
                    "original = " + target + "\n"
                    "def blocked(*args, **kwargs):\n"
                    "    Path(" + repr(str(marker)) + ").write_text('entered')\n"
                    "    time.sleep(" + repr(self.BLOCK_SECONDS) + ")\n"
                    "    return original(*args, **kwargs)\n"
                    + target + " = blocked\n"
                    "sys.exit(ci_wait.http_worker_main())\n")
            with patch.object(ci_wait, "HTTP_WORKER_COMMAND", (sys.executable, "-c", code)):
                self.bounded_wait()
            self.assertEqual(marker.read_text(), "entered")

    def test_blocked_resolution_cannot_extend_deadline(self):
        self.blocked_transport("socket.getaddrinfo")

    def test_blocked_connect_cannot_extend_deadline(self):
        self.blocked_transport("http.client.HTTPConnection.connect")

    def test_blocked_tls_cannot_extend_deadline(self):
        self.env["FORGEJO_URL"] = self.url.replace("http:", "https:")
        self.blocked_transport("ssl.SSLContext.wrap_socket")

    def test_actual_cli_returns_bounded_secret_safe_timeout(self):
        self.trickled_response("headers")
        command = [sys.executable, str(HERE / "ship.py"), "wait-ci", "--owner", "owner", "--repo", "repo",
                   "--pr", "7", "--base", "main", "--once", "--timeout", str(self.WAIT_TIMEOUT)]
        started = time.monotonic()
        with tempfile.TemporaryDirectory() as cwd:
            completed = subprocess.run(command, cwd=cwd, env={"PATH": "", **self.env},
                                       text=True, capture_output=True, timeout=self.BLOCK_SECONDS + self.WALL_LIMIT)
        elapsed = time.monotonic() - started
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn(TOKEN, completed.stdout + completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "timeout")
        self.assertIn("absolute HTTP deadline", result["sources"]["pr"]["error"])
        self.assertLess(elapsed, self.WALL_LIMIT)
        self.assertTrue(self.requests, "the CLI worker must reach the slow HTTP peer")


if __name__ == "__main__":
    unittest.main()
