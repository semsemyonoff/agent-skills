#!/usr/bin/env python3
"""Validate repo layout: marketplace, plugin manifests, skill/command frontmatter, paths, links.

Frontmatter rules follow skill-creator's quick_validate.py (the agent-skills spec); Claude-only keys
are allowed in plugins, codex/ skills are held to the spec keys.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SPEC_KEYS = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
CLAUDE_KEYS = SPEC_KEYS | {
    "argument-hint", "model", "disable-model-invocation", "user-invocable", "when_to_use",
    "context", "agent", "hooks",
}
COMMAND_KEYS = {"description", "argument-hint", "allowed-tools", "model", "disable-model-invocation"}

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
# skills run from a plugin cache or ~/.agents/skills, so paths into install dirs or homes break
FORBIDDEN_PATH_RE = re.compile(r"~/\.claude/(skills|plugins)|~/\.agents/skills|/home/[a-z]|/Users/[A-Za-z]")
LINK_RE = re.compile(r"\]\(([^)\s#]+)(?:#[^)]*)?\)")

errors: list[str] = []


def err(path: Path, msg: str) -> None:
    errors.append(f"{path.relative_to(ROOT)}: {msg}")


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        err(path, "missing")
    except json.JSONDecodeError as e:
        err(path, f"invalid JSON: {e}")
    return None


def parse_frontmatter(path: Path) -> dict[str, str] | None:
    """Minimal YAML subset: `key: value`, quoted values, `>`/`|` block scalars, nested maps skipped."""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        err(path, "no frontmatter (--- ... ---) at the top")
        return None
    result: dict[str, str] = {}
    lines = m.group(1).split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        km = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not km:
            if line.strip() and not line.startswith((" ", "\t", "#")):
                err(path, f"unparsable frontmatter line: {line!r}")
            i += 1
            continue
        key, value = km.group(1), km.group(2).strip()
        i += 1
        if value in (">", "|", ">-", "|-", ""):
            block = []
            while i < len(lines) and (lines[i].startswith((" ", "\t")) or not lines[i].strip()):
                block.append(lines[i].strip())
                i += 1
            value = " ".join(b for b in block if b) if value.startswith(">") or value == "" else "\n".join(block)
        elif len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        result[key] = value
    return result


def check_skill(skill_md: Path, allowed_keys: set[str]) -> None:
    fm = parse_frontmatter(skill_md)
    if fm is None:
        return
    for key in sorted(set(fm) - allowed_keys):
        err(skill_md, f"unexpected frontmatter key {key!r}")
    name = fm.get("name", "")
    dirname = skill_md.parent.name
    if not name:
        err(skill_md, "missing name")
    elif name != dirname:
        err(skill_md, f"name {name!r} must equal directory name {dirname!r}")
    elif not NAME_RE.match(name) or len(name) > 64:
        err(skill_md, f"name {name!r} must be kebab-case, max 64 chars")
    desc = fm.get("description", "")
    if not desc:
        err(skill_md, "missing description")
    elif len(desc) > 1024:
        err(skill_md, f"description too long ({len(desc)} > 1024)")
    elif "<" in desc or ">" in desc:
        err(skill_md, "description must not contain angle brackets")


def check_command(cmd: Path) -> None:
    fm = parse_frontmatter(cmd)
    if fm is None:
        return
    for key in sorted(set(fm) - COMMAND_KEYS):
        err(cmd, f"unexpected frontmatter key {key!r}")
    if not fm.get("description"):
        err(cmd, "missing description")


def check_text(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for n, line in enumerate(text.splitlines(), 1):
        if FORBIDDEN_PATH_RE.search(line):
            err(path, f"line {n}: absolute install/home path, use a path relative to the skill")
    # markup examples live in code, only real links count
    prose = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    prose = re.sub(r"`[^`\n]*`", "", prose)
    for target in LINK_RE.findall(prose):
        if re.match(r"^[a-z]+:", target):
            continue
        if not (path.parent / target).exists():
            err(path, f"broken relative link {target!r}")


def check_plugin(entry: dict) -> set[str]:
    name = entry.get("name", "")
    source = entry.get("source", "")
    mp = ROOT / ".claude-plugin/marketplace.json"
    if not NAME_RE.match(name):
        err(mp, f"plugin name {name!r} must be kebab-case")
    if not isinstance(source, str) or not source.startswith("./plugins/"):
        err(mp, f"plugin {name!r}: source must be ./plugins/<name>")
        return set()
    pdir = (ROOT / source).resolve()
    if not pdir.is_dir():
        err(mp, f"plugin {name!r}: {source} does not exist")
        return set()
    manifest = load_json(pdir / ".claude-plugin/plugin.json")
    if manifest is not None:
        if manifest.get("name") != name:
            err(pdir / ".claude-plugin/plugin.json", f"name must be {name!r}")
        if not SEMVER_RE.match(str(manifest.get("version", ""))):
            err(pdir / ".claude-plugin/plugin.json", "version must be semver X.Y.Z")
        if not manifest.get("description"):
            err(pdir / ".claude-plugin/plugin.json", "missing description")
    if not (pdir / "CHANGELOG.md").is_file():
        err(pdir, "missing CHANGELOG.md")

    skills = sorted((pdir / "skills").glob("*/SKILL.md"))
    commands = sorted((pdir / "commands").glob("*.md"))
    if not skills and not commands:
        err(pdir, "plugin has no skills or commands")
    for skill_md in skills:
        check_skill(skill_md, CLAUDE_KEYS)
    for cmd in commands:
        check_command(cmd)
    names = {s.parent.name for s in skills}
    for dup in names & {c.stem for c in commands}:
        err(pdir, f"command and skill share the name {dup!r}")
    for md in [*pdir.rglob("*.md")]:
        if md.name != "CHANGELOG.md":
            check_text(md)
    return {pdir.name}


def main() -> int:
    mp = load_json(ROOT / ".claude-plugin/marketplace.json")
    listed: set[str] = set()
    if mp is not None:
        for key in ("name", "owner", "plugins"):
            if key not in mp:
                err(ROOT / ".claude-plugin/marketplace.json", f"missing {key!r}")
        seen: set[str] = set()
        for entry in mp.get("plugins", []):
            if entry.get("name") in seen:
                err(ROOT / ".claude-plugin/marketplace.json", f"duplicate plugin {entry.get('name')!r}")
            seen.add(entry.get("name"))
            listed |= check_plugin(entry)

    plugins_dir = ROOT / "plugins"
    if plugins_dir.is_dir():
        for pdir in sorted(p for p in plugins_dir.iterdir() if p.is_dir()):
            if pdir.name not in listed:
                err(pdir, "plugin directory not listed in marketplace.json")
                check_plugin({"name": pdir.name, "source": f"./plugins/{pdir.name}"})

    codex_dir = ROOT / "codex"
    if codex_dir.is_dir():
        for sdir in sorted(p for p in codex_dir.iterdir() if p.is_dir()):
            skill_md = sdir / "SKILL.md"
            if not skill_md.is_file():
                err(sdir, "missing SKILL.md")
                continue
            check_skill(skill_md, SPEC_KEYS)
            for md in sdir.rglob("*.md"):
                check_text(md)
            # a script shared with the Claude side of the same skill is a copy, not a fork
            for script in sorted((sdir / "scripts").glob("*")):
                for twin in (ROOT / "plugins").glob(f"*/skills/{sdir.name}/scripts/{script.name}"):
                    if twin.read_bytes() != script.read_bytes():
                        err(script, f"differs from {twin.relative_to(ROOT)}; keep the copies identical")

    for e in errors:
        print(f"error: {e}", file=sys.stderr)
    if errors:
        print(f"{len(errors)} error(s)", file=sys.stderr)
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
