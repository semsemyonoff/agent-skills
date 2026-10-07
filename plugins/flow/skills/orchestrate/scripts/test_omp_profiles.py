"""Profile inventory fixtures; no live configuration, extensions or model calls."""

import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("omp_profiles.py")
SPEC = importlib.util.spec_from_file_location("omp_profiles", SCRIPT)
PROFILES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROFILES)


class InventoryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.values = {
            "modelRoles": {"light": "provider/light:medium", "strong": "provider/strong:high"},
            "task.agentModelOverrides": {}, "task.disabledAgents": [],
            "task.enableEffort": False, "task.maxEffort": "high",
        }
        self.status = dict.fromkeys(PROFILES.CONFIG_KEYS, "ok")

    def agent(self, directory="user", filename="worker.md", extra="", name="worker"):
        path = self.root / directory / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'---\nname: {name}\ndescription: A worker.\n{extra}---\nBody.\n')
        return path

    def inventory(self, *roots):
        return PROFILES.inventory([(kind, self.root / path) for kind, path in roots], self.values, self.status)

    def test_csv_and_block_frontmatter_with_comments(self):
        path = self.agent(extra='model: "@light" # route\ntools: read, bash, lsp # tools\nspawns:\n  - helper\nthinking: medium\n')
        fields = PROFILES.frontmatter(path)
        self.assertEqual(fields["model"], ["@light"])
        self.assertEqual(fields["tools"], ["read", "bash", "lsp"])
        self.assertEqual(fields["spawns"], ["helper"])
        self.assertEqual(fields["thinking-level"], "medium")

    def test_quoted_list_empty_tools_and_multiline_description(self):
        path = self.root / "agent.md"
        path.write_text('---\nname: worker\ndescription: >\n  Wrapped description.\nmodel: ["@light", \'provider/strong:high\']\ntools: []\nspawns: []\n---\n')
        fields = PROFILES.frontmatter(path)
        self.assertEqual(fields["tools"], [])
        self.assertEqual(fields["model"], ["@light", "provider/strong:high"])

    def test_bad_frontmatter_is_reported_not_silently_defaulted(self):
        for extra in ('tools: {bash: true}\n', 'tools: [read, false]\n', 'model: &alias value\n', 'thinking: nonsense\n', 'model: "unterminated\n'):
            with self.subTest(extra=extra):
                self.agent(extra=extra)
                rows, issues = self.inventory(("user", "user"))
                self.assertEqual(rows, [])
                self.assertEqual(len(issues), 1)

    def test_first_wins_exact_name_and_shadowed_locations(self):
        project = self.agent("project", extra='model: "@light"\n')
        user = self.agent("user", extra='model: "@strong"\n')
        extension = self.agent("extension", extra='model: "@strong"\n')
        self.agent("user", "different-case.md", name="Worker")
        rows, issues = self.inventory(("project", "project"), ("user", "user"), ("extension", "extension"))
        row = next(item for item in rows if item["name"] == "worker")
        self.assertEqual(row["winner_in_inspected_roots"]["path"], str(project))
        self.assertEqual([item["path"] for item in row["shadowed"]], [str(user), str(extension)])
        self.assertEqual(len(rows), 2)
        self.assertEqual(issues, [])

    def test_sorted_filename_precedence_within_root(self):
        self.agent(filename="z.md", extra='model: "@strong"\n')
        first = self.agent(filename="a.md", extra='model: "@light"\n')
        rows, _ = self.inventory(("user", "user"))
        self.assertEqual(rows[0]["winner_in_inspected_roots"]["path"], str(first))

    def test_nearest_project_root_and_symlink_target(self):
        outer = self.agent(".omp/agents")
        nested = self.root / "nested"
        nested.mkdir()
        self.assertEqual(PROFILES.project_root(nested), outer.parent)
        (nested / ".omp").mkdir()
        self.assertIsNone(PROFILES.project_root(nested))
        linked = self.root / "user" / "linked.md"
        linked.parent.mkdir()
        linked.symlink_to(outer)
        rows, _ = self.inventory(("user", "user"))
        self.assertEqual(rows[0]["winner_in_inspected_roots"]["target"], str(outer.resolve()))

    def test_override_role_chain_order_thinking_and_disabled(self):
        self.agent(extra='model: "@strong"\nthinking-level: high\ntools: [read, bash, eval, lsp]\nspawns: []\n')
        self.values["task.agentModelOverrides"] = {"worker": "@chain:low"}
        self.values["modelRoles"]["chain"] = ["@light", "@strong"]
        self.values["task.disabledAgents"] = ["worker"]
        rows, issues = self.inventory(("user", "user"))
        row = rows[0]
        self.assertEqual(row["model"], ["@strong"])
        self.assertEqual(row["effective_selector"], ["@chain:low"])
        self.assertEqual([item["selector"] for item in row["expanded"]], ["provider/light:low", "provider/strong:low"])
        self.assertEqual(row["expanded"][0]["roles"], ["chain", "light"])
        self.assertEqual(row["thinking_level"], "high")  # Declared, not guessed runtime precedence.
        self.assertTrue(row["disabled"])
        self.assertIsNone(row["capabilities"]["eval_browser"])
        self.assertEqual(issues, [])

    def test_default_is_live_parent_not_saved_default_role(self):
        result = PROFILES.expand_models(["@default", "*", "@chain:high"], {"default": "wrong", "chain": "@default"})
        self.assertTrue(all(item["status"] == "parent model unknown" for item in result))
        self.assertEqual(result[2]["selector"], "@default:high")

    def test_role_cycle_and_unset_roles_remain_unknown(self):
        result = PROFILES.expand_models(["@a", "@missing"], {"a": "@b", "b": "@a"})
        self.assertEqual([item["status"] for item in result], ["role cycle", "role unset/unavailable"])

    def test_empty_role_and_missing_disabled_key_are_not_false_certainty(self):
        result = PROFILES.expand_models(["@empty"], {"empty": []})
        self.assertEqual(result[0]["status"], "role has no selectors")
        self.agent()
        del self.values["task.disabledAgents"]
        self.status["task.disabledAgents"] = "unset"
        rows, _ = self.inventory(("user", "user"))
        self.assertIsNone(rows[0]["disabled"])

    def test_claude_plugin_model_is_discarded_not_a_native_selector(self):
        self.agent("plugin", extra='model: sonnet\n')
        rows, _ = self.inventory(("claude-plugin", "plugin"))
        self.assertIsNone(rows[0]["model"])
        self.assertEqual(rows[0]["route_status"], "profile/default route unknown")

    def test_missing_override_configuration_never_claims_effective_model(self):
        self.agent(extra='model: "@light"\n')
        self.status["task.agentModelOverrides"] = "unset"
        rows, _ = self.inventory(("user", "user"))
        self.assertIsNone(rows[0]["effective_selector"])
        self.assertEqual(rows[0]["expanded"], [])

    def test_override_only_name_keeps_unknown_definition_and_capabilities(self):
        self.values["task.agentModelOverrides"] = {"scout": "@light"}
        rows, _ = self.inventory()
        self.assertIsNone(rows[0]["winner_in_inspected_roots"])
        self.assertIsNone(rows[0]["capabilities"]["bash"])
        self.assertEqual(rows[0]["expanded"][0]["selector"], "provider/light:medium")

    def test_tools_do_not_promise_eval_browser_or_default_toolset(self):
        self.assertIsNone(PROFILES.capabilities(None)["browser"])
        self.assertTrue(PROFILES.capabilities(["Bash", "LSP"])["bash"])
        self.assertFalse(PROFILES.capabilities(["bash"])["browser"])
        self.assertIsNone(PROFILES.capabilities(["eval"])["eval_browser"])
        self.assertTrue(PROFILES.capabilities(["mcp__playwright__browser_snapshot"])["browser"])

    def test_config_reads_only_allowlisted_keys_and_validates_envelope(self):
        calls = []

        def read(command, cwd):
            calls.append(command)
            key = command[-2]
            return json.dumps({"key": key, "value": self.values[key]}), None

        with patch.object(PROFILES, "run_read", side_effect=read):
            values, status = PROFILES.read_config(["omp"], self.root)
        self.assertEqual(values, self.values)
        self.assertEqual(status, self.status)
        self.assertEqual(calls, [["omp", "config", "get", key, "--json"] for key in PROFILES.CONFIG_KEYS])

    def test_unset_malformed_and_failed_config_are_explicit(self):
        for output, error, expected in (("{}", None, "invalid JSON/value"),
                                        ("not json", None, "invalid JSON/value"),
                                        (None, "command failed (exit 1)", "command failed (exit 1)")):
            with self.subTest(output=output), patch.object(PROFILES, "run_read", return_value=(output, error)):
                values, status = PROFILES.read_config(["omp"], self.root)
                self.assertEqual(values, {})
                self.assertTrue(all(value == expected for value in status.values()))
        with patch.object(PROFILES, "run_read", side_effect=lambda command, cwd: (json.dumps({"key": command[-2]}), None)):
            values, status = PROFILES.read_config(["omp"], self.root)
        self.assertTrue(all(value == "unset" for value in status.values()))

    def test_cli_uses_native_config_path_and_profile_without_dumping_roles(self):
        self.agent("active/agents", extra='model: "@light"\n')
        self.values["modelRoles"]["unrelated"] = "DO_NOT_PRINT"

        def read(command, cwd):
            self.assertEqual(command[:3], ["/fake/omp", "--profile", "work"])
            if command[-1] == "path":
                return str(self.root / "active"), None
            key = command[-2]
            return json.dumps({"key": key, "value": self.values[key]}), None

        stream = io.StringIO()
        with patch.object(PROFILES.shutil, "which", return_value="/fake/omp"), patch.object(PROFILES, "run_read", side_effect=read), contextlib.redirect_stdout(stream):
            rc = PROFILES.main(["--cwd", str(self.root), "--profile", "work", "--json"])
        self.assertEqual(rc, 0)
        self.assertNotIn("DO_NOT_PRINT", stream.getvalue())
        self.assertEqual(json.loads(stream.getvalue())["profiles"][0]["name"], "worker")

    def test_missing_omp_cli_reports_unknown_without_guessing_user_root(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--omp", str(self.root / "absent"),
                                 "--cwd", str(self.root), "--json"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(report["roots"], [])
        self.assertTrue(all(value == "omp unavailable" for value in report["config_status"].values()))

    def test_command_errors_never_echo_arbitrary_stderr(self):
        result = subprocess.CompletedProcess(["omp"], 2, "", "secret contents")
        with patch.object(PROFILES.subprocess, "run", return_value=result):
            output, error = PROFILES.run_read(["omp", "config", "path"], self.root)
        self.assertIsNone(output)
        self.assertEqual(error, "command failed (exit 2)")


if __name__ == "__main__":
    unittest.main()
