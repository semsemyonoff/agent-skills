#!/usr/bin/env python3
"""Validate a Vikunja task description or comment before sending it through MCP.

Vikunja renders HTML, not markdown. Reads a file (or stdin with "-"), prints one problem per line
and exits 1 when any is found. Optionally builds HTML from simple sections:

    html_check.py FILE|-               validate
    html_check.py --build FILE|-       build HTML from the section format, validate, print it

Section format for --build: blocks separated by blank lines. "# Title" starts an <h3>; "- " lines
form a <ul>; "1. " lines form an <ol>; anything else is a <p>. Inline "**x**" -> <b>, "`x`" -> <code>,
"#N" -> a task link when VIKUNJA_URL is set (plain "#N" otherwise). Text is escaped, so literal
< > & are safe.
"""

import html
import os
import re
import sys
from html.parser import HTMLParser

BASE = os.environ.get("VIKUNJA_URL", "").rstrip("/")
ALLOWED = {"p", "b", "strong", "i", "em", "u", "code", "pre", "ul", "ol", "li", "h1", "h2", "h3", "h4",
           "a", "br", "blockquote", "hr", "s", "mark"}
VOID = {"br", "hr"}
ESCAPED_TAG_RE = re.compile(r"&lt;/?(?:p|b|strong|i|em|code|pre|ul|ol|li|h[1-4]|a|br|blockquote)\b", re.I)


class Checker(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.problems: list[str] = []
        self.stack: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED:
            self.problems.append(f"line {self.getpos()[0]}: tag <{tag}> is not in the allowed set")
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.problems.append(f"line {self.getpos()[0]}: unbalanced </{tag}>")
            if tag in self.stack:
                while self.stack and self.stack.pop() != tag:
                    pass
        else:
            self.stack.pop()

    def handle_data(self, data):
        for n, line in enumerate(data.splitlines() or [data]):
            ln = self.getpos()[0] + n
            s = line.strip()
            if "**" in s:
                self.problems.append(f"line {ln}: markdown bold '**' (use <b>)")
            if "`" in s:
                self.problems.append(f"line {ln}: backtick (use <code>)")
            if re.match(r"^([-*+]\s|\d+[.)]\s)", s):
                self.problems.append(f"line {ln}: markdown list line {s[:30]!r} (use <ul>/<ol><li>)")
            if re.match(r"^#{1,6}\s", s):
                self.problems.append(f"line {ln}: markdown heading (use <h3>)")

    def close(self):
        super().close()
        for tag in self.stack:
            self.problems.append(f"unclosed <{tag}>")


def check(text: str) -> list[str]:
    problems = []
    if ESCAPED_TAG_RE.search(text):
        problems.append("entity-escaped tags (&lt;p&gt; ...): they render as visible text, send raw HTML")
    if not text.strip():
        problems.append("empty")
    elif not re.search(r"<[a-z][^>]*>", text, re.I):
        problems.append("no HTML tags at all: plain text collapses into one line, wrap in <p>")
    c = Checker()
    c.feed(text)
    c.close()
    return problems + c.problems


def inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    if not BASE:
        return s
    return re.sub(r"(?<![\w&])#(\d+)\b", rf'<a href="{BASE}/tasks/\1">#\1</a>', s)


def build(text: str) -> str:
    out = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [l.rstrip() for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        if lines[0].startswith("# "):
            out.append(f"<h3>{inline(lines[0][2:].strip())}</h3>")
            lines = lines[1:]
        if not lines:
            continue
        if all(l.startswith("- ") for l in lines):
            out.append("<ul>" + "".join(f"<li>{inline(l[2:])}</li>" for l in lines) + "</ul>")
        elif all(re.match(r"\d+\. ", l) for l in lines):
            out.append("<ol>" + "".join(f"<li>{inline(re.sub(r'^\d+\. ', '', l))}</li>" for l in lines) + "</ol>")
        else:
            out.append("<p>" + "<br>".join(inline(l) for l in lines) + "</p>")
    return "".join(out)


def main() -> int:
    args = sys.argv[1:]
    do_build = "--build" in args
    args = [a for a in args if a != "--build"]
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    text = sys.stdin.read() if args[0] == "-" else open(args[0], encoding="utf-8").read()
    if do_build:
        text = build(text)
    problems = check(text)
    for p in problems:
        print(f"problem: {p}", file=sys.stderr)
    if do_build:
        print(text)
    elif not problems:
        print("ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
