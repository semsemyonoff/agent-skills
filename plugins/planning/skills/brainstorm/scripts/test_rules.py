"""Behavioral boundaries for the bundled read-only rule resolver."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("load_rules.py")


class RuleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        # The loader resolves the project dir; macOS temp dirs sit behind the /var symlink.
        self.root = Path(self.tmp.name).resolve()
        self.project = self.root / "project"
        self.project.mkdir()
        self.home = self.root / "home"
        self.home.mkdir()
        self.env = {"HOME": str(self.home), "PATH": os.defpath}

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def run_loader(self, name="planning", explicit=True):
        command = [sys.executable, str(SCRIPT), "--name", name]
        if explicit:
            command += ["--project", str(self.project)]
        result = subprocess.run(command, cwd=self.project if not explicit else self.root,
                                env=self.env, text=True, capture_output=True, check=True)
        return json.loads(result.stdout)

    def test_first_nonempty_project_rule_wins_without_merging(self):
        for name in ("brainstorm", "planning"):
            with self.subTest(name=name):
                filename = name + "-rules.md"
                agents = self.project / ".agents" / filename
                claude = self.project / ".claude" / filename
                user = self.home / ".config" / "agent-skills" / filename
                self.put(user, "user rule")
                self.put(claude, "Claude project rule")
                self.put(agents, "Правило проекта")
                self.assertEqual(self.run_loader(name), {
                    "name": name, "path": str(agents), "provenance": "project-agents",
                    "content": "Правило проекта"})
                self.put(agents, "")
                self.assertEqual(self.run_loader(name)["content"], "Claude project rule")
                self.put(claude, "")
                self.assertEqual(self.run_loader(name)["provenance"], "user")
                self.assertEqual(user.read_text(), "user rule")

    def test_missing_rules_and_empty_xdg_use_home_default(self):
        self.assertEqual(self.run_loader(), {
            "name": "planning", "path": None, "provenance": None, "content": ""})
        self.env["XDG_CONFIG_HOME"] = ""
        self.put(self.home / ".config" / "agent-skills" / "planning-rules.md", "home rule")
        self.assertEqual(self.run_loader()["content"], "home rule")

    def test_xdg_override_and_symlink_are_used_not_claude_environment(self):
        config = self.root / "config"
        self.env.update(XDG_CONFIG_HOME=str(config), CLAUDE_PLUGIN_DATA=str(self.root / "old-data"))
        self.put(self.home / ".config" / "agent-skills" / "planning-rules.md", "wrong home rule")
        self.put(self.root / "old-data" / "planning-rules.md", "wrong Claude data rule")
        target = self.root / "existing-personal-rule.md"
        self.put(target, "existing rule")
        link = config / "agent-skills" / "planning-rules.md"
        link.parent.mkdir(parents=True)
        link.symlink_to(target)
        result = self.run_loader()
        self.assertEqual((result["path"], result["provenance"], result["content"]),
                         (str(link), "user", "existing rule"))
        self.assertEqual(target.read_text(), "existing rule")

    def test_actual_cwd_is_default_and_whitespace_matches_upstream(self):
        self.put(self.project / ".agents" / "planning-rules.md", " \n")
        self.put(self.project / ".claude" / "planning-rules.md", "lower rule")
        self.assertEqual(self.run_loader(explicit=False)["content"], " \n")


if __name__ == "__main__":
    unittest.main()
