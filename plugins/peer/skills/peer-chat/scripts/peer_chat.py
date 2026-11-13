#!/usr/bin/env python3
"""Safely send peer messages between Claude Code, Codex CLI and omp."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass, replace
from typing import Any, Protocol

PROBE_TIMEOUT = 3.0
SUBMIT_DELAY = 0.15
RETRY_ATTEMPTS = 5
RETRY_DELAY = 10.0
BOX_LINES = 80
EMPTY_CURSOR_COLUMN = 2
MIN_WRAPPED_PROBE = 40
RULE_RE = re.compile(r"^\s*[─━—-]{10,}\s*$")
TOP_RULE_RE = re.compile(r"^\s*(?:[─━—-]{10,}|[─━]+\s+\S.*[─━]\s*$)")
CODEX_PROMPT_RE = re.compile(r"^\s*›\s?(.*?)\s*$")
# Codex dims these hints in an empty composer; plain screen text loses the
# styling. send()/doctor still require the caret right after the prompt glyph.
CODEX_PLACEHOLDERS = frozenset({"Ask Codex to do anything", "Ask a follow-up question"})
BOX_PROMPT_RE = re.compile(r"^\s*❯\s?(.*?)\s*$")
LABEL_RE = re.compile(r"chat from \w+(?: \([^)]*\))?\s*:\s*", re.IGNORECASE)
ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
CURSOR_RE = re.compile(r"\x1b\[(\d+);(\d+)H")
PASTED_RE = re.compile(r"\[Pasted Content (\d+) chars?\]")
CLAUDE_PASTED_RE = re.compile(r"\[Pasted text #\d+\]")
OMP_PASTED_RE = re.compile(r"\[Paste #\d+, (?:(\d+) chars|\+(\d+) lines)\]")
OMP_CHIP_RE = re.compile(r"((?:|📄|txt) #([1-9]\d*))")
OMP_CARD_COUNT_RE = re.compile(r"╰[─ ]* (\d+) chars [─ ]*╯")
STATUS_RE = re.compile(
    r"^(?:.*(?:·|\|).*|\? for shortcuts.*|msg:.*|"
    r"(?:esc|tab|shift\+tab|ctrl\+\w+) (?:to |for ).*|"
    r".*\d+% (?:left|context left).*|[⏵▶]+\s*(?:bypass|accept edits|plan mode|auto mode).*)$",
    re.IGNORECASE,
)
DIALOG_RE = re.compile(
    r"^(?:do you trust\b|trust (?:this|the)\b|allow\b|approve\b|permission\b|"
    r"choose\b|select\b|press enter to (?:confirm|approve)|\d+[.)]\s|[❯›])",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Harness:
    name: str
    command: str
    submit: str
    bracketed_paste: bool = True


PROFILES = {
    "claude": Harness("claude", "claude", "enter"),
    "codex": Harness("codex", "codex", "tab"),
    "omp": Harness("omp", "omp", "followup"),
}
SENDER_NAMES = {"claude": "Claude", "codex": "Codex", "omp": "omp"}


@dataclass(frozen=True)
class Target:
    id: str
    profile: Harness
    pane_id: str | None = None
    pid: int | None = None


class PromptBlocked(RuntimeError):
    """A pre-write refusal; no input has been sent."""


class Backend(Protocol):
    name: str
    def locate(self, source: str, profile: Harness | None) -> Target: ...
    def candidates(self, source: str, profile: Harness | None) -> list[Target]: ...
    def screen(self, target: Target) -> str: ...
    def cursor_column(self, target: Target) -> int: ...
    def type(self, target: Target, text: str) -> None: ...
    def key(self, name: str) -> str: ...


def command_name(value: str) -> str:
    name = os.path.basename(value.strip())
    if not name or name in {".", ".."} or any(c.isspace() for c in name):
        raise ValueError("target command must be one executable name or path")
    return name


def target_profile(target: str, explicit_command: str | None = None) -> Harness | None:
    if target == "auto":
        if explicit_command:
            raise ValueError("--target-command requires an explicit --to harness")
        return None
    profile = PROFILES[target]
    configured = explicit_command or os.environ.get(f"PEER_CHAT_{target.upper()}_COMMAND")
    command = command_name(configured) if configured else profile.command
    if command in PROFILES and command != profile.command:
        raise ValueError("a different harness is not a wrapper; select it with --to")
    return replace(profile, command=command)


def runs(argv: Any, command: str) -> bool:
    """Match the executable, not a harness name appearing in prompt/flag text."""
    if not isinstance(argv, list) or not argv or not all(isinstance(p, str) for p in argv):
        return False
    if os.path.basename(argv[0]) == command:
        return True
    # Script launchers report the interpreter first. Never search arbitrary args.
    interpreter = os.path.basename(argv[0])
    if interpreter in {"node", "bun", "python", "python3", "bash", "sh", "zsh"}:
        for arg in argv[1:]:
            if arg.startswith("-"):
                return False
            return os.path.basename(arg) == command
    return False


def detected(argv: Any, profile: Harness | None) -> Harness | None:
    profiles = [profile] if profile else list(PROFILES.values())
    matches = [p for p in profiles if runs(argv, p.command)]
    return matches[0] if len(matches) == 1 else None


def select_target(targets: list[Target]) -> Target:
    if len(targets) == 1:
        return targets[0]
    if not targets:
        raise RuntimeError("no visible peer running the requested harness; nothing was typed")
    raise RuntimeError("more than one peer matches; do not guess a destination")


def run_command(command: list[str], stdin: str | None = None) -> str:
    result = subprocess.run(command, input=stdin, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError(f"{shlex.join(command[:3])} failed: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout


class Kitty:
    name = "kitty"
    KEYS = {"enter": "\r", "tab": "\t", "followup": "\x11"}

    def __init__(self, window_id: str, run: Any = None) -> None:
        self.window_id = int(window_id)
        self.run = run or self.ctl

    @staticmethod
    def ctl(args: list[str], stdin: str | None = None) -> str:
        command = ["kitty", "@"]
        if socket := os.environ.get("KITTY_LISTEN_ON"):
            command += ["--to", socket]
        return run_command([*command, *args], stdin)

    def tab_windows(self) -> list[dict[str, Any]]:
        for window in json.loads(self.run(["ls"])):
            for tab in window.get("tabs", []):
                windows = tab.get("windows", [])
                if any(w.get("id") == self.window_id for w in windows):
                    return windows
        raise RuntimeError(f"kitty window {self.window_id} not found; terminal context is stale")

    @staticmethod
    def process(window: dict[str, Any], profile: Harness | None) -> tuple[Harness, int | None] | None:
        matches = []
        for process in window.get("foreground_processes", []):
            if harness := detected(process.get("cmdline"), profile):
                matches.append((harness, process.get("pid")))
        return matches[0] if len(matches) == 1 else None

    def candidates(self, source: str, profile: Harness | None) -> list[Target]:
        windows = self.tab_windows()
        own = next(w for w in windows if w.get("id") == self.window_id)
        if not self.process(own, PROFILES[source]):
            raise RuntimeError(f"own kitty window is not running {source}; wrong --from or stale context")
        targets = []
        for window in windows:
            if window.get("id") == self.window_id:
                continue
            if match := self.process(window, profile):
                targets.append(Target(str(window["id"]), match[0], pid=match[1]))
        return targets

    def locate(self, source: str, profile: Harness | None) -> Target:
        return select_target(self.candidates(source, profile))

    def require_target(self, target: Target) -> None:
        for window in self.tab_windows():
            if str(window.get("id")) == target.id and window.get("id") != self.window_id:
                match = self.process(window, target.profile)
                if match and (target.pid is None or match[1] == target.pid):
                    return
                raise RuntimeError("peer process changed; nothing more will be typed")
        raise RuntimeError("peer window left this kitty tab")

    def screen(self, target: Target) -> str:
        self.require_target(target)
        return self.run(["get-text", "--match", f"id:{target.id}", "--extent", "screen"])

    def cursor_column(self, target: Target) -> int:
        self.require_target(target)
        text = self.run(["get-text", "--match", f"id:{target.id}", "--extent", "screen", "--add-cursor"])
        found = CURSOR_RE.findall(text)
        if not found:
            raise RuntimeError("kitty get-text returned no cursor position")
        return int(found[-1][1]) - 1

    def type(self, target: Target, text: str) -> None:
        self.require_target(target)
        self.run(["send-text", "--match", f"id:{target.id}", "--stdin"], stdin=text)

    def key(self, name: str) -> str:
        return self.KEYS[name]


class Agterm:
    name = "agterm"
    KEYS = {"enter": "\n", "tab": "\t", "followup": "\x11"}

    def __init__(self, session: str | None = None) -> None:
        self.session = session or os.environ.get("AGTERM_SESSION_ID")
        self.own_pane = os.environ.get("AGTERM_PANE_ID")

    def ctl(self, *args: str, stdin: str | None = None) -> str:
        command = os.environ.get("AGTERMCTL", "agtermctl")
        options = []
        for flag, variable in (("--socket", "AGTERM_SOCKET"), ("--window", "AGTERM_WINDOW_ID")):
            if value := os.environ.get(variable):
                options += [flag, value]
        return run_command([command, *args, *options], stdin)

    def tree(self) -> list[dict[str, Any]]:
        envelope = json.loads(self.ctl("tree", "--json"))
        if envelope.get("ok") is not True:
            raise RuntimeError(f"agterm tree failed: {envelope.get('error', 'invalid response')}")
        tree = envelope.get("result", {}).get("tree")
        if not isinstance(tree, dict) or not isinstance(tree.get("workspaces"), list):
            raise RuntimeError("agterm tree returned an unsupported response")
        return [s for w in tree["workspaces"] for s in w.get("sessions", [])]

    @staticmethod
    def surfaces(session: dict[str, Any]) -> list[dict[str, Any]]:
        if not session.get("hasSplit") or session.get("overlay") or session.get("htmlOverlays"):
            return []
        if any(str(p.get("kind", "")).startswith("overlay") and p.get("visible")
               for p in session.get("surfaces", [])):
            return []
        return [p for p in session.get("surfaces", [])
                if p.get("kind") in {"left", "right"} and p.get("visible") is True and p.get("paneID")]

    @staticmethod
    def foreground(session: dict[str, Any], pane: dict[str, Any]) -> Any:
        return session.get("foreground" if pane["kind"] == "left" else "splitForeground")

    def source_session(self, source: str) -> tuple[dict[str, Any], dict[str, Any]]:
        sessions = self.tree()
        if self.session:
            sessions = [s for s in sessions if str(s.get("id", "")).lower().startswith(self.session.lower())]
            if len(sessions) != 1:
                raise RuntimeError("agterm session identity is missing or ambiguous")
        elif not self.own_pane:
            raise RuntimeError("agterm needs AGTERM_SESSION_ID or AGTERM_PANE_ID; never infer the active session")
        matches = []
        for session in sessions:
            panes = self.surfaces(session)
            if len(panes) != 2:
                continue
            for pane in panes:
                if self.own_pane and pane["paneID"] != self.own_pane:
                    continue
                if runs(self.foreground(session, pane), PROFILES[source].command):
                    matches.append((session, pane))
        if len(matches) != 1:
            raise RuntimeError("own agterm pane cannot be verified; split must be visible and --from must match")
        return matches[0]

    def candidates(self, source: str, profile: Harness | None) -> list[Target]:
        session, own = self.source_session(source)
        targets = []
        for pane in self.surfaces(session):
            if pane["paneID"] == own["paneID"]:
                continue
            if harness := detected(self.foreground(session, pane), profile):
                targets.append(Target(str(session["id"]), harness, str(pane["paneID"])))
        return targets

    def locate(self, source: str, profile: Harness | None) -> Target:
        return select_target(self.candidates(source, profile))

    def require_target(self, target: Target) -> None:
        for session in self.tree():
            if str(session.get("id")) != target.id:
                continue
            panes = self.surfaces(session)
            if len(panes) != 2:
                continue
            for pane in panes:
                if pane["paneID"] == target.pane_id and runs(self.foreground(session, pane), target.profile.command):
                    return
        raise RuntimeError("peer agterm pane is hidden, covered, gone, or running a different process")

    def screen(self, target: Target) -> str:
        self.require_target(target)
        return self.ctl("session", "text", "--target", target.id, "--pane-id", str(target.pane_id))

    def cursor_column(self, target: Target) -> int:
        self.require_target(target)
        value = self.ctl("surface", "cursor", "--target", target.id, "--pane-id", str(target.pane_id)).strip()
        try:
            return int(value)
        except ValueError as err:
            raise RuntimeError(f"agterm cursor returned {value!r}") from err

    def type(self, target: Target, text: str) -> None:
        self.require_target(target)
        response = json.loads(self.ctl("session", "type", "--stdin", "--target", target.id,
                                      "--pane-id", str(target.pane_id), "--json", stdin=text))
        if response.get("ok") is not True:
            raise RuntimeError(f"agterm type failed: {response.get('error', 'invalid response')}")

    def key(self, name: str) -> str:
        return self.KEYS[name]


def pick_backend(session: str | None = None, backend: str = "auto") -> Backend:
    window = os.environ.get("KITTY_WINDOW_ID")
    agterm = (session or os.environ.get("AGTERM_ENABLED") == "1" or os.environ.get("TERM_PROGRAM") == "agterm"
              or os.environ.get("AGTERM_SESSION_ID") or os.environ.get("AGTERM_PANE_ID"))
    if backend == "auto":
        if window and agterm:
            raise ValueError("conflicting terminal identities; select --backend explicitly")
        if window:
            backend = "kitty"
        elif os.environ.get("KITTY_LISTEN_ON") or os.environ.get("TERM") == "xterm-kitty":
            raise ValueError("kitty context lacks KITTY_WINDOW_ID; in omp run through Bash, not an Eval subprocess")
        elif agterm:
            backend = "agterm"
        else:
            raise ValueError("no supported terminal context; run through the harness shell tool with inherited terminal variables")
    if backend == "kitty":
        if session:
            raise ValueError("--session applies to agterm only")
        if not window:
            raise ValueError("kitty requires inherited KITTY_WINDOW_ID; do not guess a window")
        return Kitty(window)
    return Agterm(session)


def screen_lines(text: str) -> list[str]:
    return ANSI_RE.sub("", text).splitlines()[-BOX_LINES:]


def status_footer(lines: list[str]) -> bool:
    rows = [line.strip() for line in lines if line.strip()]
    return bool(rows) and all(not DIALOG_RE.match(line) and STATUS_RE.fullmatch(line) for line in rows)


def boxed_prompt_text(text: str, *, titled: bool, claude_paste: bool = False) -> str | None:
    lines = screen_lines(text)
    # Only the bottommost box can be the current composer. Historical prompt
    # glyphs in output must not certify an approval dialog or a chooser.
    lower = next((i for i in range(len(lines) - 1, -1, -1) if RULE_RE.fullmatch(lines[i])), None)
    if lower is None:
        return None
    upper_rule = TOP_RULE_RE if titled else RULE_RE
    upper = next((i for i in range(lower - 1, -1, -1) if upper_rule.match(lines[i])), None)
    if upper is None:
        return None
    body = lines[upper + 1:lower]
    if not body or not (match := BOX_PROMPT_RE.fullmatch(body[0])):
        return None
    # A second prompt/selector or another box means this is not a composer.
    if any(BOX_PROMPT_RE.match(line) or TOP_RULE_RE.match(line) for line in body[1:]):
        return None
    content = " ".join([match.group(1).strip(), *(line.strip() for line in body[1:])]).strip()
    footer = lines[lower + 1:]
    if claude_paste and (not content or CLAUDE_PASTED_RE.fullmatch(content)):
        # Claude retains this composer hint briefly after Enter clears the
        # paste token. Neither phase changes the box/cursor/dialog checks.
        footer = [line for line in footer if line.strip() != "paste again to expand"]
    return content if status_footer(footer) else None


def claude_prompt_text(text: str) -> str | None:
    return boxed_prompt_text(text, titled=True, claude_paste=True)


def omp_prompt_text(text: str) -> str | None:
    content = boxed_prompt_text(text, titled=True)
    chip = OMP_CHIP_RE.fullmatch(content or "")
    if not chip:
        return content
    # omp stages large pastes as an atomic chip with metadata in a separate
    # card immediately above the composer. Never trust the opaque token alone.
    lines = screen_lines(text)
    lower = next(i for i in range(len(lines) - 1, -1, -1) if RULE_RE.fullmatch(lines[i]))
    upper = next(i for i in range(lower - 1, -1, -1) if TOP_RULE_RE.match(lines[i]))
    card = [line.rstrip() for line in lines[:upper]]
    while card and not card[-1]:
        card.pop()
    if len(card) < 6:
        return content
    header, *body, footer = card[-6:]
    if not re.fullmatch(r"╭[─ ]* " + re.escape(chip[1]) + r" [─ ]*╮", header):
        return content
    if not all(re.fullmatch(r"│.*│", line) for line in body):
        return content
    count = OMP_CARD_COUNT_RE.fullmatch(footer)
    if not count:
        return content
    # Reuse the legacy paste's UTF-16 length check; the ID and caption must
    # belong to this exact composer chip, not a historical or adjacent card.
    return f"[Paste #{chip[2]}, {count[1]} chars]"


def codex_prompt_text(text: str) -> str | None:
    lines = screen_lines(text)
    for index in range(len(lines) - 1, -1, -1):
        if match := CODEX_PROMPT_RE.fullmatch(lines[index]):
            following = lines[index + 1:]
            separator = next((i for i, line in enumerate(following) if not line.strip()), None)
            if separator is None or not status_footer(following[separator + 1:]):
                return None
            wrapped = following[:separator]
            if any(BOX_PROMPT_RE.match(line) or CODEX_PROMPT_RE.match(line) for line in wrapped):
                return None
            if not wrapped and match.group(1).strip() in CODEX_PLACEHOLDERS:
                return ""
            return " ".join([match.group(1).strip(), *(line.strip() for line in wrapped)]).strip()
    return None


def prompt_text(profile: Harness, text: str) -> str | None:
    return {"claude": claude_prompt_text, "codex": codex_prompt_text, "omp": omp_prompt_text}[profile.name](text)


def sender_label(sender: str) -> str:
    return f"Chat from {SENDER_NAMES[sender]} (reply via peer-chat skill): "


def normalize(sender: str, message: str) -> str:
    if any((ord(c) < 32 and not c.isspace()) or 127 <= ord(c) < 160 for c in message):
        raise ValueError("chat message contains terminal control characters")
    line = " ".join(message.split())
    while match := LABEL_RE.match(line):
        line = line[match.end():]
    if not line:
        raise ValueError("chat message is empty")
    return sender_label(sender) + line


def composer_has_message(profile: Harness, content: str, typed: str) -> bool:
    visible = "".join(content.split())
    expected = "".join(typed.split())
    if visible == expected:
        return True
    # An overflowing boxed composer can expose only a middle slice. Require a
    # substantial exact slice, not an arbitrary nonempty row or just the label.
    if (profile.name in {"claude", "omp"} and len(visible) >= MIN_WRAPPED_PROBE
            and visible in expected and not expected.startswith(visible)):
        return True
    # Claude 2.1 renders a new bracketed paste as an opaque numbered token.
    # send() establishes an empty composer before this paste and rechecks the
    # token before submission; an already-present token is never overwritten.
    if profile.name == "claude" and profile.bracketed_paste and CLAUDE_PASTED_RE.fullmatch(content):
        return True
    if profile.name == "codex" and (match := PASTED_RE.fullmatch(content)):
        return int(match.group(1)) == len(typed)
    if profile.name == "omp" and (match := OMP_PASTED_RE.fullmatch(content)):
        # omp's editor uses JavaScript string length (UTF-16 code units).
        if match.group(1):
            return int(match.group(1)) == len(typed.encode("utf-16-le")) // 2
        return int(match.group(2)) == typed.count("\n") + 1
    return False


def wait_for_composed(backend: Backend, target: Target, typed: str) -> str | None:
    deadline = time.monotonic() + PROBE_TIMEOUT
    while True:
        content = prompt_text(target.profile, backend.screen(target))
        if content and composer_has_message(target.profile, content, typed):
            return content
        if time.monotonic() >= deadline:
            return None
        time.sleep(0.1)


def wait_for_accepted(backend: Backend, target: Target, held: str) -> bool:
    deadline = time.monotonic() + PROBE_TIMEOUT
    while True:
        content = prompt_text(target.profile, backend.screen(target))
        if content == "":
            return True
        if content is not None and content != held:
            return False
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.1)


def send(backend: Backend, target: Target, sender: str, message: str) -> int:
    typed = normalize(sender, message)
    before = prompt_text(target.profile, backend.screen(target))
    if before is None:
        raise RuntimeError("target is not a recognized composer; nothing was typed (dialog/approval may be open)")
    if before or backend.cursor_column(target) != EMPTY_CURSOR_COLUMN:
        raise PromptBlocked("target composer is not empty; nothing was typed")
    payload = f"\x1b[200~{typed}\x1b[201~" if target.profile.bracketed_paste else typed
    backend.type(target, payload)
    held = wait_for_composed(backend, target, typed)
    if held is None:
        raise RuntimeError("message was typed but not verified in the target composer; submit withheld; do not resend")
    time.sleep(SUBMIT_DELAY)
    content = prompt_text(target.profile, backend.screen(target))
    if content is None or not composer_has_message(target.profile, content, typed):
        raise RuntimeError("composer changed after typing; submit withheld; do not resend")
    backend.type(target, backend.key(target.profile.submit))
    if not wait_for_accepted(backend, target, content):
        raise RuntimeError("message acceptance is unconfirmed; it may remain composed; do not resend")
    return len(message)


def send_with_retry(backend: Backend, target: Target, sender: str, message: str) -> int:
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            return send(backend, target, sender, message)
        except PromptBlocked:
            if attempt == RETRY_ATTEMPTS:
                raise
            print(f"peer-chat: composer occupied, retry {attempt}/{RETRY_ATTEMPTS} in {RETRY_DELAY:g}s",
                  file=sys.stderr, flush=True)
            time.sleep(RETRY_DELAY)
    raise AssertionError("unreachable")


def doctor(backend: Backend, source: str, profile: Harness | None) -> dict[str, Any]:
    report: dict[str, Any] = {"backend": backend.name, "source": source, "peers": [], "ready": False}
    try:
        targets = backend.candidates(source, profile)
        report["peers"] = [{"id": t.id, "harness": t.profile.name, "pane_id": t.pane_id} for t in targets]
        target = select_target(targets)
        report["target"] = {"id": target.id, "harness": target.profile.name, "pane_id": target.pane_id}
        content = prompt_text(target.profile, backend.screen(target))
        report["composer"] = "unrecognized" if content is None else "occupied" if content else "empty"
        report["ready"] = content == "" and backend.cursor_column(target) == EMPTY_CURSOR_COLUMN
        if not report["ready"]:
            report["error"] = "peer composer is not confirmably empty"
    except (OSError, subprocess.SubprocessError, ValueError, RuntimeError) as err:
        report["error"] = str(err)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="sender", choices=PROFILES, required=True, help="actual sender harness, not model")
    parser.add_argument("--to", choices=[*PROFILES, "auto"], default="auto")
    parser.add_argument("--backend", choices=["auto", "kitty", "agterm"], default="auto")
    parser.add_argument("--session", help="injected or user-supplied agterm session id")
    parser.add_argument("--target-command", type=command_name, metavar="NAME", help="known wrapper for explicit --to")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--stdin", action="store_true", help="read one message from stdin")
    mode.add_argument("--doctor", action="store_true", help="read-only discovery and composer checks")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        profile = target_profile(args.to, args.target_command)
        backend = pick_backend(args.session, args.backend)
        if args.doctor:
            report = doctor(backend, args.sender, profile)
            print(json.dumps(report))
            return 0 if report["ready"] else 1
        target = backend.locate(args.sender, profile)
        sent = send_with_retry(backend, target, args.sender, sys.stdin.read())
        print(json.dumps({"sent": sent, "backend": backend.name, "source": args.sender, "target": target.profile.name}))
        return 0
    except KeyboardInterrupt:
        print("peer-chat: interrupted; delivery may be unconfirmed, do not resend blindly", file=sys.stderr)
        return 130
    except (OSError, subprocess.SubprocessError, ValueError, RuntimeError) as err:
        if args.doctor:
            print(json.dumps({"ready": False, "source": args.sender, "error": str(err)}))
        else:
            print(f"peer-chat: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
