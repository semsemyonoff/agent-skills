"""Isolated native-CLI protocol tests; synthetic executables, no model calls.

Native parser/control fixtures adapted from peer's test_consult.py.
Copyright (c) 2026 Umputun. MIT License; see the bundled ../LICENSE.
Python 3.11+ is required by the fixture's stdlib TOML parser, not the adapter.
"""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

SCRIPT = Path(__file__).with_name("consult.py")
STATE = SCRIPT.with_name("review_state.py")
SPEC = importlib.util.spec_from_file_location("bundled_plan_consult", SCRIPT)
consult = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(consult)
CLAUDE_INIT = {"type": "system", "subtype": "init", "tools": ["Read", "Grep", "Glob"],
               "mcp_servers": [], "model": "observed-fixture-model"}


def claude_events(result):
    return [CLAUDE_INIT, {"type": "result", "subtype": "success", "is_error": False, "result": result}]


def codex_events(result):
    return [{"type": "thread.started", "thread_id": "fixture"}, {"type": "turn.started"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": result}},
            {"type": "turn.completed", "usage": {}}]


FAKE_CLI = r'''
import hashlib, json, os, pathlib, signal, subprocess, sys, time, tomllib
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
    "features": {name: True for name in ("hooks", "apps", "plugins", "remote_plugin", "multi_agent", "multi_agent_v2", "code_mode", "shell_snapshot", "shell_snapshot_v2", "goals", "memories", "skill_mcp_dependency_install")},
    "skills": {"include_instructions": True},
    "mcp_servers": {name: {"enabled": True, "command": "trusted-fixture-launcher", "env": {"SECRET": "never-display"}} for name in names},
}
def merge(base, overlay):
    for key, value in overlay.items():
        if isinstance(base.get(key), dict) and isinstance(value, dict):
            merge(base[key], value)
        else:
            base[key] = value
    return base
# Native CLI splits only the LHS on literal dots, parses RHS as TOML and
# recursively merges the complete CLI layer over the inherited config.
layer = {}
for index, arg in enumerate(args):
    if arg != "--config":
        continue
    key, raw = args[index + 1].split("=", 1)
    try:
        value = tomllib.loads("value = " + raw)["value"]
    except tomllib.TOMLDecodeError:
        value = raw.strip().strip("\"'")
    current = layer
    parts = key.strip().split(".")
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = value
effective = merge(base, layer)
# Native loading rejects a recognized key of the wrong type and ignores unknown keys.
valid = {"approval_policy": lambda v: v in ("untrusted", "on-failure", "on-request", "never"),
         "default_permissions": lambda v: type(v) is str, "web_search": lambda v: type(v) is str,
         "notify": lambda v: type(v) is list, "allow_login_shell": lambda v: type(v) is bool,
         "project_doc_max_bytes": lambda v: type(v) is int, "skills.include_instructions": lambda v: type(v) is bool}
flat = {key: layer.get(key) for key in valid if "." not in key}
flat["skills.include_instructions"] = layer.get("skills", {}).get("include_instructions")
for key, check in valid.items():
    if key != os.environ.get("FAKE_IGNORED_KEY") and flat[key] is not None and not check(flat[key]):
        if key == os.environ.get("FAKE_PROBE_CRASH_KEY"):
            print("thread 'main' panicked; do-not-print", file=sys.stderr)
            sys.exit(101)
        path = "notify" if key == os.environ.get("FAKE_PROBE_OTHER_PATH_KEY") else key
        print(f"Error: failed to load bootstrap configuration\n\nCaused by:\n    invalid type: fixture\n    in `{path}`\n", file=sys.stderr, flush=True)
        if key == os.environ.get("FAKE_PROBE_SIGNAL_KEY"):
            os.kill(os.getpid(), signal.SIGKILL)
        sys.exit(1)
for name in names:
    assert effective["mcp_servers"][name]["command"] == "trusted-fixture-launcher"
    assert effective["mcp_servers"][name]["env"] == {"SECRET": "never-display"}
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
    else:
        print(json.dumps([{"name": name, "enabled": effective["mcp_servers"][name]["enabled"] or bool(os.environ.get("FAKE_STUCK_MCP")), "transport": effective["mcp_servers"][name]} for name in names]))
    sys.exit(0)
assert not any("bypass" in arg or "dangerously" in arg for arg in args)
assert all(arg not in args for arg in ("--model", "--effort", "--ignore-user-config", "--bare", "--restricted"))
if target == "claude":
    for flag, value in (("--tools", "Read,Grep,Glob"), ("--allowedTools", "Read,Grep,Glob"), ("--disallowedTools", "mcp__*"), ("--permission-mode", "dontAsk"), ("--permission-prompts", "none"), ("--output-format", "stream-json")):
        assert args[args.index(flag) + 1] == value
    assert json.loads(args[args.index("--mcp-config") + 1]) == {"mcpServers": {}}
    assert json.loads(args[args.index("--settings") + 1]) == {"disableAllHooks": True, "fallbackModel": []}
    assert all(flag in args for flag in ("--safe-mode", "--strict-mcp-config", "--no-session-persistence", "--no-chrome", "--disable-slash-commands"))
    assert os.environ["CLAUDE_CODE_MAX_RETRIES"] == "0"
    assert os.environ["CLAUDE_CODE_DISABLE_ADVISOR_TOOL"] == "1"
else:
    assert args[args.index("--sandbox") + 1] == "read-only"
    assert effective["approval_policy"] == "never"
    assert effective["default_permissions"] == ":read-only"
    assert effective["web_search"] == "disabled"
    assert effective["notify"] == [] and effective["allow_login_shell"] is False
    assert effective["project_doc_max_bytes"] == 0
    assert effective["skills"]["include_instructions"] is False
    assert all(value is False for value in effective["features"].values())
    assert "memory_tool" not in effective["features"] and "js_repl" not in effective["features"]
    assert all(effective["mcp_servers"][name]["enabled"] is False for name in names)
    assert set(effective["mcp_servers"]) == set(names)
with open(os.environ["FAKE_ATTEMPTS"], "a") as file:
    file.write("consultation\n")
if os.environ.get("FAKE_CHILD_PID"):
    child = subprocess.Popen([sys.executable, "-c", "import os,pathlib,signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); pathlib.Path(os.environ['FAKE_CHILD_READY']).write_text('ready'); time.sleep(60)"])
    pathlib.Path(os.environ["FAKE_CHILD_PID"]).write_text(str(child.pid))
    time.sleep(60)
prompt = sys.stdin.read()
packet = json.loads(prompt.partition("\n\n")[2])
snapshot = packet["snapshot"]
assert hashlib.sha256(snapshot["plan_text"].encode("utf-8")).hexdigest() == snapshot["plan_version"]
# Exercise the snapshot payload and evidence, not a hardcoded approval/default.
evidence = pathlib.Path("source.txt").read_text()
findings = []
if "rollback" in packet["requirements"] and "rollback" not in snapshot["plan_text"].lower():
    findings = [{"severity": "blocker", "section": "Recovery", "evidence": "Supplied plan omits rollback; " + evidence.strip(), "impact": "No recovery after failed cutover", "fix": "Add a rollback step"}]
report = {"verdict": "NEEDS REVISION" if findings else "APPROVE", "plan_path": snapshot["plan_path"], "plan_version": snapshot["plan_version"], "findings": findings, "unknowns": []}
text = json.dumps(report, ensure_ascii=False)
if "FAKE_EVENTS" in os.environ:
    events = json.loads(os.environ["FAKE_EVENTS"])
elif target == "claude":
    events = [{"type": "system", "subtype": "init", "tools": ["Read", "Grep", "Glob", "EndConversation"], "mcp_servers": [], "model": "observed-fixture-model"}, {"type": "result", "subtype": "success", "is_error": False, "result": text}]
else:
    events = [{"type": "thread.started", "thread_id": "fixture"}, {"type": "turn.started"}, {"type": "item.completed", "item": {"type": "agent_message", "text": text}}, {"type": "turn.completed", "usage": {}}]
for event in events:
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


@unittest.skipUnless(os.name == "posix", "POSIX native process lifecycle")
class ConsultationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.project = self.root / "project"
        self.project.mkdir()
        (self.project / "source.txt").write_text("Existing source has persistent data.\n", encoding="utf-8")
        self.plan = self.project / "plan.md"
        self.plan.write_bytes("# План\r\nDeploy and verify.\r\n".encode("utf-8"))
        self.attempts = self.root / "attempts"
        for target in ("claude", "codex"):
            binary = self.bin / target
            binary.write_text(f"#!{sys.executable}\n" + FAKE_CLI, encoding="utf-8")
            binary.chmod(0o755)
        self.env = {"PATH": str(self.bin), "HOME": str(self.root), "FAKE_ATTEMPTS": str(self.attempts)}
        data = self.plan.read_bytes()
        self.snapshot = {"plan_path": str(self.plan), "plan_version": hashlib.sha256(data).hexdigest(),
                         "plan_text": data.decode("utf-8")}
        self.packet = {"snapshot": self.snapshot, "requirements": "Deploy safely with rollback", "decisions": []}

    def tearDown(self):
        self.tmp.cleanup()

    def command(self, target="claude", extra=(), script=SCRIPT):
        return [sys.executable, str(script), "--target", target, "--project", str(self.project), *extra]

    def run_consult(self, target="claude", events=None, prompt=None, extra=(), script=SCRIPT, **env):
        environment = dict(self.env, **env)
        if events is not None:
            environment["FAKE_EVENTS"] = json.dumps(events)
        process = subprocess.run(self.command(target, extra, script),
                                 input=json.dumps(self.packet, ensure_ascii=False) if prompt is None else prompt,
                                 text=True, capture_output=True, env=environment, cwd=self.root, timeout=10)
        return process, json.loads(process.stdout)

    def assert_failed(self, process, result, status="error"):
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(result["status"], status)
        self.assertIsNone(result["result"])
        self.assertFalse(result["consultation_completed"])

    def test_real_packet_finding_and_validation_pipeline_for_both_targets(self):
        original = self.plan.read_bytes()
        for target in ("claude", "codex"):
            with self.subTest(target=target):
                process, result = self.run_consult(target)
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertEqual(result["status"], "ok")
                self.assertFalse(result["check"])
                self.assertTrue(result["consultation_completed"])
                report = json.loads(result["result"])
                self.assertEqual(report["verdict"], "NEEDS REVISION")
                self.assertIn("persistent data", report["findings"][0]["evidence"])
                validated = subprocess.run([sys.executable, str(STATE), "validate", str(self.plan),
                                            "--version", self.snapshot["plan_version"]],
                                           input=result["result"], text=True, capture_output=True,
                                           env=self.env, cwd=self.root, timeout=5)
                self.assertEqual(validated.returncode, 0, validated.stderr)
                self.assertEqual(json.loads(validated.stdout), report)
                self.assertEqual(result["model"], "observed-fixture-model" if target == "claude" else None)
        self.assertEqual(self.plan.read_bytes(), original)
        self.assertEqual(self.attempts.read_text().splitlines(), ["consultation", "consultation"])


    def test_check_never_reads_open_stdin_or_requests_model(self):
        for target in ("claude", "codex"):
            process = subprocess.Popen(self.command(target, ("--check",)), stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.env)
            try:
                process.wait(timeout=5)
                result = json.loads(process.stdout.read())
                self.assertEqual(process.returncode, 0)
                self.assertTrue(result["check"])
                self.assertFalse(result["consultation_completed"])
                self.assertIsNone(result["model"])
                self.assertIsNone(result["result"])
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                for stream in (process.stdin, process.stdout, process.stderr):
                    stream.close()
        self.assertFalse(self.attempts.exists())

    def test_missing_unstartable_and_constraint_fail_before_request(self):
        for target, env in (("claude", {"PATH": str(self.root / "absent")}),
                            ("claude", {"FAKE_MISSING_FLAG": "--safe-mode"}),
                            ("codex", {"FAKE_MISSING_FLAG": "--strict-config"})):
            with self.subTest(target=target, env=env):
                process, result = self.run_consult(target, **env)
                self.assert_failed(process, result, "unavailable")
        binary = self.bin / "claude"
        binary.write_text("#!/nonexistent/native-interpreter\n", encoding="utf-8")
        process, result = self.run_consult()
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

    def test_codex_key_probe_requires_the_expected_diagnostic(self):
        for env in ({"FAKE_PROBE_CRASH_KEY": "web_search"},
                    {"FAKE_PROBE_OTHER_PATH_KEY": "allow_login_shell"},
                    {"FAKE_PROBE_SIGNAL_KEY": "project_doc_max_bytes"}):
            with self.subTest(env=env):
                process, result = self.run_consult("codex", **env)
                self.assert_failed(process, result, "unavailable")
                self.assertIn(next(iter(env.values())), result["error"])
                self.assertNotIn("do-not-print", process.stdout + process.stderr)
                self.assertFalse(self.attempts.exists())

    def test_codex_key_probe_cleanup_failure_is_never_accepted(self):
        binary = str(self.bin / "codex")
        # The first probe decides: approval_policy is CODEX_KEYS[0], so ignoring it
        # exercises cleanup after a successful exit rather than after a rejection.
        self.assertEqual(consult.CODEX_KEYS[0][0], "approval_policy")
        for env in ({}, {"FAKE_IGNORED_KEY": "approval_policy"}):
            with self.subTest(env=env):
                with mock.patch.object(consult.os, "killpg", side_effect=PermissionError(1, "Denied")):
                    with self.assertRaises(consult.Failure) as caught:
                        consult.ignored_keys(binary, self.project, dict(self.env, **env), time.monotonic() + 10)
                self.assertEqual(caught.exception.status, "unavailable")
                self.assertIn("errno=1", caught.exception.cleanup_error)
                self.assertFalse(self.attempts.exists())

    def test_unrecognized_codex_key_is_unavailable(self):
        for key, _, _ in consult.CODEX_KEYS:
            with self.subTest(key=key):
                process, result = self.run_consult("codex", FAKE_IGNORED_KEY=key)
                self.assert_failed(process, result, "unavailable")
                self.assertIn(key, result["error"])
                self.assertFalse(self.attempts.exists())

    def test_codex_native_mcp_names_disable_with_transport_preserved(self):
        names = ["writer", "team.service", "org/tool", "team:service", "service@org", "dash-name"]
        process, result = self.run_consult("codex", FAKE_MCP_NAMES=json.dumps(names))
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(result["disabled_mcp_count"], len(names))
        self.assertNotIn("never-display", process.stdout + process.stderr)
        for name in names:
            self.attempts.unlink(missing_ok=True)
            process, result = self.run_consult("codex", FAKE_MCP_NAMES=json.dumps([name]), FAKE_STUCK_MCP="1")
            self.assert_failed(process, result, "unavailable")
            self.assertFalse(self.attempts.exists())

    def test_invalid_mcp_inventories_never_authorize_consultation(self):
        for raw in ('{}', '[{"name":"writer"}]', '[{"name":"x y","enabled":true}]',
                    '[{"name":"x","enabled":true},{"name":"x","enabled":false}]'):
            process, result = self.run_consult("codex", FAKE_BAD_INVENTORY=raw)
            self.assert_failed(process, result, "unavailable")
        self.assertFalse(self.attempts.exists())

    def test_contradictory_runtime_capabilities_and_prohibited_actions_refuse(self):
        for event in (dict(CLAUDE_INIT, tools=["Read"]),
                      dict(CLAUDE_INIT, tools=["Read", "Grep", "Glob", "Bash"]),
                      dict(CLAUDE_INIT, mcp_servers=[{"name": "writer"}])):
            process, result = self.run_consult(events=[event])
            self.assert_failed(process, result)
        for tool in ("Bash", "Write", "Agent", "mcp__writer"):
            process, result = self.run_consult(events=[CLAUDE_INIT, {"type": "assistant", "message": {
                "content": [{"type": "tool_use", "name": tool}]}}])
            self.assert_failed(process, result)
        for kind in ("mcp_tool_call", "web_search", "file_change", "collab_tool_call"):
            process, result = self.run_consult("codex", events=[{"type": "turn.started"},
                {"type": "item.started", "item": {"type": kind}}])
            self.assert_failed(process, result)

    def test_empty_truncated_duplicate_stream_and_incomplete_results_refuse(self):
        for target, events in (("claude", claude_events("{}")), ("codex", codex_events("{}"))):
            for stream, trailer in (([], ""), (events[:-1], ""), (events, '{"type":'),
                                    (events, '{"type":"error","type":"ignored"}'),
                                    (claude_events("") if target == "claude" else codex_events(""), "")):
                process, result = self.run_consult(target, events=stream, FAKE_TRAILER=trailer)
                self.assert_failed(process, result)
        process, result = self.run_consult(events=claude_events("{}") + claude_events("{}")[-1:])
        self.assert_failed(process, result)

    def test_provider_auth_retry_and_reroute_fail_without_relaunch_or_leak(self):
        for diagnostic, category in (("rate limit SECRET=not-public", "Provider limit"),
                                     ("Failed to authenticate SECRET=not-public", "authentication")):
            self.attempts.unlink(missing_ok=True)
            process, result = self.run_consult(events=[], FAKE_EXIT="42", FAKE_DIAGNOSTIC=diagnostic)
            self.assert_failed(process, result)
            self.assertIn(category, result["error"])
            self.assertNotIn("not-public", process.stdout + process.stderr)
            self.assertEqual(self.attempts.read_text().splitlines(), ["consultation"])
        process, result = self.run_consult(events=[CLAUDE_INIT, {"type": "system", "subtype": "api_retry"}])
        self.assert_failed(process, result)
        events = codex_events("{}")
        events.insert(2, {"type": "item.completed", "item": {"type": "error", "message": "model rerouted: old -> new"}})
        process, result = self.run_consult("codex", events=events)
        self.assert_failed(process, result)
        self.assertIn("rerouted", result["error"])
        events[2]["item"]["message"] = "A deprecated native setting was ignored"
        process, result = self.run_consult("codex", events=events)
        self.assertEqual(process.returncode, 0, process.stderr)

    def test_transport_completion_is_not_schema_or_current_approval(self):
        # The adapter preserves inner text; only the state validator accepts it.
        for text in ('```json\n{}\n```', '{"verdict":"APPROVE","verdict":"NEEDS REVISION"}', '{}'):
            process, result = self.run_consult(events=claude_events(text))
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual(result["result"], text)
            validated = subprocess.run([sys.executable, str(STATE), "validate", str(self.plan),
                                        "--version", self.snapshot["plan_version"]], input=result["result"],
                                       text=True, capture_output=True, env=self.env, timeout=5)
            self.assertNotEqual(validated.returncode, 0)
            self.assertEqual(validated.stdout, "")
        process, result = self.run_consult()
        self.plan.write_bytes(b"New plan scope\n")
        validated = subprocess.run([sys.executable, str(STATE), "validate", str(self.plan),
                                    "--version", self.snapshot["plan_version"]], input=result["result"],
                                   text=True, capture_output=True, env=self.env, timeout=5)
        self.assertNotEqual(validated.returncode, 0)
        self.assertEqual(validated.stdout, "")

    def test_input_limit_encoding_deadline_and_closed_regular_file(self):
        for prompt, timeout in (("", "600"), ("x", "nan"), ("x", "0"), ("x", "inf")):
            process, result = self.run_consult(prompt=prompt, extra=("--timeout", timeout))
            self.assert_failed(process, result)
        for prompt in (b"\xff", b"x" * (consult.MAX_PROMPT + 1)):
            process = subprocess.run(self.command(), input=prompt, capture_output=True, env=self.env, timeout=5)
            self.assert_failed(process, json.loads(process.stdout))
        self.assertFalse(self.attempts.exists())
        process = subprocess.Popen(self.command(extra=("--timeout", "0.1")), stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.env)
        try:
            process.stdin.write(b"not closed")
            process.stdin.flush()
            process.wait(timeout=5)
            result = json.loads(process.stdout.read())
            self.assertEqual(process.returncode, 124)
            self.assertEqual(result["status"], "timeout")
            self.assertFalse(self.attempts.exists())
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            for stream in (process.stdin, process.stdout, process.stderr):
                stream.close()
        packetfile = self.root / "packet.json"
        packetfile.write_text(json.dumps(self.packet), encoding="utf-8")
        with packetfile.open("rb") as source:
            process = subprocess.run(self.command(), stdin=source, capture_output=True, env=self.env, timeout=5)
        self.assertEqual(process.returncode, 0, process.stderr)

    def test_passthrough_and_mode_flags_are_not_supported(self):
        for extra in (("--model", "replacement"), ("--mode", "debug"), ("--effort", "low")):
            process = subprocess.run(self.command(extra=extra), input="packet", text=True,
                                     capture_output=True, env=self.env, timeout=5)
            self.assertEqual(process.returncode, 2)
        self.assertFalse(self.attempts.exists())

    def test_timeout_and_interruption_clean_term_ignoring_descendants(self):
        for interrupt in (None, signal.SIGINT, signal.SIGTERM):
            with self.subTest(interrupt=interrupt):
                pidfile = self.root / "child.pid"
                ready = self.root / "child.ready"
                pidfile.unlink(missing_ok=True)
                ready.unlink(missing_ok=True)
                environment = dict(self.env, FAKE_CHILD_PID=str(pidfile), FAKE_CHILD_READY=str(ready))
                process = subprocess.Popen(self.command(extra=("--timeout", "3" if interrupt is None else "10")),
                                           stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE, env=environment)
                try:
                    process.stdin.write(json.dumps(self.packet).encode("utf-8"))
                    process.stdin.close()
                    until = time.monotonic() + 5
                    while not ready.exists() and process.poll() is None and time.monotonic() < until:
                        time.sleep(0.02)
                    self.assertTrue(ready.exists(), "Child installs TERM handler before interruption")
                    if interrupt is not None:
                        os.kill(process.pid, interrupt)
                    process.wait(timeout=6)
                    result = json.loads(process.stdout.read())
                    self.assert_failed(process, result, "timeout" if interrupt is None else "error")
                    child = int(pidfile.read_text())
                    until = time.monotonic() + 2
                    while alive(child) and time.monotonic() < until:
                        time.sleep(0.02)
                    self.assertFalse(alive(child))
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
                    for stream in (process.stdin, process.stdout, process.stderr):
                        stream.close()
                    if pidfile.exists() and alive(int(pidfile.read_text())):
                        os.kill(int(pidfile.read_text()), signal.SIGKILL)

    def test_cleanup_permission_failures_preserve_original_failure_and_reject_success(self):
        for diagnostic, category in (("rate limit SECRET=not-public", "Provider limit"),
                                     ("Failed to authenticate SECRET=not-public", "authentication")):
            command = [sys.executable, "-c", f"import sys; sys.stderr.write({diagnostic!r}); sys.exit(42)"]
            with mock.patch.object(consult.os, "killpg", side_effect=PermissionError(1, "Denied")):
                with self.assertRaises(consult.Failure) as caught:
                    consult.run_process(command, self.project, self.env, time.monotonic() + 5)
            self.assertIn(category, str(caught.exception))
            self.assertIn("errno=1", caught.exception.cleanup_error)
            self.assertNotIn("not-public", str(caught.exception))
        with mock.patch.object(consult.os, "killpg", side_effect=PermissionError(1, "Denied")):
            with self.assertRaises(consult.Failure) as caught:
                consult.run_process([sys.executable, "-c", "print('complete')"],
                                    self.project, self.env, time.monotonic() + 5)
        self.assertIn("cleanup incomplete", str(caught.exception))
        self.assertIn("errno=1", caught.exception.cleanup_error)
        events = consult.Events("claude")
        text = "\n".join(json.dumps(event) for event in [CLAUDE_INIT,
            {"type": "result", "subtype": "success", "is_error": True, "result": "Failed to authenticate"}]) + "\n"
        with mock.patch.object(consult.os, "killpg", side_effect=PermissionError(1, "Denied")):
            with self.assertRaises(consult.Failure) as caught:
                consult.run_process([sys.executable, "-c", f"print({text!r}, end='')"],
                                    self.project, self.env, time.monotonic() + 5, on_line=events)
        self.assertIn("authentication", str(caught.exception))
        self.assertIn("errno=1", caught.exception.cleanup_error)

    def test_signal_during_popen_cannot_leak_the_consultation_process(self):
        ready = self.root / "launch-ready"
        release = self.root / "launch-release"
        effect = self.root / "launch-effect"
        child_code = (
            "import pathlib,signal,sys,time\n"
            "signal.signal(signal.SIGTERM,signal.SIG_IGN)\n"
            "root=pathlib.Path(sys.argv[1])\n"
            "(root/'launch-ready').write_text('ready')\n"
            "while not (root/'launch-release').exists(): time.sleep(0.01)\n"
            "(root/'launch-effect').write_text('continued after cancellation')\n"
        )
        real_popen = subprocess.Popen
        launched = []

        def interrupt(signum, frame):
            raise consult.Failure("error", "Consultation interrupted; no result accepted")

        def cancel_before_ownership(*args, **kwargs):
            process = real_popen(*args, **kwargs)
            launched.append(process)
            until = time.monotonic() + 5
            while not ready.exists():
                if time.monotonic() >= until:
                    self.fail("Synthetic consultation process did not become ready")
                time.sleep(0.01)
            os.kill(os.getpid(), signal.SIGTERM)
            return process

        original_handler = signal.signal(signal.SIGTERM, interrupt)
        try:
            with mock.patch.object(consult.subprocess, "Popen", cancel_before_ownership):
                with self.assertRaises(consult.Failure):
                    consult.run_process([sys.executable, "-c", child_code, str(self.root)],
                                        self.project, self.env, time.monotonic() + 10)
            release.write_text("release after cancellation is reported")
            time.sleep(0.2)
            self.assertFalse(effect.exists(), "Consultation continued after cancellation during launch")
        finally:
            signal.signal(signal.SIGTERM, original_handler)
            for process in launched:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=4)
                for stream in (process.stdin, process.stdout, process.stderr):
                    if stream is not None:
                        stream.close()

    def test_output_capture_limits_are_enforced_on_real_processes(self):
        for stream, limit in (("stdout", "MAX_OUTPUT"), ("stderr", "MAX_STDERR")):
            with mock.patch.object(consult, limit, 128):
                with self.assertRaisesRegex(consult.Failure, "capture limit"):
                    consult.run_process([sys.executable, "-c", f"import sys; sys.{stream}.write('x' * 1024)"],
                                        self.project, self.env, time.monotonic() + 5)

    def test_cold_cached_execution_without_peer_skill_files(self):
        cached = self.root / "cache" / "plan-review" / "scripts" / SCRIPT.name
        cached.parent.mkdir(parents=True)
        shutil.copyfile(SCRIPT, cached)
        process, result = self.run_consult("codex", script=cached)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(result["result"])["plan_version"], self.snapshot["plan_version"])


if __name__ == "__main__":
    unittest.main()
