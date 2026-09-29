#!/usr/bin/env python3
"""Flag markdown leftovers in a Redmine Textile draft.

Usage: textile_check.py FILE [FILE...]

If a file contains ```textile fences (a *-drafts.md file), only the fenced blocks are checked,
so the fences themselves are not reported. Otherwise the whole file is checked.
Exit code 1 when anything is found, 0 when clean.
"""
import os
import re
import sys

CHECKS = [
    (re.compile(r"\*\*[^\s*][^*]*?\*\*"), "markdown bold **text**, use *text*"),
    (re.compile(r"^\s*```"), "code fence, use <pre>...</pre> or @code@"),
    (re.compile(r"\[[^\]\n]+\]\([^)\s]+\)"), "markdown link [text](url), use \"text\":url"),
    (re.compile(r"^\s*-\s+\S"), "'- ' list item, use '* '"),
    (re.compile(r"^\s*\d+[.)]\s+\S"), "'1. ' numbered item, use '# '"),
    (re.compile(r"^\s*>\s+\S"), "markdown quote '> ', use 'bq. '"),
    (re.compile(r"(?<!\w)`[^`\n]+`(?!\w)"), "backtick code `x`, use @x@"),
    (re.compile(r"^\s*\|\s*-{3,}"), "markdown table separator row, delete it (header cells are |_. x|)"),
]
HEADING = re.compile(r"^\s*(#{2,6})\s+\S")


def textile_lines(path):
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    fenced, inside, found = [], False, False
    for n, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith("```textile"):
            inside, found = True, True
            continue
        if inside and s.startswith("```"):
            inside = False
            continue
        if inside:
            fenced.append((n, line))
    return fenced if found else list(enumerate(lines, 1))


def main(paths):
    problems = 0
    for path in paths:
        in_pre = False
        in_numbered = False  # '## x' is a valid nested item only inside a '#' list
        for n, line in textile_lines(path):
            if "<pre" in line:
                in_pre = True
            if in_pre:
                if "</pre>" in line:
                    in_pre = False
                continue
            stripped = line.strip()
            if stripped:
                m = HEADING.match(line)
                if m and not in_numbered:
                    print(f"{path}:{n}: markdown heading, use 'h2. Title': {stripped[:60]}")
                    problems += 1
                    continue
                in_numbered = stripped.startswith("#")
            for rx, msg in CHECKS:
                if msg and rx.search(line):
                    print(f"{path}:{n}: {msg}: {line.strip()[:60]}")
                    problems += 1
    return 1 if problems else 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        sys.exit(__doc__)
    missing = [p for p in args if not os.path.isfile(p)]
    if missing:
        sys.exit(f"no such file: {', '.join(missing)}")
    sys.exit(main(args))
