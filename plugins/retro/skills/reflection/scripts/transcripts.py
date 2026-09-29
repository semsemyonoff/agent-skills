#!/usr/bin/env python3
"""Extract a compact, redacted digest from Claude Code session transcripts.

Reads <config-dir>/projects/*/*.jsonl (plus */*/subagents/*.jsonl with
--include-subagents). Deterministic extraction only; interpretation is left
to the caller. Stdlib only.
"""
import argparse
import collections
import datetime as dt
import glob
import json
import os
import re
import sys

TEXT_MAX = 200

# Heuristic markers of a user correcting the previous assistant turn.
CORRECTION_RE = re.compile(
    r"(?:^|[\s,.;:!?(\"'])(?:"
    r"нет\b|не так|не то\b|не надо|не нужно|поправь|исправь|опять|снова|"
    r"я же (?:говорил|просил|писал)|зачем|почему ты|не делай|перестань|"
    r"stop\b|wrong\b|don'?t\b|do not\b|no,|nope\b|that'?s not|not what i|"
    r"again\b|i (?:said|told|asked)|why did you|undo\b|revert\b"
    r")",
    re.I,
)

META_PREFIXES = (
    "<system-reminder>", "<task-notification", "<local-command", "<command-message>",
    "<user-prompt-submit-hook", "Caveat:", "[Request interrupted",
    "Base directory for this skill", "This session is being continued",
    "<ide_", "<bash-", "<tool_use_error>",
)

REDACT_PATTERNS = [
    (re.compile(r"(?i)\b(pass(?:word|wd)?|passphrase|secret|token|api[_-]?key|apikey|auth|credentials?|пароль|токен|ключ)\b(\s*[:=]\s*|\s+is\s+|\s+)\S+"), r"\1 [REDACTED]"),
    (re.compile(r"(?i)\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{8,}"), r"\1 [REDACTED]"),
    (re.compile(r"\b(?:sk|pk|ghp|gho|ghs|glpat|xox[bpas]|AKIA|AIza)[-_A-Za-z0-9]{12,}"), "[REDACTED]"),
    (re.compile(r"\b[0-9a-fA-F]{32,}\b"), "[REDACTED]"),
    (re.compile(r"\b(?=[A-Za-z0-9+/_]*\d)[A-Za-z0-9+/_]{40,}={0,2}"), "[REDACTED]"),
    (re.compile(r"(?i)(://[^/\s:@]+:)[^@\s/]+@"), r"\1[REDACTED]@"),
]


def redact(s):
    for rx, rep in REDACT_PATTERNS:
        s = rx.sub(rep, s)
    return s


def clip(s, n=TEXT_MAX):
    s = redact(" ".join(str(s).split()))
    return s if len(s) <= n else s[: n - 1] + "…"


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--since", help="YYYY-MM-DD (local date, inclusive)")
    p.add_argument("--days", type=int, help="last N days (default 7 when --since is absent)")
    p.add_argument("--project", help="substring of project dir name or cwd")
    p.add_argument("--config-dir", default=os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude"))
    p.add_argument("--include-subagents", action="store_true", help="also read subagents/*.jsonl (tokens, tools, errors)")
    p.add_argument("--include-sdk", action="store_true", help="include non-interactive sdk-* sessions (excluded by default: automation noise)")
    p.add_argument("--out", choices=["json", "md"], default="md")
    p.add_argument("--max-prompts", type=int, default=80)
    p.add_argument("--max-sessions", type=int, default=25)
    p.add_argument("--max-corrections", type=int, default=30)
    return p.parse_args(argv)


def since_iso(args):
    if args.since:
        d = dt.datetime.strptime(args.since, "%Y-%m-%d")
    else:
        d = dt.datetime.now() - dt.timedelta(days=args.days or 7)
    return d.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def find_files(root, include_sub):
    files = glob.glob(os.path.join(root, "projects", "*", "*.jsonl"))
    if include_sub:
        files += glob.glob(os.path.join(root, "projects", "*", "*", "subagents", "*.jsonl"))
    return files


def user_text(msg):
    """Return (kind, text): kind is 'prompt', 'command', 'tool_result' or 'meta'."""
    c = msg.get("content")
    if isinstance(c, str):
        text = c
    elif isinstance(c, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
            return "tool_result", ""
        text = "\n".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
    else:
        return "meta", ""
    t = text.strip()
    if not t:
        return "meta", ""
    m = re.search(r"<command-name>\s*(/?[^<\s]+)\s*</command-name>", t)
    if m:
        a = re.search(r"<command-args>(.*?)</command-args>", t, re.S)
        return "command", (m.group(1) + " " + (a.group(1).strip() if a else "")).strip()
    if t.startswith(META_PREFIXES):
        return "meta", ""
    return "prompt", t


def norm_error(name, text):
    first = next((ln for ln in text.splitlines() if ln.strip()), "")
    first = re.sub(r"(?:/[\w.@+-]+){2,}", "<path>", first)
    first = re.sub(r"\d+", "N", first)
    return f"{name}: {clip(first, 90)}"


def result_text(b):
    c = b.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "\n".join(x.get("text", "") for x in c if isinstance(x, dict))
    return ""


def classify_denial(text):
    if "denied by the Claude Code auto mode classifier" in text:
        m = re.search(r"Reason:\s*\[([^\]]+)", text)
        return "classifier: " + (m.group(1) if m else "unspecified")
    if "doesn't want to proceed with this tool use" in text or "tool use was rejected" in text:
        return "user rejected"
    return None


def new_session(sid, project):
    return {
        "id": sid, "project": project, "start": None, "end": None, "prompts": 0,
        "first_prompt": None, "tools": collections.Counter(), "errors": 0, "denials": 0,
        "agents": 0, "tokens": 0, "interrupts": 0, "cwd": "", "entrypoint": "",
    }


def process_file(path, since, agg):
    is_sub = os.sep + "subagents" + os.sep in path
    parts = path.split(os.sep)
    if is_sub:
        proj_dir, sid = parts[-4], parts[-3]
    else:
        proj_dir, sid = parts[-2], os.path.basename(path)[:-6]
    sess = agg["sessions"].get(sid) or new_session(sid, proj_dir)
    tool_names = {}
    seen_tool = set()
    msg_usage = {}  # message id -> (model, usage); streaming repeats the id
    seen_prompt = False
    interesting = False
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            ts = d.get("timestamp")
            typ = d.get("type")
            if not ts or ts < since or typ not in ("user", "assistant"):
                continue
            if d.get("cwd") and not sess["cwd"]:
                sess["cwd"] = d["cwd"]
                sess["entrypoint"] = d.get("entrypoint", "")
            interesting = True
            sess["start"] = min(sess["start"] or ts, ts)
            sess["end"] = max(sess["end"] or ts, ts)
            msg = d.get("message") or {}
            content = msg.get("content")
            if typ == "assistant":
                mid = msg.get("id") or d.get("uuid")
                if msg.get("usage"):
                    msg_usage[mid] = (msg.get("model") or "unknown", msg["usage"])
                for b in content if isinstance(content, list) else []:
                    if b.get("type") != "tool_use" or b.get("id") in seen_tool:
                        continue
                    seen_tool.add(b.get("id"))
                    name = b.get("name", "?")
                    tool_names[b.get("id")] = name
                    sess["tools"][name] += 1
                    agg["tools"][name] += 1
                    if name in ("Agent", "Task"):
                        inp = b.get("input") or {}
                        sess["agents"] += 1
                        agg["subagents"][(inp.get("subagent_type") or "general-purpose", inp.get("model") or "unset")] += 1
                continue
            kind, text = user_text(msg)
            if kind == "tool_result":
                for b in content:
                    if not (isinstance(b, dict) and b.get("type") == "tool_result") or not b.get("is_error"):
                        continue
                    rt = result_text(b)
                    name = tool_names.get(b.get("tool_use_id"), "?")
                    den = classify_denial(rt)
                    if den:
                        sess["denials"] += 1
                        agg["denials"][den] += 1
                        agg["denial_tools"][f"{name} / {den}"] += 1
                    else:
                        sess["errors"] += 1
                        agg["errors"][norm_error(name, rt)] += 1
                continue
            if isinstance(content, list) and any(
                isinstance(b, dict) and b.get("type") == "text" and b.get("text", "").startswith("[Request interrupted")
                for b in content
            ):
                sess["interrupts"] += 1
            if kind not in ("prompt", "command") or is_sub or d.get("isSidechain") or d.get("isMeta"):
                continue
            sess["prompts"] += 1
            clipped = clip(text)
            if sess["first_prompt"] is None:
                sess["first_prompt"] = clipped
            key = re.sub(r"\W+", " ", clipped.lower()).strip()[:120]
            entry = agg["prompts"].setdefault((sid, key), {"text": clipped, "count": 0})
            entry["count"] += 1
            words = key.split()
            if words:
                agg["openers"][" ".join(words[:3])] += 1
            if kind == "prompt" and seen_prompt and CORRECTION_RE.search(text[:300]):
                agg["corrections"].append({"session": sid[:8], "time": ts[:16], "text": clipped})
            seen_prompt = True
    if not interesting:
        return
    for model, u in msg_usage.values():
        if model.startswith("<"):  # <synthetic> placeholders carry no usage
            continue
        t = agg["tokens"][model]
        inp, cw = u.get("input_tokens", 0) or 0, u.get("cache_creation_input_tokens", 0) or 0
        cr, out = u.get("cache_read_input_tokens", 0) or 0, u.get("output_tokens", 0) or 0
        t["input"] += inp
        t["cache_creation"] += cw
        t["cache_read"] += cr
        t["output"] += out
        t["messages"] += 1
        sess["tokens"] += inp + cw + out
        agg["sub_tokens" if is_sub else "main_tokens"][model] += out
    agg["sessions"][sid] = sess


def build(args):
    since = since_iso(args)
    agg = {
        "sessions": {}, "tools": collections.Counter(), "errors": collections.Counter(),
        "denials": collections.Counter(), "denial_tools": collections.Counter(),
        "subagents": collections.Counter(), "prompts": {}, "openers": collections.Counter(),
        "corrections": [], "main_tokens": collections.Counter(), "sub_tokens": collections.Counter(),
        "tokens": collections.defaultdict(collections.Counter),
    }
    since_epoch = dt.datetime.strptime(since, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.timezone.utc).timestamp()
    nfiles = 0
    for f in find_files(args.config_dir, args.include_subagents):
        try:
            if os.path.getmtime(f) < since_epoch:
                continue
        except OSError:
            continue
        nfiles += 1
        process_file(f, since, agg)
    sessions = list(agg["sessions"].values())
    if not args.include_sdk:
        sessions = [s for s in sessions if not s["entrypoint"].startswith("sdk")]
    if args.project:
        pl = args.project.lower()
        sessions = [s for s in sessions if pl in s["project"].lower() or pl in s["cwd"].lower()]
    return since, nfiles, sessions, agg


def top(counter, n):
    return [{"name": k, "count": v} for k, v in counter.most_common(n)]


def digest(args):
    since, nfiles, sessions, agg = build(args)
    keep = {s["id"] for s in sessions}
    merged = {}
    for (sid, key), e in agg["prompts"].items():
        if sid in keep:
            m = merged.setdefault(key, {"text": e["text"], "count": 0, "sessions": 0})
            m["count"] += e["count"]
            m["sessions"] += 1
    prompts = sorted(merged.values(), key=lambda e: (-e["count"], -e["sessions"]))
    keep8 = {s[:8] for s in keep}
    corrections = [c for c in agg["corrections"] if c["session"] in keep8]
    for s in sessions:
        s["project"] = os.path.basename(s["cwd"]) or s["project"]
    by_proj = collections.Counter(s["project"] for s in sessions)
    out = {
        "period_since_utc": since,
        "config_dir": args.config_dir,
        "files_read": nfiles,
        "sessions_total": len(sessions),
        "prompts_total": sum(s["prompts"] for s in sessions),
        "note": "heuristic extraction; correction candidates are regex matches, not verified friction; tool/token totals cover all sessions read (not project-filtered)",
        "projects_top": top(by_proj, 10),
        "tools_top": top(agg["tools"], 15),
        "errors_top": top(agg["errors"], 15),
        "denials": top(agg["denials"], 10),
        "denials_by_tool": top(agg["denial_tools"], 10),
        "subagent_calls": [{"subagent_type": k[0], "model": k[1], "count": v} for k, v in agg["subagents"].most_common(20)],
        "subagent_model_set": sum(v for k, v in agg["subagents"].items() if k[1] != "unset"),
        "subagent_model_unset": sum(v for k, v in agg["subagents"].items() if k[1] == "unset"),
        "tokens_by_model": {m: dict(t) for m, t in sorted(agg["tokens"].items(), key=lambda kv: -sum(kv[1].values()))},
        "prompt_openers_top": top(agg["openers"], 15),
        "prompts": prompts[: args.max_prompts],
        "prompts_omitted": max(0, len(prompts) - args.max_prompts),
        "correction_candidates": corrections[: args.max_corrections],
        "correction_candidates_omitted": max(0, len(corrections) - args.max_corrections),
        "sessions": [
            {"id": s["id"][:8], "project": s["project"], "start": (s["start"] or "")[:16], "end": (s["end"] or "")[:16],
             "prompts": s["prompts"], "first_prompt": s["first_prompt"], "tools": sum(s["tools"].values()),
             "errors": s["errors"], "denials": s["denials"], "agents": s["agents"], "interrupts": s["interrupts"],
             "tokens_in_out": s["tokens"]}
            for s in sorted(sessions, key=lambda s: -s["tokens"])[: args.max_sessions]
        ],
        "sessions_omitted": max(0, len(sessions) - args.max_sessions),
    }
    if args.include_subagents:
        out["output_tokens_main_vs_subagent"] = {"main": dict(agg["main_tokens"]), "subagents": dict(agg["sub_tokens"])}
    return out


def fmt_md(o):
    L = []
    a = L.append
    kv = lambda xs: ", ".join(f"{x['name']} {x['count']}" for x in xs) or "-"
    a(f"# Transcript digest (since {o['period_since_utc']} UTC)")
    a(f"config: {o['config_dir']} | files: {o['files_read']} | sessions: {o['sessions_total']} | user prompts: {o['prompts_total']}")
    a(f"_{o['note']}_\n")
    a("## Projects\n" + kv(o["projects_top"]))
    a("\n## Tools\n" + kv(o["tools_top"]))
    a("\n## Errors (tool_result is_error, normalized)")
    a("\n".join(f"- {x['count']}x {x['name']}" for x in o["errors_top"]) or "-")
    a("\n## Permission denials / rejections\n" + kv(o["denials"]))
    a("by tool: " + kv(o["denials_by_tool"]))
    a("\n## Subagent routing")
    a(f"model set: {o['subagent_model_set']} | unset (inherits): {o['subagent_model_unset']}")
    a("\n".join(f"- {x['count']}x {x['subagent_type']} -> model={x['model']}" for x in o["subagent_calls"]) or "-")
    a("\n## Tokens by model (deduped by message id)")
    for m, t in o["tokens_by_model"].items():
        a(f"- {m}: in {t['input']:,} | cache_write {t['cache_creation']:,} | cache_read {t['cache_read']:,} | out {t['output']:,} | msgs {t['messages']}")
    if "output_tokens_main_vs_subagent" in o:
        a("output tokens main vs subagents: " + json.dumps(o["output_tokens_main_vs_subagent"]))
    a("\n## Prompt openers (first 3 words)\n" + kv(o["prompt_openers_top"]))
    a(f"\n## User prompts (deduped, by count; {o['prompts_omitted']} more omitted)")
    for p in o["prompts"]:
        a(f"- [{p['count']}x/{p['sessions']}s] {p['text']}")
    a(f"\n## Correction candidates (HEURISTIC; {o['correction_candidates_omitted']} more omitted)")
    for c in o["correction_candidates"]:
        a(f"- {c['session']} {c['time']}: {c['text']}")
    a(f"\n## Sessions by tokens ({o['sessions_omitted']} more omitted)")
    for s in o["sessions"]:
        a(f"- {s['id']} {s['project']} {s['start']}..{s['end']} p={s['prompts']} tools={s['tools']} err={s['errors']} deny={s['denials']} agents={s['agents']} int={s['interrupts']} tok={s['tokens_in_out']:,} | {s['first_prompt']}")
    return "\n".join(L)


def main(argv=None):
    args = parse_args(argv)
    if not os.path.isdir(os.path.join(args.config_dir, "projects")):
        print(f"error: no projects dir under {args.config_dir}", file=sys.stderr)
        return 2
    o = digest(args)
    print(json.dumps(o, ensure_ascii=False, indent=1) if args.out == "json" else fmt_md(o))
    return 0


if __name__ == "__main__":
    sys.exit(main())
