import json
import os
import unittest
from unittest import mock

import peer_chat as pc

RULE = "─" * 60
CLAUDE_EMPTY = "\n".join(["some output", "", RULE, "❯ ", RULE, "  Opus | main"])
CODEX_EMPTY = "\n".join(["• Worked for 1s", "", "› ", "", "  gpt · ~/src"])


def claude_with(text):
    return CLAUDE_EMPTY.replace("❯ ", f"❯ {text}")


def window(wid, *cmdlines):
    return {"id": wid, "foreground_processes": [{"cmdline": c} for c in cmdlines]}


def ls(*tabs):
    return json.dumps([{"tabs": [{"windows": list(t)} for t in tabs]}])


class PromptTest(unittest.TestCase):
    def test_claude_empty(self):
        self.assertEqual(pc.claude_prompt_text(CLAUDE_EMPTY), "")

    def test_claude_composed(self):
        self.assertEqual(pc.claude_prompt_text(claude_with("Chat from Codex: hi")), "Chat from Codex: hi")

    def test_claude_prompt_outside_box_ignored(self):
        self.assertIsNone(pc.claude_prompt_text("❯ ls\nfile"))

    def test_codex_empty(self):
        self.assertEqual(pc.codex_prompt_text(CODEX_EMPTY), "")

    def test_normalize_collapses_and_strips_labels(self):
        profile = pc.PROFILES["claude"]
        self.assertEqual(
            pc.normalize(profile, "Chat from Claude (x): chat from codex:  a\n\n b "),
            "Chat from Codex: a b",
        )

    def test_normalize_empty(self):
        with self.assertRaises(ValueError):
            pc.normalize(pc.PROFILES["claude"], "Chat from Codex:  \n")


class KittyTest(unittest.TestCase):
    def kitty(self, tree, screen="", own=1):
        calls = []

        def run(args, stdin=None):
            calls.append((args, stdin))
            if args[0] == "ls":
                return tree
            if args[0] == "get-text":
                return screen
            return ""

        return pc.Kitty(str(own), run), calls

    def test_locates_peer_in_own_tab(self):
        tree = ls(
            [window(1, ["claude"]), window(3, ["node", "/opt/bin/codex", "-c", "x"])],
            [window(5, ["codex"])],
        )
        k, _ = self.kitty(tree)
        self.assertEqual(k.locate(pc.PROFILES["codex"]), "3")

    def test_never_targets_itself(self):
        k, _ = self.kitty(ls([window(1, ["claude"]), window(2, ["zsh"])]))
        with self.assertRaisesRegex(RuntimeError, "--target-command"):
            k.locate(pc.PROFILES["claude"])

    def test_ambiguous_peer(self):
        k, _ = self.kitty(ls([window(1, ["claude"]), window(2, ["codex"]), window(3, ["codex"])]))
        with self.assertRaisesRegex(RuntimeError, "more than one"):
            k.locate(pc.PROFILES["codex"])

    def test_wrapper_name(self):
        k, _ = self.kitty(ls([window(1, ["claude"]), window(2, ["cx"])]))
        self.assertEqual(k.locate(pc.target_profile("codex", "cx")), "2")

    def test_own_window_missing(self):
        k, _ = self.kitty(ls([window(2, ["codex"])]))
        with self.assertRaisesRegex(RuntimeError, "not found"):
            k.locate(pc.PROFILES["codex"])

    def test_cursor_is_zero_based(self):
        tree = ls([window(1, ["claude"]), window(2, ["codex"])])
        k, _ = self.kitty(tree, screen="text\x1b[?25l\x1b[39;3H\x1b[?12h\n")
        self.assertEqual(k.cursor_column("2", pc.PROFILES["codex"]), pc.EMPTY_CURSOR_COLUMN)

    def test_type_rechecks_target(self):
        k, calls = self.kitty(ls([window(1, ["claude"]), window(2, ["zsh"])]))
        with self.assertRaises(RuntimeError):
            k.type("2", pc.PROFILES["codex"], "hello")
        self.assertFalse(any(a[0] == "send-text" for a, _ in calls))

    def test_type_sends_stdin(self):
        k, calls = self.kitty(ls([window(1, ["claude"]), window(2, ["codex"])]))
        k.type("2", pc.PROFILES["codex"], "hello")
        self.assertEqual(calls[-1], (["send-text", "--match", "id:2", "--stdin"], "hello"))


class AgtermTest(unittest.TestCase):
    TREE = {"workspaces": [{"sessions": [
        {"id": "AAA111", "hasSplit": True, "cwd": "/w/a", "foreground": ["claude"], "splitForeground": ["codex -c x"]},
        {"id": "BBB222", "hasSplit": False, "cwd": "/w/b", "foreground": ["claude"], "splitForeground": None},
    ]}]}

    def agterm(self, session=None, cursor="2"):
        calls = []

        def ctl(*args):
            calls.append(args)
            if args[0] == "tree":
                return json.dumps(self.TREE)
            if args[0] == "surface":
                return cursor + "\n"
            return "screen"

        a = pc.Agterm(session)
        a.ctl = ctl
        return a, calls

    def test_session_prefix(self):
        a, _ = self.agterm("aaa")
        self.assertEqual(a.locate(pc.PROFILES["codex"]), "AAA111")
        self.assertEqual(a.locate(pc.PROFILES["claude"]), "AAA111")

    def test_session_without_split(self):
        a, _ = self.agterm("BBB")
        with self.assertRaisesRegex(RuntimeError, "no split"):
            a.locate(pc.PROFILES["codex"])

    def test_checkout_fallback(self):
        a, _ = self.agterm()
        with mock.patch.object(pc, "checkout_key", side_effect=lambda p: "/w/a" if p in (os.getcwd(), "/w/a") else p):
            self.assertEqual(a.locate(pc.PROFILES["codex"]), "AAA111")

    def test_commands(self):
        a, calls = self.agterm("AAA111")
        p = pc.PROFILES["codex"]
        self.assertEqual(a.screen("AAA111", p), "screen")
        self.assertEqual(a.cursor_column("AAA111", p), 2)
        a.type("AAA111", p, a.key(p.submit))
        sent = [c for c in calls if c[0] != "tree"]
        self.assertEqual(sent, [
            ("session", "text", "--pane", "right", "--target", "AAA111", "--lines", "40"),
            ("surface", "cursor", "--target", "surface:AAA111:right"),
            ("session", "type", "\t", "--pane", "right", "--target", "AAA111"),
        ])

    def test_keys_unchanged(self):
        self.assertEqual(pc.Agterm.KEYS, {"enter": "\n", "tab": "\t"})

    def test_bad_cursor(self):
        a, _ = self.agterm("AAA111", cursor="n/a")
        with self.assertRaisesRegex(RuntimeError, "surface cursor"):
            a.cursor_column("AAA111", pc.PROFILES["codex"])


class PickBackendTest(unittest.TestCase):
    def test_kitty_when_window_id_set(self):
        with mock.patch.dict(os.environ, {"KITTY_WINDOW_ID": "4"}):
            self.assertIsInstance(pc.pick_backend(None), pc.Kitty)

    def test_session_flag_is_agterm_only(self):
        with mock.patch.dict(os.environ, {"KITTY_WINDOW_ID": "4"}):
            with self.assertRaises(ValueError):
                pc.pick_backend("abc")

    def test_agterm_otherwise(self):
        env = {k: v for k, v in os.environ.items() if k != "KITTY_WINDOW_ID"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertIsInstance(pc.pick_backend(None), pc.Agterm)


class FakeBackend:
    """A composer that shows whatever was typed, until a submit key clears it."""

    def __init__(self, profile, cursor=pc.EMPTY_CURSOR_COLUMN, echo=True):
        self.profile = profile
        self.cursor = cursor
        self.echo = echo
        self.composer = ""
        self.typed = []

    def locate(self, profile):
        return "t"

    def screen(self, target, profile):
        if profile.agent == "codex":
            return CODEX_EMPTY.replace("› ", f"› {self.composer}")
        return claude_with(self.composer)

    def cursor_column(self, target, profile):
        return self.cursor

    def type(self, target, profile, text):
        self.typed.append(text)
        if text == self.key(profile.submit):
            self.composer = ""
        elif self.echo:
            self.composer = text.removeprefix("\x1b[200~").removesuffix("\x1b[201~")

    def key(self, name):
        return pc.Kitty.KEYS[name]


@mock.patch.object(pc, "SUBMIT_DELAY", 0)
@mock.patch.object(pc, "PROBE_TIMEOUT", 0.05)
class SendTest(unittest.TestCase):
    def test_claude_submits_with_return(self):
        b = FakeBackend(pc.PROFILES["claude"])
        pc.send(b, "t", pc.PROFILES["claude"], "hi there")
        self.assertEqual(b.typed, ["Chat from Codex: hi there", "\r"])

    def test_codex_gets_bracketed_paste_then_tab(self):
        b = FakeBackend(pc.PROFILES["codex"])
        pc.send(b, "t", pc.PROFILES["codex"], "a longer message that easily passes the wrapped probe length")
        self.assertTrue(b.typed[0].startswith("\x1b[200~Chat from Claude"))
        self.assertEqual(b.typed[1], "\t")

    def test_busy_composer_types_nothing(self):
        b = FakeBackend(pc.PROFILES["claude"], cursor=7)
        with self.assertRaises(pc.PromptBlocked):
            pc.send(b, "t", pc.PROFILES["claude"], "hi")
        self.assertEqual(b.typed, [])

    def test_unverified_text_is_not_submitted(self):
        b = FakeBackend(pc.PROFILES["claude"], echo=False)
        with self.assertRaisesRegex(RuntimeError, "submit withheld"):
            pc.send(b, "t", pc.PROFILES["claude"], "hi")
        self.assertEqual(len(b.typed), 1)


if __name__ == "__main__":
    unittest.main()
