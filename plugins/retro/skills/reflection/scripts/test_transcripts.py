import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import transcripts  # noqa: E402

TS = "2099-01-02T10:00:0{}.000Z"


def ev(i, typ, message, **extra):
    d = {"type": typ, "timestamp": TS.format(i), "cwd": "/work/demo", "entrypoint": "cli", "message": message}
    d.update(extra)
    return d


def user(i, content, **extra):
    return ev(i, "user", {"role": "user", "content": content}, **extra)


def assistant(i, mid, blocks, model="claude-opus-x", out=10):
    return ev(i, "assistant", {"id": mid, "model": model, "content": blocks, "usage": {
        "input_tokens": 1, "cache_creation_input_tokens": 100, "cache_read_input_tokens": 1000, "output_tokens": out}})


def tool_use(tid, name, **inp):
    return {"type": "tool_use", "id": tid, "name": name, "input": inp}


def tool_result(tid, text, err=True):
    return {"type": "tool_result", "tool_use_id": tid, "content": text, "is_error": err}


FIXTURE = [
    user(1, "deploy the service, password: hunter2secret"),
    user(1, "<system-reminder>ignore me</system-reminder>"),
    assistant(2, "m1", [tool_use("t1", "Bash", command="ls")]),
    assistant(2, "m1", [tool_use("t1", "Bash", command="ls")], out=25),  # streaming repeat
    user(3, [tool_result("t1", "Exit code 1\nboom /a/b/c 42")]),
    assistant(4, "m2", [tool_use("t2", "Agent", model="sonnet", subagent_type="Explore"),
                        tool_use("t3", "Agent", subagent_type="general-purpose")]),
    user(5, [tool_result("t2", "Permission for this action was denied by the Claude Code auto mode classifier. Reason: [Git Destructive]. x")]),
    user(6, [tool_result("t3", "The user doesn't want to proceed with this tool use. The tool use was rejected")]),
    user(7, "нет, не так, поправь"),
    user(8, "<command-name>/clear</command-name><command-args></command-args>"),
    user(9, "Bearer abcdefghijklmnop1234 is my header", isMeta=True),
]


class TranscriptTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        proj = os.path.join(self.tmp.name, "projects", "-work-demo")
        os.makedirs(proj)
        with open(os.path.join(proj, "aaaaaaaa-1111.jsonl"), "w") as f:
            f.write("not json\n")
            for e in FIXTURE:
                f.write(json.dumps(e) + "\n")
        sdk = dict(FIXTURE[0], entrypoint="sdk-cli")
        with open(os.path.join(proj, "bbbbbbbb-2222.jsonl"), "w") as f:
            f.write(json.dumps(sdk) + "\n")
        future = 4102444800  # 2100-01-01; files must look fresh to the mtime pre-filter
        for n in os.listdir(proj):
            os.utime(os.path.join(proj, n), (future, future))

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *extra):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = transcripts.main(["--since", "2099-01-01", "--config-dir", self.tmp.name, "--out", "json", *extra])
        self.assertEqual(rc, 0)
        return json.loads(buf.getvalue())

    def test_digest(self):
        o = self.run_cli()
        self.assertEqual(o["sessions_total"], 1)  # sdk session excluded
        self.assertEqual(o["prompts_total"], 3)   # prompt, correction, /clear; meta and tool_results skipped
        self.assertEqual({t["name"]: t["count"] for t in o["tools_top"]}, {"Bash": 1, "Agent": 2})  # streamed tool_use counted once
        self.assertEqual(o["subagent_model_set"], 1)
        self.assertEqual(o["subagent_model_unset"], 1)
        names = {d["name"]: d["count"] for d in o["denials"]}
        self.assertEqual(names, {"classifier: Git Destructive": 1, "user rejected": 1})
        self.assertEqual(o["errors_top"][0]["name"], "Bash: Exit code N")
        t = o["tokens_by_model"]["claude-opus-x"]
        self.assertEqual((t["output"], t["messages"], t["cache_read"]), (25 + 10, 2, 2000))
        self.assertEqual(len(o["correction_candidates"]), 1)

    def test_redaction(self):
        o = self.run_cli()
        blob = json.dumps(o)
        self.assertNotIn("hunter2secret", blob)
        self.assertNotIn("abcdefghijklmnop1234", blob)
        self.assertIn("/clear", blob)

    def test_project_filter_and_sdk(self):
        self.assertEqual(self.run_cli("--project", "nomatch")["sessions_total"], 0)
        self.assertEqual(self.run_cli("--include-sdk")["sessions_total"], 2)

    def test_since_excludes_old(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            transcripts.main(["--since", "2100-01-05", "--config-dir", self.tmp.name, "--out", "json"])
        self.assertEqual(json.loads(buf.getvalue())["sessions_total"], 0)

    def test_md_output(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            transcripts.main(["--since", "2099-01-01", "--config-dir", self.tmp.name])
        self.assertIn("## Correction candidates", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
