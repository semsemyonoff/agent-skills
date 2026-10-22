#!/usr/bin/env python3
"""Read the first nonempty portable rule file; never write or merge rules."""
import argparse
import json
import os
from pathlib import Path
import re
import sys


def load_rules(name, project):
    if name not in ("brainstorm", "planning"):
        raise ValueError("rule name must be brainstorm or planning")
    project = Path(project).expanduser().resolve()
    config = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config").expanduser()
    profile = os.environ.get("AGENT_SKILLS_PROFILE") or None
    if profile is not None and not re.fullmatch(r"[a-z0-9-]+", profile):
        raise ValueError("AGENT_SKILLS_PROFILE must match [a-z0-9-]+")
    filename = name + "-rules.md"
    # The profile replaces only the user file, with no fallback to the common one.
    user_filename = name + "-rules." + profile + ".md" if profile else filename
    candidates = (
        ("project-agents", project / ".agents" / filename),
        ("project-claude", project / ".claude" / filename),
        ("user", config / "agent-skills" / user_filename),
    )
    for provenance, path in candidates:
        try:
            content = path.read_text(encoding="utf-8")
        except (FileNotFoundError, IsADirectoryError):
            continue
        if content:  # Match upstream -s: whitespace is nonempty; zero bytes fall through.
            return {"name": name, "path": str(path.absolute()),
                    "provenance": provenance, "content": content, "profile": profile}
    return {"name": name, "path": None, "provenance": None, "content": "", "profile": profile}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", choices=("brainstorm", "planning"), required=True)
    parser.add_argument("--project", default=str(Path.cwd()), help="actual project directory; defaults to cwd")
    args = parser.parse_args(argv)
    try:
        result = load_rules(args.name, args.project)
    except (OSError, UnicodeError, ValueError) as error:
        print("cannot read custom rules: " + str(error), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
