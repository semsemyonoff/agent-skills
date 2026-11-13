"""Consumer-visible peer-chat safety contracts; no terminal or model is started."""

import copy
import contextlib
import io
import json
import os
import unittest
from unittest import mock

import peer_chat as pc


RULE = "─" * 68
MESSAGE = "Please compare the recorded evidence and reply through the peer-chat skill."


def boxed_prompt(harness, *lines):
    top = RULE if harness == "claude" else RULE[:24] + " Follow-up " + RULE[24:]
    content = ["❯ " + (lines[0] if lines else "")]
    content.extend("  " + line for line in lines[1:])
    status = "  Opus | main" if harness == "claude" else "  model · context 12%"
    return "\n".join(["Prior assistant output", "", top, *content, RULE, status])


def composer(harness, *lines):
    if harness != "codex":
        return boxed_prompt(harness, *lines)
    content = ["› " + (lines[0] if lines else "")]
    content.extend("  " + line for line in lines[1:])
    return "\n".join(["• Worked for 1s", "", *content, "", "  gpt · ~/src"])


def accepted_screen(harness):
    if harness == "codex":
        transcript = "• Working on the comparison\n• Message queued as a follow-up"
    elif harness == "omp":
        transcript = "Queued follow-up: Please compare the recorded evidence."
    else:
        transcript = "⏺ Comparing the recorded evidence…"
    return transcript + "\n" + composer(harness)


def omp_chip_screen(token=" #1", count=1999):
    # omp 18.13.2 PTY capture: the count is on a card, not in the editor token.
    card = "\n".join([
        "╭───  #1 ───╮",
        "│Chat from C…│",
        "│            │",
        "│            │",
        "│            │",
        f"╰ {count} chars ╯",
    ])
    return composer("omp", token).replace("Prior assistant output", card, 1)




def kitty_window(identity, *argv):
    return {
        "id": identity,
        "foreground_processes": [{"cmdline": list(command)} for command in argv],
    }


def kitty_tree(*tabs):
    return json.dumps([{"tabs": [{"windows": list(tab)} for tab in tabs]}])


def agterm_tree(source="claude", peer="codex"):
    """Schema-shaped fixture, not a claim that a live screen was captured."""
    return {
        "ok": True,
        "result": {
            "tree": {
                "workspaces": [{
                    "sessions": [{
                        "id": "SESSION-ONE",
                        "hasSplit": True,
                        "foreground": [source],
                        "splitForeground": [peer],
                        "surfaces": [
                            {"id": "surface-left", "kind": "left", "visible": True, "paneID": "SOURCE-TOKEN"},
                            {"id": "surface-right", "kind": "right", "visible": True, "paneID": "PEER-TOKEN"},
                        ],
                    }],
                }],
            },
        },
    }


def agterm_session(tree):
    return tree["result"]["tree"]["workspaces"][0]["sessions"][0]


class KittyTranscript:
    def __init__(self, tree):
        self.tree = tree
        self.calls = []
        self.writes = []

    def __call__(self, args, stdin=None):
        self.calls.append((list(args), stdin))
        if args[0] == "ls":
            return self.tree
        if args[0] == "get-text":
            return composer("codex") + "\x1b[12;3H"
        self.writes.append((list(args), stdin))
        return ""


class AgtermTranscript:
    def __init__(self, tree):
        self.tree = tree
        self.calls = []
        self.writes = []

    def __call__(self, *args, stdin=None):
        self.calls.append((args, stdin))
        if args[0] == "tree":
            return json.dumps(self.tree)
        if args[:2] == ("surface", "cursor"):
            return "2\n"
        if args[:2] == ("session", "text"):
            return composer("codex")
        self.writes.append((args, stdin))
        return json.dumps({"ok": True, "result": {}})


class Clock:
    """Let bounded rendering probes expire without real sleeps or wall-clock races."""

    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += max(seconds, 0.01)


class ScreenTape:
    """Replay separate preflight, post-paste and post-submit screen observations.

    Screens are supplied independently of text writes. A faulty transport cannot
    manufacture a successful verification by merely echoing its input argument.
    """

    def __init__(self, target, before, pasted, submitted, cursor=2):
        self.target = target
        self.phases = [list(before), list(pasted), list(submitted)]
        self.cursor = cursor
        self.writes = []
        self.observations = []

    def locate(self, source, profile):
        return self.target

    def screen(self, target):
        self.observations.append("screen")
        phase = self.phases[min(len(self.writes), 2)]
        if len(phase) > 1:
            return phase.pop(0)
        return phase[0]

    def cursor_column(self, target):
        self.observations.append("cursor")
        return self.cursor

    def type(self, target, text):
        self.observations.append("write")
        self.writes.append(text)

    def key(self, name):
        return {"enter": "\r", "tab": "\t", "followup": "\x11"}[name]


class PromptSafetyTest(unittest.TestCase):
    def test_all_harnesses_have_empty_composers(self):
        for harness in ("claude", "codex", "omp"):
            with self.subTest(harness=harness):
                self.assertEqual(pc.prompt_text(pc.PROFILES[harness], composer(harness)), "")

    def test_boxed_composers_preserve_every_wrapped_line(self):
        lines = ["First segment of the user's draft", "the middle must not disappear", "nor the last segment"]
        for harness in ("claude", "omp"):
            with self.subTest(harness=harness):
                content = pc.prompt_text(pc.PROFILES[harness], composer(harness, *lines))
                self.assertIsNotNone(content)
                self.assertEqual(" ".join(content.split()), " ".join(lines))

    def test_latest_box_wins_over_historical_prompt(self):
        for harness in ("claude", "omp"):
            with self.subTest(harness=harness):
                screen = composer(harness, "old draft") + "\nAssistant response\n" + composer(harness)
                self.assertEqual(pc.prompt_text(pc.PROFILES[harness], screen), "")

    def test_titled_omp_top_rule_is_a_real_composer(self):
        self.assertEqual(pc.prompt_text(pc.PROFILES["omp"], boxed_prompt("omp", "held text")), "held text")

    def test_omp_short_titled_border_after_todo_card_preserves_composer(self):
        todo = [
            "╭─ Tasks ─────────────────────────╮",
            "│ Verify peer-chat                │",
            "╰─────────────────────────────────╯",
        ]
        title = "── Fix per-chat Kitty detection and Claude sending · 777K · 36.6%/922K ─"
        for rows in ([""], ["Existing draft", "and its wrapped continuation"]):
            with self.subTest(rows=rows):
                screen = "\n".join([
                    *todo, "", title, "❯ " + rows[0],
                    *("  " + row for row in rows[1:]),
                    RULE, "  GPT · high · agent-skills",
                ])
                self.assertEqual(pc.omp_prompt_text(screen), " ".join(rows).strip())

    def test_todo_card_closer_does_not_certify_an_omp_composer(self):
        screen = "\n".join([
            "╭─ Tasks ─────────────────────────╮",
            "│ Verify peer-chat                │",
            "╰─────────────────────────────────╯",
            "❯ ", RULE, "  GPT · high · agent-skills",
        ])
        self.assertIsNone(pc.omp_prompt_text(screen))

    def test_named_claude_composer_keeps_its_top_border_title(self):
        screen = boxed_prompt("claude", "held text").replace(RULE, RULE[:24] + " Session name " + RULE[24:], 1)
        self.assertEqual(pc.prompt_text(pc.PROFILES["claude"], screen), "held text")

    def test_claude_auto_mode_footer_preserves_wrapped_peer_message(self):
        rows = [
            "Chat from omp (reply via peer-chat skill): Проверяем реальный peer-chat.",
            "Я работаю в harness omp, не native Codex CLI.",
        ]
        screen = "\n".join([
            RULE,
            "❯\u00a0" + rows[0],
            "  " + rows[1],
            RULE,
            "  Opus\u00a05.5\u00a0|\u00a0high\u00a0|\u00a00.0%\u00a0|\u00a0⎇\u00a0main",
            "  ⏵⏵ auto mode on (shift+tab to cycle)",
        ])
        content = pc.prompt_text(pc.PROFILES["claude"], screen)
        self.assertEqual(content, " ".join(rows))
        self.assertTrue(pc.composer_has_message(pc.PROFILES["claude"], content, " ".join(rows)))

    def test_unboxed_prompt_is_not_a_composer(self):
        for harness in ("claude", "omp"):
            with self.subTest(harness=harness):
                self.assertIsNone(pc.prompt_text(pc.PROFILES[harness], "❯ previous shell command\ncommand output"))


class SenderSafetyTest(unittest.TestCase):
    def test_sender_is_actual_harness_not_destination_or_model(self):
        labels = []
        for sender in ("claude", "codex", "omp"):
            with self.subTest(sender=sender):
                normalized = pc.normalize(sender, MESSAGE)
                label, body = normalized.split(":", 1)
                self.assertIn(sender, label.casefold())
                self.assertEqual(body.strip(), MESSAGE)
                labels.append(label)
        self.assertEqual(len(set(labels)), 3)
        for model in ("opus", "gpt", "gpt-6-sol"):
            with self.subTest(model=model), self.assertRaises((ValueError, KeyError)):
                pc.normalize(model, MESSAGE)

    def test_incoming_label_cannot_impersonate_sender(self):
        normalized = pc.normalize("omp", "Chat from Claude: Chat from Codex: " + MESSAGE)
        label, body = normalized.split(":", 1)
        self.assertIn("omp", label)
        self.assertEqual(body.strip(), MESSAGE)

    def test_payload_whitespace_collapses_but_terminal_controls_refuse(self):
        self.assertTrue(pc.normalize("codex", "  first\n\t second  ").endswith("first second"))
        for control in ("\x00", "\x01", "\x08", "\x11", "\x1b", "\x7f"):
            with self.subTest(control=repr(control)), self.assertRaises(ValueError):
                pc.normalize("claude", "before" + control + "after")

    def test_empty_message_cannot_become_label_only_input(self):
        for message in ("", " \n\t ", "Chat from Codex: "):
            with self.subTest(message=message), self.assertRaises(ValueError):
                pc.normalize("claude", message)

    def test_supported_harness_name_is_not_a_wrapper_for_another(self):
        for destination, impersonator in (("codex", "omp"), ("claude", "codex"), ("omp", "claude")):
            with self.subTest(destination=destination, impersonator=impersonator), self.assertRaises(ValueError):
                pc.target_profile(destination, impersonator)


class ProcessIdentityTest(unittest.TestCase):
    def test_arguments_cannot_impersonate_supported_foreground(self):
        for harness in ("claude", "codex", "omp"):
            for argv in (
                ["zsh", "-c", harness],
                ["printf", harness],
                ["python3", "/tmp/helper.py", "--message", harness],
                ["node", "/tmp/helper.js", "--target", harness],
            ):
                with self.subTest(harness=harness, argv=argv):
                    self.assertFalse(pc.runs(argv, harness))

    def test_actual_executable_and_node_entrypoint_are_recognized(self):
        for harness in ("claude", "codex", "omp"):
            with self.subTest(harness=harness):
                self.assertTrue(pc.runs([f"/usr/local/bin/{harness}", "--flag"], harness))
                self.assertTrue(pc.runs(["node", f"/opt/bin/{harness}", "--flag"], harness))

    def test_omp_and_codex_are_distinct_processes(self):
        self.assertFalse(pc.runs(["omp"], "codex"))
        self.assertFalse(pc.runs(["codex"], "omp"))


class SendSafetyTest(unittest.TestCase):
    def setUp(self):
        clock = Clock()
        self.enterContext(mock.patch.object(pc.time, "monotonic", clock.monotonic))
        self.enterContext(mock.patch.object(pc.time, "sleep", clock.sleep))
        self.enterContext(contextlib.redirect_stderr(io.StringIO()))

    def tape(self, harness, before=None, pasted=None, submitted=None, cursor=2, sender="claude"):
        target = pc.Target("peer", pc.PROFILES[harness])
        held = pc.normalize(sender, MESSAGE)
        return ScreenTape(
            target,
            [composer(harness)] if before is None else before,
            [composer(harness, held)] if pasted is None else pasted,
            [accepted_screen(harness)] if submitted is None else submitted,
            cursor=cursor,
        )

    def deliver(self, backend, sender="claude"):
        return pc.send_with_retry(backend, backend.target, sender, MESSAGE)

    def test_all_source_destination_pairs_submit_after_realistic_transition(self):
        for sender in ("claude", "codex", "omp"):
            for destination in ("claude", "codex", "omp"):
                if sender == destination:
                    continue
                with self.subTest(sender=sender, destination=destination):
                    held = pc.normalize(sender, MESSAGE)
                    words = held.split()
                    wrapped = [" ".join(words[:7]), " ".join(words[7:14]), " ".join(words[14:])]
                    backend = self.tape(
                        destination,
                        pasted=[composer(destination, *wrapped)],
                        sender=sender,
                    )
                    self.deliver(backend, sender)
                    self.assertEqual(len(backend.writes), 2)
                    self.assertIn(held, backend.writes[0])
                    self.assertEqual(backend.writes[1], {"claude": "\r", "codex": "\t", "omp": "\x11"}[destination])
                    preflight = backend.observations[:backend.observations.index("write")]
                    self.assertIn("screen", preflight)
                    self.assertIn("cursor", preflight)

    def test_omp_single_rule_title_allows_delivery_but_not_drafts_or_dialogs(self):
        # Captured from omp 18.20.0 in the failed agterm recipient pane.
        title = "─ 󰐨 KIMI: Обсудить… ·  132K ·  prolite · 7d 45% (4d) · ✦ 3 exp 17d 11h ·  10.9%/922K…─"

        def screen(*rows):
            return composer("omp", *rows).replace(
                RULE[:24] + " Follow-up " + RULE[24:], title, 1,
            )

        backend = self.tape(
            "omp", before=[screen()],
            pasted=[screen(pc.normalize("omp", MESSAGE))],
            submitted=[screen()], sender="omp",
        )
        self.assertEqual(self.deliver(backend, "omp"), len(MESSAGE))
        self.assertEqual(backend.writes[-1], "\x11")
        for unsafe in (
            screen("unfinished draft"),
            screen() + "\nPermission required\n1. Allow once\n2. Deny",
        ):
            with self.subTest(unsafe=unsafe):
                backend = self.tape("omp", before=[unsafe])
                with self.assertRaises(RuntimeError):
                    self.deliver(backend)
                self.assertEqual(backend.writes, [])

    def test_occupied_text_with_caret_at_start_never_writes(self):
        for harness in ("claude", "codex", "omp"):
            with self.subTest(harness=harness):
                backend = self.tape(harness, before=[composer(harness, "user's unfinished draft")], cursor=2)
                with self.assertRaises(RuntimeError):
                    self.deliver(backend)
                self.assertEqual(backend.writes, [])

    def test_codex_placeholder_hint_is_an_empty_composer(self):
        for hint in sorted(pc.CODEX_PLACEHOLDERS):
            with self.subTest(hint=hint):
                backend = self.tape(
                    "codex",
                    before=[composer("codex", hint)],
                    submitted=[accepted_screen("codex").replace("› ", "› Ask a follow-up question")],
                )
                self.deliver(backend)
                self.assertEqual(len(backend.writes), 2)

    def test_codex_placeholder_lookalikes_never_write(self):
        for before, cursor in (
            (composer("codex", "Ask Codex to do anything"), 26),
            (composer("codex", "Ask Codex to do anything", "and more"), 2),
            (composer("codex", "Ask Codex to do something"), 2),
        ):
            with self.subTest(before=before, cursor=cursor):
                backend = self.tape("codex", before=[before], cursor=cursor)
                with self.assertRaises(RuntimeError):
                    self.deliver(backend)
                self.assertEqual(backend.writes, [])

    def test_empty_screen_with_displaced_cursor_never_writes(self):
        for harness in ("claude", "codex", "omp"):
            with self.subTest(harness=harness):
                backend = self.tape(harness, cursor=8)
                with self.assertRaises(RuntimeError):
                    self.deliver(backend)
                self.assertEqual(backend.writes, [])

    def test_historical_prompt_followed_by_dialog_never_writes(self):
        for harness in ("claude", "codex", "omp"):
            for suffix in (
                "Trust this directory?\n❯ Yes\n  No",
                "Permission required\nAllow this command?\n1. Allow once\n2. Deny",
                "Choose a model\n  model-a\n❯ model-b",
            ):
                with self.subTest(harness=harness, suffix=suffix):
                    backend = self.tape(harness, before=[composer(harness) + "\n\n" + suffix])
                    with self.assertRaises(RuntimeError):
                        self.deliver(backend)
                    self.assertEqual(backend.writes, [])

    def test_wrapped_tail_difference_is_not_verified_by_matching_prefix(self):
        for harness in ("claude", "omp"):
            with self.subTest(harness=harness):
                held = pc.normalize("claude", MESSAGE)
                backend = self.tape(harness, pasted=[composer(harness, held, "UNRELATED TAIL")])
                with self.assertRaises(RuntimeError):
                    self.deliver(backend)
                self.assertEqual(len(backend.writes), 1)

    def test_partial_rendered_label_does_not_verify_a_whole_message(self):
        for harness in ("claude", "omp"):
            with self.subTest(harness=harness):
                prefix = pc.normalize("claude", MESSAGE)[:55]
                backend = self.tape(harness, pasted=[composer(harness, prefix)])
                with self.assertRaises(RuntimeError):
                    self.deliver(backend)
                self.assertEqual(len(backend.writes), 1)

    def test_unverified_paste_gets_no_submit_key_and_no_reinsertion(self):
        for harness in ("claude", "codex", "omp"):
            for observed in (composer(harness), composer(harness, "different user's input"), "Approval required"):
                with self.subTest(harness=harness, observed=observed):
                    backend = self.tape(harness, pasted=[observed])
                    with self.assertRaises(RuntimeError):
                        self.deliver(backend)
                    self.assertEqual(len(backend.writes), 1)

    def test_delayed_rendering_waits_without_retyping(self):
        for harness in ("claude", "codex", "omp"):
            with self.subTest(harness=harness):
                held = pc.normalize("claude", MESSAGE)
                backend = self.tape(
                    harness,
                    pasted=[composer(harness), composer(harness), composer(harness, held)],
                )
                self.deliver(backend)
                self.assertEqual(len(backend.writes), 2)

    def test_composer_changing_after_verification_gets_no_submit(self):
        for harness in ("claude", "codex", "omp"):
            with self.subTest(harness=harness):
                held = pc.normalize("claude", MESSAGE)
                backend = self.tape(harness, pasted=[composer(harness, held), "Permission required"])
                with self.assertRaises(RuntimeError):
                    self.deliver(backend)
                self.assertEqual(len(backend.writes), 1)

    def test_long_paste_plaques_are_harness_specific_and_count_checked(self):
        message = "Evidence " + "recorded observation " * 100
        typed = pc.normalize("claude", message)
        for harness, plaque in (
            ("codex", f"[Pasted Content {len(typed)} chars]"),
            ("omp", f"[Paste #7, {len(typed.encode('utf-16-le')) // 2} chars]"),
            ("claude", "[Pasted text #1]"),
        ):
            with self.subTest(harness=harness):
                target = pc.Target("peer", pc.PROFILES[harness])
                backend = ScreenTape(target, [composer(harness)], [composer(harness, plaque)], [accepted_screen(harness)])
                pc.send_with_retry(backend, target, "claude", message)
                self.assertEqual(len(backend.writes), 2)

        for harness, plaque in (
            ("codex", f"[Pasted Content {len(typed) + 1} chars]"),
            ("omp", f"[Paste #7, {len(typed.encode('utf-16-le')) // 2 + 1} chars]"),
            ("claude", f"[Pasted Content {len(typed)} chars]"),
            ("codex", f"[Paste #7, {len(typed)} chars]"),
            ("omp", f"[Pasted Content {len(typed)} chars]"),
            ("codex", "[Pasted text #1]"),
            ("omp", "[Pasted text #1]"),
        ):
            with self.subTest(harness=harness, plaque=plaque):
                target = pc.Target("peer", pc.PROFILES[harness])
                backend = ScreenTape(target, [composer(harness)], [composer(harness, plaque)], [accepted_screen(harness)])
                with self.assertRaises(RuntimeError):
                    pc.send_with_retry(backend, target, "claude", message)
                self.assertEqual(len(backend.writes), 1)

    def test_existing_claude_paste_token_is_occupied_even_with_cursor_at_start(self):
        backend = self.tape("claude", before=[composer("claude", "[Pasted text #1]")])
        with self.assertRaises(RuntimeError):
            self.deliver(backend, "omp")
        self.assertEqual(backend.writes, [])

    def test_claude_long_paste_submits_during_transient_expand_hint(self):
        message = "Recorded evidence " + "длинный абзац " * 100
        target = pc.Target("peer", pc.PROFILES["claude"])
        pasted = composer("claude", "[Pasted text #3]") + "\n  paste again to expand"
        submitted = accepted_screen("claude") + "\n  paste again to expand"
        backend = ScreenTape(target, [composer("claude")], [pasted], [submitted])
        pc.send_with_retry(backend, target, "omp", message)
        self.assertEqual(len(backend.writes), 2)

    def test_retained_paste_help_does_not_certify_a_dialog(self):
        for body in ("", "[Pasted text #3]"):
            with self.subTest(body=body):
                dialog = composer("claude", body) + "\n  paste again to expand\nAllow this command?"
                self.assertIsNone(pc.prompt_text(pc.PROFILES["claude"], dialog))

    def test_omp_paste_count_uses_javascript_characters_not_python_or_utf8_length(self):
        message = "Evidence " + "😀résumé " * 180
        typed = pc.normalize("claude", message)
        target = pc.Target("peer", pc.PROFILES["omp"])
        for count in (len(typed.encode("utf-16-le")) // 2, len(typed), len(typed.encode("utf-8"))):
            with self.subTest(count=count):
                plaque = f"[Paste #7, {count} chars]"
                backend = ScreenTape(target, [composer("omp")], [composer("omp", plaque)], [accepted_screen("omp")])
                if count == len(typed.encode("utf-16-le")) // 2:
                    pc.send_with_retry(backend, target, "claude", message)
                    self.assertEqual(len(backend.writes), 2)
                else:
                    with self.assertRaises(RuntimeError):
                        pc.send_with_retry(backend, target, "claude", message)
                    self.assertEqual(len(backend.writes), 1)

    def test_omp_attachment_chip_submits_only_with_matching_card_and_utf16_count(self):
        message = "Measured evidence 😀 " * 100
        typed = pc.normalize("claude", message)
        count = len(typed.encode("utf-16-le")) // 2
        for glyph in ("", "📄", "txt"):
            with self.subTest(glyph=glyph):
                pasted = omp_chip_screen(count=count).replace("", glyph)
                target = pc.Target("peer", pc.PROFILES["omp"])
                backend = ScreenTape(target, [composer("omp")], [pasted], [accepted_screen("omp")])
                pc.send_with_retry(backend, target, "claude", message)
                self.assertEqual(backend.writes[1:], ["\x11"])

    def test_omp_unverified_attachment_chip_never_submits_or_reinserts(self):
        message = "Measured evidence 😀 " * 100
        typed = pc.normalize("claude", message)
        count = len(typed.encode("utf-16-le")) // 2
        valid = omp_chip_screen(count=count)
        for pasted in (
            composer("omp", " #1"),
            omp_chip_screen(token=" #2", count=count),
            omp_chip_screen(token="📄 #1", count=count),
            omp_chip_screen(count=count + 1),
            omp_chip_screen(count=len(typed)),
            omp_chip_screen(token=" #1 and an unrelated draft", count=count),
            valid.replace("chars ╯\n", "chars ╯\nUnrelated output\n"),
            valid + "\nAllow this command?",
        ):
            with self.subTest(pasted=pasted):
                target = pc.Target("peer", pc.PROFILES["omp"])
                backend = ScreenTape(target, [composer("omp")], [pasted], [accepted_screen("omp")])
                with self.assertRaises(RuntimeError):
                    pc.send_with_retry(backend, target, "claude", message)
                self.assertEqual(len(backend.writes), 1)

    def test_existing_omp_attachment_chip_is_an_occupied_composer(self):
        backend = self.tape("omp", before=[omp_chip_screen()], cursor=2)
        with self.assertRaises(pc.PromptBlocked):
            self.deliver(backend)
        self.assertEqual(backend.writes, [])

    def test_idle_codex_and_omp_submit_without_queue_status(self):
        for harness in ("codex", "omp"):
            with self.subTest(harness=harness):
                submitted = "User: Please compare the recorded evidence.\nAssistant: Comparing…\n" + composer(harness)
                backend = self.tape(harness, submitted=[submitted])
                self.deliver(backend)
                self.assertEqual(len(backend.writes), 2)

    def test_unknown_submission_outcome_never_reinserts(self):
        for harness in ("claude", "codex", "omp"):
            with self.subTest(harness=harness):
                held = pc.normalize("claude", MESSAGE)
                backend = self.tape(harness, submitted=[composer(harness, held)])
                with self.assertRaises(RuntimeError):
                    self.deliver(backend)
                self.assertEqual(len(backend.writes), 2)

    def test_control_payload_refuses_before_any_terminal_write(self):
        backend = self.tape("codex")
        with self.assertRaises(ValueError):
            pc.send_with_retry(backend, backend.target, "claude", "unsafe\x1b[31m")
        self.assertEqual(backend.writes, [])


class BackendEnvironmentTest(unittest.TestCase):
    def test_missing_kitty_identity_refuses_instead_of_falling_back(self):
        for env in (
            {"TERM": "xterm-kitty"},
            {"KITTY_LISTEN_ON": "unix:/tmp/test-kitty"},
            {"TERM": "xterm-kitty", "AGTERM_ENABLED": "1"},
        ):
            with self.subTest(env=env), mock.patch.dict(os.environ, env, clear=True):
                with self.assertRaises(ValueError):
                    pc.pick_backend()

    def test_genuine_agterm_environment_routes_without_kitty_guess(self):
        for env in (
            {"AGTERM_ENABLED": "1"},
            {"TERM_PROGRAM": "agterm"},
            {"AGTERM_SESSION_ID": "SESSION-ONE"},
            {"AGTERM_PANE_ID": "SOURCE-TOKEN"},
        ):
            with self.subTest(env=env), mock.patch.dict(os.environ, env, clear=True):
                self.assertIsInstance(pc.pick_backend(), pc.Agterm)

    def test_explicit_agterm_selection_is_possible_without_ambient_identity(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsInstance(pc.pick_backend(session="SESSION-ONE", backend="agterm"), pc.Agterm)

    def test_explicit_session_is_positive_agterm_context_for_auto_routing(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsInstance(pc.pick_backend(session="SESSION-ONE"), pc.Agterm)

    def test_no_terminal_context_and_conflicting_identities_refuse(self):
        for env in ({}, {"KITTY_WINDOW_ID": "1", "AGTERM_ENABLED": "1"}):
            with self.subTest(env=env), mock.patch.dict(os.environ, env, clear=True):
                with self.assertRaises(ValueError):
                    pc.pick_backend()

    def test_kitty_identity_routes_and_session_flag_cannot_redirect_it(self):
        with mock.patch.dict(os.environ, {"KITTY_WINDOW_ID": "1", "KITTY_LISTEN_ON": "unix:/tmp/test-kitty"}, clear=True):
            self.assertIsInstance(pc.pick_backend(), pc.Kitty)
            with self.assertRaises(ValueError):
                pc.pick_backend(session="SESSION-ONE")


class KittySafetyTest(unittest.TestCase):
    def setUp(self):
        self.enterContext(mock.patch.dict(os.environ, {"KITTY_LISTEN_ON": "unix:/tmp/test-kitty"}, clear=True))

    def backend(self, tree):
        transcript = KittyTranscript(tree)
        return pc.Kitty("1", transcript), transcript

    def test_peer_is_selected_only_in_source_tab(self):
        backend, _ = self.backend(kitty_tree(
            [kitty_window(1, ["claude"]), kitty_window(2, ["node", "/opt/bin/codex"])],
            [kitty_window(3, ["codex"])],
        ))
        target = backend.locate("claude", pc.PROFILES["codex"])
        self.assertEqual(target.id, "2")
        self.assertEqual(target.profile.name, "codex")

    def test_source_is_excluded_even_for_same_harness_target(self):
        backend, transcript = self.backend(kitty_tree([kitty_window(1, ["claude"]), kitty_window(2, ["zsh"])]))
        with self.assertRaises(RuntimeError):
            backend.locate("claude", pc.PROFILES["claude"])
        self.assertEqual(transcript.writes, [])

    def test_peer_in_another_tab_is_not_a_fallback(self):
        backend, _ = self.backend(kitty_tree(
            [kitty_window(1, ["claude"]), kitty_window(2, ["zsh"])],
            [kitty_window(3, ["codex"])],
        ))
        with self.assertRaises(RuntimeError):
            backend.locate("claude", None)

    def test_automatic_selection_refuses_multiple_supported_harnesses(self):
        backend, _ = self.backend(kitty_tree([
            kitty_window(1, ["claude"]), kitty_window(2, ["codex"]), kitty_window(3, ["omp"]),
        ]))
        with self.assertRaises(RuntimeError):
            backend.locate("claude", None)
        self.assertEqual(backend.locate("claude", pc.PROFILES["omp"]).id, "3")

    def test_explicit_selection_refuses_two_peers_of_same_harness(self):
        backend, _ = self.backend(kitty_tree([
            kitty_window(1, ["claude"]), kitty_window(2, ["codex"]), kitty_window(3, ["codex"]),
        ]))
        with self.assertRaises(RuntimeError):
            backend.locate("claude", pc.PROFILES["codex"])

    def test_foreground_argv_content_cannot_impersonate_harness(self):
        for argv in (
            ["zsh", "-c", "codex"],
            ["printf", "omp"],
            ["node", "/tmp/helper.js", "--message", "claude"],
        ):
            with self.subTest(argv=argv):
                backend, transcript = self.backend(kitty_tree([kitty_window(1, ["claude"]), kitty_window(2, argv)]))
                with self.assertRaises(RuntimeError):
                    backend.locate("claude", None)
                self.assertEqual(transcript.writes, [])

    def test_wrong_actual_sender_or_missing_source_window_refuses(self):
        for tree in (
            kitty_tree([kitty_window(1, ["zsh"]), kitty_window(2, ["codex"])]),
            kitty_tree([kitty_window(1, ["omp"]), kitty_window(2, ["codex"])]),
            kitty_tree([kitty_window(2, ["codex"])]),
        ):
            with self.subTest(tree=tree):
                backend, transcript = self.backend(tree)
                with self.assertRaises(RuntimeError):
                    backend.locate("claude", None)
                self.assertEqual(transcript.writes, [])

    def test_changed_foreground_refuses_write_after_discovery(self):
        backend, transcript = self.backend(kitty_tree([kitty_window(1, ["claude"]), kitty_window(2, ["codex"])]))
        target = backend.locate("claude", None)
        transcript.tree = kitty_tree([kitty_window(1, ["claude"]), kitty_window(2, ["zsh"])])
        with self.assertRaises(RuntimeError):
            backend.type(target, MESSAGE)
        self.assertEqual(transcript.writes, [])

    def test_omp_is_not_misclassified_as_codex(self):
        backend, _ = self.backend(kitty_tree([kitty_window(1, ["claude"]), kitty_window(2, ["omp"])]))
        self.assertEqual(backend.locate("claude", None).profile.name, "omp")
        with self.assertRaises(RuntimeError):
            backend.locate("claude", pc.PROFILES["codex"])


class AgtermSafetyTest(unittest.TestCase):
    def setUp(self):
        self.enterContext(mock.patch.dict(os.environ, {
            "AGTERM_ENABLED": "1",
            "AGTERM_SESSION_ID": "SESSION-ONE",
            "AGTERM_PANE_ID": "SOURCE-TOKEN",
        }, clear=True))

    def backend(self, tree=None, session=None):
        transcript = AgtermTranscript(agterm_tree() if tree is None else tree)
        backend = pc.Agterm(session)
        backend.ctl = transcript
        return backend, transcript

    def test_wrapped_tree_envelope_locates_real_peer_identity(self):
        backend, _ = self.backend()
        target = backend.locate("claude", None)
        self.assertEqual(target.id, "SESSION-ONE")
        self.assertEqual(target.pane_id, "PEER-TOKEN")
        self.assertEqual(target.profile.name, "codex")

    def test_stable_peer_token_survives_swap_for_reads_and_writes(self):
        backend, transcript = self.backend()
        target = backend.locate("claude", None)
        session = agterm_session(transcript.tree)
        session["foreground"], session["splitForeground"] = session["splitForeground"], session["foreground"]
        session["surfaces"][0]["kind"] = "right"
        session["surfaces"][1]["kind"] = "left"
        self.assertEqual(backend.locate("claude", None).pane_id, target.pane_id)
        self.assertEqual(backend.screen(target), composer("codex"))
        self.assertEqual(backend.cursor_column(target), 2)
        backend.type(target, MESSAGE)
        self.assertEqual(len(transcript.writes), 1)
        arguments, stdin = transcript.writes[0]
        self.assertIn("PEER-TOKEN", arguments)
        self.assertNotIn("SOURCE-TOKEN", arguments)
        self.assertEqual(stdin, MESSAGE)

    def test_missing_identity_never_uses_active_session_or_checkout(self):
        with mock.patch.dict(os.environ, {"AGTERM_ENABLED": "1", "PWD": "/repo"}, clear=True):
            backend, transcript = self.backend()
            with self.assertRaises(RuntimeError):
                backend.locate("claude", None)
            self.assertEqual(transcript.writes, [])

    def test_known_session_can_establish_unique_source_without_pane_token(self):
        with mock.patch.dict(os.environ, {"AGTERM_SESSION_ID": "SESSION-ONE"}, clear=True):
            backend, _ = self.backend()
            self.assertEqual(backend.locate("claude", None).pane_id, "PEER-TOKEN")

    def test_ambiguous_source_in_known_session_without_token_refuses(self):
        with mock.patch.dict(os.environ, {"AGTERM_SESSION_ID": "SESSION-ONE"}, clear=True):
            backend, _ = self.backend(agterm_tree(source="claude", peer="claude"))
            with self.assertRaises(RuntimeError):
                backend.locate("claude", None)

    def test_ambiguous_session_prefix_refuses_even_with_pane_token(self):
        tree = agterm_tree()
        other = copy.deepcopy(agterm_session(tree))
        other["id"] = "SESSION-TWO"
        tree["result"]["tree"]["workspaces"][0]["sessions"].append(other)
        backend, transcript = self.backend(tree, session="SESSION-")
        with self.assertRaises(RuntimeError):
            backend.locate("claude", None)
        self.assertEqual(transcript.writes, [])

    def test_hidden_split_overlay_or_missing_token_refuses(self):
        for hazard in (
            "no-split", "hidden-source", "hidden-peer", "overlay",
            "overlay-surface", "overlay-left-surface", "overlay-right-surface",
            "missing-source-token", "missing-peer-token",
        ):
            with self.subTest(hazard=hazard):
                tree = agterm_tree()
                session = agterm_session(tree)
                if hazard == "no-split":
                    session["hasSplit"] = False
                elif hazard == "overlay":
                    session["overlay"] = {"visible": True}
                elif hazard.endswith("-surface"):
                    session["surfaces"].append({
                        "id": "cover", "kind": hazard.removesuffix("-surface"),
                        "visible": True, "paneID": "OVERLAY-TOKEN",
                    })
                elif hazard.startswith("hidden"):
                    session["surfaces"][0 if hazard == "hidden-source" else 1]["visible"] = False
                else:
                    session["surfaces"][0 if hazard == "missing-source-token" else 1].pop("paneID")
                backend, transcript = self.backend(tree)
                with self.assertRaises(RuntimeError):
                    backend.locate("claude", None)
                self.assertEqual(transcript.writes, [])

    def test_wrong_or_shell_foreground_refuses(self):
        for source, peer in (("zsh", "codex"), ("omp", "codex"), ("claude", "zsh")):
            with self.subTest(source=source, peer=peer):
                backend, transcript = self.backend(agterm_tree(source=source, peer=peer))
                with self.assertRaises(RuntimeError):
                    backend.locate("claude", pc.PROFILES["codex"])
                self.assertEqual(transcript.writes, [])

    def test_target_becoming_hidden_or_shell_refuses_write(self):
        for hazard in ("hidden-source", "hidden-peer", "shell"):
            with self.subTest(hazard=hazard):
                backend, transcript = self.backend()
                target = backend.locate("claude", None)
                session = agterm_session(transcript.tree)
                if hazard.startswith("hidden"):
                    session["surfaces"][0 if hazard == "hidden-source" else 1]["visible"] = False
                else:
                    session["splitForeground"] = ["zsh"]
                with self.assertRaises(RuntimeError):
                    backend.type(target, MESSAGE)
                self.assertEqual(transcript.writes, [])

    def test_omp_remains_distinct_from_codex(self):
        backend, _ = self.backend(agterm_tree(peer="omp"))
        self.assertEqual(backend.locate("claude", None).profile.name, "omp")
        with self.assertRaises(RuntimeError):
            backend.locate("claude", pc.PROFILES["codex"])

    def test_unsuccessful_or_unwrapped_tree_refuses(self):
        for tree in ({"ok": False, "error": "not connected"}, {"workspaces": []}, {"ok": True, "result": {}}):
            with self.subTest(tree=tree):
                backend, transcript = self.backend(tree)
                with self.assertRaises(RuntimeError):
                    backend.locate("claude", None)
                self.assertEqual(transcript.writes, [])


if __name__ == "__main__":
    unittest.main()
