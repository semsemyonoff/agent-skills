#!/usr/bin/env python3
"""Send one peer-chat message between Claude Code and Codex in a split pane.

Two terminal backends: kitty (picked when KITTY_WINDOW_ID is set) and agterm.
The copy under codex/peer-chat/scripts must stay byte-identical to this one.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, replace
from typing import Any, Protocol

SUBMIT_DELAY = 0.15
PROBE_TIMEOUT = 0.6
RETRY_ATTEMPTS = 5
RETRY_DELAY = 10.0
BOX_LINES = 40
EMPTY_CURSOR_COLUMN = 2
MIN_WRAPPED_PROBE = 40
RULE_RE = re.compile(r"^\s*[─—-]{10,}\s*$")
CODEX_PROMPT_RE = re.compile(r"^\s*›[\s ]*(.*?)\s*$")
CLAUDE_PROMPT_RE = re.compile(r"^\s*❯[\s ]*(.*?)\s*$")
PASTED_RE = re.compile(r"\[Pasted Content \d+ chars?\]")
LABEL_RE = re.compile(r"chat from \w+(?: \([^)]*\))?\s*:\s*", re.IGNORECASE)
CURSOR_RE = re.compile(r"\x1b\[(\d+);(\d+)H")


@dataclass(frozen=True)
class Profile:
    # agterm split side; kitty finds the peer by command within the tab instead
    pane: str
    agent: str
    command: str
    label: str
    submit: str
    # Codex 0.157 guesses pastes from keystroke timing: a long message renders
    # late (past PROBE_TIMEOUT), and under load a literal prefix renders first,
    # passes the composer check, and the submit key lands inside the burst as
    # text. A bracketed paste arrives as one event, so neither can happen.
    bracketed_paste: bool = False


# The Codex label names the skill because gpt-6-sol does not load it from the
# skill description alone, and then answers in its own pane where Claude never
# sees the reply.
PROFILES = {
    "claude": Profile("left", "claude", "claude", "Chat from Codex: ", "enter"),
    "codex": Profile(
        "right",
        "codex",
        "codex",
        "Chat from Claude (reply via peer-chat skill): ",
        "tab",
        True,
    ),
}


class PromptBlocked(RuntimeError):
    """The target prompt is occupied before any text was written."""


class Backend(Protocol):
    def locate(self, profile: Profile) -> str: ...
    def screen(self, target: str, profile: Profile) -> str: ...
    def cursor_column(self, target: str, profile: Profile) -> int: ...
    def type(self, target: str, profile: Profile, text: str) -> None: ...
    def key(self, name: str) -> str: ...


def command_name(value: str) -> str:
    name = os.path.basename(value.strip())
    if not name or name in {".", ".."} or any(char.isspace() for char in name):
        raise ValueError("target command must be one executable name or path")
    return name


def target_profile(target: str, explicit_command: str | None) -> Profile:
    profile = PROFILES[target]
    env_name = f"PEER_CHAT_{profile.agent.upper()}_COMMAND"
    configured = explicit_command or os.environ.get(env_name) or profile.command
    return replace(profile, command=command_name(configured))


def runs(foreground: Any, command: str) -> bool:
    if not isinstance(foreground, list):
        return False
    pattern = re.compile(rf"(?:^|[/\s]){re.escape(command)}(?:$|\s)")
    return any(pattern.search(str(part)) for part in foreground)


def wrapper_hint(profile: Profile) -> str:
    return f"{profile.agent} target is not running {profile.command!r}; for a wrapper, pass --target-command NAME"


# --- agterm -----------------------------------------------------------------


def checkout_key(path: str) -> str:
    command = [
        "git", "-C", path, "rev-parse", "--path-format=absolute", "--git-common-dir"
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return os.path.realpath(path)
    if result.returncode == 0 and result.stdout.strip():
        return os.path.realpath(result.stdout.strip())
    return os.path.realpath(path)


def walk(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        if "id" in value and ("foreground" in value or "splitForeground" in value):
            yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


class Agterm:
    KEYS = {"enter": "\n", "tab": "\t"}

    def __init__(self, session: str | None) -> None:
        self.session = session or os.environ.get("AGTERM_SESSION_ID")

    def ctl(self, *args: str) -> str:
        command = os.environ.get("AGTERMCTL", "agtermctl")
        result = subprocess.run(
            [command, *args],
            capture_output=True,
            check=False,
            text=True,
            timeout=30,
        )
        if result.returncode:
            detail = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f"agtermctl {' '.join(args)} failed: {detail}")
        return result.stdout

    def tree(self) -> Any:
        return json.loads(self.ctl("tree", "--json"))

    @staticmethod
    def has_target(info: dict[str, Any], profile: Profile) -> bool:
        if not info.get("hasSplit"):
            return False
        field = "foreground" if profile.pane == "left" else "splitForeground"
        return runs(info.get(field), profile.command)

    def find_node(self, sid: str) -> dict[str, Any]:
        needle = sid.lower()
        matches = [
            info
            for info in walk(self.tree())
            if str(info.get("id", "")).lower().startswith(needle)
        ]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise RuntimeError(f"no such session: {sid}")
        raise RuntimeError(f"ambiguous session prefix {sid!r}")

    def require_target(self, sid: str, profile: Profile) -> str:
        info = self.find_node(sid)
        if not info.get("hasSplit"):
            raise RuntimeError(f"session {sid} has no split")
        if not self.has_target(info, profile):
            raise RuntimeError(wrapper_hint(profile))
        return str(info["id"])

    def locate(self, profile: Profile) -> str:
        if self.session:
            return self.require_target(self.session, profile)
        wanted = checkout_key(os.getcwd())
        matches = [
            str(info["id"])
            for info in walk(self.tree())
            if self.has_target(info, profile)
            and info.get("cwd")
            and checkout_key(str(info["cwd"])) == wanted
        ]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise RuntimeError(
                "this checkout maps to no session running the expected "
                f"{profile.agent}-{profile.pane} layout; "
                "for a wrapper, pass --target-command NAME"
            )
        raise RuntimeError(
            "more than one session shares this checkout; pass --session ID or launch "
            "Codex with shell_environment_policy.set.AGTERM_SESSION_ID"
        )

    def screen(self, target: str, profile: Profile) -> str:
        self.require_target(target, profile)
        return self.ctl(
            "session", "text", "--pane", profile.pane, "--target", target,
            "--lines", str(BOX_LINES),
        )

    def cursor_column(self, target: str, profile: Profile) -> int:
        self.require_target(target, profile)
        value = self.ctl(
            "surface", "cursor", "--target", f"surface:{target}:{profile.pane}"
        ).strip()
        try:
            return int(value)
        except ValueError as err:
            raise RuntimeError(f"surface cursor returned {value!r}") from err

    def type(self, target: str, profile: Profile, text: str) -> None:
        self.require_target(target, profile)
        self.ctl("session", "type", text, "--pane", profile.pane, "--target", target)

    def key(self, name: str) -> str:
        return self.KEYS[name]


# --- kitty ------------------------------------------------------------------


def kitty_run(args: list[str], stdin: str | None = None) -> str:
    result = subprocess.run(
        ["kitty", "@", *args],
        input=stdin,
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"kitty @ {args[0]} failed: {detail}")
    return result.stdout


class Kitty:
    # raw bytes into the pty: Return is CR, as a real keypress sends it
    KEYS = {"enter": "\r", "tab": "\t"}

    def __init__(
        self, window_id: str, run: Callable[..., str] = kitty_run
    ) -> None:
        self.window_id = int(window_id)
        self.run = run

    def tab_windows(self) -> list[dict[str, Any]]:
        """Windows of the tab holding this one; the peer must share the tab."""
        for os_window in json.loads(self.run(["ls"])):
            for tab in os_window.get("tabs", []):
                windows = tab.get("windows", [])
                if any(w.get("id") == self.window_id for w in windows):
                    return windows
        raise RuntimeError(f"kitty window {self.window_id} not found in `kitty @ ls`")

    @staticmethod
    def has_target(window: dict[str, Any], profile: Profile) -> bool:
        cmdlines = [
            " ".join(p.get("cmdline") or [])
            for p in window.get("foreground_processes", [])
        ]
        return runs(cmdlines, profile.command)

    def locate(self, profile: Profile) -> str:
        matches = [
            str(w["id"])
            for w in self.tab_windows()
            if w.get("id") != self.window_id and self.has_target(w, profile)
        ]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise RuntimeError(f"no other window in this kitty tab: {wrapper_hint(profile)}")
        raise RuntimeError(
            f"more than one window in this kitty tab runs {profile.command!r}: "
            + ", ".join(matches)
        )

    def require_target(self, target: str, profile: Profile) -> None:
        for w in self.tab_windows():
            if str(w.get("id")) == target:
                if not self.has_target(w, profile):
                    raise RuntimeError(wrapper_hint(profile))
                return
        raise RuntimeError(f"kitty window {target} left this tab")

    def screen(self, target: str, profile: Profile) -> str:
        self.require_target(target, profile)
        return self.run(["get-text", "--match", f"id:{target}", "--extent", "screen"])

    def cursor_column(self, target: str, profile: Profile) -> int:
        self.require_target(target, profile)
        text = self.run(
            ["get-text", "--match", f"id:{target}", "--extent", "screen", "--add-cursor"]
        )
        found = CURSOR_RE.findall(text)
        if not found:
            raise RuntimeError("kitty get-text returned no cursor position")
        return int(found[-1][1]) - 1

    def type(self, target: str, profile: Profile, text: str) -> None:
        self.require_target(target, profile)
        self.run(["send-text", "--match", f"id:{target}", "--stdin"], stdin=text)

    def key(self, name: str) -> str:
        return self.KEYS[name]


def pick_backend(session: str | None) -> Backend:
    window = os.environ.get("KITTY_WINDOW_ID")
    if window:
        if session:
            raise ValueError("--session applies to agterm only; kitty finds the peer in this tab")
        return Kitty(window)
    return Agterm(session)


# --- composer checks ----------------------------------------------------------


def codex_prompt_text(text: str) -> str | None:
    for line in reversed(text.splitlines()[-BOX_LINES:]):
        if match := CODEX_PROMPT_RE.match(line):
            return match.group(1)
    return None


def claude_prompt_text(text: str) -> str | None:
    lines = text.splitlines()[-BOX_LINES:]
    for index in range(len(lines) - 1, 0, -1):
        match = CLAUDE_PROMPT_RE.match(lines[index])
        if not match or not RULE_RE.match(lines[index - 1]):
            continue
        if any(RULE_RE.match(line) for line in lines[index + 1 :]):
            return match.group(1)
    return None


def prompt_text(profile: Profile, text: str) -> str | None:
    if profile.agent == "codex":
        return codex_prompt_text(text)
    return claude_prompt_text(text)


def normalize(profile: Profile, message: str) -> str:
    line = " ".join(message.split())
    while match := LABEL_RE.match(line):
        line = line[match.end() :]
    if not line:
        raise ValueError("chat message is empty")
    return profile.label + line


def composer_has_message(profile: Profile, content: str, typed: str) -> bool:
    if profile.agent == "claude":
        # A message long enough to overflow Claude's composer scrolls it, so the
        # first rendered row is some middle line and the label check can never
        # match. Fall back to proving the visible row is a slice of what we
        # typed, which is still evidence the text landed in this pane and not in
        # a dialog. Codex escapes this only because it collapses a long paste
        # into a plaque that PASTED_RE accepts.
        if content.startswith(profile.label):
            return True
        return len(content) >= MIN_WRAPPED_PROBE and content in typed
    required = min(len(typed), MIN_WRAPPED_PROBE)
    literal = typed.startswith(content) and len(content) >= required
    return literal or bool(PASTED_RE.fullmatch(content))


def wait_for_composed(backend: Backend, target: str, profile: Profile, typed: str) -> str | None:
    deadline = time.monotonic() + PROBE_TIMEOUT
    while True:
        content = prompt_text(profile, backend.screen(target, profile))
        if content and composer_has_message(profile, content, typed):
            return content
        if time.monotonic() >= deadline:
            return None
        time.sleep(0.1)


def wait_for_accepted(backend: Backend, target: str, profile: Profile, held: str) -> bool:
    deadline = time.monotonic() + PROBE_TIMEOUT
    while True:
        content = prompt_text(profile, backend.screen(target, profile))
        if content is None or content != held:
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.1)


def send(backend: Backend, target: str, profile: Profile, message: str) -> int:
    typed = normalize(profile, message)
    if backend.cursor_column(target, profile) != EMPTY_CURSOR_COLUMN:
        raise PromptBlocked("target composer is not confirmably empty; nothing was typed")

    payload = f"\x1b[200~{typed}\x1b[201~" if profile.bracketed_paste else typed
    backend.type(target, profile, payload)
    held = wait_for_composed(backend, target, profile, typed)
    if held is None:
        raise RuntimeError(
            "message was typed but not verified in the target composer; submit withheld"
        )

    time.sleep(SUBMIT_DELAY)
    backend.type(target, profile, backend.key(profile.submit))
    if not wait_for_accepted(backend, target, profile, held):
        raise RuntimeError("target did not accept the message; it may remain composed")
    return len(message)


def send_with_retry(backend: Backend, target: str, profile: Profile, message: str) -> int:
    """Retry only a pre-write occupied-composer refusal."""
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            return send(backend, target, profile, message)
        except PromptBlocked as err:
            if attempt == RETRY_ATTEMPTS:
                raise PromptBlocked(
                    f"{err} after {RETRY_ATTEMPTS} attempts"
                ) from err
            print(
                f"peer-chat: attempt {attempt}/{RETRY_ATTEMPTS} blocked; "
                f"retrying in {RETRY_DELAY:g}s: {err}",
                file=sys.stderr,
                flush=True,
            )
            time.sleep(RETRY_DELAY)
    raise AssertionError("unreachable")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--to", choices=PROFILES, required=True)
    parser.add_argument("--session", help="agterm session id")
    parser.add_argument(
        "--target-command",
        type=command_name,
        metavar="NAME",
        help="target agent executable or wrapper name",
    )
    parser.add_argument("--stdin", action="store_true", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        profile = target_profile(args.to, args.target_command)
        backend = pick_backend(args.session)
        target = backend.locate(profile)
        sent = send_with_retry(backend, target, profile, sys.stdin.read())
        print(json.dumps({"sent": sent}))
        return 0
    except KeyboardInterrupt:
        print("peer-chat: interrupted", file=sys.stderr)
        return 130
    except (OSError, subprocess.SubprocessError, ValueError, RuntimeError) as err:
        print(f"peer-chat: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
