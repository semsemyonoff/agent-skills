#!/usr/bin/env python3
"""Orchestration retrospective: coordinator context, workers, stalls and idle notices.

Read-only, stdlib-only. Reuses transcripts.py discovery, filters and redaction. Selects
sessions that invoked the orchestration skill (--skill regex) and reports per session:
coordinator usage before/after the skill loaded, an approximate attribution of coordinator
context growth, coordinator edits, workers with routing/usage/stall signals, a same-call-sequence
replay estimate, and short redacted excerpts (plan, idle notices) for the model to judge.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import transcripts as T  # noqa: E402

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit", "edit", "write", "ast_edit"}
DELEGATION = {"Agent", "Task", "task", "SendMessage", "wait", "TaskStop", "TaskOutput"}
URI_SCHEMES = ("xd://", "agent://", "history://", "proc://", "skill://", "local://", "omp://", "http://", "https://")
BASH_WRITE = re.compile(r"(sed -i|perl -pi|\bcat\s*>|\btee\b|>\s*[\w./-]+\.\w+\b|write_text|apply_patch|git apply)")
GIT = re.compile(r"\bgit (commit|push|log|diff|status|show|fetch|checkout|switch|merge|rebase|branch)\b")
EXCERPT = 900


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", choices=("claude", "omp", "both"), required=True)
    period = p.add_mutually_exclusive_group()
    period.add_argument("--since", help="YYYY-MM-DD (local date, inclusive)")
    period.add_argument("--days", type=int, help="last N days (default 7)")
    p.add_argument("--project", help="substring of recorded cwd or project bucket")
    p.add_argument("--config-dir", default=os.environ.get("CLAUDE_CONFIG_DIR") or "~/.claude")
    p.add_argument("--omp-sessions-dir", default="~/.omp/agent/sessions")
    p.add_argument("--skill", default="orchestrate", help="regex naming the orchestration skill")
    p.add_argument("--stall-minutes", type=int, default=20, help="worker gap reported as a stall candidate")
    p.add_argument("--large-context", type=int, default=150000,
                   help="experimental worker context guide, reported, never a verdict")
    p.add_argument("--out", choices=("json", "md"), default="md")
    p.add_argument("--max-sessions", type=int, default=15)
    args = p.parse_args(argv)
    if args.days is not None and args.days < 1:
        p.error("--days must be positive")
    if args.since:
        try:
            dt.datetime.strptime(args.since, "%Y-%m-%d")
        except ValueError:
            p.error("--since must be YYYY-MM-DD")
    args.config_dir = os.path.abspath(os.path.expanduser(args.config_dir))
    args.omp_sessions_dir = os.path.abspath(os.path.expanduser(args.omp_sessions_dir))
    args.include_subagents = True
    args.skill_re = re.compile(args.skill, re.I)
    return args


def ordered(sess):
    rows = []
    for path, number, d in sess["records"]:
        t = T.timestamp(d.get("timestamp")) or T.timestamp(T.obj(d.get("message")).get("timestamp"))
        rows.append((t, path, number, d))
    rows.sort(key=lambda r: (r[0] or dt.datetime.min.replace(tzinfo=dt.timezone.utc), r[1], r[2]))
    return rows


def text_of(content):
    if isinstance(content, str):
        return content
    out = []
    for b in T.blocks(content):
        if b.get("type") == "text" and isinstance(b.get("text"), str):
            out.append(b["text"])
        elif b.get("type") == "tool_result":
            out.append(text_of(b.get("content")))
    return "\n".join(out)


def skill_hit(source, d, rx):
    """True when this record shows the orchestration skill being loaded or invoked."""
    msg = T.obj(d.get("message"))
    if source == "omp":
        if d.get("type") == "custom_message" and d.get("customType") == "skill-prompt":
            invoked = re.search(r'invoked the "([^"]+)"', str(d.get("content")))
            return bool(invoked and rx.search(invoked.group(1)))
        if msg.get("role") == "assistant":
            for b in T.blocks(msg.get("content")):
                path = str(T.obj(b.get("arguments")).get("path") or "")
                if b.get("type") == "toolCall" and b.get("name") == "read" and rx.search(path) and (
                        path.startswith("skill://") or path.endswith("SKILL.md")):
                    return True
        return False
    if d.get("type") == "assistant":
        for b in T.blocks(msg.get("content")):
            if b.get("type") == "tool_use" and b.get("name") == "Skill" and rx.search(str(T.obj(b.get("input")).get("skill"))):
                return True
    if d.get("type") == "user" and not d.get("isSidechain"):
        text = text_of(msg.get("content"))
        cmd = re.search(r"<command-name>\s*/?([^<\s]+)", text)
        if cmd and rx.search(cmd.group(1)):
            return True
        if text.startswith("Base directory for this skill") and rx.search(text[:300]):
            return True
    return False


def calls_of(sess):
    """Ordered coordinator/worker model calls: time, context, output, cost, model, tools."""
    source = sess["source"]
    by, order = {}, []
    for t, _, number, d in ordered(sess):
        msg = T.obj(d.get("message"))
        if source == "omp":
            if d.get("type") != "message" or msg.get("role") != "assistant":
                continue
            u = T.obj(msg.get("usage"))
            key = str(d.get("id") or number)
            vals = {"in": u.get("input"), "cw": u.get("cacheWrite"), "cr": u.get("cacheRead"), "out": u.get("output")}
            cost = T.obj(u.get("cost")).get("total")
            tools = [(b.get("name"), T.obj(b.get("arguments"))) for b in T.blocks(msg.get("content")) if b.get("type") == "toolCall"]
        else:
            if d.get("type") != "assistant" or str(msg.get("model", "")).startswith("<"):
                continue
            u = T.obj(msg.get("usage"))
            key = str(msg.get("id") or d.get("uuid") or number)
            vals = {"in": u.get("input_tokens"), "cw": u.get("cache_creation_input_tokens"),
                    "cr": u.get("cache_read_input_tokens"), "out": u.get("output_tokens")}
            cost = None
            tools = [(b.get("name"), T.obj(b.get("input"))) for b in T.blocks(msg.get("content")) if b.get("type") == "tool_use"]
        e = by.get(key)
        if e is None:
            e = by[key] = {"time": t, "in": 0, "cw": 0, "cr": 0, "out": 0, "cost": None, "model": msg.get("model"), "tools": []}
            order.append(key)
        for k, v in vals.items():  # streaming updates: keep the largest reported value
            if T.numeric(v) is not None:
                e[k] = max(e[k], v)
        if T.numeric(cost) is not None:
            e["cost"] = cost
        e["tools"].extend(tools)
    out = [by[k] for k in order]
    for e in out:
        e["ctx"] = e["in"] + e["cw"] + e["cr"]
    return [e for e in out if e["ctx"] > 0]


def category(name, args):
    a = args or {}
    path = str(a.get("path") or a.get("file_path") or "")
    if name in ("Read", "read"):
        if "SKILL.md" in path or path.startswith("skill://") or "/skills/" in path:
            return "skill"
        if "playwright" in path or "browser" in path:
            return "verify"
        if re.match(r"xd://mcp__(forgejo|vikunja|gitea|github|gitlab)", path):
            return "ship/tracker"
        if path.startswith(("agent://", "history://", "proc://")):
            return "delegation"
        return "other" if path.startswith(URI_SCHEMES) else "recon"
    if name == "write":
        if "playwright" in path or "browser" in path:
            return "verify"
        if re.match(r"xd://mcp__(forgejo|vikunja|gitea|github|gitlab)", path):
            return "ship/tracker"
        if path.startswith(("agent://", "proc://")):
            return "delegation"
        return "other" if path.startswith(URI_SCHEMES) else "edit"
    if name in ("Grep", "Glob", "grep", "glob", "find", "lsp", "LSP"):
        return "recon"
    if name in EDIT_TOOLS:
        return "edit"
    if name in DELEGATION:
        return "delegation"
    if name == "Skill":
        return "skill"
    if name and re.search(r"forgejo|vikunja|gitea|github|gitlab", name):
        return "ship/tracker"
    if name and re.search(r"playwright|browser", name):
        return "verify"
    if name in ("Bash", "bash", "eval"):
        cmd = str(a.get("command") or a.get("code") or "")
        if GIT.search(cmd):
            return "ship/tracker"
        if re.search(r"playwright|chromium|curl|wget|\b(test|pytest|vitest|tsc|lint|ruff|check|build|validate|typecheck)\b", cmd):
            return "verify"
        if re.search(r"\b(cat|sed -n|head|tail|rg|grep|ls|find|wc|nl)\b", cmd):
            return "recon"
    return "other"


def coordinator_edit(name, args):
    a = args or {}
    if name in ("Bash", "bash"):
        return bool(BASH_WRITE.search(str(a.get("command") or "")))
    if name == "write":
        return not str(a.get("path") or "").startswith(URI_SCHEMES)
    return name in EDIT_TOOLS


def edited_path(name, args):
    a = args or {}
    if a.get("path") or a.get("file_path"):
        return str(a.get("path") or a.get("file_path"))
    patch = str(a.get("input") or a.get("patch") or "")
    m = re.search(r"\*\*\* (?:Update|Add|Delete) File: (\S+)", patch) or re.search(r"\[([^\]#\n]+)#", patch)
    if m:
        return m.group(1)
    return "<bash>" if name in ("Bash", "bash") else "<unknown>"


def growth(calls, start):
    """Context growth after `start`, weighted by later re-reads. Approximate attribution."""
    shares, n = {}, len(calls)
    for i in range(n - 1):
        if start and calls[i]["time"] and calls[i]["time"] < start:
            continue
        delta = calls[i + 1]["ctx"] - calls[i]["ctx"]
        if delta <= 0:
            continue
        weight = delta * (n - 1 - i)
        tools = calls[i]["tools"] or [("<text/user turn>", {})]
        for name, args in tools:
            cat = "other" if name == "<text/user turn>" else category(name, args)
            shares[cat] = shares.get(cat, 0) + weight / len(tools)
    total = sum(shares.values()) or 1
    return {k: round(100 * v / total, 1) for k, v in sorted(shares.items(), key=lambda kv: -kv[1])}


def usage_summary(calls):
    return {"calls": len(calls), "tokens": sum(c["ctx"] + c["out"] for c in calls),
            "output": sum(c["out"] for c in calls), "peak_context": max((c["ctx"] for c in calls), default=0),
            "cost": round(sum(c["cost"] for c in calls if c["cost"] is not None), 2)
            if any(c["cost"] is not None for c in calls) else None}


def iso(t):
    return t.isoformat(timespec="seconds") if t else None


def children_of(sessions, parent):
    pid = parent["raw_id"]
    out = []
    for s in sessions.values():
        if not s["is_subagent"] or s["source"] != parent["source"]:
            continue
        if parent["source"] == "claude" and s["raw_id"].startswith(pid + "/"):
            out.append(s)
        elif parent["source"] == "omp" and s.get("artifact_parent") in parent["paths"]:
            out.append(s)
    return out


def worker_meta(child):
    """Agent identity/description from Claude meta.json or omp session_init."""
    meta = {"agent": None, "description": None, "thinking": None}
    for path in child["paths"]:
        mp = path[:-6] + ".meta.json"
        if os.path.isfile(mp):
            try:
                with open(mp, encoding="utf-8") as fh:
                    m = json.load(fh)
                meta["agent"], meta["description"] = m.get("agentType"), m.get("description")
            except (OSError, ValueError):
                pass
    for _, _, _, d in ordered(child):
        if d.get("type") == "session_init":
            meta["agent"] = meta["agent"] or T.string(d.get("agent"))
        if d.get("type") == "thinking_level_change" and meta["thinking"] is None:
            meta["thinking"] = T.string(d.get("thinkingLevel"))
    if child["source"] == "omp" and not meta["description"]:
        meta["description"] = os.path.basename(child["paths"][0])[:-6]
    return meta


def conversational(source, d):
    if source == "omp":
        return d.get("type") == "message" or (d.get("type") == "custom_message" and d.get("customType") in ("async-result", "irc:incoming"))
    return d.get("type") in ("user", "assistant")


def incoming(source, d):
    """A message from the parent/user arriving in a worker journal (a new assignment or follow-up)."""
    msg = T.obj(d.get("message"))
    if source == "omp":
        return (d.get("type") == "message" and msg.get("role") == "user") or (
            d.get("type") == "custom_message" and d.get("customType") == "irc:incoming")
    content = msg.get("content")
    if d.get("type") != "user" or any(b.get("type") == "tool_result" for b in T.blocks(content)):
        return False
    # Parent follow-ups arrive as isMeta user records; harness reminders are not assignments.
    text = text_of(content).lstrip()
    return bool(text) and not text.startswith(T.META_PREFIXES)


def worker_report(child, coord_calls, args):
    source = child["source"]
    rows = [r for r in ordered(child) if r[0] and conversational(source, r[3])]
    calls = calls_of(child)
    times = [r[0] for r in rows]
    gap, gap_at, reassigned = 0, None, 0
    for (a, *_), (b, _, _, d) in zip(rows, rows[1:]):
        if incoming(source, d):
            reassigned += 1  # waiting for the parent's next message is idle time, not a stall
            continue
        g = (b - a).total_seconds() / 60
        if g > gap:
            gap, gap_at = g, a
    interrupted = any("[Request interrupted" in text_of(T.obj(d.get("message")).get("content"))
                      for _, _, _, d in rows[-3:])
    meta = worker_meta(child)
    start = times[0] if times else None
    base = 0
    for c in coord_calls:
        if start and c["time"] and c["time"] > start:
            break
        base = c["ctx"]
    first = calls[0]["ctx"] if calls else 0
    replay = sum(base + (c["ctx"] - first) + c["out"] for c in calls)
    summary = usage_summary(calls)
    return {
        "agent": meta["agent"], "description": T.clip(meta["description"] or "", 80),
        "models": sorted({c["model"] for c in calls if c["model"]}), "thinking": meta["thinking"],
        "start": iso(start), "end": iso(times[-1] if times else None), **summary,
        "first_context": first, "context_growth": summary["peak_context"] - first,
        "edits": sum(coordinator_edit(n, a) for c in calls for n, a in c["tools"]),
        "follow_up_messages": reassigned,
        "max_working_gap_minutes": round(gap, 1), "max_gap_after": iso(gap_at),
        "stall_candidate": gap >= args.stall_minutes or interrupted, "ended_interrupted": interrupted,
        "large_context": summary["peak_context"] >= args.large_context,
        "replay_tokens_estimate": replay,
    }


def excerpts(sess, start, workers):
    """Redacted excerpts: first and last table-bearing coordinator texts, idle notices while workers run."""
    tables, idle = [], []
    source = sess["source"]
    rows = [r for r in ordered(sess) if r[0] and (not start or r[0] >= start) and conversational(source, r[3])]
    spans = [(T.timestamp(w["start"]), T.timestamp(w["end"])) for w in workers if w["start"] and w["end"]]
    for i, (t, _, _, d) in enumerate(rows):
        msg = T.obj(d.get("message"))
        role = msg.get("role") if source == "omp" else d.get("type")
        if role != "assistant":
            continue
        text = "\n".join(b["text"] for b in T.blocks(msg.get("content")) if b.get("type") == "text" and isinstance(b.get("text"), str)).strip()
        if not text:
            continue
        if text.count("|") >= 6:
            tables.append({"time": iso(t), "text": T.redact(text)[:EXCERPT]})
        nxt = rows[i + 1][0] if i + 1 < len(rows) else None
        running = [sp for sp in spans if sp[0] <= t < sp[1]]
        if running and nxt and (nxt - t).total_seconds() >= 120 and len(idle) < 4:
            idle.append({"time": iso(t), "running_workers": len(running), "idle_minutes": round((nxt - t).total_seconds() / 60, 1),
                         "text": T.clip(text, 300)})
    first = tables[0] if tables else None
    last = tables[-1] if len(tables) > 1 else None
    return first, last, idle


def analyze(args):
    diagnostics = {"files_read": 0, "malformed_records": 0, "unreadable_files": 0, "invalid_headers": 0}
    sessions, roots = T.load_sessions(args, diagnostics)
    since = T.since_time(args)
    proj = (args.project or "").lower()
    found = []
    for sess in sessions.values():
        if sess["is_subagent"]:
            continue
        if proj and proj not in sess["cwd"].lower() and proj not in sess["project"].lower():
            continue
        rows = ordered(sess)
        times = [t for t, *_ in rows if t]
        if not times or times[-1] < since:
            continue
        start = next((t for t, _, _, d in rows if skill_hit(sess["source"], d, args.skill_re)), None)
        if start is None:
            continue
        coord = calls_of(sess)
        post = [c for c in coord if c["time"] and c["time"] >= start]
        workers = [worker_report(ch, coord, args) for ch in children_of(sessions, sess)]
        workers = sorted([w for w in workers if w["start"] and T.timestamp(w["start"]) >= start], key=lambda w: w["start"])
        edits = [(n, a) for c in post for n, a in c["tools"] if coordinator_edit(n, a)]
        files = {}
        for n, a in edits:
            f = edited_path(n, a)
            files[f] = files.get(f, 0) + 1
        first_table, last_table, idle = excerpts(sess, start, workers)
        worker_tokens = sum(w["tokens"] for w in workers)
        found.append({
            "session": sess["id"], "project": sess["project"], "cwd": sess["cwd"],
            "first": iso(times[0]), "last": iso(times[-1]), "skill_loaded": iso(start),
            "coordinator": {"before": usage_summary([c for c in coord if not (c["time"] and c["time"] >= start)]), "after": usage_summary(post),
                            "growth_share_pct": growth(coord, start),
                            "edits_after_skill": len(edits),
                            "edited_files_top": sorted(files.items(), key=lambda kv: -kv[1])[:8],
                            "approval_questions": sum(1 for c in post for n, _ in c["tools"] if n in ("AskUserQuestion", "ask"))},
            "workers": workers,
            "worker_totals": {"count": len(workers), "tokens": worker_tokens,
                              "replay_tokens_estimate": sum(w["replay_tokens_estimate"] for w in workers),
                              "stall_candidates": sum(w["stall_candidate"] for w in workers),
                              "large_context": sum(w["large_context"] for w in workers)},
            "first_table_excerpt": first_table, "last_table_excerpt": last_table, "idle_notices": idle,
        })
    found.sort(key=lambda s: s["skill_loaded"], reverse=True)
    return {"scope": {"source": args.source, "since": iso(since), "project": args.project, "skill": args.skill,
                      "roots": roots, "stall_minutes": args.stall_minutes, "large_context": args.large_context},
            "sessions_total": len(found), "omitted_sessions": max(0, len(found) - args.max_sessions),
            "sessions": found[:args.max_sessions], "diagnostics": diagnostics,
            "caveats": ["growth_share_pct splits each context delta equally across that call's tools and weights it by "
                        "later calls; it is an approximate attribution, not a cost share",
                        "replay_tokens_estimate replays the same worker call sequence on the coordinator context at "
                        "spawn; it is not a measured causal saving",
                        "stall_candidate is a gap/interrupt signal inside the worker journal, not proof of a hang"]}


def k(n):
    return "?" if n is None else (f"{n / 1e6:.2f}M" if n >= 1e6 else f"{n / 1e3:.0f}k")


def fmt_md(r):
    out = [f"# Orchestration retrospective ({r['scope']['source']}, since {r['scope']['since'][:10]})", "",
           f"Sessions with `{r['scope']['skill']}`: {r['sessions_total']}" + (f" (omitted {r['omitted_sessions']})" if r["omitted_sessions"] else ""), ""]
    for s in r["sessions"]:
        c, a = s["coordinator"], s["coordinator"]["after"]
        out += [f"## {s['session']} ({s['project']})", "",
                f"- skill loaded {s['skill_loaded']}; coordinator after: {a['calls']} calls, {k(a['tokens'])} tokens, "
                f"peak {k(a['peak_context'])}" + (f", ${a['cost']}" if a["cost"] is not None else ""),
                f"- growth share %: " + ", ".join(f"{n} {v}" for n, v in c["growth_share_pct"].items()),
                f"- coordinator edits after load: {c['edits_after_skill']}; top: "
                + ", ".join(f"{T.clip(f, 60)}×{n}" for f, n in c["edited_files_top"]),
                f"- approval questions: {c['approval_questions']}",
                f"- workers {s['worker_totals']['count']}: {k(s['worker_totals']['tokens'])} tokens; replay estimate "
                f"{k(s['worker_totals']['replay_tokens_estimate'])}; stall candidates {s['worker_totals']['stall_candidates']}; "
                f"large context {s['worker_totals']['large_context']}", ""]
        if s["workers"]:
            out += ["| start | agent | models / thinking | calls | tokens | first→peak | edits | follow-ups | max working gap | flags | description |",
                    "|---|---|---|---|---|---|---|---|---|---|---|"]
            for w in s["workers"]:
                flags = ",".join(f for f, on in (("stall", w["stall_candidate"]), ("interrupted", w["ended_interrupted"]),
                                                   ("large", w["large_context"])) if on)
                out.append(f"| {w['start'][11:16]} | {w['agent']} | {'/'.join(w['models'])} {w['thinking'] or ''} | {w['calls']} | "
                           f"{k(w['tokens'])} | {k(w['first_context'])}→{k(w['peak_context'])} | {w['edits']} | {w['follow_up_messages']} | "
                           f"{w['max_working_gap_minutes']}m | {flags} | {w['description']} |")
            out.append("")
        for label, ex in (("First table after skill load", s["first_table_excerpt"]), ("Last table", s["last_table_excerpt"])):
            if ex:
                out += [f"{label} ({ex['time']}, redacted):", "", "```text", ex["text"], "```", ""]
        for n in s["idle_notices"]:
            out.append(f"- idle notice {n['time']} ({n['running_workers']} running, {n['idle_minutes']}m idle): {n['text']}")
        out.append("")
    out += ["## Caveats", ""] + [f"- {c}" for c in r["caveats"]]
    d = r["diagnostics"]
    out += ["", f"Diagnostics: files {d['files_read']}, malformed {d['malformed_records']}, unreadable {d['unreadable_files']}, "
            f"invalid headers {d['invalid_headers']}"]
    return "\n".join(out) + "\n"


def main(argv=None):
    args = parse_args(argv)
    try:
        report = analyze(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=1, default=str) if args.out == "json" else fmt_md(report), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
