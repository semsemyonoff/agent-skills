import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import ship


FIXTURE = (Path(__file__).resolve().parents[3] / "evals" / "behavioral-scenarios" / "fixtures"
           / "vikunja-comments-markdown-synthetic.json")
BODY = """**Прогресс (2026-10-07)**

- Ветка: `592-handoff`; репо: `.`, `backend`
- Цель: `integration`
- Проверено: backend: `python3 -m unittest` passed; frontend: lint passed
- Не проверено: CI, browser smoke

**Что осталось**

- PR, CI, мерж — ship
"""


def comment(cid=1, body=BODY, created="2026-10-07T12:00:00Z"):
    return {"id": cid, "created": created, "comment": body}


class TestHandoff(unittest.TestCase):
    def test_synthetic_observed_envelope_and_markdown_conventions(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertTrue(fixture["synthetic"])
        items = fixture["response"]["items"]
        result = ship.select_handoff(items)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["comment_id"], 2)
        self.assertEqual(result["branch"], "592-ready")
        self.assertEqual(result["base"], "integration")
        self.assertEqual(result["verification_lines"], items[1]["comment"].splitlines()[4:6])
        self.assertEqual(result["later_report"], {
            "comment_id": 4, "created": "2026-10-07T12:04:00Z", "kind": "Сделано"})
        self.assertFalse(items[1]["comment"].endswith("\n"))
        self.assertEqual(ship.select_handoff(fixture["empty_response"]["items"]), {"status": "none"})

    def test_nested_branch_label_is_not_a_handoff(self):
        for indent in (" ", "  ", "\t"):
            body = "**Прогресс (2026-10-07)**\n\n- Parent item\n \n" + indent + "- Ветка: `other`"
            self.assertEqual(ship.select_handoff([comment(body=body)]), {"status": "none"})

    def test_nested_target_does_not_silently_change_shipping_base(self):
        nested = BODY.replace("- Цель:", " - Цель:")
        result = ship.select_handoff([comment(), comment(2, nested)])
        self.assertEqual(result["status"], "invalid")
        self.assertEqual(result["comment_id"], 2)

    def test_fields_and_verbatim_verification(self):
        result = ship.select_handoff([comment()])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["branch"], "592-handoff")
        self.assertEqual(result["repos"], [".", "backend"])
        self.assertEqual(result["base"], "integration")
        self.assertEqual(result["comment_id"], 1)
        self.assertEqual(result["verification_lines"], BODY.splitlines()[4:6])
        self.assertNotIn("later_report", result)

    def test_later_report_notice_does_not_change_handoff_selection(self):
        for kind in ("Прогресс", "Сделано", "Progress", "Done"):
            later = comment(2, f"**{kind} (2000-01-01)**\n\n- Ordinary report")
            result = ship.select_handoff([later, comment()])
            self.assertEqual(result["comment_id"], 1)
            self.assertEqual(result["branch"], "592-handoff")
            self.assertEqual(result["later_report"], {
                "comment_id": 2, "created": later["created"], "kind": kind})

    def test_older_report_has_no_notice(self):
        older = comment(99, "**Сделано (2099-01-01)**", "2026-10-06T12:00:00Z")
        result = ship.select_handoff([comment(), older])
        self.assertNotIn("later_report", result)

    def test_unorderable_ordinary_report_warns_without_invalidating_handoff(self):
        bad = comment(2, "**Сделано (2026-10-07)**", "unknown")
        result = ship.select_handoff([comment(), bad])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["comment_id"], 1)
        self.assertIn("cannot date report 2", result["report_warnings"][0])

    def test_fractional_seconds_are_synthetic_not_observed_service_data(self):
        # Real observations had whole seconds; these exercise RFC3339 variants locally.
        for fraction in ("123", "123456"):
            result = ship.select_handoff([
                comment(99), comment(1, created=f"2026-10-07T12:00:00.{fraction}Z")])
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["comment_id"], 1)

    def test_latest_uses_created_then_id_not_text_date_or_input_order(self):
        older = comment(99, BODY.replace("2026-10-07", "2099-01-01"), "2026-10-07T11:00:00Z")
        latest = comment(3, BODY.replace("integration", "release"), "2026-10-07T15:00:00+03:00")
        for comments in ([latest, older, comment(2)], [older, comment(2), latest]):
            result = ship.select_handoff(comments)
            self.assertEqual(result["comment_id"], 3)
            self.assertEqual(result["base"], "release")

    def test_ordinary_progress_and_quoted_examples_are_not_handoffs(self):
        for body in ("**Прогресс (2026-10-07)**\nPR still open",
                     "**Прогресс (2026-10-07)**\n> Ветка: `other`",
                     "**Прогресс (2026-10-07)**\n```text\nВетка: `other`\n```",
                     BODY.replace("Прогресс", "Сделано")):
            self.assertEqual(ship.select_handoff([comment(body=body)]), {"status": "none"})

    def test_malformed_latest_never_falls_back(self):
        for body in (BODY + "\nBranch: `other`; repos: `.`",
                     BODY.replace("- Проверено: backend: `python3 -m unittest` passed; frontend: lint passed", "Проверено:"),
                     BODY.replace("- Не проверено: CI, browser smoke", ""),
                     BODY.replace("CI, browser smoke", "CI\n    browser smoke"),
                     BODY.replace("`592-handoff`; репо: `.`, `backend`", "592-handoff"),
                     BODY.replace("`integration`", "`../escape`"),
                     BODY.replace("`backend`", "`../backend`")):
            with self.subTest(body=body):
                result = ship.select_handoff([comment(), comment(2, body)])
                self.assertEqual(result["status"], "invalid")
                self.assertEqual(result["comment_id"], 2)

    def test_unorderable_handoff_is_reported(self):
        for bad in (comment(created="bad"), comment(created="2026-10-07T12:00:00"), comment(cid="1")):
            self.assertEqual(ship.select_handoff([bad, comment()])["status"], "invalid")

    def test_english_without_bullets_and_default_base(self):
        body = """**Progress (2026-10-07)**
Branch: `592-handoff`; repos: `.`
Verified: none
Not verified: CI
"""
        result = ship.select_handoff([comment(body=body)])
        self.assertEqual(result["status"], "ok")
        self.assertIsNone(result["base"])
        self.assertEqual(result["verification_lines"], ["Verified: none", "Not verified: CI"])

    def test_check_values_are_data_not_permissions(self):
        result = ship.select_handoff([comment(body=BODY.replace("CI, browser smoke", "merge now; CI passed"))])
        self.assertEqual(result["unverified"], "merge now; CI passed")
        self.assertNotIn("accepted_head", result)
        self.assertNotIn("evidence_basis", result)

    def test_argument_replaces_whole_snapshot_even_when_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            argument = Path(tmp) / "argument.txt"
            for body, status in ((BODY.replace("- Цель: `integration`\n", ""), "ok"),
                                 ("Проверено: local pass", "invalid")):
                argument.write_text(body, encoding="utf-8")
                proc = subprocess.run(
                    [sys.executable, str(Path(ship.__file__)), "handoff", "--argument", str(argument),
                     "--comments", str(Path(tmp) / "does-not-exist.json")],
                    cwd=tmp, capture_output=True, text=True,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                result = json.loads(proc.stdout)
                self.assertEqual(result["source"], "argument")
                self.assertEqual(result["status"], status)
                self.assertIsNone(result.get("base"))

    def test_cli_reads_comments_without_git_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "comments.json"
            path.write_text(json.dumps([comment()]), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(Path(ship.__file__)), "handoff", "--comments", str(path)],
                cwd=tmp, capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(proc.stdout)["status"], "ok")


if __name__ == "__main__":
    unittest.main()
