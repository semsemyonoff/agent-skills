import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orchestration

DAY = "2099-01-02T10:{:02d}:{:02d}.000Z"


def ts(minute, second=0):
    return DAY.format(minute, second)


def c_assistant(minute, mid, ctx, tools=(), text=None, model="claude-demo"):
    content = [{"type": "text", "text": text}] if text else []
    content += [{"type": "tool_use", "id": f"{mid}-{i}", "name": n, "input": a} for i, (n, a) in enumerate(tools)]
    return {"type": "assistant", "timestamp": ts(minute), "sessionId": "p1", "cwd": "/work/demo",
            "message": {"id": mid, "model": model, "content": content,
                        "usage": {"input_tokens": 0, "cache_creation_input_tokens": 0,
                                  "cache_read_input_tokens": ctx, "output_tokens": 10}}}


def c_user(minute, content, **extra):
    return {"type": "user", "timestamp": ts(minute), "sessionId": "p1", "cwd": "/work/demo",
            "message": {"role": "user", "content": content}, **extra}


def o_entry(minute, typ="message", **extra):
    return {"type": typ, "id": f"e{minute}-{len(extra)}", "timestamp": ts(minute), **extra}


def o_assistant(minute, ctx, tools=(), cost=0.5, text=None):
    content = [{"type": "text", "text": text}] if text else []
    content += [{"type": "toolCall", "id": f"c{minute}{i}", "name": n, "arguments": a} for i, (n, a) in enumerate(tools)]
    return o_entry(minute, message={"role": "assistant", "model": "gpt-demo", "content": content,
                                    "usage": {"input": 0, "cacheRead": ctx, "cacheWrite": 0, "output": 10,
                                              "cost": {"total": cost}}})


def write(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(json.dumps(r) for r in rows) + "\n")


def claude_tree(root):
    bucket = os.path.join(root, "projects", "-work-demo")
    write(os.path.join(bucket, "p1.jsonl"), [
        c_user(0, "fix it"),
        c_assistant(1, "m1", 1000, [("Read", {"file_path": "/work/demo/a.py"})]),
        c_assistant(2, "m2", 2000, [("Skill", {"skill": "flow:orchestrate"})]),
        c_assistant(3, "m3", 5000, [("Read", {"file_path": "/work/demo/b.py"})]),
        c_assistant(4, "m4", 6000, [("Agent", {"subagent_type": "flow:flow-implementation"})],
                    text="| slice | owner |\n|---|---|\n| a | worker |"),
        c_assistant(5, "m5", 7000, [("Edit", {"file_path": "/work/demo/c.py"})]),
        c_assistant(6, "m6", 7500, text="Waiting for the worker."),
        c_user(40, "status?"),
        c_assistant(41, "m7", 9000, [("Bash", {"command": "git push"})]),
    ])
    sub = os.path.join(bucket, "p1", "subagents")
    write(os.path.join(sub, "agent-a.jsonl"), [
        c_user(5, "brief", isSidechain=True),
        c_assistant(5, "w1", 300, [("Edit", {"file_path": "/work/demo/c.py"})], model="claude-small"),
        c_assistant(35, "w2", 900, [("Bash", {"command": "pytest"})], model="claude-small"),
        c_user(36, "[Request interrupted by user]", isSidechain=True),
    ])
    with open(os.path.join(sub, "agent-a.meta.json"), "w") as fh:
        json.dump({"agentType": "flow:flow-implementation", "description": "Slice A"}, fh)
    write(os.path.join(sub, "agent-b.jsonl"), [
        c_user(6, "review brief", isSidechain=True),
        c_assistant(6, "r1", 400, model="claude-big"),
        c_user(38, "The coordinator sent a message while you were working: re-check", isSidechain=True, isMeta=True),
        c_assistant(39, "r2", 600, model="claude-big"),
    ])
    plain = [c_user(0, "no skill here"), c_assistant(1, "x1", 1000, [("Read", {"file_path": "/x"})])]
    for row in plain:
        row["sessionId"] = "plain"
    write(os.path.join(bucket, "plain.jsonl"), plain)


def omp_tree(root):
    bucket = os.path.join(root, "--work-demo--")
    parent = os.path.join(bucket, "2099-01-02T10-00-00-000Z_o1.jsonl")
    write(parent, [
        {"type": "session", "version": 3, "id": "o1", "timestamp": ts(0), "cwd": "/work/demo"},
        o_entry(1, message={"role": "user", "content": [{"type": "text", "text": "do it"}]}),
        o_entry(2, "custom_message", customType="skill-prompt",
                content='[IMPORTANT: User invoked the "orchestrate" skill; follow its instructions.]'),
        o_assistant(3, 1000, [("read", {"path": "src/a.ts"})]),
        o_assistant(4, 3000, [("task", {"tasks": [{"agent": "flow-worker-light"}]})]),
        o_assistant(5, 4000, [("edit", {"input": "*** Begin Patch\n[src/b.ts#AB12]\nPUT >1:\n+x\n*** End Patch"})]),
        o_assistant(6, 4500, [("write", {"path": "xd://mcp__forgejo_create_pull_request"})]),
    ])
    write(os.path.join(parent[:-6], "Light.jsonl"), [
        {"type": "session", "version": 3, "id": "o1-child", "timestamp": ts(4), "cwd": "/work/demo",
         "parentSession": parent},
        {"type": "session_init", "id": "i1", "timestamp": ts(4), "agent": "flow-worker-light"},
        {"type": "thinking_level_change", "id": "t1", "timestamp": ts(4), "thinkingLevel": "medium"},
        o_entry(4, message={"role": "user", "content": [{"type": "text", "text": "brief"}]}),
        o_assistant(5, 200, [("edit", {"input": "[src/c.ts#CD34]"})], cost=0.01),
    ])


def run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = orchestration.main(argv)
    return code, buf.getvalue()


class ClaudeOrchestration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        claude_tree(self.tmp.name)
        code, out = run(["--source", "claude", "--since", "2099-01-01", "--config-dir", self.tmp.name, "--out", "json"])
        self.assertEqual(code, 0)
        self.report = json.loads(out)
        self.session = self.report["sessions"][0]

    def tearDown(self):
        self.tmp.cleanup()

    def test_selects_only_orchestrated_sessions(self):
        self.assertEqual(self.report["sessions_total"], 1)
        self.assertEqual(self.session["session"], "claude:p1")
        self.assertTrue(self.session["skill_loaded"].startswith("2099-01-02T10:02"))

    def test_splits_coordinator_usage_at_skill_load(self):
        coord = self.session["coordinator"]
        self.assertEqual(coord["before"]["calls"], 1)
        self.assertEqual(coord["after"]["calls"], 6)
        self.assertEqual(coord["after"]["peak_context"], 9000)
        self.assertEqual(coord["edits_after_skill"], 1)
        self.assertEqual(coord["edited_files_top"], [["/work/demo/c.py", 1]])
        self.assertAlmostEqual(sum(coord["growth_share_pct"].values()), 100, delta=0.5)
        self.assertIn("recon", coord["growth_share_pct"])

    def test_worker_stall_interrupt_and_follow_up(self):
        workers = {w["description"]: w for w in self.session["workers"]}
        a, b = workers["Slice A"], workers[""]
        self.assertTrue(a["stall_candidate"])
        self.assertTrue(a["ended_interrupted"])
        self.assertEqual(a["max_working_gap_minutes"], 30.0)
        self.assertEqual(a["edits"], 1)
        self.assertEqual(a["models"], ["claude-small"])
        # Waiting for the parent's next message is idle time, not a stall.
        self.assertFalse(b["stall_candidate"])
        self.assertEqual(b["follow_up_messages"], 1)
        # Replay puts the worker's calls on the coordinator context at spawn (m5: 7000 at 10:05).
        self.assertEqual(a["replay_tokens_estimate"], (7000 + 0 + 10) + (7000 + 600 + 10))

    def test_excerpts_and_idle_notice(self):
        self.assertIn("| slice | owner |", self.session["first_table_excerpt"]["text"])
        notices = self.session["idle_notices"]
        self.assertEqual(notices[0]["text"], "Waiting for the worker.")
        self.assertGreaterEqual(notices[0]["idle_minutes"], 30)

    def test_period_and_project_filters(self):
        code, out = run(["--source", "claude", "--since", "2099-02-01", "--config-dir", self.tmp.name, "--out", "json"])
        self.assertEqual(json.loads(out)["sessions_total"], 0)
        code, out = run(["--source", "claude", "--since", "2099-01-01", "--project", "other",
                         "--config-dir", self.tmp.name, "--out", "json"])
        self.assertEqual(json.loads(out)["sessions_total"], 0)

    def test_markdown_renders(self):
        code, out = run(["--source", "claude", "--since", "2099-01-01", "--config-dir", self.tmp.name])
        self.assertEqual(code, 0)
        self.assertIn("stall,interrupted", out)
        self.assertIn("## Caveats", out)


class OmpOrchestration(unittest.TestCase):
    def test_reads_skill_prompt_children_cost_and_patch_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            omp_tree(tmp)
            code, out = run(["--source", "omp", "--since", "2099-01-01", "--omp-sessions-dir", tmp, "--out", "json"])
            self.assertEqual(code, 0)
            report = json.loads(out)
            s = report["sessions"][0]
            self.assertEqual(s["session"], "omp:o1")
            self.assertEqual(s["coordinator"]["after"]["cost"], 2.0)
            self.assertEqual(s["coordinator"]["edited_files_top"], [["src/b.ts", 1]])
            [w] = s["workers"]
            self.assertEqual((w["agent"], w["thinking"], w["description"]), ("flow-worker-light", "medium", "Light"))
            self.assertEqual(w["edits"], 1)
            self.assertEqual(w["cost"], 0.01)

    def test_missing_root_is_an_error(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code, _ = run(["--source", "omp", "--omp-sessions-dir", "/nonexistent/omp-root"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
