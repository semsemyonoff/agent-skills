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


if __name__ == "__main__":
    unittest.main()
