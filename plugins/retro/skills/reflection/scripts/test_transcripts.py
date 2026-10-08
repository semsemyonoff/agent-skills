import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import transcripts

try:
    from compression import zstd
except ImportError:
    zstd = None

TS = "2099-01-02T10:00:{:02d}.000Z"
OLD = "2098-12-01T00:00:00Z"


def claude_user(index, text, **extra):
    return {"type": "user", "uuid": f"user-{index}", "timestamp": TS.format(index),
            "cwd": "/work/demo", "entrypoint": "cli", "sessionId": "shared-id",
            "message": {"role": "user", "content": text}, **extra}


def claude_assistant(index, mid, content, output=10, **extra):
    return {"type": "assistant", "uuid": f"assistant-{index}", "timestamp": TS.format(index),
            "cwd": "/work/demo", "entrypoint": "cli", "sessionId": "shared-id",
            "message": {"id": mid, "model": "claude-demo", "content": content,
                        "usage": {"input_tokens": 1, "cache_creation_input_tokens": 100,
                                  "cache_read_input_tokens": 1000, "output_tokens": output}}, **extra}


def call(tid, name, **arguments):
    return {"type": "tool_use", "id": tid, "name": name, "input": arguments}


def result(tid, text):
    return {"type": "tool_result", "tool_use_id": tid, "content": text, "is_error": True}


def omp_entry(index, typ="message", parent=None, **extra):
    return {"type": typ, "id": f"entry-{index}", "parentId": parent,
            "timestamp": TS.format(index), **extra}


def omp_assistant(index, output=5, parent=None, **extra):
    return omp_entry(index, parent=parent, message={
        "role": "assistant", "provider": "openai-codex", "model": "gpt-demo",
        "content": [{"type": "toolCall", "id": f"call-{index}", "name": "bash", "arguments": {"command": "false"}}],
        "usage": {"input": 10, "output": output, "cacheRead": 20, "cacheWrite": 0, "totalTokens": 30 + output}, **extra})


CLAUDE = [
    claude_user(1, "deploy demo password: synthetic-secret"),
    claude_user(2, "<system-reminder>Bearer synthetic123456789</system-reminder>"),
    claude_assistant(3, "m1", [call("t1", "Bash")]),
    claude_assistant(3, "m1", [call("t1", "Bash")], output=25),
    claude_user(4, [result("t1", "Exit code 1\nboom /a/b/c 42")]),
    claude_assistant(5, "m2", [call("t2", "Agent", model="sonnet", subagent_type="Explore"), call("t3", "Agent")]),
    claude_user(6, [result("t2", "denied by the Claude Code auto mode classifier. Reason: [Git Destructive]")]),
    claude_user(7, [result("t3", "The user doesn't want to proceed with this tool use. The tool use was rejected")]),
    claude_user(8, "нет, не так, поправь"),
    claude_user(9, "<command-name>/clear</command-name><command-args></command-args>"),
]
OMP = [
    {"type": "session", "version": 3, "id": "shared-id", "timestamp": OLD, "cwd": "/work/demo"},
    omp_entry(1, "model_change", model="openai-codex/gpt-demo"),
    omp_entry(2, "thinking_level_change", parent="entry-1", thinkingLevel="high", configured="auto"),
    omp_entry(3, parent="entry-2", message={"role": "user", "content": "deploy demo token: synthetic-token"}),
    omp_assistant(4, parent="entry-3"),
    omp_entry(5, parent="entry-4", message={"role": "toolResult", "toolCallId": "call-4", "toolName": "bash", "isError": True,
                                                   "content": [{"type": "text", "text": "Permission denied /private/example 12"}]}),
    omp_entry(6, "model_usage", parent="entry-5", purpose="title", provider="local", model="tiny", role="tiny",
              usage={"input": 2, "output": 3, "cacheRead": 0, "cacheWrite": 0, "totalTokens": 5}),
    omp_entry(7, parent="entry-5", message={"role": "user", "content": [{"type": "text", "text": "нет, поправь только demo"}]}),
]


class TranscriptTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.config = os.path.join(self.tmp.name, "claude")
        self.omp = os.path.join(self.tmp.name, "omp-sessions")
        self.write("claude/projects/demo/main.jsonl", CLAUDE)
        self.write("omp-sessions/demo/main.jsonl", OMP, title=True)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, relative, records, title=False):
        path = os.path.join(self.tmp.name, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as stream:
            if title:
                slot = {"type": "title", "v": 1, "title": "Synthetic title", "updatedAt": OLD, "pad": ""}
                raw = json.dumps(slot, separators=(",", ":"))
                slot["pad"] = " " * (255 - len(raw.encode()))
                stream.write(json.dumps(slot, separators=(",", ":")) + "\n")
            stream.write("malformed synthetic line\n")
            for record in records:
                stream.write(json.dumps(record) + "\n")
            stream.write('{"type":"message"')  # interrupted append
        return path

    def run_cli(self, source="both", *extra):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = transcripts.main(["--source", source, "--since", "2099-01-01", "--config-dir", self.config,
                                     "--omp-sessions-dir", self.omp, "--out", "json", *extra])
        self.assertEqual(code, 0)
        return json.loads(output.getvalue())

    def test_claude_streaming_denials_and_prompts(self):
        digest = self.run_cli("claude")
        self.assertEqual(digest["prompts_total"], 3)
        self.assertEqual({r["name"]: r["count"] for r in digest["tools_top"]}, {"Bash": 1, "Agent": 2})
        usage = digest["tokens_by_model"]["claude:unknown/claude-demo"]
        self.assertEqual((usage["output"], usage["messages"], usage["cache_read"]), (35, 2, 2000))
        self.assertEqual(usage["total"], 2237)
        self.assertEqual((digest["subagent_model_set"], digest["subagent_model_unset"]), (1, 1))
        self.assertEqual({r["name"]: r["count"] for r in digest["denials"]}, {"classifier: Git Destructive": 1, "user rejected": 1})
        self.assertEqual(digest["errors_top"], [{"name": "Bash: Exit code N", "count": 1}])
        self.assertEqual(digest["correction_candidates"][0]["session"], "claude:shared-id")

    def test_omp_title_camelcase_usage_and_effort(self):
        digest = self.run_cli("omp")
        self.assertEqual((digest["sessions_total"], digest["prompts_total"]), (1, 2))
        self.assertEqual(digest["tools_top"], [{"name": "bash", "count": 1}])
        self.assertEqual(digest["denials"], [{"name": "permission denied", "count": 1}])
        self.assertEqual(digest["tokens_by_model"]["omp:openai-codex/gpt-demo"]["total"], 35)
        self.assertEqual(digest["tokens_by_model"]["omp:local/tiny"]["total"], 5)
        route = next(r for r in digest["usage_routes"] if r["model"] == "gpt-demo")
        self.assertEqual((route["provider"], route["effort"], route["configured_effort"]), ("openai-codex", "high", "auto"))
        self.assertEqual(digest["sessions"][0]["usage"]["total"], 40)

    def test_explicit_selection_and_mixed_identity(self):
        mixed = self.run_cli()
        self.assertEqual({r["id"] for r in mixed["sessions"]}, {"claude:shared-id", "omp:shared-id"})
        self.assertEqual(mixed["prompts_total"], 5)
        self.assertEqual(set(self.run_cli("omp")["roots"]), {"omp"})
        self.assertEqual(set(self.run_cli("claude")["roots"]), {"claude"})
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            transcripts.parse_args([])
        # Unselected nonexistent storage must not be accessed.
        self.assertEqual(self.run_cli("omp", "--config-dir", "/does-not-exist")["sessions_total"], 1)
        self.assertEqual(self.run_cli("claude", "--omp-sessions-dir", "/does-not-exist")["sessions_total"], 1)

    def test_project_and_sdk_filters_apply_to_every_total(self):
        other = [claude_user(20, "noise", cwd="/work/noise", sessionId="noise", entrypoint="sdk-cli"),
                 claude_assistant(21, "noise-model-call", [call("noise-tool", "Danger")], cwd="/work/noise", sessionId="noise", entrypoint="sdk-cli")]
        self.write("claude/projects/noise/noise.jsonl", other)
        self.assertNotIn("Danger", {r["name"] for r in self.run_cli("claude")["tools_top"]})
        self.assertIn("Danger", {r["name"] for r in self.run_cli("claude", "--include-sdk")["tools_top"]})
        self.assertNotIn("Danger", {r["name"] for r in self.run_cli("both", "--include-sdk", "--project", "demo")["tools_top"]})
        empty = self.run_cli("both", "--project", "absent")
        for key in ("sessions_total", "prompts_total", "subagent_model_set", "subagent_model_unset"):
            self.assertEqual(empty[key], 0)
        for key in ("tools_top", "errors_top", "denials", "subagent_calls", "prompts", "prompt_openers_top", "usage_routes"):
            self.assertEqual(empty[key], [])
        self.assertEqual(empty["tokens_by_model"], {})

    def test_period_filters_usage_tools_errors_and_prompts(self):
        digest = self.run_cli("omp", "--since", "2099-01-03")
        self.assertEqual(digest["sessions_total"], 0)
        self.assertEqual(digest["tokens_by_model"], {})
        self.assertEqual(digest["tools_top"], [])
        self.assertEqual(digest["denials"], [])
        # Files restored with old mtimes still contain in-period events.
        for root, _, files in os.walk(self.tmp.name):
            for name in files:
                os.utime(os.path.join(root, name), (1, 1))
        self.assertEqual(self.run_cli("both")["prompts_total"], 5)

    def test_missing_metrics_are_not_zero(self):
        unknown = omp_assistant(8, usage={"output": 7})
        self.write("omp-sessions/demo/main.jsonl", [*OMP, unknown])
        usage = self.run_cli("omp")["tokens_by_model"]["omp:openai-codex/gpt-demo"]
        self.assertIsNone(usage["input"])
        self.assertIsNone(usage["total"])
        self.assertEqual((usage["output"], usage["known"]["input"], usage["missing"]["input"]), (12, 10, 1))
        self.assertIsNone(usage["cache_creation"])

    def test_partial_stream_updates_keep_known_buckets(self):
        partial = {**CLAUDE[3], "message": {"id": "m1", "model": "claude-demo", "content": [],
                                           "usage": {"output_tokens": 30}}}
        self.write("claude/projects/demo/main.jsonl", [*CLAUDE, partial])
        usage = self.run_cli("claude")["tokens_by_model"]["claude:unknown/claude-demo"]
        self.assertEqual((usage["messages"], usage["input"], usage["output"], usage["total"]), (2, 2, 40, 2242))

    def test_partial_stream_updates_preserve_reported_total_and_accept_new_totals(self):
        cases = (
            ("omp", "omp-sessions/demo/main.jsonl", OMP[0],
             omp_assistant(8), "totalTokens", "output", "omp:openai-codex/gpt-demo"),
            ("claude", "claude/projects/demo/main.jsonl", None,
             claude_assistant(8, "reported-total", []), "total_tokens", "output_tokens",
             "claude:unknown/claude-demo"),
        )
        for source, path, header, entry, total_field, output_field, route in cases:
            with self.subTest(source=source):
                initial = json.loads(json.dumps(entry))
                initial["message"]["usage"] = {
                    ("input" if source == "omp" else "input_tokens"): 40,
                    ("cacheRead" if source == "omp" else "cache_read_input_tokens"): 10,
                    ("cacheWrite" if source == "omp" else "cache_creation_input_tokens"): 0,
                    output_field: 50, total_field: 150,
                }
                partial = json.loads(json.dumps(initial))
                partial["timestamp"] = TS.format(9)
                partial["message"]["usage"] = {output_field: 60}
                records = ([header] if header else []) + [initial, partial]
                self.write(path, records)
                usage = self.run_cli(source)["tokens_by_model"][route]
                self.assertEqual((usage["messages"], usage["total"], usage["output"]), (1, 150, 60))
                self.assertEqual((usage["input"], usage["cache_read"], usage["missing"]["total"]), (40, 10, 0))
                final = json.loads(json.dumps(partial))
                final["timestamp"] = TS.format(10)
                final["message"]["usage"] = {total_field: 170}
                self.write(path, [*records, final])
                usage = self.run_cli(source)["tokens_by_model"][route]
                self.assertEqual((usage["messages"], usage["total"], usage["output"]), (1, 170, 60))

    def test_copied_stream_chronology_is_independent_of_filename_and_controls_period(self):
        for source, directory, header, initial, output_field, route in (
            ("omp", "omp-sessions/demo", OMP[0], omp_assistant(8), "output",
             "omp:openai-codex/gpt-demo"),
            ("claude", "claude/projects/demo", None, claude_assistant(8, "copied", []),
             "output_tokens", "claude:unknown/claude-demo"),
        ):
            with self.subTest(source=source):
                final = json.loads(json.dumps(initial))
                final["timestamp"] = TS.format(9)
                final["message"]["usage"][output_field] = 25
                if source == "omp":
                    final["message"]["usage"]["totalTokens"] = 55
                prefix = [header] if header else []
                for newer_name, stale_name in (("main", "z-copy"), ("z-copy", "main")):
                    self.write(f"{directory}/{newer_name}.jsonl", [*prefix, initial, final])
                    self.write(f"{directory}/{stale_name}.jsonl", [*prefix, initial])
                    digest = self.run_cli(source)
                    usage = digest["tokens_by_model"][route]
                    self.assertEqual((digest["sessions_total"], usage["messages"], usage["output"]), (1, 1, 25))
                initial["timestamp"] = OLD
                self.write(f"{directory}/main.jsonl", [*prefix, initial, final])
                self.write(f"{directory}/z-copy.jsonl", [*prefix, initial])
                digest = self.run_cli(source)
                self.assertEqual(digest["tokens_by_model"][route]["output"], 25)
                self.assertEqual(digest["sessions"][0]["start"], transcripts.timestamp(TS.format(9)).isoformat())
                final["timestamp"] = OLD
                self.write(f"{directory}/main.jsonl", [*prefix, initial, final])
                self.assertEqual(self.run_cli(source)["sessions_total"], 0)

    def test_same_file_stream_ties_and_untimed_partial_updates_keep_append_order(self):
        for source, path, header, initial, output_field, route in (
            ("omp", "omp-sessions/demo/main.jsonl", OMP[0], omp_assistant(8), "output",
             "omp:openai-codex/gpt-demo"),
            ("claude", "claude/projects/demo/main.jsonl", None,
             claude_assistant(8, "append-order", []), "output_tokens",
             "claude:unknown/claude-demo"),
        ):
            with self.subTest(source=source):
                final = json.loads(json.dumps(initial))
                final["message"]["usage"][output_field] = 25
                if source == "omp":
                    final["message"]["usage"]["totalTokens"] = 55
                partial = json.loads(json.dumps(final))
                partial.pop("timestamp")
                partial["message"]["usage"] = {output_field: 30}
                self.write(path, ([header] if header else []) + [initial, final, partial])
                usage = self.run_cli(source)["tokens_by_model"][route]
                self.assertEqual((usage["messages"], usage["output"]), (1, 30))

    def test_unrelated_short_ids_are_not_copied_events(self):
        self.write("omp-sessions/demo/unrelated.jsonl", [{**OMP[0], "id": "unrelated"}, *OMP[1:]])
        digest = self.run_cli("omp")
        self.assertEqual(digest["prompts_total"], 4)
        self.assertEqual(digest["tokens_by_model"]["omp:openai-codex/gpt-demo"]["output"], 10)
        self.assertEqual(digest["denials"][0]["count"], 2)

    def test_period_filters_events_inside_a_session(self):
        old_assistant = {**OMP[4], "timestamp": OLD}
        old_prompt = {**OMP[3], "timestamp": OLD}
        self.write("omp-sessions/demo/main.jsonl", [*OMP[:3], old_prompt, old_assistant, *OMP[5:]])
        digest = self.run_cli("omp")
        self.assertEqual(digest["prompts_total"], 1)
        self.assertEqual(digest["tools_top"], [])
        self.assertEqual(set(digest["tokens_by_model"]), {"omp:local/tiny"})
        self.assertEqual(digest["tokens_by_model"]["omp:local/tiny"]["total"], 5)
        self.assertEqual(digest["denials_by_tool"], [{"name": "bash / permission denied", "count": 1}])
        self.assertEqual(digest["correction_candidates"], [])

    def test_unrelated_claude_provider_ids_remain_distinct(self):
        self.write("claude/projects/demo/other.jsonl", [{**entry, "sessionId": "other-session"} for entry in CLAUDE])
        digest = self.run_cli("claude")
        self.assertEqual(digest["sessions_total"], 2)
        self.assertEqual(digest["prompts_total"], 6)
        self.assertEqual(digest["tokens_by_model"]["claude:unknown/claude-demo"]["output"], 70)
        self.assertEqual({r["name"]: r["count"] for r in digest["tools_top"]}, {"Bash": 2, "Agent": 4})


    def test_subagents_are_separate_and_tasks_are_not_prompts(self):
        self.write("claude/projects/demo/main/subagents/agent-child.jsonl", [
            CLAUDE[2], CLAUDE[3],  # parent context copied into child
            claude_user(22, "delegated task"),
            claude_assistant(23, "child-model-call", [call("child-tool", "Read")], output=4)])
        child = [{"type": "session", "id": "omp-child", "cwd": "/work/demo", "timestamp": OLD},
                 omp_entry(20, "session_init", agent="scout", modelRole="smol", resolvedModel="openai-codex/gpt-demo", task="delegated task", tools=["read"]),
                 omp_entry(21, message={"role": "user", "content": "delegated task"}),
                 *OMP[1:],  # copied parent tree is not new child activity
                 omp_assistant(22, parent="entry-20", output=9)]
        self.write("omp-sessions/demo/main/child.jsonl", child)
        excluded = self.run_cli()
        included = self.run_cli("both", "--include-subagents")
        self.assertEqual((excluded["sessions_total"], included["sessions_total"]), (2, 4))
        self.assertEqual(included["prompts_total"], excluded["prompts_total"])
        self.assertEqual(included["tokens_by_model"]["claude:unknown/claude-demo"]["output"], 39)
        self.assertEqual(included["tokens_by_model"]["omp:openai-codex/gpt-demo"]["output"], 14)
        self.assertEqual(included["tokens_by_model"]["omp:local/tiny"]["total"], 5)
        self.assertEqual({row["name"]: row["count"] for row in included["denials"]},
                         {"classifier: Git Destructive": 1, "user rejected": 1, "permission denied": 1})
        self.assertEqual(next(r for r in included["sessions"] if r["id"] == "omp:omp-child")["model_role"], "smol")
        self.assertEqual(included["output_tokens_main_vs_subagent"]["subagents"]["claude:unknown/claude-demo"], 4)
        self.assertEqual({r["name"]: r["count"] for r in included["tools_top"]}["Bash"], 1)

    def test_fork_lineage_is_not_subagent_and_copy_history_counts_once(self):
        for marker in ("shared-id", os.path.join(self.omp, "demo", "main.jsonl")):
            header = {**OMP[0], "id": "fork-id", "parentSession": marker}
            self.write("omp-sessions/demo/fork.jsonl", [header, *OMP[1:], omp_entry(10, message={"role": "user", "content": "new fork task"})])
            digest = self.run_cli("omp")
            self.assertEqual(digest["prompts_total"], 3)
            self.assertEqual(digest["tokens_by_model"]["omp:openai-codex/gpt-demo"]["output"], 5)
            self.assertTrue(all(not r["is_subagent"] for r in digest["sessions"]))
            self.assertEqual(digest["tools_top"], [{"name": "bash", "count": 1}])

    def test_distinct_results_prompts_and_branches_survive_dedup(self):
        repeated_result = {**OMP[5], "id": "distinct-result"}
        low = omp_entry(8, "thinking_level_change", parent="entry-1", thinkingLevel="low")
        self.write("omp-sessions/demo/main.jsonl", [*OMP, OMP[4], OMP[5], repeated_result, low,
                                                  omp_assistant(9, parent="entry-8"),
                                                  omp_entry(10, message={"role": "user", "content": "x" * 220 + " first"}),
                                                  omp_entry(11, message={"role": "user", "content": "x" * 220 + " second"})])
        digest = self.run_cli("omp")
        self.assertEqual(digest["denials"][0]["count"], 2)
        self.assertEqual(digest["tokens_by_model"]["omp:openai-codex/gpt-demo"]["output"], 10)
        self.assertEqual({r["effort"] for r in digest["usage_routes"] if r["model"] == "gpt-demo"}, {"high", "low"})
        self.assertEqual(digest["prompts_total"], 4)
        self.assertEqual(len(digest["prompts"]), 4)  # clipped prefixes must not merge distinct intents

    def test_redaction_caps_and_malformed_shape(self):
        self.write("omp-sessions/demo/main.jsonl", [*OMP, {"type": "message", "id": "bad", "parentId": [], "message": []},
                                                  omp_entry(10, message={"role": "assistant", "provider": [], "model": {}, "content": [None, {"type": "toolCall", "name": "task", "arguments": {"agent": {}}}], "usage": []})])
        digest = self.run_cli("both", "--max-prompts", "1", "--max-sessions", "1", "--max-corrections", "0")
        blob = json.dumps(digest)
        self.assertNotIn("synthetic-secret", blob)
        self.assertNotIn("synthetic-token", blob)
        self.assertNotIn("synthetic123456789", blob)
        self.assertIn("[REDACTED]", blob)
        self.assertEqual((len(digest["prompts"]), digest["prompts_omitted"]), (1, 4))
        self.assertEqual((len(digest["sessions"]), digest["sessions_omitted"]), (1, 1))
        self.assertEqual(digest["prompts_total"], 5)
        self.assertEqual(digest["correction_candidates_omitted"], 2)
        self.assertGreaterEqual(digest["diagnostics"]["malformed_records"], 4)

    def test_invalid_header_and_permission_error_are_visible(self):
        self.write("omp-sessions/demo/invalid.jsonl", [omp_assistant(20)])
        digest = self.run_cli("omp")
        self.assertEqual(digest["diagnostics"]["invalid_headers"], 1)
        with mock.patch("builtins.open", side_effect=PermissionError("synthetic denial")):
            digest = self.run_cli("omp")
        self.assertEqual(digest["sessions_total"], 0)
        self.assertEqual(digest["diagnostics"]["unreadable_files"], 2)
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(transcripts.main(["--source", "omp", "--omp-sessions-dir", "/does-not-exist"]), 2)


def codex_record(index, typ, **payload):
    return {"timestamp": TS.format(index), "type": typ, "payload": payload}


def codex_tokens(input_tokens=100, cached=20, write=10, output=5, total=105):
    return {"input_tokens": input_tokens, "cached_input_tokens": cached,
            "cache_write_input_tokens": write, "output_tokens": output,
            "total_tokens": total}


class CodexTranscriptTest(unittest.TestCase):
    write = TranscriptTest.write
    tearDown = TranscriptTest.tearDown

    def setUp(self):
        TranscriptTest.setUp(self)
        self.codex = os.path.join(self.tmp.name, "codex")
        self.base = [
            codex_record(0, "session_meta", id="native", cwd="/work/demo",
                         originator="codex_cli", source="cli", cli_version="synthetic",
                         model_provider="openai"),
            codex_record(1, "turn_context", model="gpt-demo", effort="medium"),
            codex_record(2, "response_item", type="message", role="user",
                         content=[{"type": "input_text", "text": "implement synthetic plan"}]),
        ]
        self.path = self.write("codex/sessions/2026/10/08/rollout-native.jsonl", self.base)

    def run_cli(self, source="both", *extra):
        return TranscriptTest.run_cli(self, source, "--codex-sessions-dir", self.codex, *extra)

    def load_codex(self, records=None):
        if records is not None:
            self.write("codex/sessions/2026/10/08/rollout-native.jsonl", records)
        diagnostics = transcripts.collections.Counter()
        args = transcripts.parse_args(["--source", "codex", "--codex-sessions-dir", self.codex])
        sessions, _ = transcripts.load_sessions(args, diagnostics)
        session = sessions["codex:native"]
        return session, transcripts.normalize(session, diagnostics), diagnostics

    def test_identity_archives_exec_history_and_project(self):
        archived = [
            codex_record(0, "session_meta", id="archive", session_id="ancestor",
                         cwd="/work/demo", originator="codex_exec", source="exec",
                         cli_version="synthetic", history_base={"id": "ancestor"}),
            codex_record(2, "response_item", type="message", role="user", content="exec task"),
        ]
        self.write("codex/archived_sessions/2026/rollout-exec.jsonl", archived)
        self.assertEqual(self.run_cli("codex")["sessions_total"], 1)
        included = self.run_cli("codex", "--include-exec")
        self.assertEqual(included["sessions_total"], 2)
        row = next(r for r in included["sessions"] if r["id"] == "codex:archive")
        self.assertEqual((row["project"], row["parent_lineage"]), ("demo", "ancestor"))
        self.assertTrue(row["automation"])
        self.assertTrue(row["partial_history"])
        session, _, _ = self.load_codex()
        self.assertIsNone(session["parent_lineage"])  # Missing legacy session_id.
        self.assertEqual(self.run_cli("codex", "--project", "2026")["sessions_total"], 0)
        self.assertEqual(set(self.run_cli("both")["roots"]), {"claude", "omp"})

    def test_explicit_spawn_children_nested_lineage_and_cost_split(self):
        parent_usage = codex_record(3, "token_usage_record", usage=codex_tokens())
        self.write("codex/sessions/2026/10/08/rollout-native.jsonl",
                   [*self.base, parent_usage])
        inherited = codex_tokens(1000, 200, 100, 50, 1050)
        for index, sid, parent, role in (
                (10, "child", "native", None), (20, "nested", "child", "quality")):
            source = {"subagent": {"thread_spawn": {
                "parent_thread_id": parent, "depth": index // 10,
                "agent_path": "/root/quality", "agent_nickname": "Synthetic",
                "agent_role": role}}}
            records = [
                codex_record(index, "session_meta", id=sid, session_id="native",
                             cwd="/work/demo", originator="codex_exec", source=source,
                             model_provider="openai"),
                *self.base[1:], parent_usage,  # inherited context and identical response
                codex_record(index + 1, "response_item", type="message", role="user",
                             content="synthetic delegated task " + sid),
                codex_record(index + 2, "response_item", type="function_call",
                             call_id=sid + "-tool", name="shell", arguments="{}"),
                codex_record(index + 3, "event_msg", type="item_completed",
                             item={"call_id": sid + "-tool", "exit_code": 1}),
                codex_record(index + 4, "token_usage_record",
                             usage=codex_tokens(output=index, total=100 + index),
                             thread_token_usage=inherited),
                codex_record(index + 5, "compacted", latest_token_usage_record={
                    "thread_token_usage": inherited})]
            self.write("codex/sessions/2026/10/08/rollout-" + sid + ".jsonl", records)
        excluded = self.run_cli("codex", "--include-exec")
        self.assertEqual(excluded["sessions_total"], 1)
        self.assertEqual(excluded["tokens_by_model"]["codex:openai/gpt-demo"]["output"], 5)
        self.assertEqual(self.run_cli("codex", "--include-subagents")["sessions_total"], 1)
        included = self.run_cli("codex", "--include-exec", "--include-subagents")
        self.assertEqual(included["sessions_total"], 3)
        self.assertEqual(included["prompts_total"], excluded["prompts_total"])
        self.assertEqual(included["tokens_by_model"]["codex:openai/gpt-demo"]["output"], 35)
        self.assertEqual(included["output_tokens_main_vs_subagent"]["main"]["codex:openai/gpt-demo"], 5)
        self.assertEqual(included["output_tokens_main_vs_subagent"]["subagents"]["codex:openai/gpt-demo"], 30)
        self.assertEqual(included["tools_top"], [{"name": "shell", "count": 2}])
        self.assertEqual(sum(r["errors"] for r in included["sessions"]), 2)
        rows = {row["id"]: row for row in included["sessions"]}
        args = transcripts.parse_args(["--source", "codex", "--codex-sessions-dir", self.codex])
        sessions, _ = transcripts.load_sessions(args, transcripts.collections.Counter())
        for sid, parent, depth, role in (
                ("child", "native", 1, None), ("nested", "child", 2, "quality")):
            row = rows["codex:" + sid]
            self.assertTrue(row["is_subagent"])
            self.assertEqual((row["parent_lineage"], row["parent_thread_id"]), (parent, parent))
            self.assertEqual(row["root_lineage"], "native")
            self.assertEqual((row["subagent_depth"], row["agent_path"], row["agent_nickname"],
                              row["agent_role"]), (depth, "/root/quality", "Synthetic", role))
            self.assertEqual(row["codex_source"], sessions["codex:" + sid]["codex_source"])
            self.assertEqual(row["thread_total"]["total"], 1050)
            self.assertEqual((row["prompts"], row["first_prompt"]), (0, None))
            events = transcripts.normalize(sessions["codex:" + sid])
            self.assertFalse(any(event["kind"] == "prompt" for event in events))
        self.assertGreater(included["diagnostics"]["copied_events_skipped"], 0)

    def test_child_tool_id_collisions_require_identical_persisted_payload(self):
        parent_tool = codex_record(3, "response_item", type="function_call",
                                   call_id="same-id", name="shell",
                                   arguments='{"command":"echo parent"}')
        shared_usage = codex_record(4, "token_usage_record", usage=codex_tokens())
        self.write("codex/sessions/2026/10/08/rollout-native.jsonl",
                   [*self.base, parent_tool, shared_usage])
        child_tool = codex_record(13, "response_item", type="function_call",
                                  call_id="same-id", name="shell",
                                  arguments='{"command":"echo child"}')
        self.write("codex/sessions/2026/10/08/rollout-child.jsonl", [
            codex_record(10, "session_meta", id="child", session_id="native",
                         cwd="/work/demo", originator="codex_exec", model_provider="openai",
                         source={"subagent": {"thread_spawn": {"parent_thread_id": "native"}}}),
            *self.base[1:], parent_tool, shared_usage, child_tool,
            codex_record(14, "token_usage_record", usage=codex_tokens(output=7, total=107))])
        digest = self.run_cli("codex", "--include-exec", "--include-subagents")
        self.assertEqual(digest["tools_top"], [{"name": "shell", "count": 2}])
        rows = {row["id"]: row for row in digest["sessions"]}
        self.assertEqual((rows["codex:native"]["tools"], rows["codex:child"]["tools"]), (1, 1))
        self.assertEqual(digest["tokens_by_model"]["codex:openai/gpt-demo"]["output"], 12)
        self.assertEqual(digest["tokens_by_model"]["codex:openai/gpt-demo"]["total"], 212)
        self.assertEqual(digest["output_tokens_main_vs_subagent"]["main"]["codex:openai/gpt-demo"], 5)
        self.assertEqual(digest["output_tokens_main_vs_subagent"]["subagents"]["codex:openai/gpt-demo"], 7)
        # Identical IDs and records outside the proven family remain independent.
        self.write("codex/sessions/2026/10/08/rollout-unrelated.jsonl", [
            codex_record(20, "session_meta", id="unrelated", cwd="/work/demo",
                         originator="codex_exec", source="exec", model_provider="openai"),
            self.base[1], parent_tool, shared_usage])
        independent = self.run_cli("codex", "--include-exec", "--include-subagents")
        self.assertEqual(independent["tools_top"], [{"name": "shell", "count": 3}])
        self.assertEqual(independent["tokens_by_model"]["codex:openai/gpt-demo"]["output"], 17)
        self.assertEqual(independent["tokens_by_model"]["codex:openai/gpt-demo"]["total"], 317)

    def test_fork_lineage_without_spawn_is_not_a_child(self):
        usage = codex_record(3, "token_usage_record", usage=codex_tokens())
        self.write("codex/sessions/2026/10/08/rollout-native.jsonl", [*self.base, usage])
        self.write("codex/sessions/2026/10/08/rollout-fork.jsonl", [
            codex_record(10, "session_meta", id="fork", session_id="native",
                         cwd="/work/demo", originator="codex_cli", source={"future": "opaque"},
                         history_base={"id": "native"}, model_provider="openai"),
            *self.base[1:], usage,
            codex_record(11, "response_item", type="message", role="user", content="new fork task")])
        digest = self.run_cli("codex")
        self.assertEqual((digest["sessions_total"], digest["prompts_total"]), (2, 2))
        self.assertTrue(all(not row["is_subagent"] for row in digest["sessions"]))
        self.assertEqual(digest["tokens_by_model"]["codex:openai/gpt-demo"]["output"], 5)
        fork = next(row for row in digest["sessions"] if row["id"] == "codex:fork")
        self.assertEqual((fork["parent_lineage"], fork["root_lineage"]), ("native", "native"))
        self.assertIsNone(fork["parent_thread_id"])
        self.assertEqual(fork["codex_source"], {"future": "opaque"})

    def test_missing_or_malformed_spawn_is_not_child_proof(self):
        for source in (None, {}, {"subagent": "opaque"},
                       {"subagent": {"thread_spawn": []}},
                       *({"subagent": {"thread_spawn": {"parent_thread_id": parent}}}
                         for parent in (None, "", " ", 12, True, [], {}))):
            with self.subTest(source=source):
                records = [codex_record(0, "session_meta", id="native", session_id="root",
                                       cwd="/work/demo", originator="codex_cli", source=source),
                           *self.base[1:]]
                session, events, _ = self.load_codex(records)
                self.assertFalse(session["is_subagent"])
                self.assertEqual(session["parent_lineage"], "root")
                self.assertEqual(session.get("codex_source"), source)
                self.assertEqual(len([e for e in events if e["kind"] == "prompt"]), 1)

    def test_physical_copies_preserve_spawn_metadata_in_either_order(self):
        source = {"subagent": {"thread_spawn": {
            "parent_thread_id": "parent", "depth": 1,
            "agent_path": "/root/quality", "agent_nickname": "Synthetic", "agent_role": None}}}
        proven = [codex_record(0, "session_meta", id="native", session_id="root",
                               cwd="/work/demo", originator="codex_exec", source=source,
                               history_base={"id": "root"}, model_provider="openai"),
                  *self.base[1:], codex_record(3, "token_usage_record", usage=codex_tokens())]
        incomplete = [codex_record(0, "session_meta", id="native", cwd="/work/demo"),
                      *proven[1:]]
        for original, copy in ((proven, incomplete), (incomplete, proven)):
            self.load_codex(original)
            self.write("codex/sessions/2026/10/08/rollout-zcopy.jsonl", copy)
            session, events, _ = self.load_codex()
            self.assertTrue(session["is_subagent"])
            self.assertTrue(session["automation"])
            self.assertTrue(session["partial_history"])
            self.assertEqual(session["codex_source"], source)
            self.assertEqual((session["parent_lineage"], session["root_lineage"]), ("parent", "root"))
            self.assertEqual(session["subagent_depth"], 1)
            self.assertIsNone(session.get("agent_role"))
            self.assertFalse(any(e["kind"] == "prompt" for e in events))
            digest = self.run_cli("codex", "--include-exec", "--include-subagents")
            self.assertEqual(digest["sessions_total"], 1)
            self.assertEqual(digest["tokens_by_model"]["codex:openai/gpt-demo"]["output"], 5)

    def test_spawn_optional_properties_are_typed_not_inferred(self):
        source = {"subagent": {"thread_spawn": {
            "parent_thread_id": "parent", "depth": True,
            "agent_path": 12, "agent_nickname": "quality", "agent_role": {"name": "quality"}}}}
        session, _, _ = self.load_codex([
            codex_record(0, "session_meta", id="native", source=source), *self.base[1:]])
        self.assertTrue(session["is_subagent"])
        self.assertIsNone(session.get("subagent_depth"))
        self.assertIsNone(session.get("agent_path"))
        self.assertIsNone(session.get("agent_role"))
        self.assertEqual(session["agent_nickname"], "quality")
        self.assertEqual(session["codex_source"], source)

    def test_exec_source_only_evidence_survives_physical_copies(self):
        recorded = [
            codex_record(0, "session_meta", id="native", source="exec"),
            *self.base[1:]]
        incomplete = [
            codex_record(0, "session_meta", id="native"), *self.base[1:]]
        for original, copy in ((recorded, incomplete), (incomplete, recorded)):
            self.load_codex(original)
            self.write("codex/sessions/2026/10/08/rollout-zcopy.jsonl", copy)
            session, _, _ = self.load_codex()
            self.assertTrue(session["automation"])
            self.assertFalse(session["is_subagent"])
            self.assertEqual(self.run_cli("codex")["sessions_total"], 0)
            self.assertEqual(self.run_cli("codex", "--include-exec")["sessions_total"], 1)

    def test_structured_spawn_without_exec_evidence_is_not_automation(self):
        source = {"subagent": {"thread_spawn": {"parent_thread_id": "parent"}}}
        session, _, _ = self.load_codex([
            codex_record(0, "session_meta", id="native", source=source),
            *self.base[1:]])
        self.assertTrue(session["is_subagent"])
        self.assertFalse(session["automation"])
        self.assertEqual(self.run_cli("codex", "--include-subagents")["sessions_total"], 1)

    def test_codex_missing_root_exit_two(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(transcripts.main(["--source", "codex", "--codex-sessions-dir",
                                              os.path.join(self.tmp.name, "absent")]), 2)

    def test_mtime_filter_before_reader_all_sources_and_legacy_namespace(self):
        for source, path in (("codex", self.path),
                             ("claude", os.path.join(self.config, "projects/demo/main.jsonl")),
                             ("omp", os.path.join(self.omp, "demo/main.jsonl"))):
            with self.subTest(source=source):
                os.utime(path, (1, 1))
                args = transcripts.argparse.Namespace(source=source, config_dir=self.config,
                    omp_sessions_dir=self.omp, include_subagents=True)
                if source == "codex":
                    args.codex_sessions_dir = self.codex
                diagnostics = transcripts.collections.Counter()
                with mock.patch.object(transcripts, "read_records") as reader:
                    sessions, _ = transcripts.load_sessions(args, diagnostics, min_mtime=2)
                reader.assert_not_called()
                self.assertEqual(sessions, {})
                self.assertEqual(diagnostics["mtime_skipped"], 1)

    @unittest.skipUnless(zstd is not None, "compression.zstd unavailable")
    def test_compressed_rollout(self):
        path = os.path.join(self.codex, "archived_sessions", "rollout-compressed.jsonl.zst")
        os.makedirs(os.path.dirname(path))
        with zstd.open(path, "wt", encoding="utf-8") as stream:
            for record in self.base:
                stream.write(json.dumps(record) + "\n")
        os.remove(self.path)
        self.assertEqual(self.run_cli("codex")["prompts_total"], 1)

    def test_compressed_skip_is_diagnosable(self):
        path = os.path.join(self.codex, "sessions", "rollout-cold.jsonl.zst")
        with open(path, "wb") as stream:
            stream.write(b"synthetic compressed placeholder")
        original_import = __import__
        def unavailable(name, *args, **kwargs):
            if name == "compression":
                raise ImportError("synthetic unavailable stdlib")
            return original_import(name, *args, **kwargs)
        with mock.patch("builtins.__import__", side_effect=unavailable):
            result = self.run_cli("codex")
        self.assertEqual(result["diagnostics"]["zst_skipped"], 1)
        self.assertEqual(result["prompts_total"], 1)

    def test_per_response_usage_thread_total_and_resume_not_charged(self):
        inherited = codex_tokens(1000, 200, 100, 50, 1050)
        records = [*self.base,
            codex_record(3, "event_msg", type="token_count", info={"total_token_usage": inherited}),
            codex_record(4, "token_usage_record", usage=codex_tokens(),
                         turn_token_usage=inherited, thread_token_usage=inherited),
            codex_record(5, "event_msg", type="token_count",
                         info={"total_token_usage": codex_tokens(1100, 220, 110, 55, 1155)})]
        session, events, _ = self.load_codex(records)
        usage = [e for e in events if e["kind"] == "usage"]
        self.assertEqual(len(usage), 1)
        self.assertEqual(usage[0]["usage"], {"input": 70, "cache_read": 20,
            "cache_creation": 10, "output": 5, "total": 105})
        self.assertEqual(session["thread_total"]["total"], 1050)
        digest = self.run_cli("codex")
        self.assertEqual(digest["sessions"][0]["usage"]["total"], 105)
        self.assertEqual(digest["sessions"][0]["tokens_in_out"], 85)
        self.assertEqual(digest["sessions"][0]["thread_total"]["total"], 1050)

    def test_fallback_consecutive_deltas_ignore_null_and_inherited_baseline(self):
        records = [*self.base,
            codex_record(3, "event_msg", type="token_count", info={
                "total_token_usage": codex_tokens(1000, 200, 100, 50, 1050)}),
            codex_record(4, "event_msg", type="token_count", info=None),
            codex_record(5, "event_msg", type="token_count", info={
                "total_token_usage": codex_tokens(1100, 220, 110, 55, 1155),
                "last_token_usage": codex_tokens(9999, 0, 0, 99, 10098)})]
        session, events, _ = self.load_codex(records)
        usage = [e for e in events if e["kind"] == "usage"]
        self.assertEqual(len(usage), 1)
        self.assertEqual(usage[0]["usage"]["input"], 70)
        self.assertEqual(usage[0]["usage"]["total"], 105)
        self.assertEqual(usage[0]["usage_source"], "token_count")
        self.assertEqual(session["thread_total"]["total"], 1155)
        summary = self.run_cli("codex")["sessions"][0]["usage"]
        self.assertIsNone(summary["total"])
        self.assertEqual(summary["known"]["total"], 105)
        self.assertEqual(summary["completeness"], "partial")
        self.assertTrue(summary["coverage_missing"])

    def test_missing_and_inconsistent_cache_values_stay_unknown(self):
        self.assertIsNone(transcripts.codex_usage({"input_tokens": 5})["input"])
        self.assertIsNone(transcripts.codex_usage(codex_tokens(5, 20, 10))["input"])
        partial = codex_record(3, "token_usage_record", usage={"output_tokens": 7})
        self.load_codex([*self.base, partial])
        usage = self.run_cli("codex")["sessions"][0]["usage"]
        self.assertIsNone(usage["input"])
        self.assertIsNone(usage["total"])
        self.assertEqual(usage["missing"]["input"], 1)
        self.assertEqual(usage["output"], 7)

    def test_model_and_effort_follow_turn_changes_not_turn_count(self):
        _, events, _ = self.load_codex([*self.base,
            codex_record(3, "token_usage_record", usage=codex_tokens()),
            codex_record(4, "event_msg", type="thread_settings_applied", model="gpt-next", effort="high"),
            codex_record(5, "turn_context", model="gpt-next", effort="high"),
            codex_record(6, "token_usage_record", usage=codex_tokens())])
        usage = [e for e in events if e["kind"] == "usage"]
        self.assertEqual([(e["model"], e["effort"], e["provider"]) for e in usage],
                         [("gpt-demo", "medium", "openai"), ("gpt-next", "high", "openai")])

    def test_tool_outputs_explicit_join_and_unjoined_failure(self):
        records = [*self.base,
            codex_record(3, "response_item", type="function_call", call_id="one",
                         name="shell", arguments='{"command":"false"}'),
            codex_record(4, "response_item", type="function_call_output", call_id="one",
                         output="Error word alone is not status"),
            codex_record(5, "event_msg", type="item_completed",
                         item={"call_id": "one", "status": "failed", "exit_code": 1}),
            codex_record(6, "response_item", type="custom_tool_call", call_id="two",
                         name="apply_patch", input="*** Update File: docs/plans/example.md\n"),
            codex_record(7, "response_item", type="custom_tool_call_output", call_id="two",
                         output={"content": [{"type": "text", "text": "structured"}]}),
            codex_record(8, "event_msg", type="item_completed", item={"id": "unjoinable", "status": "failed"}),
            codex_record(9, "response_item", type="function_call", call_id="three", name="mcp", arguments="{}"),
            codex_record(10, "event_msg", type="mcp_tool_call_end", call_id="three",
                         result={"Ok": {"isError": True}})]
        _, events, diagnostics = self.load_codex(records)
        tools = {e["key"]: e for e in events if e["kind"] == "tool"}
        self.assertEqual([tools[k]["status"] for k in ("one", "two", "three")],
                         ["error", "unknown", "error"])
        self.assertEqual(tools["one"]["arguments"]["command"], "false")
        self.assertIn("*** Update File:", tools["two"]["raw_input"])
        self.assertIsInstance(tools["two"]["output"], dict)
        self.assertEqual(diagnostics["unjoined_tool_failures"], 1)
        self.assertEqual(len([e for e in events if e["kind"] == "error"]), 3)

    def test_output_text_never_proves_error_and_unknown_records_count(self):
        _, events, diagnostics = self.load_codex([*self.base,
            codex_record(3, "response_item", type="function_call", call_id="one", name="shell", arguments="{}"),
            codex_record(4, "response_item", type="function_call_output", call_id="one", output="Error: not a status"),
            codex_record(5, "future_record", invented=True),
            codex_record(6, "response_item", type="message", role="developer", content="private instruction"),
            codex_record(7, "response_item", type="message", role="system", content="system instruction")])
        self.assertEqual(next(e for e in events if e["kind"] == "tool")["status"], "unknown")
        self.assertFalse(any(e["kind"] == "error" for e in events))
        self.assertEqual(diagnostics["unknown_codex_records"], 1)
        self.assertEqual(len([e for e in events if e["kind"] == "prompt"]), 1)

    def test_explicit_success_and_checkpoint_not_usage_events(self):
        checkpoint = codex_tokens(1000, 200, 100, 50, 1050)
        _, events, _ = self.load_codex([*self.base,
            codex_record(3, "response_item", type="function_call", call_id="ok",
                         name="shell", arguments="{}"),
            codex_record(4, "event_msg", type="item_completed",
                         item={"call_id": "ok", "exit_code": 0}),
            codex_record(5, "response_item", type="function_call", call_id="mcp",
                         name="mcp", arguments="{}"),
            codex_record(6, "response_item", type="function_call_output", call_id="mcp",
                         output={"isError": False, "content": []}),
            codex_record(7, "compacted", latest_token_usage_record={
                "usage": codex_tokens(), "thread_token_usage": checkpoint})])
        tools = [e for e in events if e["kind"] == "tool"]
        self.assertTrue(all(e["status"] == "success" for e in tools))
        self.assertEqual(tools[0]["duration_seconds"], 1)
        self.assertFalse(any(e["kind"] in ("usage", "error") for e in events))
        self.assertEqual(self.run_cli("codex")["sessions"][0]["thread_total"]["total"], 1050)

    def test_fallback_baseline_bounds_digest_coverage_without_charging_history(self):
        baseline = codex_record(3, "event_msg", type="token_count",
                                info={"total_token_usage": codex_tokens(1000, 200, 100, 50, 1050)})
        baseline["timestamp"] = "2098-12-31T23:59:00Z"
        final = codex_record(5, "event_msg", type="token_count",
                             info={"total_token_usage": codex_tokens(1100, 220, 110, 55, 1155)})
        session, events, _ = self.load_codex([baseline, *self.base, final])
        self.assertEqual(session["usage_baseline_time"], "2098-12-31T23:59:00+00:00")
        self.assertEqual(session["usage_coverage_end"], transcripts.timestamp(TS.format(5)).isoformat())
        event = next(e for e in events if e["kind"] == "usage")
        self.assertEqual(event["usage_interval_start"], session["usage_baseline_time"])
        self.assertEqual(event["usage"]["total"], 105)
        boundary = transcripts.timestamp("2099-01-01T00:00:00Z")
        with mock.patch.object(transcripts, "since_time", return_value=boundary):
            summary = self.run_cli("codex")["sessions"][0]["usage"]
        self.assertEqual((summary["total"], summary["completeness"]), (105, "observed"))
        self.assertFalse(summary["coverage_missing"])
        baseline["timestamp"] = TS.format(3)
        self.load_codex([*self.base, baseline, final])
        with mock.patch.object(transcripts, "since_time", return_value=boundary):
            digest = self.run_cli("codex")
        for summary in (digest["sessions"][0]["usage"],
                        digest["usage_routes"][0]["usage"],
                        digest["tokens_by_model"]["codex:openai/gpt-demo"]):
            self.assertIsNone(summary["total"])
            self.assertEqual(summary["known"]["total"], 105)
            self.assertEqual(summary["completeness"], "partial")
        self.assertIsNone(digest["sessions"][0]["tokens_in_out"])

    def test_fallback_one_or_untimed_baseline_does_not_claim_complete_usage(self):
        first = codex_record(3, "event_msg", type="token_count",
                             info={"total_token_usage": codex_tokens()})
        _, events, _ = self.load_codex([*self.base, first])
        self.assertFalse(any(e["kind"] == "usage" for e in events))
        summary = self.run_cli("codex")["sessions"][0]["usage"]
        self.assertEqual(summary["completeness"], "unknown")
        self.assertIsNone(summary["known"]["total"])
        first.pop("timestamp")
        final = codex_record(5, "event_msg", type="token_count",
                             info={"total_token_usage": codex_tokens(200, 40, 20, 10, 210)})
        session, _, _ = self.load_codex([first, *self.base, final])
        self.assertIsNone(session["usage_baseline_time"])
        summary = self.run_cli("codex")["sessions"][0]["usage"]
        self.assertEqual(summary["completeness"], "partial")
        self.assertEqual(summary["known"]["total"], 105)
        self.assertIsNone(summary["total"])

    def test_joined_output_elapsed_independent_of_status_and_error_at_result(self):
        records = [*self.base,
            codex_record(3, "response_item", type="function_call", call_id="unknown",
                         name="exec_command", arguments='{"command":"sleep 6"}'),
            codex_record(9, "response_item", type="function_call_output", call_id="unknown",
                         output="Error word is not an explicit status"),
            codex_record(10, "response_item", type="custom_tool_call", call_id="failed",
                         name="apply_patch", input="synthetic patch"),
            codex_record(15, "response_item", type="custom_tool_call_output", call_id="failed",
                         output={"isError": True, "content": []})]
        _, events, _ = self.load_codex(records)
        tools = {e["key"]: e for e in events if e["kind"] == "tool"}
        self.assertEqual(tools["unknown"]["status"], "unknown")
        self.assertEqual(tools["unknown"]["duration_seconds"], 6)
        self.assertEqual(tools["unknown"]["duration_source"], "call_to_result_elapsed")
        self.assertEqual(tools["failed"]["duration_seconds"], 5)
        self.assertEqual(tools["failed"]["result_time"], transcripts.timestamp(TS.format(15)))
        error = next(e for e in events if e["kind"] == "error")
        self.assertEqual(error["time"], transcripts.timestamp(TS.format(15)))
        self.assertEqual(error["tool_id"], "failed")

    def test_missing_or_reversed_tool_timestamps_never_invent_elapsed(self):
        untimed = codex_record(3, "response_item", type="function_call", call_id="untimed",
                               name="shell", arguments="{}")
        untimed.pop("timestamp")
        _, events, _ = self.load_codex([*self.base, untimed,
            codex_record(4, "response_item", type="function_call_output", call_id="untimed", output="ok"),
            codex_record(10, "response_item", type="function_call", call_id="reversed", name="shell", arguments="{}"),
            codex_record(5, "response_item", type="function_call_output", call_id="reversed", output="ok")])
        tools = [e for e in events if e["kind"] == "tool"]
        self.assertEqual(len(tools), 2)
        self.assertTrue(all("duration_seconds" not in e for e in tools))


if __name__ == "__main__":
    unittest.main()
