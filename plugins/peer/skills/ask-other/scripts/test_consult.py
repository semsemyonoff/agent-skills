import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

import consult

SCRIPT = Path(__file__).with_name("consult.py")
CLAUDE_INIT = {"type": "system", "subtype": "init", "tools": ["Read", "Grep", "Glob"],
               "mcp_servers": [], "model": "observed-native-model"}


def claude_events(result="Findings with uncertainties"):
    return [CLAUDE_INIT, {"type": "result", "subtype": "success", "is_error": False, "result": result}]


def codex_events(result="Findings with uncertainties"):
    return [{"type": "thread.started", "thread_id": "fixture"}, {"type": "turn.started"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": result}},
            {"type": "turn.completed", "usage": {}}]


FAKE_CLI = r'''
import json, os, pathlib, signal, subprocess, sys, time, tomllib
args = sys.argv[1:]
target = pathlib.Path(sys.argv[0]).name
if args == ["--version"]:
    print(os.environ.get("FAKE_VERSION", "2.1.296" if target == "claude" else "0.162.1"))
    sys.exit(0)
if "--help" in args:
    flags = "--safe-mode --tools --allowedTools --disallowedTools --strict-mcp-config --mcp-config --settings --permission-mode --permission-prompts --no-session-persistence --no-chrome --disable-slash-commands --output-format --verbose --sandbox --json --ephemeral --ignore-rules --strict-config --config"
    print(flags.replace(os.environ.get("FAKE_MISSING_FLAG", "not-present"), ""))
    sys.exit(0)
names = json.loads(os.environ.get("FAKE_MCP_NAMES", "[]"))
base = {
    "features": {name: True for name in ("hooks", "apps", "plugins", "multi_agent", "multi_agent_v2", "code_mode", "memories")},
    "skills": {"include_instructions": True},
    "mcp_servers": {name: {"enabled": True, "command": "fixture-read-only-launcher",
                           "env": {"SECRET": "never-display-this"}} for name in names},
}
def deep_merge(base, overlay):
    for key, value in overlay.items():
        if isinstance(base.get(key), dict) and isinstance(value, dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base

# Match the researched native parser: split only the LHS on literal dots,
# parse only the RHS as TOML, replace repeated paths within the CLI layer,
# then recursively merge that complete layer over inherited native config.
cli_layer = {}
for index, arg in enumerate(args):
    if arg != "--config":
        continue
    path, raw = args[index + 1].split("=", 1)
    try:
        value = tomllib.loads("_value = " + raw)["_value"]
    except tomllib.TOMLDecodeError:
        value = raw.strip().strip("\"'")
    current = cli_layer
    segments = path.strip().split(".")
    for segment in segments[:-1]:
        current = current.setdefault(segment, {})
    current[segments[-1]] = value
effective = deep_merge(base, cli_layer)
# Native loading rejects a recognized key of the wrong type and ignores unknown keys.
valid = {"approval_policy": lambda v: v in ("untrusted", "on-failure", "on-request", "never"),
         "default_permissions": lambda v: type(v) is str, "web_search": lambda v: type(v) is str,
         "notify": lambda v: type(v) is list, "allow_login_shell": lambda v: type(v) is bool,
         "project_doc_max_bytes": lambda v: type(v) is int, "skills.include_instructions": lambda v: type(v) is bool}
flat = {key: cli_layer.get(key) for key in valid if "." not in key}
flat["skills.include_instructions"] = cli_layer.get("skills", {}).get("include_instructions")
for key, check in valid.items():
    if key != os.environ.get("FAKE_IGNORED_KEY") and flat[key] is not None and not check(flat[key]):
        print(f"invalid type in `{key}`", file=sys.stderr)
        sys.exit(1)
for name in names:
    assert effective["mcp_servers"][name]["command"] == "fixture-read-only-launcher"
    assert effective["mcp_servers"][name]["env"] == {"SECRET": "never-display-this"}
if args[:2] == ["features", "list"]:
    if os.environ.get("FAKE_FEATURES_FAIL"):
        sys.exit(1)
    if "FAKE_FEATURE_ROWS" in os.environ:
        print(os.environ["FAKE_FEATURE_ROWS"])
        sys.exit(0)
    registry = ("hooks", "apps", "plugins", "remote_plugin", "multi_agent", "multi_agent_v2", "code_mode",
                "shell_snapshot", "shell_snapshot_v2", "goals", "memories", "skill_mcp_dependency_install",
                "shell_tool")
    missing = os.environ.get("FAKE_UNKNOWN_FEATURE")
    stuck = os.environ.get("FAKE_STUCK_FEATURE")
    for name in registry:
        if name != missing:
            state = name == stuck or effective["features"].get(name, True)
            print(f"{name:<40} under development  {str(state).lower()}")
    sys.exit(0)
if args[:2] == ["mcp", "list"]:
    if os.environ.get("FAKE_BAD_INVENTORY"):
        print(os.environ["FAKE_BAD_INVENTORY"])
        sys.exit(0)
    rows = [{"name": name, "enabled": (effective["mcp_servers"][name]["enabled"] or bool(os.environ.get("FAKE_STUCK_MCP"))),
             "transport": {"type": "stdio", "command": effective["mcp_servers"][name]["command"],
                           "env": effective["mcp_servers"][name]["env"]}} for name in names]
    print(json.dumps(rows))
    sys.exit(0)
assert "--model" not in args and "--effort" not in args and "--ignore-user-config" not in args
assert "--bare" not in args and "--restricted" not in args
assert not any("bypass" in arg or "dangerously" in arg for arg in args)
if target == "claude":
    assert args[args.index("--tools") + 1] == "Read,Grep,Glob"
    assert args[args.index("--mcp-config") + 1] == '{"mcpServers":{}}'
    assert args[args.index("--permission-mode") + 1] == "dontAsk"
else:
    assert args[args.index("--sandbox") + 1] == "read-only"
    assert effective["approval_policy"] == "never"
    assert all(effective["features"][feature] is False for feature in ("hooks", "apps", "plugins", "multi_agent", "multi_agent_v2", "code_mode", "memories"))
    assert effective["skills"]["include_instructions"] is False
    assert "memory_tool" not in effective["features"] and "js_repl" not in effective["features"]
    assert all(effective["mcp_servers"][name]["enabled"] is False for name in names)
    assert set(effective["mcp_servers"]) == set(names)
with open(os.environ["FAKE_ATTEMPTS"], "a") as file:
    file.write("consultation\n")
if os.environ.get("FAKE_CHILD_PID"):
    child = subprocess.Popen([sys.executable, "-c", "import os,pathlib,signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); pathlib.Path(os.environ['FAKE_CHILD_READY']).write_text('ready') if os.environ.get('FAKE_CHILD_READY') else None; time.sleep(60)"])
    pathlib.Path(os.environ["FAKE_CHILD_PID"]).write_text(str(child.pid))
    time.sleep(60)
prompt = sys.stdin.read()
assert prompt.strip() and "Return findings and uncertainties" in prompt
if os.environ.get("FAKE_CAPTURE"):
    pathlib.Path(os.environ["FAKE_CAPTURE"]).write_text(json.dumps({"argv": args, "prompt": prompt, "native_model": os.environ.get("ANTHROPIC_MODEL"), "native_effort": os.environ.get("CLAUDE_CODE_EFFORT_LEVEL")}))
for event in json.loads(os.environ["FAKE_EVENTS"]):
    print(json.dumps(event), flush=True)
if os.environ.get("FAKE_TRAILER"):
    print(os.environ["FAKE_TRAILER"], flush=True)
if os.environ.get("FAKE_DIAGNOSTIC"):
    print(os.environ["FAKE_DIAGNOSTIC"], file=sys.stderr)
sys.exit(int(os.environ.get("FAKE_EXIT", "0")))
'''


def alive(pid):
    state = Path(f"/proc/{pid}/stat")
    if Path("/proc/self/stat").exists():
        try:
            return state.read_text().rsplit(")", 1)[1].split()[0] not in ("Z", "X")
        except FileNotFoundError:
            return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


@unittest.skipUnless(os.name == "posix", "POSIX process lifecycle")
class ConsultationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.project = self.root / "project"
        self.project.mkdir()
        (self.project / "source.py").write_text("one\ntwo\nthree\n")
        self.attempts = self.root / "attempts"
        for target in ("claude", "codex"):
            path = self.bin / target
            path.write_text(f"#!{sys.executable}\n" + FAKE_CLI)
            path.chmod(0o755)
        self.env = dict(os.environ, PATH=str(self.bin), FAKE_ATTEMPTS=str(self.attempts))

    def tearDown(self):
        self.tmp.cleanup()

    def command(self, target="claude", mode="debug", *extra):
        return [sys.executable, str(SCRIPT), "--target", target, "--mode", mode,
                "--project", str(self.project), *extra]

    def run_consult(self, target="claude", mode="debug", events=None, prompt="Selected problem", extra=(), **env):
        if events is None:
            events = claude_events() if target == "claude" else codex_events()
        process = subprocess.run(self.command(target, mode, *extra), input=prompt, text=True,
                                 capture_output=True, env=dict(self.env, FAKE_EVENTS=json.dumps(events), **env), timeout=10)
        return process, json.loads(process.stdout)

    def assert_failed(self, process, result, status="error"):
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(result["status"], status)
        self.assertIsNone(result["result"])
        self.assertFalse(result["consultation_completed"])

    def test_success_preserves_result_and_observed_model(self):
        text = "Evidence\nUncertainties: not tested."
        process, result = self.run_consult(events=claude_events(text))
        self.assertEqual(process.returncode, 0)
        self.assertEqual(result["result"], text)
        self.assertEqual(result["model"], "observed-native-model")
        self.assertEqual(self.attempts.read_text().splitlines(), ["consultation"])

    def test_native_model_and_effort_are_not_replaced(self):
        capture = self.root / "capture"
        process, result = self.run_consult(FAKE_CAPTURE=str(capture), ANTHROPIC_MODEL="native-choice",
                                          CLAUDE_CODE_EFFORT_LEVEL="native-effort")
        self.assertEqual(process.returncode, 0)
        captured = json.loads(capture.read_text())
        self.assertEqual(captured["native_model"], "native-choice")
        self.assertEqual(captured["native_effort"], "native-effort")
        self.assertNotIn("--model", captured["argv"])

    def test_check_does_not_consult_or_read_stdin(self):
        for target in ("claude", "codex"):
            with self.subTest(target=target):
                process, result = self.run_consult(target, extra=("--check",), prompt="")
                self.assertEqual(process.returncode, 0)
                self.assertTrue(result["check"])
                self.assertFalse(result["consultation_completed"])
                self.assertIsNone(result["result"])
                self.assertIsNone(result["model"])
        self.assertFalse(self.attempts.exists())

    def test_missing_cli_is_unavailable(self):
        process, result = self.run_consult(PATH=str(self.root / "absent"))
        self.assert_failed(process, result, "unavailable")
        self.assertFalse(self.attempts.exists())

    def test_missing_constraint_fails_before_model_call(self):
        process, result = self.run_consult(FAKE_MISSING_FLAG="--safe-mode")
        self.assert_failed(process, result, "unavailable")
        self.assertFalse(self.attempts.exists())

    def test_new_codex_version_is_not_pinned_out(self):
        process, result = self.run_consult("codex", FAKE_VERSION="9.9.9")
        self.assertEqual(process.returncode, 0)
        self.assertEqual(result["cli_version"], "9.9.9")

    def test_codex_feature_rows_must_be_unique_applied_and_false(self):
        rows = {name: f"{name}  stable  false" for name in consult.CODEX_DISABLED}
        for name, bad in (("hooks", "hooks  removed  false"), ("hooks", "hooks  sunset  false"),
                          ("hooks", "hooks  stable  true\nhooks  stable  false"),
                          ("hooks", "hooks  stable  false\nhooks  stable  true"),
                          ("hooks", "hooks  false"), ("hooks", "hooks  stable  off")):
            with self.subTest(bad=bad):
                output = "\n".join(bad if key == name else row for key, row in rows.items())
                self.assertEqual(consult.unconfirmed_features(output.encode()), [name])
        multiword = dict(rows, code_mode="code_mode  under development  false")
        self.assertEqual(consult.unconfirmed_features("\n".join(multiword.values()).encode()), [])
        self.assertEqual(consult.unconfirmed_features(b""), list(consult.CODEX_DISABLED))

    def test_unconfirmed_codex_feature_is_unavailable(self):
        for env in ({"FAKE_UNKNOWN_FEATURE": "code_mode"}, {"FAKE_STUCK_FEATURE": "hooks"}):
            with self.subTest(env=env):
                process, result = self.run_consult("codex", **env)
                self.assert_failed(process, result, "unavailable")
                self.assertIn(next(iter(env.values())), result["error"])
                self.assertFalse(self.attempts.exists())

    def test_codex_feature_inventory_failure_is_unavailable(self):
        for env in ({"FAKE_FEATURES_FAIL": "1"}, {"FAKE_FEATURE_ROWS": ""}):
            with self.subTest(env=env):
                process, result = self.run_consult("codex", **env)
                self.assert_failed(process, result, "unavailable")
                self.assertFalse(self.attempts.exists())

    def test_unrecognized_codex_key_is_unavailable(self):
        for key, _, _ in consult.CODEX_KEYS:
            with self.subTest(key=key):
                process, result = self.run_consult("codex", FAKE_IGNORED_KEY=key)
                self.assert_failed(process, result, "unavailable")
                self.assertIn(key, result["error"])
                self.assertFalse(self.attempts.exists())

    def test_codex_disables_inherited_mcp_and_does_not_guess_model(self):
        names = ["writer", "tracker", "team.service", "org/tool", "team:service", "service@org"]
        process, result = self.run_consult("codex", FAKE_MCP_NAMES=json.dumps(names))
        self.assertEqual(process.returncode, 0)
        self.assertEqual(result["disabled_mcp_count"], len(names))
        self.assertIsNone(result["model"])
        self.assertNotIn("never-display-this", process.stdout + process.stderr)

    def test_ignored_mcp_disable_refuses_before_consultation(self):
        for name in ("writer", "team.service", "org/tool", "team:service", "service@org"):
            with self.subTest(name=name):
                process, result = self.run_consult("codex", FAKE_MCP_NAMES=json.dumps([name]), FAKE_STUCK_MCP="1")
                self.assert_failed(process, result, "unavailable")
                self.assertFalse(self.attempts.exists())

    def test_invalid_inventory_refuses(self):
        for inventory in ('{}', '[{"name":"writer"}]', '[{"name":"x y","enabled":true}]', '[{"name":"x","enabled":true},{"name":"x","enabled":false}]'):
            with self.subTest(inventory=inventory):
                process, result = self.run_consult("codex", FAKE_BAD_INVENTORY=inventory)
                self.assert_failed(process, result, "unavailable")
        self.assertFalse(self.attempts.exists())

    def test_contradictory_claude_capabilities_refuse(self):
        for tools in (["Read"], ["Read", "Grep", "Glob", "Bash"], ["Read", "Grep", "Glob", "Agent"]):
            with self.subTest(tools=tools):
                process, result = self.run_consult(events=[dict(CLAUDE_INIT, tools=tools)])
                self.assert_failed(process, result)

    def test_mcp_claude_capability_refuses(self):
        process, result = self.run_consult(events=[dict(CLAUDE_INIT, mcp_servers=[{"name": "writer"}])])
        self.assert_failed(process, result)

    def test_empty_truncated_and_failed_output_never_approve(self):
        for target, stream in (("claude", claude_events()), ("codex", codex_events())):
            for events, trailer in (([], ""), (stream[:-1], ""), (stream, '{"type":'),
                                    (claude_events("") if target == "claude" else codex_events(""), "")):
                with self.subTest(target=target, events=events, trailer=trailer):
                    process, result = self.run_consult(target, events=events, FAKE_TRAILER=trailer)
                    self.assert_failed(process, result)

    def test_provider_failure_does_not_retry_or_leak_diagnostics(self):
        process, result = self.run_consult(events=[], FAKE_EXIT="42",
                                          FAKE_DIAGNOSTIC="rate limit SECRET=secret-value")
        self.assert_failed(process, result)
        self.assertIn("Provider limit", result["error"])
        self.assertNotIn("secret-value", process.stdout + process.stderr)
        self.assertEqual(self.attempts.read_text().splitlines(), ["consultation"])

    def test_claude_auth_error_result_is_not_a_consultation(self):
        events = [CLAUDE_INIT, {"type": "result", "subtype": "success", "is_error": True,
                               "terminal_reason": "api_error", "result": "Failed to authenticate: OAuth expired"}]
        process, result = self.run_consult(events=events)
        self.assert_failed(process, result)
        self.assertIn("authentication", result["error"])

    def test_empty_and_nonfinite_input_refuses_before_model_call(self):
        for prompt, timeout in (("", "600"), ("x", "nan"), ("x", "0"), ("x", "inf")):
            with self.subTest(prompt=prompt, timeout=timeout):
                process, result = self.run_consult(prompt=prompt, extra=("--timeout", timeout))
                self.assert_failed(process, result)
        self.assertFalse(self.attempts.exists())

    def test_oversized_and_invalid_utf8_prompt_refuse(self):
        for prompt in (b"x" * (consult.MAX_PROMPT + 1), b"\xff"):
            with self.subTest(size=len(prompt)):
                process = subprocess.run(self.command(), input=prompt, capture_output=True,
                                         env=dict(self.env, FAKE_EVENTS="[]"), timeout=10)
                result = json.loads(process.stdout)
                self.assert_failed(process, result)
        self.assertFalse(self.attempts.exists())

    def test_arbitrary_cli_arguments_are_not_forwarded(self):
        process = subprocess.run(self.command("claude", "debug", "--model", "replacement"),
                                 input="Selected problem", text=True, capture_output=True,
                                 env=self.env, timeout=10)
        self.assertEqual(process.returncode, 2)
        self.assertFalse(self.attempts.exists())

    def test_open_input_pipe_has_a_deadline(self):
        process = subprocess.Popen(self.command("claude", "debug", "--timeout", "0.15"),
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   env=dict(self.env, FAKE_EVENTS="[]"))
        try:
            process.stdin.write(b"prompt without EOF")
            process.stdin.flush()
            process.wait(timeout=5)
            result = json.loads(process.stdout.read())
            self.assertEqual(result["status"], "timeout")
            self.assertFalse(self.attempts.exists())
        finally:
            for stream in (process.stdin, process.stdout, process.stderr):
                stream.close()
            if process.poll() is None:
                process.kill()
                process.wait()

    def test_timeout_kills_term_ignoring_descendant(self):
        pidfile = self.root / "child.pid"
        process, result = self.run_consult(extra=("--timeout", "1"), FAKE_CHILD_PID=str(pidfile))
        self.assert_failed(process, result, "timeout")
        self.assertEqual(process.returncode, 124)
        self.assertTrue(pidfile.exists())
        pid = int(pidfile.read_text())
        until = time.monotonic() + 2
        while alive(pid) and time.monotonic() < until:
            time.sleep(0.02)
        self.assertFalse(alive(pid))

    def test_interruption_kills_term_ignoring_descendant(self):
        for interrupt in (signal.SIGINT, signal.SIGTERM):
            with self.subTest(signal=interrupt):
                pidfile = self.root / f"child-{interrupt}.pid"
                ready = self.root / f"child-{interrupt}.ready"
                env = dict(self.env, FAKE_EVENTS="[]", FAKE_CHILD_PID=str(pidfile), FAKE_CHILD_READY=str(ready))
                process = subprocess.Popen(self.command("claude", "debug", "--timeout", "10"),
                                           stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE, env=env)
                try:
                    process.stdin.write(b"Selected problem")
                    process.stdin.close()
                    until = time.monotonic() + 5
                    while not ready.exists() and process.poll() is None and time.monotonic() < until:
                        time.sleep(0.02)
                    self.assertTrue(ready.exists(), "Descendant must install its TERM handler before interruption")
                    os.kill(process.pid, interrupt)
                    process.wait(timeout=5)
                    result = json.loads(process.stdout.read())
                    self.assert_failed(process, result)
                    self.assertIn("interrupted", result["error"])
                    child = int(pidfile.read_text())
                    until = time.monotonic() + 2
                    while alive(child) and time.monotonic() < until:
                        time.sleep(0.02)
                    self.assertFalse(alive(child))
                finally:
                    for stream in (process.stdin, process.stdout, process.stderr):
                        stream.close()
                    if process.poll() is None:
                        process.kill()
                        process.wait()
                    if pidfile.exists() and alive(int(pidfile.read_text())):
                        os.kill(int(pidfile.read_text()), signal.SIGKILL)

    def test_auth_failure_preserves_diagnostic_when_cleanup_permission_is_denied(self):
        events = consult.Events("claude")
        text = "\n".join(json.dumps(event) for event in [
            CLAUDE_INIT, {"type": "result", "subtype": "success", "is_error": True,
                          "result": "Failed to authenticate: OAuth expired"}]) + "\n"
        command = [sys.executable, "-c", f"import sys; sys.stdout.write({text!r}); sys.stdout.flush()"]
        with mock.patch.object(consult.os, "killpg", side_effect=PermissionError(1, "Denied")):
            with self.assertRaises(consult.Failure) as caught:
                consult.run_process(command, self.project, self.env, time.monotonic() + 5, on_line=events)
        self.assertIn("authentication", str(caught.exception))
        self.assertIn("errno=1", caught.exception.cleanup_error)

    def test_nonzero_provider_exit_preserves_category_when_cleanup_is_denied(self):
        for diagnostic, category in (("rate limit SECRET=do-not-print", "Provider limit"),
                                     ("Failed to authenticate SECRET=do-not-print", "authentication")):
            with self.subTest(category=category):
                command = [sys.executable, "-c",
                           f"import sys; sys.stderr.write({diagnostic!r}); sys.exit(42)"]
                with mock.patch.object(consult.os, "killpg", side_effect=PermissionError(1, "Denied")):
                    with self.assertRaises(consult.Failure) as caught:
                        consult.run_process(command, self.project, self.env, time.monotonic() + 5)
                self.assertEqual(caught.exception.status, "error")
                self.assertIn(category, str(caught.exception))
                self.assertIn("errno=1", caught.exception.cleanup_error)
                self.assertNotIn("do-not-print", str(caught.exception))

    def test_nonzero_preflight_exit_remains_unavailable_when_cleanup_is_denied(self):
        with mock.patch.object(consult.os, "killpg", side_effect=PermissionError(1, "Denied")):
            with self.assertRaises(consult.Failure) as caught:
                consult.run_process([sys.executable, "-c", "import sys; sys.exit(42)"],
                                    self.project, self.env, time.monotonic() + 5,
                                    failure_status="unavailable")
        self.assertEqual(caught.exception.status, "unavailable")
        self.assertIn("errno=1", caught.exception.cleanup_error)

    def test_unresolved_cleanup_cannot_accept_an_otherwise_successful_process(self):
        with mock.patch.object(consult.os, "killpg", side_effect=PermissionError(1, "Denied")):
            with self.assertRaises(consult.Failure) as caught:
                consult.run_process([sys.executable, "-c", "print('complete')"],
                                    self.project, self.env, time.monotonic() + 5)
        self.assertEqual(caught.exception.status, "error")
        self.assertIn("cleanup incomplete", str(caught.exception))
        self.assertIn("errno=1", caught.exception.cleanup_error)

    def test_code_review_preserves_valid_json_and_checks_evidence(self):
        review = {"verdict": "needs-attention", "summary": "Defect demonstrated", "findings": [
            {"severity": "high", "title": "Defect", "body": "Evidence and impact", "file": "source.py",
             "line_start": 2, "line_end": 3, "confidence": 0.8, "recommendation": "Fix it"}],
                  "next_steps": ["Suggested check"], "uncertainties": []}
        text = json.dumps(review, indent=2)
        process, result = self.run_consult(mode="code-review", events=claude_events(text))
        self.assertEqual(process.returncode, 0)
        self.assertEqual(result["result"], text)
        for mutate in (
            lambda data: data.pop("next_steps"),
            lambda data: data.update(verdict="approve"),
            lambda data: data["findings"][0].update(line_start=True),
            lambda data: data["findings"][0].update(line_end=50),
            lambda data: data["findings"][0].update(file="../outside.py"),
            lambda data: data["findings"][0].update(confidence=2),
            lambda data: data["findings"][0].update(severity="unknown"),
        ):
            data = json.loads(text)
            mutate(data)
            process, result = self.run_consult(mode="code-review", events=claude_events(json.dumps(data)))
            self.assert_failed(process, result)

    def test_code_review_rejects_fences_duplicate_keys_and_truncation(self):
        for text in ('```json\n{}\n```', '{"verdict":"approve"}',
                     '{"verdict":"approve","verdict":"needs-attention"}', '{"verdict":'):
            with self.subTest(text=text):
                process, result = self.run_consult(mode="code-review", events=claude_events(text))
                self.assert_failed(process, result)

    def test_valid_empty_findings_are_not_empty_output(self):
        text = json.dumps({"verdict": "approve", "summary": "No supported defects", "findings": [], "next_steps": []})
        process, result = self.run_consult("codex", "code-review", events=codex_events(text))
        self.assertEqual(process.returncode, 0)
        self.assertEqual(result["result"], text)

    def test_codex_rejects_external_or_writing_capability_events(self):
        for kind in ("mcp_tool_call", "web_search", "file_change", "collab_tool_call"):
            with self.subTest(kind=kind):
                process, result = self.run_consult("codex", events=[{"type": "turn.started"},
                    {"type": "item.started", "item": {"type": kind}}])
                self.assert_failed(process, result)

    def test_codex_model_reroute_rejects_subsequent_clean_approval(self):
        review = json.dumps({"verdict": "approve", "summary": "No defects", "findings": [], "next_steps": []})
        events = codex_events(review)
        events.insert(2, {"type": "item.completed", "item": {
            "type": "error", "message": "model rerouted: configured -> replacement (Capacity)"}})
        process, result = self.run_consult("codex", "code-review", events=events)
        self.assert_failed(process, result)
        self.assertIn("model rerouted", result["error"])
        self.assertEqual(self.attempts.read_text().splitlines(), ["consultation"])

    def test_codex_nonfatal_configuration_warning_is_not_a_model_reroute(self):
        events = codex_events()
        events.insert(2, {"type": "item.completed", "item": {
            "type": "error", "message": "A deprecated native setting was ignored"}})
        process, result = self.run_consult("codex", events=events)
        self.assertEqual(process.returncode, 0)
        self.assertEqual(result["result"], "Findings with uncertainties")


if __name__ == "__main__":
    unittest.main()
