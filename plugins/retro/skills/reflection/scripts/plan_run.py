#!/usr/bin/env python3
"""Read-only, stdlib-only retrospective of one ralphex plan run; never runs ralphex."""
import argparse
import collections
import datetime as dt
import glob
import json
import os
import re
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import transcripts as T  # noqa: E402

UTC = dt.timezone.utc
STAMP = r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[+-]\d{2}:\d{2}|Z)?"


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan")
    p.add_argument("--progress")
    p.add_argument("--project-root", default=os.getcwd())
    p.add_argument("--tz", help="IANA zone for zoneless progress times (default system zone)")
    p.add_argument("--config-dir", default=os.environ.get("CLAUDE_CONFIG_DIR") or "~/.claude")
    p.add_argument("--omp-sessions-dir", default="~/.omp/agent/sessions")
    p.add_argument("--codex-sessions-dir", default=os.environ.get("CODEX_HOME") or "~/.codex")
    p.add_argument("--planning-days", type=int, default=3)
    p.add_argument("--out", choices=("json", "md"), default="md")
    args = p.parse_args(argv)
    if args.planning_days < 0:
        p.error("--planning-days must be nonnegative")
    if args.tz:
        try:
            ZoneInfo(args.tz)
        except ZoneInfoNotFoundError:
            p.error("--tz must name an available IANA zone")
    for key in ("project_root", "config_dir", "omp_sessions_dir", "codex_sessions_dir"):
        setattr(args, key, os.path.realpath(os.path.expanduser(getattr(args, key))))
    return args


def local_time(value, zone=None):
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None and zone:
            parsed = parsed.replace(tzinfo=ZoneInfo(zone))
        return parsed.astimezone(UTC)
    except (ValueError, OverflowError):
        return None


def iso(value):
    return value.isoformat() if value else None


def resolve(path, cwd):
    return os.path.realpath(path if os.path.isabs(path) else os.path.join(cwd, path))


def read_text(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError as error:
        raise ValueError(f"cannot read {path}: {error.strerror}") from error


def progress_positions(text):
    """Yield positions outside balanced parentheses and quoted/code spans."""
    depth, quote, index = 0, None, 0
    while index < len(text):
        char = text[index]
        if quote:
            if char == "\\" and not quote.startswith("`"):
                index += 2
                continue
            if text.startswith(quote, index):
                index += len(quote)
                quote = None
                continue
        else:
            if depth == 0:
                yield index
            if char == "`":
                end = index + 1
                while end < len(text) and text[end] == "`":
                    end += 1
                quote = text[index:end]
                index = end
                continue
            if char in "\"'«“" and not (char == "'" and index and text[index - 1].isalnum()):
                quote = {"«": "»", "“": "”"}.get(char, char)
            elif char == "(":
                depth += 1
            elif char == ")":
                depth = max(0, depth - 1)
        index += 1
    if not depth and not quote:
        yield len(text)


def task_clauses(line):
    """Split status chains only at separators outside titles and quoted spans."""
    text = re.sub(r"^\[[^\]]+\]\s*", "", line).strip()
    text = re.sub(r"^[-*]\s+", "", text)
    # A declared selection's colon introduces its title, not a status chain.
    if re.match(r"(?:Выбран[ао]?|Начат[ао]?|Selected|Started)\s+(?:Task|Задача)\s*\d+\s*:", text, re.I):
        yield line
        return
    separator = re.compile(
        r"(?:[.;,]\s+|\s+(?:and|и)\s+)(?=(?:(?:Task|Задача)\s*\d+\b|I\s+did\s+(?:Task|Задача)\s*\d+\b|(?:Выбран[ао]?|Начат[ао]?)\s+(?:Task|Задача)\s*\d+\b))", re.I)
    start = 0
    for index in progress_positions(line):
        if index < start:
            continue
        match = separator.match(line, index)
        if match:
            yield line[start:index]
            start = match.end()
    yield line[start:]


def task_progress(line):
    """Recognize affirmative task status, not future references or quoted commands."""
    text = re.sub(r"^\[[^\]]+\]\s*", "", line).strip()
    text = re.sub(r"^(?:[-*]\s+)", "", text)
    selected = re.match(r"(?:Выбран[ао]?|Начат[ао]?|Selected|Started)\s+(?:Task|Задача)\s*(\d+)\b", text, re.I)
    did = re.match(r"I\s+did\s+(?:Task|Задача)\s*(\d+)\b", text, re.I)
    if selected:
        number, completed, end = int(selected[1]), False, selected.end()
        if re.match(r"\s*(?:[-–—/,]\s*\d+|(?:и|and)\s+\d+)\b", text[end:], re.I):
            return None
        title = re.match(r"\s*\(", text[end:])
        if title:
            end += title.end() - 1
            title_end = next((pos for pos in progress_positions(text[end:]) if pos > 0), None)
            if title_end is None:
                return None
            end += title_end
    elif did:
        number, completed, end = int(did[1]), True, did.end()
    else:
        task = re.match(r"(?:Task|Задача)\s*(\d+)\b\s*", text, re.I)
        if not task:
            return None
        number, end = int(task[1]), task.end()
        if text[end:end + 1] == "(":
            title_end = next((pos for pos in progress_positions(text[end:]) if pos > 0), None)
            if title_end is None:
                return None
            end += title_end
        status = re.match(
            r"\s*(?:is\s+)?(done|complete|completed|finished|started|starting|in progress|"
            r"выполнен[ао]?|заверш[её]н[ао]?|начат[ао]?|выбран[ао]?|готов[ао]?\s+к\s+фиксации)\b",
            text[end:], re.I)
        if not status:
            return None
        completed = bool(re.fullmatch(r"done|complete|completed|finished|выполнен[ао]?|заверш[её]н[ао]?", status[1], re.I))
        end += status.end()
    tail = text[end:]
    if selected:
        tail = tail.split(":", 1)[0]
    assertion_tail = re.split(r"[.!]", tail, maxsplit=1)[0]
    # Inspect assertion framing only: task titles may legitimately contain code,
    # negation words, or punctuation unrelated to the completion assertion.
    if ("?" in assertion_tail
            or re.search(r"\b(?:if|unless|provided|assuming|если|когда|при\s+условии|не|будет|буду|бы|ли)\b", assertion_tail, re.I)
            or re.match(r"\s*(?:[`\"'«“]|(?:is\s+)?(?:not|yet to|would|will|не|ещ[её]\s+не|будет|буду)\b)", tail, re.I)):
        return None
    return {"task_number": number, "status": "completed" if completed else "started"}


def parse_progress(path, zone=None):
    lines = read_text(path).splitlines()
    header = {}
    times = []
    quoted_lines = set()
    fence = None
    for line in lines:
        text = re.sub(r"^\[[^\]]+\]\s*", "", line).strip()
        marker = re.match(r"(`{3,}|~{3,})(.*)$", text)
        if fence:
            quoted_lines.add(len(times))
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = None
        elif marker:
            quoted_lines.add(len(times))
            fence = marker[1]
        h = re.match(r"^(Plan|Branch|Mode|Started):\s*(.*)", line)
        if h and h[1] not in header:
            header[h[1]] = h[2]
        stamp = re.match(r"\[(\d{2}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]", line)
        if stamp:
            times.append(local_time("20" + stamp[1], zone))
        else:
            stamp = re.search(STAMP, line)
            times.append(local_time(stamp[0], zone) if stamp else None)
    start = local_time(header.get("Started", ""), zone)
    boundaries, failures, resumes, terminals, restarts = [], [], [], [], []
    phase = None
    for index, line in enumerate(lines):
        # Untimed markers use the preceding timestamp as a conservative boundary.
        # The executor can start before its first printed output.
        time = times[index] or next((t for t in reversed(times[:index]) if t), start)
        time_source = "explicit" if times[index] else "preceding-progress-time"
        text = re.sub(r"^\[[^\]]+\]\s*", "", line).strip()
        phase_match = re.match(r"starting (.+?) phase\b", text, re.I)
        review_match = re.fullmatch(
            r"---\s*(claude review(?:\s+(\d+))?(?::\s*.*?)?|"
            r"codex external review|codex iteration\s+(\d+)|custom external review|"
            r"custom review iteration\s+(\d+)|claude evaluating codex findings)\s*---", text, re.I)
        review_start = re.fullmatch(r"all tasks completed[,.;]?\s*starting code review[.!…]*", text, re.I)
        iteration = re.fullmatch(r"--- task iteration (\d+) ---", text, re.I)
        restart = re.search(r"--- restarted at (.+?) ---", line)
        terminal = re.match(r"^([A-Z][a-z]+):\s*(" + STAMP + r")(.*)$", line)
        if phase_match or review_match or review_start:
            metadata = {}
            if review_match:
                label = review_match[1].lower()
                if label.startswith("claude review"):
                    name, role = "claude review", "review"
                    round_number = review_match[2]
                elif label.startswith("codex"):
                    name, role = "external codex review", "external-review"
                    round_number = review_match[3]
                elif label.startswith("custom"):
                    name, role = "custom external review", "external-review"
                    round_number = review_match[4]
                else:
                    name, role = "claude evaluating codex findings", "evaluation"
                    round_number = None
                metadata = {"review_label": review_match[1], "review_role": role,
                            "review_round": int(round_number) if round_number is not None else None}
            else:
                name = phase_match[1] if phase_match else "claude review"
                if review_start:
                    metadata = {"review_label": text, "review_role": "review", "review_round": None}
            phase = name
            boundary = {"kind": "phase", "name": phase, "start": time, "line": index + 1,
                        "time_source": time_source, **metadata}
            # A phase introduction and its first round may share one timestamp.
            # Keep the earlier line as the task stop, but refine its round metadata.
            if (boundaries and boundaries[-1]["kind"] == "phase"
                    and boundaries[-1]["name"] == name and boundaries[-1]["start"] == time
                    and (boundaries[-1].get("review_round") is None
                         or boundaries[-1].get("review_round") == metadata.get("review_round"))):
                boundaries[-1].update(metadata)
            else:
                boundaries.append(boundary)
        elif iteration:
            boundaries.append({"kind": "iteration", "number": int(iteration[1]), "phase": phase,
                               "start": time, "line": index + 1, "task_number": None, "time_source": time_source})
        elif restart:
            time = local_time(restart[1], zone)
            restarts.append({"time": iso(time), "line": index + 1})
            boundaries.append({"kind": "restart", "start": time, "line": index + 1})
            phase = None
        elif terminal and terminal[1] != "Started":
            terminals.append({"status": terminal[1], "time": iso(time), "text": line, "line": index + 1})
            boundaries.append({"kind": "terminal", "start": time, "line": index + 1})
        failure_position = line.find("<<<RALPHEX:TASK_FAILED>>>")
        if (index not in quoted_lines and failure_position >= 0
                and failure_position in progress_positions(line)):
            failures.append({"time": iso(time), "line": index + 1,
                             "excerpt": [T.clip(text, 500) for text in lines[max(0, index - 8):index]]})
        resume = re.search(r"(?:^|\]\s*)(ralphex\s+.+)", line)
        if resume:
            resumes.append({"time": iso(time), "line": index + 1, "command": T.clip(resume[1], 1500)})
    for pos, boundary in enumerate(boundaries):
        following = boundaries[pos + 1:]
        boundary["end"] = following[0]["start"] if following else None
        if boundary["kind"] == "phase":
            boundary["end"] = next((b["start"] for b in following if b["kind"] != "iteration"), None)
        if boundary["kind"] != "iteration":
            continue
        stop = following[0]["line"] - 1 if following else len(lines)
        evidence = []
        for number, line in enumerate(lines[boundary["line"]:stop], boundary["line"] + 1):
            if number - 1 in quoted_lines:
                continue
            clauses = list(task_clauses(line))
            # Only expand later affirmative clauses when the line itself is status,
            # not a command/quotation containing task-shaped text.
            if not task_progress(clauses[0]):
                continue
            for clause in clauses:
                status = task_progress(clause)
                if status:
                    evidence.append({**status, "line": number, "text": T.clip(line, 300)})
        completed_ids = {e["task_number"] for e in evidence if e["status"] == "completed"}
        ids = completed_ids or {e["task_number"] for e in evidence}
        boundary["task_number"] = next(iter(ids)) if len(ids) == 1 else None
        boundary["task_identity"] = "explicit-progress" if len(ids) == 1 else "ambiguous" if ids else "unknown"
        boundary["task_evidence"] = evidence
        boundary["failures"] = [f for f in failures if boundary["line"] <= f["line"] <= stop]
        boundary["outcome"] = "failed" if boundary["failures"] else "completed" if completed_ids else "unknown"
        # The terminal protocol signal completes only this safely identified window.
        # Conflicting identities and failures remain authoritative.
        if (not completed_ids and len(ids) == 1 and not boundary["failures"]
                and any(re.sub(r"^\[[^\]]+\]\s*", "", lines[n]).strip() == "<<<RALPHEX:ALL_TASKS_DONE>>>"
                        for n in range(boundary["line"], stop) if n not in quoted_lines)):
            boundary["outcome"] = "completed"
            boundary["task_evidence"].append({"task_number": boundary["task_number"], "status": "completed",
                                              "line": next(n + 1 for n in range(boundary["line"], stop)
                                                           if "<<<RALPHEX:ALL_TASKS_DONE>>>" in lines[n]),
                                              "text": "<<<RALPHEX:ALL_TASKS_DONE>>>"})
    last_terminal = terminals[-1] if terminals else None
    if last_terminal and restarts and restarts[-1]["line"] > last_terminal["line"]:
        last_terminal = None
    return {"path": os.path.realpath(path), "header": header, "start": start,
            "end": T.timestamp(last_terminal["time"]) if last_terminal else None,
            "status": last_terminal["status"] if last_terminal else "unknown",
            "failed": last_terminal["status"] == "Failed" if last_terminal else None,
            "terminals": terminals, "restarts": restarts, "resume_lines": resumes,
            "failures": failures, "boundaries": boundaries}


def parse_plan(path):
    text = read_text(path)
    tasks, current, validation, in_validation = [], None, [], False
    for line in text.splitlines():
        heading = re.match(r"### Task (\d+):\s*(.*)", line)
        if heading:
            current = {"number": int(heading[1]), "title": heading[2], "done": 0, "total": 0}
            tasks.append(current)
        elif re.match(r"#{1,3}\s", line):
            current = None
        box = re.match(r"\s*[-*]\s+\[([ xX])\]", line)
        if current and box:
            current["total"] += 1
            current["done"] += box[1].lower() == "x"
        if re.match(r"##\s+Validation Commands\s*$", line):
            in_validation = True
        elif re.match(r"#{1,2}\s", line):
            in_validation = False
        elif in_validation:
            command = re.match(r"\s*[-*]\s+(.*)", line)
            if command:
                validation.append(command[1].strip().strip("`"))
    return {"path": os.path.realpath(path), "bytes": os.path.getsize(path), "lines": len(text.splitlines()),
            "tasks": tasks, "validation_commands": validation}


def select_inputs(args):
    root = args.project_root
    plan = resolve(args.plan, root) if args.plan else None
    candidates = glob.glob(os.path.join(root, ".ralphex", "progress", "progress-*.txt"))
    candidates.sort(key=os.path.getmtime, reverse=True)
    if args.progress:
        progress = resolve(args.progress, root)
        run = parse_progress(progress, args.tz)
        match = "explicit-progress"
    else:
        parsed = [(path, parse_progress(path, args.tz)) for path in candidates]
        if plan:
            exact = [(p, r) for p, r in parsed if r["header"].get("Plan") and resolve(r["header"]["Plan"], root) == plan]
            matches = exact or [(p, r) for p, r in parsed if os.path.basename(r["header"].get("Plan", "")) == os.path.basename(plan)]
            match = "realpath" if exact else "basename"
        else:
            matches, match = parsed, "newest"
        if not matches:
            raise ValueError("no matching progress log found")
        progress, run = matches[0]
    if not plan:
        if not run["header"].get("Plan"):
            raise ValueError("progress has no Plan header; supply --plan")
        plan = resolve(run["header"]["Plan"], root)
    return run, parse_plan(plan), {"matched_by": match, "other_progress": [os.path.realpath(p) for p in candidates if os.path.realpath(p) != os.path.realpath(progress)]}


def inside(cwd, root):
    if not cwd:
        return False
    try:
        return os.path.commonpath((os.path.realpath(cwd), root)) == root
    except ValueError:
        return False


def in_window(time, start, end):
    return time is not None and start is not None and start <= time and (end is None or time < end)


def duration(start, end):
    return (end - start).total_seconds() if start and end and end >= start else None


def metrics(events):
    return T.metric_summary([e for e in events if e["kind"] == "usage"])


def partial_metrics(value):
    """Keep observed subtotals without presenting them as a complete cost."""
    return {**value, **{key: None for key in T.METRICS}, "completeness": "partial", "coverage_missing": True}


def usage_completeness(value):
    """Describe the measured summary, independently of stage attribution."""
    if value.get("coverage_missing") or any(value["missing"].values()):
        return "partial"
    return "observed" if value["total"] is not None else "unknown"


def usage_gap(sess, start):
    if sess.get("usage_source") != "token_count":
        return False
    baseline = T.timestamp(sess.get("usage_baseline_time"))
    return start is None or baseline is None or baseline > start


def window_events(events, start, end):
    return [e for e in events if in_window(e.get("time"), start, end)]


def tool_details(sess, events):
    """Use explicit result envelopes, never output-text error guesses."""
    results = {}
    for _, _, raw in sess["records"]:
        msg = T.obj(raw.get("message"))
        time = T.timestamp(raw.get("timestamp")) or T.timestamp(msg.get("timestamp"))
        if sess["source"] == "omp" and msg.get("role") == "toolResult":
            results[msg.get("toolCallId")] = (time, msg.get("isError"))
        elif sess["source"] == "claude" and raw.get("type") == "user":
            for block in T.blocks(msg.get("content")):
                if block.get("type") == "tool_result":
                    results[block.get("tool_use_id")] = (time, block.get("is_error"))
    tools = []
    for event in events:
        if event["kind"] != "tool":
            continue
        result_time, error = results.get(event["key"], (None, None))
        status = event.get("status", "error" if error is True else "success" if error is False else "unknown")
        tools.append({**event, "status": status,
                      "duration_seconds": event.get("duration_seconds", duration(event.get("time"), result_time))})
    return tools


def link_row(sess, events, start, end, linked_by, confidence):
    selected = window_events(events, start, end)
    usage = [e for e in selected if e["kind"] == "usage"]
    usage_incomplete = usage_gap(sess, start) or sess.get("evidence_coverage") == "partial"
    usage_summary = T.metric_summary(usage)
    if usage_incomplete:
        usage_summary = partial_metrics(usage_summary)
    tools = tool_details(sess, selected)
    observed_errors = sum(e["kind"] == "error" for e in selected)
    errors = observed_errors if observed_errors else 0 if tools and all(t["status"] != "unknown" for t in tools) else None
    routes = collections.defaultdict(list)
    for event in usage:
        routes[(event.get("provider"), event.get("model"), event.get("effort"), event.get("configured_effort"))].append(event)
    slow = sorted((t for t in tools if t["duration_seconds"] is not None),
                  key=lambda t: t["duration_seconds"], reverse=True)[:5]
    times = [e["time"] for e in events if e.get("time")]
    return {"session": sess["id"], "source": sess["source"], "cwd": sess.get("cwd"),
            "is_subagent": bool(sess.get("is_subagent")), "parent_lineage": sess.get("parent_lineage"),
            "parent_thread_id": sess.get("parent_thread_id"), "root_lineage": sess.get("root_lineage"),
            "start": iso(min(times)) if times else None, "linked_by": linked_by, "confidence": confidence,
            "evidence_files": sess["paths"], "usage": usage_summary,
            "calls": len(usage) if usage else None, "tool_calls": len(tools) if tools else None,
            "errors": errors, "observed_errors": observed_errors,
            "models": [{"provider": key[0], "model": key[1], "effort": key[2], "configured_effort": key[3],
                        "usage": partial_metrics(T.metric_summary(value)) if usage_incomplete else T.metric_summary(value)}
                       for key, value in routes.items()],
            "slowest_commands": [{"name": t["name"], "command": T.clip(str(t.get("arguments", {}).get("command") or t.get("raw_input") or t.get("arguments")), 500),
                                  "duration_seconds": t["duration_seconds"], "status": t["status"],
                                  "duration_source": t.get("duration_source", "call_to_result_elapsed"),
                                  "result_time": iso(t.get("result_time"))} for t in slow],
            "duration_seconds": duration(min(times), max(times)) if times else None,
            "partial_history": bool(sess.get("partial_history")), "thread_total": sess.get("thread_total"),
            "usage_source": sess.get("usage_source"),
            "usage_baseline_time": sess.get("usage_baseline_time"),
            "usage_coverage_end": sess.get("usage_coverage_end"),
            "usage_completeness": "partial" if usage_incomplete else "observed" if usage else "unknown",
            "evidence_coverage": sess.get("evidence_coverage", "observed"),
            "completeness": "partial" if usage_incomplete or sess.get("partial_history") or not usage
                            or any(e.get("time") is None for e in events)
                            or any(v for v in usage_summary["missing"].values()) else "observed"}


def planning_evidence(sess, events, plan_paths, start, end):
    evidence = []
    for event in window_events(events, start, end):
        if event["kind"] != "tool":
            continue
        paths = []
        args = T.obj(event.get("arguments"))
        if event["name"] in ("Write", "Edit", "MultiEdit"):
            paths = [args.get("file_path") or args.get("path")]
        elif event["name"] == "apply_patch":
            raw = event.get("raw_input") or args.get("input") or args.get("patch") or ""
            paths = re.findall(r"^\*\*\* (?:Add|Update) File:\s*(.+?)\s*$", str(raw), re.M)
        for path in paths:
            if not isinstance(path, str) or (not os.path.isabs(path) and not sess.get("cwd")):
                continue
            if resolve(path, sess.get("cwd") or "") in plan_paths:
                evidence.append({"path": path, "time": iso(event.get("time")), "tool": event["name"],
                                 "entry": event.get("entry"), "key": event["key"]})
    return evidence


def serial(value):
    if isinstance(value, dt.datetime):
        return iso(value)
    if isinstance(value, dict):
        return {key: serial(item) for key, item in value.items()}
    if isinstance(value, list):
        return [serial(item) for item in value]
    return value


def suppress_family_copies(sessions, normalized, diagnostics):
    """Deduplicate identical artifact-family events, without assigning child costs."""
    families = {sid: sid for sid in sessions}
    paths = {os.path.abspath(path): sid for sid, sess in sessions.items() for path in sess["paths"]}

    def family(sid):
        while families[sid] != sid:
            sid = families[sid]
        return sid

    for sid, sess in sessions.items():
        parent = sess.get("artifact_parent") or sess.get("parent_lineage")
        if not isinstance(parent, str):
            continue
        target = sess["source"] + ":" + parent
        target = target if target in sessions else paths.get(os.path.abspath(parent))
        if target is not None and sessions[target]["source"] == sess["source"]:
            families[family(sid)] = family(target)
    seen = set()
    message_proofs = {}
    for sid, sess in sessions.items():
        if sess["source"] != "claude":
            continue
        proofs = {}
        for _, _, raw in sess["records"]:
            message = T.obj(raw.get("message"))
            identity = message.get("id") or raw.get("uuid")
            if message and isinstance(identity, str) and identity:
                proofs[T.fingerprint(raw)] = (raw.get("type"), identity, T.fingerprint(message))
        message_proofs[sid] = proofs
    for sid, sess in sorted(sessions.items(), key=lambda pair: (pair[1].get("is_subagent", False), pair[0])):
        selected = []
        for event in normalized[sid]:
            proof = message_proofs.get(sid, {}).get(event.get("fingerprint"))
            # Claude transport wrappers may differ while preserving the exact
            # provider message. Other sources retain full persisted-record proof.
            payload = ("claude-message", proof) if proof else ("raw-record", event.get("fingerprint"))
            key = (family(sid), event["kind"], event["key"], payload)
            if event.get("fingerprint") and key in seen:
                diagnostics["copied_events_skipped"] += 1
                continue
            seen.add(key)
            selected.append(event)
        normalized[sid] = selected


def report(args):
    run, plan, selection = select_inputs(args)
    diagnostics = collections.Counter()
    sources, sessions, normalized = {}, {}, {}
    lookback = run["start"] - dt.timedelta(days=args.planning_days) if run["start"] else None
    loss_keys = ("zst_skipped", "unreadable_files", "malformed_records", "invalid_headers")
    for source in ("claude", "omp", "codex"):
        loader = argparse.Namespace(source=source, config_dir=args.config_dir,
                                    omp_sessions_dir=args.omp_sessions_dir, codex_sessions_dir=args.codex_sessions_dir,
                                    include_subagents=True, include_sdk=True, include_exec=True)
        source_diagnostics = collections.Counter()
        try:
            loaded, roots = T.load_sessions(loader, source_diagnostics, min_mtime=lookback)
        except ValueError as error:
            diagnostics.update(source_diagnostics)
            sources[source] = {"status": "unavailable", "coverage": "unknown", "reason": str(error)}
            continue
        sources[source] = {"status": "available", "root": roots[source], "sessions": len(loaded)}
        sessions.update(loaded)
        for sid, sess in loaded.items():
            normalized[sid] = T.normalize(sess, source_diagnostics)
        diagnostics.update(source_diagnostics)
        loss = {key: source_diagnostics[key] for key in loss_keys if source_diagnostics[key]}
        sources[source].update(coverage="partial" if loss else "observed", evidence_loss=loss,
                               diagnostics=dict(source_diagnostics))
    suppress_family_copies(sessions, normalized, diagnostics)
    coverage_loss = any(source.get("coverage") == "partial" for source in sources.values())
    # Lost records have no reliable cwd/time to exclude them from this report.
    for sess in sessions.values():
        sess["evidence_coverage"] = "partial" if coverage_loss else "observed"
    eligible = {}
    for sid, sess in sessions.items():
        if not inside(sess.get("cwd"), args.project_root):
            continue
        times = [e["time"] for e in normalized[sid] if e.get("time")]
        # Session headers are authoritative for start; prompts may come later.
        times.extend(t for _, _, raw in sess["records"] if (t := T.timestamp(raw.get("timestamp"))) is not None)
        if times:
            eligible[sid] = min(times)
        else:
            diagnostics["sessions_without_time"] += 1
    def automation(sess):
        return bool(sess.get("automation") or (sess["source"] == "claude" and
                    (sess.get("raw_id", "").startswith("sdk") or sess.get("entrypoint", "").startswith("sdk"))))
    iterations, reviews, attributed_keys = [], [], set()
    attributed = collections.defaultdict(list)
    for boundary in run["boundaries"]:
        kind = boundary["kind"]
        if kind != "iteration" and not (kind == "phase" and boundary["name"].lower() != "task execution"):
            continue
        start, end = boundary["start"], boundary["end"]
        candidates = [sid for sid, time in eligible.items() if not sessions[sid].get("is_subagent")
                      and in_window(time, start, end)
                      and (automation(sessions[sid]) or (kind == "phase" and sessions[sid]["source"] == "omp"))]
        row = {**boundary, "duration_seconds": duration(start, end),
               "link_status": "ambiguous" if len(candidates) > 1 else "linked" if candidates else "unlinked",
               "candidates": []}
        if kind == "phase":
            row["review_provider"] = sessions[candidates[0]]["source"] if len(candidates) == 1 else None
        for sid in candidates:
            confidence = "low" if sessions[sid]["source"] == "omp" else "medium"
            row["candidates"].append(link_row(sessions[sid], normalized[sid], start, end, "time-window|cwd", confidence))
            # Candidate identity alone does not attribute events outside this window.
        row["usage"] = row["candidates"][0]["usage"] if len(candidates) == 1 else metrics([])
        if len(candidates) == 1:
            events = window_events(normalized[candidates[0]], start, end)
            phase_key = (boundary.get("phase") or "task execution") if kind == "iteration" else boundary["name"]
            attributed[phase_key].extend(events)
            attributed_keys.update((candidates[0], e["kind"], e["key"]) for e in events)
        (iterations if kind == "iteration" else reviews).append(row)
    tasks = []
    for task in plan["tasks"] + ([{"number": None, "title": "Unidentified task", "done": None, "total": None}]
                                 if any(i["task_number"] not in {t["number"] for t in plan["tasks"]} for i in iterations) else []):
        selected = [i for i in iterations if i["task_number"] == task["number"]] if task["number"] is not None else [
            i for i in iterations if i["task_number"] not in {t["number"] for t in plan["tasks"]}]
        events = []
        for iteration in selected:
            if iteration["link_status"] == "linked":
                sid = iteration["candidates"][0]["session"]
                events.extend(window_events(normalized[sid], iteration["start"], iteration["end"]))
        usage = metrics(events)
        incomplete = any(i["link_status"] != "linked" for i in selected)
        usage_incomplete = coverage_loss or any(c["usage_completeness"] == "partial" for i in selected for c in i["candidates"])
        if usage_incomplete or incomplete:
            usage = partial_metrics(usage)
        durations = [i["duration_seconds"] for i in selected]
        tasks.append({**task, "iterations": selected, "usage": usage,
                      "duration_seconds": sum(durations) if durations and all(d is not None for d in durations) else None,
                      "outcome": selected[-1]["outcome"] if selected else "unknown",
                      "calls": len([e for e in events if e["kind"] == "usage"]) if events and not incomplete else None,
                      "errors": sum(e["kind"] == "error" for e in events) or None,
                      "models": [m for i in selected for c in i["candidates"] for m in c["models"]],
                      "slowest_commands": sorted([s for i in selected for c in i["candidates"] for s in c["slowest_commands"]],
                                                key=lambda s: s["duration_seconds"], reverse=True)[:5],
                      "failure_excerpt": [f for i in selected for f in i["failures"]],
                      "completeness": "partial" if incomplete or not selected or any(
                          c["completeness"] == "partial" for i in selected for c in i["candidates"])
                          or any(s["status"] != "available" for s in sources.values()) else "observed"})
    plan_paths = {plan["path"]}
    if run["header"].get("Plan"):
        plan_paths.add(resolve(run["header"]["Plan"], args.project_root))
    planning, planning_events = [], []
    for sid, sess in sessions.items():
        if automation(sess) or sess.get("is_subagent"):
            continue
        evidence = planning_evidence(sess, normalized[sid], plan_paths, lookback, run["start"])
        if evidence:
            row = link_row(sess, normalized[sid], lookback, run["start"], "path|time-window|cwd", "high")
            row["evidence"] = evidence
            planning.append(row)
            planning_events.extend(window_events(normalized[sid], lookback, run["start"]))
    other, observed, unlinked = [], [], []
    for sid in eligible:
        events = window_events(normalized[sid], run["start"], run["end"])
        observed.extend(events)
        remaining = [e for e in events if (sid, e["kind"], e["key"]) not in attributed_keys]
        if remaining:
            other.append(link_row(sessions[sid], remaining, run["start"], run["end"], "time-window|cwd", "low"))
            unlinked.extend(remaining)
    total_usage, unlinked_usage = metrics(observed), metrics(unlinked)
    run_usage_gap = coverage_loss or any(usage_gap(sessions[sid], run["start"]) for sid in eligible)
    if run_usage_gap:
        total_usage = partial_metrics(total_usage)
        unlinked_usage = partial_metrics(unlinked_usage)
    read_completeness = "partial" if coverage_loss or any(
        s["status"] != "available" for s in sources.values()) else "observed"
    attribution_completeness = "partial" if (
        not iterations and not reviews
        or any(row["link_status"] != "linked" for row in iterations + reviews)
        or any(i["task_number"] not in {t["number"] for t in plan["tasks"]} for i in iterations)
        or run["start"] is None or run["end"] is None) else "observed"
    run_usage_completeness = usage_completeness(total_usage)
    completeness = "observed" if (read_completeness == run_usage_completeness
        == attribution_completeness == "observed" and not any(
            s.get("partial_history") for s in sessions.values())) else "partial"
    for row in iterations + reviews:
        row["models"] = [model for c in row["candidates"] for model in c["models"]]
        row["calls"] = row["candidates"][0]["calls"] if len(row["candidates"]) == 1 else None
        row["errors"] = row["candidates"][0]["errors"] if len(row["candidates"]) == 1 else None
        row["slowest_commands"] = [command for c in row["candidates"] for command in c["slowest_commands"]]
        row["read_completeness"] = read_completeness
        row["usage_completeness"] = usage_completeness(row["usage"])
        row["attribution_completeness"] = "observed" if (
            row["link_status"] == "linked" and (row["kind"] != "iteration"
            or row["task_number"] in {t["number"] for t in plan["tasks"]})) else "partial"
        row["completeness"] = "observed" if (
            row["read_completeness"] == row["usage_completeness"]
            == row["attribution_completeness"] == "observed"
            and all(c["completeness"] == "observed" for c in row["candidates"])) else "partial"
    for task in tasks:
        task["read_completeness"] = read_completeness
        task["usage_completeness"] = usage_completeness(task["usage"])
        task["attribution_completeness"] = "observed" if task["iterations"] and all(
            i["attribution_completeness"] == "observed" for i in task["iterations"]) else "partial"
        if task["attribution_completeness"] != "observed":
            task["completeness"] = "partial"
    phase_totals = {}
    for row in iterations + reviews:
        name = (row.get("phase") or "task execution") if row["kind"] == "iteration" else row["name"]
        phase_usage = metrics(attributed[name])
        phase_windows = [window for window in iterations + reviews
                         if ((window.get("phase") or "task execution") if window["kind"] == "iteration" else window["name"]) == name]
        if coverage_loss or any(window["link_status"] != "linked" for window in phase_windows) or any(
                c["usage_completeness"] == "partial" for window in phase_windows for c in window["candidates"]):
            phase_usage = partial_metrics(phase_usage)
        phase_attribution = "observed" if all(
            window["attribution_completeness"] == "observed" for window in phase_windows) else "partial"
        phase_totals[name] = {**phase_usage, "read_completeness": read_completeness,
                             "usage_completeness": usage_completeness(phase_usage),
                             "attribution_completeness": phase_attribution,
                             "completeness": "observed" if all(
                                 window["completeness"] == "observed" for window in phase_windows) else "partial"}
    planning_usage = metrics(planning_events)
    if coverage_loss or any(s["usage_completeness"] == "partial" for s in planning):
        planning_usage = partial_metrics(planning_usage)
    result = {"run": {key: value for key, value in run.items() if key != "boundaries"},
              "plan": plan, "tasks": tasks, "reviews": reviews,
              "planning": {"sessions": planning, "usage": planning_usage, "lookback_start": lookback,
                           "completeness": "partial" if coverage_loss or any(s["status"] != "available" for s in sources.values()) or any(
                               s["completeness"] == "partial" for s in planning) else "observed" if planning else "unknown"},
              "other_in_run": other,
              "totals": {"by_phase": phase_totals,
                         "by_task": [{key: t[key] for key in (
                             "number", "usage", "completeness", "read_completeness",
                             "usage_completeness", "attribution_completeness")} for t in tasks],
                         "planning": planning_usage, "observed_in_run": total_usage, "unlinked": unlinked_usage,
                         "unlinked_share": unlinked_usage["total"] / total_usage["total"] if
                         total_usage["total"] and unlinked_usage["total"] is not None else None,
                         "read_completeness": read_completeness,
                         "usage_completeness": run_usage_completeness,
                         "attribution_completeness": attribution_completeness,
                         "completeness": completeness},
              "diagnostics": {"sources": sources, "counts": dict(diagnostics),
                              "notes": ["Costs sum timestamped usage events, never thread snapshots.",
                                        "Iteration numbers do not identify plan tasks without explicit evidence.",
                                        "Time/cwd links are approximate; ambiguous candidate costs are not attributed.",
                                        "Late or missing fallback baselines leave delta subtotals known, not complete.",
                                        "Read evidence loss has unknown time/cwd and conservatively limits source coverage."]}}
    result["run"].update(selection)
    result["run"]["duration_seconds"] = duration(run["start"], run["end"])
    result["run"]["completeness"] = completeness
    result["run"].update(read_completeness=read_completeness,
                         usage_completeness=run_usage_completeness,
                         attribution_completeness=attribution_completeness)
    return T.redact_tree(serial(result))


def fmt_md(value):
    value = T.redact_tree(value)
    lines = ["# Plan run retrospective", "## Run", json.dumps(value["run"], ensure_ascii=False, indent=2)]
    # Render the complete schema, not a lossy summary which hides missing metrics.
    for title, key in (("Plan", "plan"), ("Tasks", "tasks"), ("Reviews", "reviews"), ("Planning", "planning"),
                       ("Other in run", "other_in_run"), ("Totals", "totals"), ("Diagnostics", "diagnostics")):
        lines.extend((f"\n## {title}", "```json", json.dumps(value[key], ensure_ascii=False, indent=2), "```"))
    return "\n".join(lines)


def main(argv=None):
    args = parse_args(argv)
    try:
        value = report(args)
    except ValueError as error:
        print("error: " + T.redact(str(error)), file=sys.stderr)
        return 2
    print(json.dumps(value, ensure_ascii=False, indent=2) if args.out == "json" else fmt_md(value))
    return 0


if __name__ == "__main__":
    sys.exit(main())
