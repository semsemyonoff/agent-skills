#!/usr/bin/env python3
"""Read-only, partial omp profile inventory; live task discovery remains authoritative.

Only native project/user roots are discovered automatically. Optional roots must be supplied in
their already-confirmed runtime order; this helper never loads extensions or unpacks bundled agents.
Frontmatter support is deliberately limited to scalar, CSV, and string-list fields. Unsupported
syntax is reported, not interpreted as an empty/default profile. No third-party YAML dependency.
"""

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path


CONFIG_KEYS = (
    "modelRoles", "task.agentModelOverrides", "task.disabledAgents",
    "task.enableEffort", "task.maxEffort",
)
LEVELS = {"off", "minimal", "low", "medium", "high", "xhigh", "max", "auto", "inherit"}
FIELDS = {"name", "description", "model", "tools", "spawns", "thinking-level", "thinking"}


def scalar(text):
    text = text.strip()
    if text.startswith('"'):
        value, end = json.JSONDecoder().raw_decode(text)
        if text[end:].strip() and not text[end:].lstrip().startswith("#"):
            raise ValueError("unsupported quoted scalar suffix")
        return value
    if text.startswith("'"):
        match = re.fullmatch(r"'((?:[^']|'')*)'\s*(?:#.*)?", text)
        if not match:
            raise ValueError("unsupported quoted scalar")
        return match[1].replace("''", "'")
    text = re.split(r"\s+#", text, maxsplit=1)[0].strip()
    if not text or text.lower() in {"null", "~"}:
        return None
    if text.lower() in {"true", "false"}:
        return text.lower() == "true"
    if text.startswith(("[", "{", "&", "*", "!", "|", ">")):
        raise ValueError("unsupported YAML scalar; quote literal selectors")
    return text


def field_value(text):
    if not text.lstrip().startswith("["):
        return scalar(text)
    # Split only outside quotes, so commas inside a quoted selector survive.
    match = re.fullmatch(r"\s*\[(.*)\]\s*(?:#.*)?", text)
    if not match:
        raise ValueError("unsupported multiline/complex YAML list")
    body = match[1]
    parts = re.findall(r'''(?:"(?:[^"\\]|\\.)*"|'(?:[^']|'')*'|[^,])+''', body)
    values = [scalar(part) for part in parts if part.strip()]
    if any(not isinstance(value, str) for value in values):
        raise ValueError("expected string-list entries")
    return values


def string_list(value):
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, list) and all(isinstance(item, str) and item for item in value):
        return value
    raise ValueError("expected a string, CSV or string list")


def frontmatter(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        raise ValueError("missing frontmatter delimiters")
    fields = {}
    active = None
    for line in lines[1:lines[1:].index("---") + 1]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0].isspace():
            if active == "description" and fields.get(active) in {"|", ">", "|-", ">-"}:
                continue
            if active in FIELDS:
                if not line.strip().startswith("- ") or not isinstance(fields[active], list):
                    raise ValueError(f"unsupported nested field: {active}")
                fields[active].append(scalar(line.strip()[2:]))
            continue
        match = re.match(r"([\w-]+):\s*(.*)$", line)
        if not match:
            raise ValueError("unsupported frontmatter line")
        active, value = match.groups()
        active = {"thinkingLevel": "thinking-level"}.get(active, active)
        if active not in FIELDS:
            continue
        if active in fields:
            raise ValueError(f"duplicate field: {active}")
        if active == "description" and value in {"|", ">", "|-", ">-"}:
            fields[active] = value
        else:
            fields[active] = [] if not value else field_value(value)
    for key in ("name", "description"):
        if not isinstance(fields.get(key), str) or not fields[key].strip():
            raise ValueError(f"missing/non-string {key}")
    if fields["name"].strip().lower() in {"main", "sub"}:
        raise ValueError("reserved agent name")
    for key in ("model", "tools"):
        if key in fields:
            fields[key] = string_list(fields[key])
    if "spawns" in fields and fields["spawns"] not in (None, True, False):
        fields["spawns"] = string_list(fields["spawns"])
    thinking = fields.get("thinking-level", fields.get("thinking"))
    if thinking is not None and thinking not in LEVELS:
        raise ValueError("unsupported thinking level")
    fields["thinking-level"] = thinking
    return fields


def run_read(command, cwd):
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as error:
        return None, type(error).__name__
    if result.returncode:
        # Never echo arbitrary CLI stderr/config values into the inventory.
        return None, f"command failed (exit {result.returncode})"
    return result.stdout.strip(), None


def read_config(command, cwd):
    values, status = {}, {}
    for key in CONFIG_KEYS:
        output, error = run_read([*command, "config", "get", key, "--json"], cwd)
        if error:
            status[key] = error
            continue
        try:
            record = json.loads(output)
            if not isinstance(record, dict) or record.get("key") != key:
                raise ValueError("unexpected key envelope")
            value = record.get("value")
            if record.get("redacted"):
                status[key] = "unavailable (redacted)"
                continue
            if value is None:
                status[key] = "unset"
                continue
            expected = dict if key in CONFIG_KEYS[:2] else list if key == CONFIG_KEYS[2] else bool if key == CONFIG_KEYS[3] else str
            if type(value) is not expected:
                raise ValueError("unexpected value type")
            if isinstance(value, dict):
                for entry in value.values():
                    string_list(entry)
            if isinstance(value, list) and not all(isinstance(item, str) for item in value):
                raise ValueError("expected string entries")
            values[key], status[key] = value, "ok"
        except (ValueError, TypeError):
            status[key] = "invalid JSON/value"
    return values, status


def project_root(cwd):
    for parent in (cwd, *cwd.parents):
        config = parent / ".omp"
        if config.is_dir():
            candidate = config / "agents"
            return candidate if candidate.is_dir() else None
    return None


def expand_models(selectors, roles, seen=()):
    expanded = []
    for selector in selectors:
        base, sep, suffix = selector.rpartition(":")
        level = suffix if sep and suffix in LEVELS else None
        base = base if level else selector
        if base in {"@default", "*"}:
            expanded.append({"selector": selector, "status": "parent model unknown", "roles": list(seen)})
        elif base.startswith("@"):
            role = base[1:]
            if role in seen or role not in roles:
                reason = "role cycle" if role in seen else "role unset/unavailable"
                expanded.append({"selector": selector, "status": reason, "roles": [*seen, role]})
                continue
            candidates = string_list(roles[role])
            if not candidates:
                expanded.append({"selector": selector, "status": "role has no selectors", "roles": [*seen, role]})
            for item in expand_models(candidates, roles, (*seen, role)):
                item = dict(item)
                if level:
                    old_base, old_sep, old_suffix = item["selector"].rpartition(":")
                    item["selector"] = (old_base if old_sep and old_suffix in LEVELS else item["selector"]) + ":" + level
                expanded.append(item)
        else:
            expanded.append({"selector": selector, "status": "configured selector, not runtime identity", "roles": list(seen)})
    return expanded


def capabilities(tools):
    if tools is None:
        return dict.fromkeys(("bash", "browser", "eval_browser", "lsp"))
    names = {tool.lower() for tool in tools}
    return {
        "bash": bool(names & {"bash", "exec"}),
        "browser": any(name == "browser" or name.startswith(("mcp__playwright__", "mcp__browser__")) for name in names),
        "eval_browser": None if names & {"eval", "exec"} else False,
        "lsp": "lsp" in names,
    }


def inventory(roots, values, config_status):
    profiles, issues = {}, []
    for source, root in roots:
        try:
            paths = sorted(root.iterdir())
        except OSError as error:
            issues.append(f"{root}: {type(error).__name__}")
            continue
        for path in paths:
            if path.suffix != ".md":
                continue
            try:
                fields = frontmatter(path)
            except (OSError, ValueError, TypeError) as error:
                issues.append(f"{path}: {type(error).__name__}: unsupported/unreadable profile")
                continue
            name = fields["name"]
            candidate = {"source": source, "path": str(path), "target": str(path.resolve())}
            if name in profiles:
                profiles[name]["shadowed"].append(candidate)
                continue
            tools = fields.get("tools")
            model = fields.get("model") if source != "claude-plugin" else None
            profiles[name] = {
                "name": name, "winner_in_inspected_roots": candidate, "shadowed": [],
                "model": model, "thinking_level": fields["thinking-level"],
                "tools": tools, "capabilities": capabilities(tools),
                "spawns": fields.get("spawns", "*" if tools and "task" in tools else None),
            }
    overrides = values.get("task.agentModelOverrides", {})
    disabled = values.get("task.disabledAgents")
    # Retain override-only/bundled names without inventing a profile definition or toolset.
    for name in sorted(set(overrides) | set(disabled or [])):
        profiles.setdefault(name, {
            "name": name, "winner_in_inspected_roots": None, "shadowed": [], "model": None,
            "thinking_level": None, "tools": None, "capabilities": capabilities(None), "spawns": None,
        })
    for row in profiles.values():
        row["disabled"] = row["name"] in disabled if disabled is not None else None
        row["override"] = overrides.get(row["name"])
        if config_status.get("task.agentModelOverrides") != "ok":
            row["effective_selector"] = None
            row["expanded"] = []
            row["route_status"] = "override configuration unavailable"
        else:
            selectors = string_list(row["override"]) if row["override"] is not None else row["model"]
            row["effective_selector"] = selectors
            row["expanded"] = expand_models(selectors or [], values.get("modelRoles", {}))
            row["route_status"] = "configured hint" if selectors else "profile/default route unknown"
    return sorted(profiles.values(), key=lambda row: row["name"]), issues


def inspect(args):
    cwd = Path(args.cwd).resolve()
    executable = shutil.which(args.omp)
    command = [executable] if executable else []
    if args.profile:
        command += ["--profile", args.profile]
    roots, issues = [], []
    project = project_root(cwd)
    if project:
        roots.append(("project", project))
    if executable:
        values, status = read_config(command, cwd)
        location, error = run_read([*command, "config", "path"], cwd)
        if error or not location or not Path(location).is_absolute():
            issues.append("user agent directory unavailable from omp config path")
        else:
            user = Path(location) / "agents"
            if user.is_dir():
                roots.append(("user", user))
    else:
        values, status = {}, dict.fromkeys(CONFIG_KEYS, "omp unavailable")
        issues.append("omp unavailable; user directory and effective configuration unknown")
    for source, directories in (("extension", args.extension_root), ("claude-plugin", args.claude_plugin_root), ("bundled", args.bundled_dir)):
        roots.extend((source, Path(directory).expanduser().resolve()) for directory in directories)
    profiles, parse_issues = inventory(roots, values, status)
    return {
        "scope": "partial read-only inventory; live task schema/roster and spawn metadata are authoritative",
        "roots": [{"source": source, "path": str(path)} for source, path in roots],
        "config_status": status,
        "effort": {"enabled": values.get("task.enableEffort"), "maximum": values.get("task.maxEffort")},
        "profiles": profiles,
        "issues": issues + parse_issues,
        "limits": [
            "Extensions/plugins/bundled definitions are uninspected unless their agent directories are supplied in live discovery order.",
            "Winners apply only to inspected roots; parse errors make precedence incomplete. Installed skill resources alone are not deployed agents.",
            "Tools are declarations, not availability: direct browser tools are separate from unverified Bash/eval browser runners.",
            "Session models/overlays, hooks, parent spawn restrictions and runtime thinking/clamping are unknown; no credentials or provider configs read.",
        ],
    }


def display(report):
    print(report["scope"])
    print("config: " + "; ".join(f"{key}={value}" for key, value in report["config_status"].items()))
    print("effort: " + json.dumps(report["effort"], separators=(",", ":")))
    print("profile | winner (shadowed) | model -> override -> expansion [roles] | declared thinking | declared tools; bash/direct-browser/eval-browser/lsp | spawns | disabled")
    for row in report["profiles"]:
        winner = row["winner_in_inspected_roots"]
        location = f'{winner["source"]}:{winner["path"]}' if winner else "uninspected definition"
        shadowed = ",".join(item["path"] for item in row["shadowed"])
        expansions = ",".join(item["selector"] + " [" + "/".join(item["roles"]) + "; " + item["status"] + "]" for item in row["expanded"])
        flags = "/".join("?" if value is None else "yes" if value else "no" for value in row["capabilities"].values())
        print(f'{row["name"]} | {location} ({shadowed or "none"}) | {row["model"]} -> {row["override"]} -> {expansions or row["route_status"]} | {row["thinking_level"] or "unknown"} | {row["tools"]}; {flags} | {row["spawns"]} | {row["disabled"]}')
    for issue in report["issues"]:
        print("issue: " + issue)
    for limit in report["limits"]:
        print("limit: " + limit)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", default=str(Path.cwd()))
    parser.add_argument("--omp", default="omp", help="omp executable; no model calls")
    parser.add_argument("--profile", help="same native profile as the live session")
    parser.add_argument("--extension-root", action="append", default=[], metavar="AGENTS_DIR")
    parser.add_argument("--claude-plugin-root", action="append", default=[], metavar="AGENTS_DIR")
    parser.add_argument("--bundled-dir", action="append", default=[], metavar="AGENTS_DIR")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = inspect(args)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        display(report)
    return 1 if report["issues"] or any(state != "ok" for state in report["config_status"].values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
