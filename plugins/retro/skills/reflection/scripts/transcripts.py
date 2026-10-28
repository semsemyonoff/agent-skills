#!/usr/bin/env python3
"""Build a redacted retrospective digest from Claude, omp or native Codex logs.

Read-only, stdlib-only. Select --source claude|omp|both|codex; both retains
Claude + omp semantics. Codex exec is included only with --include-exec.
"""
import argparse
import collections
import datetime as dt
import glob
import hashlib
import json
import math
import os
import re
import sys

TEXT_MAX = 200
METRICS = ("input", "cache_creation", "cache_read", "output", "total")
CORRECTION_RE = re.compile(
    r"(?:^|[\s,.;:!?(\"'])(?:"
    r"нет\b|не так|не то\b|не надо|не нужно|поправь|исправь|опять|снова|"
    r"я же (?:говорил|просил|писал)|зачем|почему ты|не делай|перестань|"
    r"stop\b|wrong\b|don'?t\b|do not\b|no,|nope\b|that'?s not|not what i|"
    r"again\b|i (?:said|told|asked)|why did you|undo\b|revert\b)", re.I)
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
    return s if len(s) <= n else s[:n - 1] + "…"


def obj(value):
    return value if isinstance(value, dict) else {}


def string(value):
    return value if isinstance(value, str) else None


def blocks(value):
    return [b for b in value if isinstance(b, dict)] if isinstance(value, list) else []


def text_content(value):
    if isinstance(value, str):
        return value
    return "\n".join(b["text"] for b in blocks(value)
                     if b.get("type") == "text" and isinstance(b.get("text"), str))


def user_text(msg):
    content = msg.get("content")
    if any(b.get("type") == "tool_result" for b in blocks(content)):
        return "tool_result", ""
    text = text_content(content).strip()
    if not text:
        return "meta", ""
    command = re.search(r"<command-name>\s*(/?[^<\s]+)\s*</command-name>", text)
    if command:
        args = re.search(r"<command-args>(.*?)</command-args>", text, re.S)
        return "command", (command.group(1) + " " + (args.group(1).strip() if args else "")).strip()
    if text.startswith(META_PREFIXES):
        return "meta", ""
    return "prompt", text


def timestamp(value):
    try:
        if isinstance(value, (float, int)) and not isinstance(value, bool):
            return dt.datetime.fromtimestamp(value / 1000, dt.timezone.utc)
        if isinstance(value, str):
            parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.astimezone(dt.timezone.utc)
    except (ValueError, OverflowError, OSError):
        pass
    return None


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", choices=("claude", "omp", "both", "codex"), required=True,
                   help="explicit harness format; both only by request")
    period = p.add_mutually_exclusive_group()
    period.add_argument("--since", help="YYYY-MM-DD (local date, inclusive)")
    period.add_argument("--days", type=int, help="last N days (default 7)")
    p.add_argument("--project", help="substring of recorded cwd or project bucket; filters ALL totals")
    p.add_argument("--config-dir", default=os.environ.get("CLAUDE_CONFIG_DIR") or "~/.claude",
                   help="Claude config root containing projects/ (CLAUDE_CONFIG_DIR or ~/.claude)")
    p.add_argument("--omp-sessions-dir", default="~/.omp/agent/sessions",
                   help="exact omp sessions root; pass active profile/XDG/custom root explicitly")
    p.add_argument("--codex-sessions-dir", default=os.environ.get("CODEX_HOME") or "~/.codex",
                   help="Codex home containing sessions/ and archived_sessions/")
    p.add_argument("--include-exec", action="store_true", help="include Codex exec automation")
    p.add_argument("--include-subagents", action="store_true",
                   help="include child tools/errors/usage; delegated tasks are never user prompts")
    p.add_argument("--include-sdk", action="store_true", help="include Claude sdk-* sessions")
    p.add_argument("--out", choices=("json", "md"), default="md")
    p.add_argument("--max-prompts", type=int, default=80)
    p.add_argument("--max-sessions", type=int, default=25)
    p.add_argument("--max-corrections", type=int, default=30)
    args = p.parse_args(argv)
    if args.days is not None and args.days < 1:
        p.error("--days must be positive")
    for name in ("max_prompts", "max_sessions", "max_corrections"):
        if getattr(args, name) < 0:
            p.error("caps must be nonnegative")
    if args.since:
        try:
            dt.datetime.strptime(args.since, "%Y-%m-%d")
        except ValueError:
            p.error("--since must be YYYY-MM-DD")
    args.config_dir = os.path.abspath(os.path.expanduser(args.config_dir))
    args.omp_sessions_dir = os.path.abspath(os.path.expanduser(args.omp_sessions_dir))
    args.codex_sessions_dir = os.path.abspath(os.path.expanduser(args.codex_sessions_dir))
    return args


def since_time(args):
    if args.since:
        return dt.datetime.strptime(args.since, "%Y-%m-%d").astimezone(dt.timezone.utc)
    return dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=args.days or 7)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def read_records(path, diagnostics):
    records = []
    opener = open
    read_errors = (OSError,)
    if path.endswith(".zst"):
        try:
            from compression import zstd
        except ImportError:
            diagnostics["zst_skipped"] += 1
            return records
        opener = zstd.open
        read_errors += (zstd.ZstdError,)
    try:
        with opener(path, mode="rt", encoding="utf-8", errors="replace") as fh:
            for number, line in enumerate(fh, 1):
                try:
                    record = json.loads(line)
                    if not isinstance(record, dict):
                        raise ValueError("not an object")
                except (ValueError, RecursionError):
                    diagnostics["malformed_records"] += 1
                    continue
                records.append((number, record))
    except read_errors:
        diagnostics["unreadable_files"] += 1
    return records


def load_sessions(args, diagnostics, min_mtime=None):
    sessions = {}
    sources = ("claude", "omp") if args.source == "both" else (args.source,)
    roots = {}
    for source in sources:
        if source == "codex":
            root = os.path.abspath(os.path.expanduser(args.codex_sessions_dir))
        else:
            root = os.path.join(args.config_dir, "projects") if source == "claude" else args.omp_sessions_dir
        roots[source] = root
        if not os.path.isdir(root):
            raise ValueError(f"no {source} transcript directory: {root}")
        pattern = os.path.join(root, "**", "*.jsonl") if source == "omp" else os.path.join(root, "*", "*.jsonl")
        files = glob.glob(pattern, recursive=source == "omp")
        if source == "codex":
            files = [path for directory in ("sessions", "archived_sessions")
                     for suffix in ("jsonl", "jsonl.zst")
                     for path in glob.glob(os.path.join(root, directory, "**", "rollout-*." + suffix), recursive=True)]
        if source == "claude" and args.include_subagents:
            files += glob.glob(os.path.join(root, "*", "*", "subagents", "*.jsonl"))
        for path in sorted(set(files)):
            if min_mtime is not None:
                cutoff = min_mtime.timestamp() if isinstance(min_mtime, dt.datetime) else min_mtime
                try:
                    if os.path.getmtime(path) < cutoff:
                        diagnostics["mtime_skipped"] += 1
                        continue
                except OSError:
                    diagnostics["unreadable_files"] += 1
                    continue
            diagnostics["files_read"] += 1
            records = read_records(path, diagnostics)
            if not records:
                continue
            relative = os.path.relpath(path, root)
            parts = relative.split(os.sep)
            header = {}
            if source == "codex":
                header = next((obj(d.get("payload")) for _, d in records if d.get("type") == "session_meta"), {})
                if not string(header.get("id")):
                    diagnostics["invalid_headers"] += 1
                    continue
                spawn = obj(obj(obj(header.get("source")).get("subagent")).get("thread_spawn"))
                parent_thread_id = string(spawn.get("parent_thread_id"))
                child = bool(parent_thread_id and parent_thread_id.strip())
                sid, parent_file = header["id"], ""
            elif source == "omp":
                logical = [d for _, d in records if d.get("type") != "title"]
                header = logical[0] if logical else {}
                if header.get("type") != "session" or not isinstance(header.get("id"), str):
                    diagnostics["invalid_headers"] += 1
                    continue
                sid = header["id"]
                child = any(d.get("type") == "session_init" for _, d in records)
                # Artifacts live under <parent-file-without-.jsonl>/<agent>.jsonl.
                parent_file = os.path.dirname(path) + ".jsonl"
                if os.path.isfile(parent_file):
                    child = True
            else:
                child = "subagents" in parts
                sid = next((d.get("sessionId") for _, d in records if isinstance(d.get("sessionId"), str)), None)
                sid = (parts[-3] + "/" + os.path.basename(path)[:-6]) if child else (sid or os.path.basename(path)[:-6])
                parent_file = os.path.join(root, *parts[:-3], parts[-3] + ".jsonl") if child else ""
            identity = f"{source}:{sid}"
            sess = sessions.setdefault(identity, {
                "id": identity, "source": source, "raw_id": sid, "paths": [], "records": [],
                "project": parts[0] if len(parts) > 1 else "", "cwd": string(header.get("cwd")) or "",
                "is_subagent": child, "parent_lineage": header.get("parentSession"), "entrypoint": "",
                "artifact_parent": parent_file if parent_file and os.path.isfile(parent_file) else None,
            })
            sess["paths"].append(path)
            sess["records"].extend((path, number, d) for number, d in records)
            sess["is_subagent"] |= child
            if source == "codex":
                lineage = string(header.get("session_id"))
                sess["project"] = os.path.basename(sess["cwd"].rstrip(os.sep))
                # Physical copies may omit metadata; never erase earlier spawn proof.
                for field in ("originator", "cli_version", "model_provider"):
                    value = string(header.get(field))
                    if value is not None and sess.get(field) is None:
                        sess[field] = value
                if lineage is not None and sess.get("root_lineage") is None:
                    sess["root_lineage"] = lineage
                if child:
                    if sess.get("parent_thread_id") is None:
                        sess["parent_thread_id"] = parent_thread_id
                        sess["codex_source"] = header["source"]
                    sess["parent_lineage"] = sess["parent_thread_id"]
                    for field, value in (
                            ("subagent_depth", spawn.get("depth")),
                            ("agent_path", string(spawn.get("agent_path"))),
                            ("agent_nickname", string(spawn.get("agent_nickname"))),
                            ("agent_role", string(spawn.get("agent_role")))):
                        if field == "subagent_depth":
                            value = value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None
                        if value is not None and sess.get(field) is None:
                            sess[field] = value
                elif not sess["is_subagent"] and sess.get("parent_lineage") is None:
                    sess["parent_lineage"] = lineage if lineage != sid else None
                if sess.get("codex_source") is None and header.get("source") is not None:
                    sess["codex_source"] = header["source"]
                sess["partial_history"] = sess.get("partial_history", False) or bool(header.get("history_base"))
                sess["automation"] = (sess.get("automation", False)
                                      or header.get("originator") == "codex_exec"
                                      or header.get("source") == "exec")
            for _, d in records:
                if not sess["cwd"] and isinstance(d.get("cwd"), str):
                    sess["cwd"] = d["cwd"]
                if isinstance(d.get("entrypoint"), str):
                    sess["entrypoint"] = d["entrypoint"]
    return sessions, roots


def normalize(sess, diagnostics=None):
    """Yield stable consumer events; state follows the recorded turn or branch."""
    if sess["source"] == "codex":
        return normalize_codex(sess, diagnostics)
    events = {}
    states = {}
    last_state = {"provider": None, "model": None, "effort": None, "configured_effort": None}
    ordered_records = []
    last_times = {}
    earliest = dt.datetime.min.replace(tzinfo=dt.timezone.utc)
    for path, number, d in sess["records"]:
        recorded_time = timestamp(d.get("timestamp")) or timestamp(obj(d.get("message")).get("timestamp"))
        if recorded_time is not None:
            last_times[path] = recorded_time
        # Untimed appends keep their position after the preceding timed record.
        # Equal timestamps use append position, then payload rather than filename.
        ordered_records.append((recorded_time or last_times.get(path, earliest),
                                number, fingerprint(d), path, d))
    ordered_records.sort(key=lambda record: record[:3])
    for _, number, raw_fingerprint, path, d in ordered_records:
        source, typ = sess["source"], d.get("type")
        msg = obj(d.get("message"))
        ts = timestamp(d.get("timestamp")) or timestamp(msg.get("timestamp"))
        state = dict(states.get(string(d.get("parentId")), last_state if "parentId" not in d else {
            "provider": None, "model": None, "effort": None, "configured_effort": None}))
        if source == "omp":
            if typ == "model_change" and d.get("role", "default") == "default":
                selector = d.get("model")
                if isinstance(selector, str):
                    state["provider"], sep, state["model"] = selector.partition("/")
                    if not sep:
                        state["provider"], state["model"] = None, selector
            if typ == "thinking_level_change":
                state["effort"] = string(d.get("thinkingLevel"))
                state["configured_effort"] = string(d.get("configured", d.get("thinkingLevel")))
            if typ == "session_init":
                selector = d.get("resolvedModel")
                if isinstance(selector, str):
                    state["provider"], sep, state["model"] = selector.partition("/")
                    if not sep:
                        state["provider"], state["model"] = None, selector
                sess["agent"] = string(d.get("agent"))
                sess["model_role"] = string(d.get("modelRole"))
                sess["resolved_model"] = string(d.get("resolvedModel"))
            if isinstance(d.get("id"), str):
                states[d["id"]] = state
            last_state = state
        record_id = d.get("id") if source == "omp" else d.get("uuid")
        fallback = f"{path}:{number}"
        identity = str(record_id or fallback)

        def emit(kind, key, **fields):
            event = {"kind": kind, "key": key, "time": ts, "entry": identity,
                     "fingerprint": raw_fingerprint, **fields}
            # Stable ids merge streaming updates. No-id records retain line identity.
            previous = events.get((kind, key))
            if previous and event["time"] is None:
                event["time"] = previous["time"]
            if previous and kind == "usage":
                event["usage"] = {k: event["usage"].get(k) if event["usage"].get(k) is not None
                                  else previous["usage"].get(k) for k in METRICS}
                for field in ("provider", "model", "effort", "configured_effort"):
                    if event[field] is None:
                        event[field] = previous[field]
                if not event["reported_total"] and previous["reported_total"]:
                    event["usage"]["total"] = previous["usage"]["total"]
                    event["reported_total"] = True
                if not event["reported_total"]:
                    components = [event["usage"][k] for k in METRICS[:-1]]
                    event["usage"]["total"] = sum(components) if all(v is not None for v in components) else None
            if previous and kind == "tool":
                if event["name"] == "?":
                    event["name"] = previous["name"]
                if not event["arguments"]:
                    event["arguments"] = previous["arguments"]
            events[(kind, key)] = event

        role = msg.get("role") if source == "omp" else typ
        if typ == "model_usage" and source == "omp":
            # Standalone calls (e.g. titles) do not necessarily use conversation effort.
            unknown_state = {"provider": None, "model": None, "effort": None, "configured_effort": None}
            emit("usage", identity, **usage_event(d, source, unknown_state), purpose=d.get("purpose"))
            if d.get("errorMessage"):
                emit("error", identity, name="model_usage", text=d["errorMessage"])
            continue
        if source == "omp" and typ != "message":
            continue
        content = msg.get("content")
        if role == "assistant":
            mid = str(msg.get("id") or record_id or fallback)
            model = msg.get("model")
            if not (isinstance(model, str) and model.startswith("<")):
                emit("usage", mid, **usage_event(msg, source, state))
            if msg.get("errorMessage"):
                emit("error", mid, name="model", text=msg["errorMessage"])
            if msg.get("stopReason") == "aborted":
                emit("interrupt", mid)
            for index, block in enumerate(blocks(content)):
                if block.get("type") != ("toolCall" if source == "omp" else "tool_use"):
                    continue
                tid = str(block.get("id") or f"{identity}:block:{index}")
                emit("tool", tid, name=block.get("name") or "?", arguments=obj(block.get("arguments" if source == "omp" else "input")))
        elif role == "toolResult" and source == "omp":
            if msg.get("isError"):
                emit("error", identity, tool_id=msg.get("toolCallId"), name=msg.get("toolName"), text=text_content(content))
        elif role == "user":
            for index, block in enumerate(blocks(content)):
                if block.get("type") == "tool_result" and block.get("is_error"):
                    # Entry id preserves distinct results of the same tool call.
                    emit("error", f"{identity}:block:{index}", tool_id=block.get("tool_use_id"), name=None, text=text_content(block.get("content")))
            kind, text = user_text(msg)
            if text_content(content).startswith("[Request interrupted"):
                emit("interrupt", identity)
            if kind in ("prompt", "command") and not sess["is_subagent"] and not d.get("isSidechain") and not d.get("isMeta"):
                emit("prompt", identity, text=text, command=kind == "command")
    return list(events.values())


def codex_usage(usage):
    """Partition inclusive input into uncached/read/write; never guess missing caches.

    input_tokens includes cached and cache-write input. Subtract both exactly
    once; inconsistent negative partitions are unknown. Total is reported only.
    """
    usage = obj(usage)
    read = numeric(usage.get("cached_input_tokens"))
    write = numeric(usage.get("cache_write_input_tokens"))
    total_input = numeric(usage.get("input_tokens"))
    uncached = (total_input - read - write
                if all(v is not None for v in (total_input, read, write)) else None)
    return {"input": numeric(uncached), "cache_read": read, "cache_creation": write,
            "output": numeric(usage.get("output_tokens")), "total": numeric(usage.get("total_tokens"))}


def codex_status(item):
    """Only explicit stored status/result fields prove success or failure."""
    if isinstance(item, str):
        try:
            item = json.loads(item)
        except ValueError:
            return "unknown"
    item = obj(item)
    code = numeric(item.get("exit_code"))
    if code is not None:
        return "error" if code else "success"
    if isinstance(item.get("exit_code"), int) and not isinstance(item["exit_code"], bool):
        return "error"  # Negative process return codes are failures too.
    for field in ("isError", "is_error"):
        if isinstance(item.get(field), bool):
            return "error" if item[field] else "success"
    status = item.get("status")
    if status in ("failed", "error", "cancelled"):
        return "error"
    result = obj(item.get("result"))
    if "Err" in result or item.get("error"):
        return "error"
    if "Ok" in result:
        nested = codex_status(obj(result["Ok"]))
        return nested if nested != "unknown" else "success"
    nested = codex_status(result) if result else "unknown"
    if nested != "unknown":
        return nested
    return "success" if status in ("completed", "success", "succeeded") else "unknown"


def codex_message_kind(text, automation=False):
    text = text.strip()
    if text.startswith(("# AGENTS.md instructions", "<environment_context>",
                        "<permissions instructions>", *META_PREFIXES)):
        return "injected"
    if re.match(r"Chat from (?:Claude|Codex|omp)(?: \(reply via peer-chat skill\))?:", text):
        return "peer"
    if automation or text.startswith(("<automation", "[Automated", "Automation:")):
        return "automation"
    return "user"


def codex_failure_text(value):
    """Prefer a recorded cause over transport envelopes and command echoes."""
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except ValueError:
            return value.strip()
        return codex_failure_text(decoded) if isinstance(decoded, dict) else value.strip()
    value = obj(value)
    if isinstance(value.get("exit_code"), int):
        output = value.get("stderr") or value.get("aggregated_output") or value.get("output")
        if isinstance(output, str):
            # A failed batch may print successful reads before its diagnostic.
            lines = [line.strip() for line in output.splitlines() if line.strip()]
            diagnostics = [line for line in lines if re.match(
                r"(?:[\w.]*Error:|error:|fatal:|peer-chat:|peer composer|"
                r"(?:rg|cat|bash|zsh|sh|ssh|curl|python3?):)", line, re.I)]
            if diagnostics:
                return diagnostics[-1]
            if value.get("stderr"):
                return codex_failure_text(value["stderr"])
        return "Process exited with code " + str(value["exit_code"]) + "; diagnostic cause unavailable"
    for field in ("error", "Err", "reason", "stderr", "aggregated_output", "message", "output",
                  "result", "Ok", "formatted_output", "stdout"):
        text = codex_failure_text(value.get(field)) if value.get(field) is not None else ""
        if text:
            return text
    text = text_content(value.get("content"))
    if text:
        return text
    if value.get("exit_code") is not None:
        return "Process exited with code " + str(value["exit_code"])
    return ""


def normalize_codex(sess, diagnostics=None):
    diagnostics = diagnostics if diagnostics is not None else collections.Counter()
    sess["diagnostics"] = {}
    events, calls, outputs, completions = [], {}, {}, []
    spawns = {}
    turn_states = {}
    state = {"provider": string(sess.get("model_provider")), "model": None,
             "effort": None, "configured_effort": None}
    # Copies of the same append must not charge the same response twice.
    records = {}
    for path, number, record in sess["records"]:
        records.setdefault(fingerprint(record), (path, number, record))
    ordered = sorted(records.items(), key=lambda pair: (
        timestamp(pair[1][2].get("timestamp")) or dt.datetime.min.replace(tzinfo=dt.timezone.utc),
        pair[1][1], pair[0]))
    has_usage_records = any(d.get("type") == "token_usage_record" for _, (_, _, d) in ordered)
    previous_snapshot, previous_snapshot_time = None, None
    sess["usage_baseline_time"], sess["usage_coverage_end"] = None, None
    sess["thread_total"], sess["usage_source"] = None, None

    def emit(kind, key, record, raw_fingerprint, **fields):
        event = {"kind": kind, "key": key, "time": timestamp(record.get("timestamp")),
                 "entry": key, "fingerprint": raw_fingerprint, **fields}
        events.append(event)
        return event

    def usage_event_at(usage, source, key, record, raw_fingerprint, **coverage):
        payload = obj(record.get("payload"))
        route = dict(turn_states.get(payload.get("turn_id"), state))
        for field, aliases in (("model", ("model",)), ("provider", ("model_provider_id", "model_provider")),
                               ("effort", ("effort", "reasoning_effort"))):
            for alias in aliases:
                if alias in payload:
                    route[field] = string(payload[alias])
                    break
        emit("usage", key, record, raw_fingerprint, usage=codex_usage(usage),
             reported_total=numeric(obj(usage).get("total_tokens")) is not None,
             usage_source=source, **route, **coverage)

    for raw_fingerprint, (path, number, record) in ordered:
        typ, payload = record.get("type"), obj(record.get("payload"))
        key = raw_fingerprint
        if typ == "session_meta":
            emit("meta", key, record, raw_fingerprint)
        elif typ == "turn_context":
            for field in ("model", "effort"):
                state[field] = string(payload.get(field))
            state["configured_effort"] = state["effort"]
            if string(payload.get("turn_id")):
                turn_states[payload["turn_id"]] = dict(state)
            emit("meta", key, record, raw_fingerprint, **state)
        elif typ == "token_usage_record":
            if isinstance(payload.get("usage"), dict):
                usage_event_at(payload["usage"], "token_usage_record", key, record, raw_fingerprint)
            if isinstance(payload.get("thread_token_usage"), dict):
                sess["thread_total"] = codex_usage(payload["thread_token_usage"])
                sess["usage_source"] = "token_usage_record"
        elif typ == "compacted":
            checkpoint = obj(payload.get("latest_token_usage_record"))
            if isinstance(checkpoint.get("thread_token_usage"), dict):
                sess["thread_total"] = codex_usage(checkpoint["thread_token_usage"])
                sess["usage_source"] = "token_usage_record"
        elif typ == "response_item":
            item_type = payload.get("type")
            if item_type == "message":
                text = payload.get("content")
                text = text if isinstance(text, str) else "\n".join(
                    b["text"] for b in blocks(text) if isinstance(b.get("text"), str))
                role = payload.get("role")
                if role == "user" and text.strip() and not sess["is_subagent"]:
                    message_kind = codex_message_kind(text, sess.get("automation", False))
                    emit("prompt" if message_kind == "user" else "message", key, record,
                         raw_fingerprint, text=text, command=False, message_kind=message_kind)
                else:
                    emit("meta", key, record, raw_fingerprint)
            elif item_type in ("function_call", "custom_tool_call"):
                call_id = string(payload.get("call_id"))
                raw = payload.get("arguments") if item_type == "function_call" else payload.get("input")
                arguments = raw
                if isinstance(raw, str) and item_type == "function_call":
                    try:
                        arguments = json.loads(raw)
                    except ValueError:
                        arguments = {}
                event = emit("tool", call_id or key, record, raw_fingerprint,
                             name=payload.get("name") or "?", arguments=obj(arguments),
                             raw_input=raw, status="unknown", **state)
                if call_id:
                    calls[call_id] = event
                if event["name"].split(".")[-1] == "spawn_agent":
                    spawns[call_id or key] = emit("spawn", call_id or key, record, raw_fingerprint,
                                                arguments=obj(arguments))
            elif item_type in ("function_call_output", "custom_tool_call_output"):
                if string(payload.get("call_id")):
                    outputs[payload["call_id"]] = (payload.get("output"), timestamp(record.get("timestamp")))
            elif item_type not in ("reasoning",):
                diagnostics["unknown_codex_records"] += 1
                sess["diagnostics"]["unknown_codex_records"] = sess["diagnostics"].get("unknown_codex_records", 0) + 1
        elif typ == "event_msg":
            event_type = payload.get("type")
            if event_type == "thread_settings_applied":
                settings = obj(payload.get("thread_settings")) or obj(payload.get("settings")) or payload
                for field in ("model", "effort"):
                    alias = "reasoning_effort" if field == "effort" else field
                    if field in settings or alias in settings:
                        state[field] = string(settings.get(field, settings.get(alias)))
                state["configured_effort"] = state["effort"]
                state["provider"] = string(settings.get("model_provider_id")) or state["provider"]
                emit("meta", key, record, raw_fingerprint, **state)
            elif event_type == "token_count":
                snapshot = obj(payload.get("info")).get("total_token_usage")
                if isinstance(snapshot, dict) and not has_usage_records:
                    if previous_snapshot is not None:
                        delta = {}
                        for field in ("input_tokens", "cached_input_tokens", "cache_write_input_tokens",
                                      "output_tokens", "total_tokens"):
                            before, after = numeric(previous_snapshot.get(field)), numeric(snapshot.get(field))
                            delta[field] = numeric(after - before) if before is not None and after is not None else None
                        usage_event_at(delta, "token_count", key, record, raw_fingerprint,
                                       usage_interval_start=previous_snapshot_time)
                    else:
                        first_time = timestamp(record.get("timestamp"))
                        sess["usage_baseline_time"] = first_time.isoformat() if first_time else None
                    snapshot_time = timestamp(record.get("timestamp"))
                    previous_snapshot_time = snapshot_time.isoformat() if snapshot_time else None
                    previous_snapshot = snapshot
                    sess["usage_coverage_end"] = previous_snapshot_time
                    sess["thread_total"], sess["usage_source"] = codex_usage(snapshot), "token_count"
            elif event_type in ("item_completed", "mcp_tool_call_end", "exec_command_end", "patch_apply_end"):
                item = obj(payload.get("item")) or payload
                completions.append((item, payload, key, record, raw_fingerprint))
            elif event_type in ("error", "stream_error"):
                emit("error", key, record, raw_fingerprint, name="session",
                     text=payload.get("message") or payload.get("error") or event_type)
            elif event_type not in ("task_started", "task_complete", "turn_started", "turn_complete",
                                    "user_message", "agent_message", "agent_reasoning",
                                    "context_compacted", "turn_aborted"):
                diagnostics["unknown_codex_records"] += 1
                sess["diagnostics"]["unknown_codex_records"] = sess["diagnostics"].get("unknown_codex_records", 0) + 1
        else:
            diagnostics["unknown_codex_records"] += 1
            sess["diagnostics"]["unknown_codex_records"] = sess["diagnostics"].get("unknown_codex_records", 0) + 1

    result_times = {}

    def record_result_time(call_id, ended):
        """Recorded call-to-result elapsed time is evidence, not process runtime."""
        if ended is None:
            return
        result_times[call_id] = ended
        event = calls[call_id]
        event["result_time"] = ended
        started = event["time"]
        if started is not None and ended >= started:
            event["duration_seconds"] = (ended - started).total_seconds()
            event["duration_source"] = "call_to_result_elapsed"

    for call_id, (output, ended) in outputs.items():
        if call_id in calls:
            calls[call_id]["output"] = output
            calls[call_id]["status"] = codex_status(output)
            record_result_time(call_id, ended)
    spawn_paths = {}
    for call_id, event in spawns.items():
        output = outputs.get(call_id, (None, None))[0]
        if isinstance(output, str):
            try:
                output = json.loads(output)
            except ValueError:
                output = None
        path = string(obj(output).get("task_name"))
        if path:
            spawn_paths[path] = event
    seen_failures = set()
    seen_agents = set()
    for item, payload, key, record, raw_fingerprint in completions:
        call_id = string(item.get("call_id")) or string(payload.get("call_id")) or string(item.get("id"))
        if item.get("type") == "SubAgentActivity" and item.get("kind") == "started":
            agent_id = string(item.get("agent_thread_id")) or string(item.get("agent_path"))
            if agent_id and agent_id not in seen_agents:
                seen_agents.add(agent_id)
                spawn = spawn_paths.get(item.get("agent_path"))
                if spawn is None:
                    spawn = emit("spawn", call_id or key, record, raw_fingerprint, arguments={})
                spawn["observed_model"] = string(item.get("model"))
                spawn["observed_effort"] = string(item.get("reasoning_effort"))
            continue
        status = codex_status(item)
        # Nested exec calls can have no response_item: the persisted completion
        # proves the invocation, but not its start time or parent wrapper call.
        if call_id and call_id not in calls and item.get("type") in ("CommandExecution", "McpToolCall", "FileChange"):
            name = {"CommandExecution": "exec_command", "FileChange": "apply_patch"}.get(
                item["type"], item.get("tool") or "mcp")
            calls[call_id] = emit("tool", call_id, record, raw_fingerprint, name=name,
                                 arguments=obj(item.get("arguments")), status="unknown",
                                 completion_only=True, **state)
        if call_id in calls:
            if status != "unknown":
                calls[call_id]["status"] = status
            if call_id not in result_times and not calls[call_id].get("completion_only"):
                record_result_time(call_id, timestamp(record.get("timestamp")))
            if "output" not in calls[call_id] and item.get("result") is not None:
                calls[call_id]["output"] = item["result"]
            if status == "error":
                cause = codex_failure_text(item)
                if cause:
                    calls[call_id]["failure_text"] = cause
        elif status == "error":
            if call_id and call_id in seen_failures:
                continue
            if call_id:
                seen_failures.add(call_id)
            diagnostics["unjoined_tool_failures"] += 1
            sess["diagnostics"]["unjoined_tool_failures"] = sess["diagnostics"].get("unjoined_tool_failures", 0) + 1
            emit("error", key, record, raw_fingerprint, tool_id=call_id,
                 name=item.get("tool") or item.get("type") or "session",
                 text=codex_failure_text(item) or "Explicit tool failure; cause unavailable")
    for call_id, event in calls.items():
        if event["status"] == "error":
            ended = result_times.get(call_id) or event["time"]
            emit("error", "result:" + call_id, {"timestamp": ended.isoformat() if ended else None},
                 event["fingerprint"], tool_id=call_id, name=event["name"],
                 text=event.get("failure_text") or codex_failure_text(event.get("output"))
                 or "Explicit tool failure; cause unavailable")
    return events


def numeric(value):
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return value if isinstance(value, float) and math.isfinite(value) and value >= 0 else None


def usage_event(msg, source, state):
    usage = obj(msg.get("usage"))
    fields = ("input", "cacheWrite", "cacheRead", "output", "totalTokens") if source == "omp" else (
        "input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens", "total_tokens")
    values = {k: numeric(usage.get(field)) for k, field in zip(METRICS, fields)}
    if values["total"] is None and all(values[k] is not None for k in METRICS[:-1]):
        values["total"] = sum(values[k] for k in METRICS[:-1])
    controls = obj(msg.get("requestControls"))
    return {"usage": values, "reported_total": numeric(usage.get(fields[-1])) is not None,
            "provider": string(msg.get("provider")) or state["provider"],
            "model": string(msg.get("model")) or state["model"],
            "effort": string(msg.get("effort")) or string(controls.get("effort")) or state["effort"],
            "configured_effort": state["configured_effort"]}


def metric_summary(events):
    result = {"messages": len(events), "known": {}, "missing": {}}
    coverage_missing = any(e.get("coverage_complete") is False for e in events)
    for key in METRICS:
        values = [e["usage"][key] for e in events]
        known = [v for v in values if v is not None]
        result[key] = sum(known) if values and len(known) == len(values) and not coverage_missing else None
        result["known"][key] = sum(known) if known else None
        result["missing"][key] = len(values) - len(known)
    result["coverage_missing"] = coverage_missing
    result["completeness"] = ("unknown" if not events else
                              "partial" if coverage_missing or any(result["missing"].values()) else "observed")
    return result


def norm_error(name, text):
    first = next((ln for ln in str(text).splitlines() if ln.strip()), "")
    first = re.sub(r"(?:/[\w.@+-]+){2,}", "<path>", first)
    first = re.sub(r"\d+", "N", first)
    return f"{clip(name)}: {clip(first, 90)}"


def classify_denial(text):
    if "denied by the Claude Code auto mode classifier" in text:
        match = re.search(r"Reason:\s*\[([^\]]+)", text)
        return "classifier: " + clip(match.group(1) if match else "unspecified")
    if "doesn't want to proceed with this tool use" in text or "tool use was rejected" in text:
        return "user rejected"
    if re.search(r"permission (?:denied|denial)|denied by.*(?:policy|approval)|approval (?:denied|rejected)|not allowed by.*policy", text, re.I):
        return "permission denied"
    return None


def top(counter, n):
    return [{"name": clip(k), "count": v} for k, v in counter.most_common(n)]


def digest(args):
    since = since_time(args)
    diagnostics = collections.Counter()
    sessions, roots = load_sessions(args, diagnostics)
    normalized = {sid: normalize(sess, diagnostics) for sid, sess in sessions.items()}
    # Opaque lineage is used only to prove identical copied records, never child status.
    families = {sid: sid for sid in sessions}

    def family(sid):
        while families[sid] != sid:
            sid = families[sid]
        return sid

    paths = {os.path.abspath(path): sid for sid, sess in sessions.items() for path in sess["paths"]}
    for sid, sess in sessions.items():
        parent = sess["artifact_parent"] or sess["parent_lineage"]
        if isinstance(parent, str):
            target = sess["source"] + ":" + parent
            target = target if target in sessions else paths.get(os.path.abspath(parent))
            if target is not None and sessions[target]["source"] != sess["source"]:
                target = None
            if target is None:
                # Sibling forks can share a lineage marker even without their origin file.
                target = sess["source"] + "-lineage:" + parent
                families.setdefault(target, target)
            families[family(sid)] = family(target)
    tools, errors, denials, denial_tools, openers = (collections.Counter() for _ in range(5))
    message_kinds = collections.Counter()
    spawn_observations = collections.Counter()
    routing = collections.Counter()
    usage_groups = collections.defaultdict(list)
    usage_routes = collections.defaultdict(list)
    output_split = {"main": collections.defaultdict(list), "subagents": collections.defaultdict(list)}
    prompts, corrections, session_rows = {}, [], []
    seen_copies = set()
    for sid, sess in sorted(sessions.items(), key=lambda pair: (pair[1]["is_subagent"], pair[0])):
        if sess["is_subagent"] and not args.include_subagents:
            continue
        if sess["source"] == "claude" and not args.include_sdk and sess["entrypoint"].startswith("sdk"):
            continue
        if sess["source"] == "codex" and sess.get("automation") and not getattr(args, "include_exec", False):
            continue
        if args.project and not any(args.project.lower() in str(value).lower() for value in (sess["project"], sess["cwd"])):
            continue
        names = {e["key"]: e["name"] for e in normalized[sid] if e["kind"] == "tool"}
        selected = []
        for event in normalized[sid]:
            if not event["time"]:
                diagnostics["untimed_events"] += 1
                continue
            if event["time"] < since:
                continue
            # Suppress proven family copies, not unrelated sessions with colliding ids.
            if sess["source"] in ("omp", "codex"):
                copy_key = (sess["source"], family(sid), event["kind"], event["key"], event["fingerprint"])
            else:
                copy_key = (sess["source"], family(sid), event["kind"], event["key"])
            if copy_key in seen_copies:
                diagnostics["copied_events_skipped"] += 1
                continue
            seen_copies.add(copy_key)
            if event.get("usage_source") == "token_count":
                baseline = timestamp(sess.get("usage_baseline_time"))
                event = {**event, "coverage_complete": baseline is not None and baseline <= since}
            selected.append(event)
        if not selected:
            continue
        row = {"id": sid, "source": sess["source"], "project": clip(os.path.basename(sess["cwd"]) or sess["project"]),
               "cwd": clip(sess["cwd"]), "is_subagent": sess["is_subagent"],
               "evidence_files": [clip(os.path.relpath(path, roots[sess["source"]])) for path in sess["paths"][:3]],
               "agent": sess.get("agent"), "model_role": sess.get("model_role"), "resolved_model": sess.get("resolved_model"),
               "start": min(e["time"] for e in selected).isoformat(), "end": max(e["time"] for e in selected).isoformat(),
               "prompts": 0, "first_prompt": None, "tools": 0, "errors": 0, "denials": 0, "agents": 0, "interrupts": 0}
        if sess["source"] == "codex":
            row.update({key: sess.get(key) for key in (
                "automation", "originator", "codex_source", "cli_version", "partial_history",
                "parent_lineage", "parent_thread_id", "root_lineage", "subagent_depth",
                "agent_path", "agent_nickname", "agent_role",
                "model_provider", "thread_total", "usage_source",
                "usage_baseline_time", "usage_coverage_end")})
        previous_prompt = False
        session_usage = []
        for event in selected:
            kind = event["kind"]
            if kind in ("prompt", "message") and sess["source"] == "codex":
                message_kinds[event.get("message_kind", "user")] += 1
            if kind == "usage":
                provider, model = event["provider"], event["model"]
                group = f"{sess['source']}:{provider or 'unknown'}/{model or 'unknown'}"
                usage_groups[group].append(event)
                usage_routes[(sess["source"], provider, model, event["effort"], event["configured_effort"])].append(event)
                session_usage.append(event)
                output_split["subagents" if sess["is_subagent"] else "main"][group].append(event)
            elif kind == "tool":
                name = clip(event["name"])
                tools[name] += 1
                row["tools"] += 1
                if name in ("Agent", "Task", "task"):
                    arguments = event["arguments"]
                    tasks = arguments.get("tasks")
                    items = [obj(item) for item in tasks] if isinstance(tasks, list) else [arguments]
                    for item in items:
                        routing[(sess["source"], string(item.get("subagent_type")) or string(item.get("agent")) or "default", string(item.get("model")), string(item.get("effort")))] += 1
                        row["agents"] += 1
            elif kind == "spawn":
                arguments = event["arguments"]
                routing[(sess["source"], string(arguments.get("agent_type")) or "default",
                         string(arguments.get("model")), string(arguments.get("reasoning_effort")))] += 1
                row["agents"] += 1
                if event.get("observed_model") or event.get("observed_effort"):
                    spawn_observations[(event.get("observed_model"), event.get("observed_effort"))] += 1
            elif kind == "error":
                name = event.get("name") or names.get(string(event.get("tool_id")), "?")
                text = str(event["text"])
                denial = classify_denial(text)
                if denial:
                    denials[denial] += 1
                    denial_tools[f"{name} / {denial}"] += 1
                    row["denials"] += 1
                else:
                    errors[norm_error(name, text)] += 1
                    row["errors"] += 1
            elif kind == "interrupt":
                row["interrupts"] += 1
            elif kind == "prompt":
                raw = event["text"]
                clipped = clip(raw)
                # Group complete redacted text, not the clipped prefix (distinct intents survive caps).
                key = redact(" ".join(raw.split())).casefold()
                prompt = prompts.setdefault(key, {"text": clipped, "count": 0, "refs": set()})
                prompt["count"] += 1
                prompt["refs"].add(sid)
                row["prompts"] += 1
                if row["first_prompt"] is None:
                    row["first_prompt"] = clipped
                words = re.sub(r"\W+", " ", clipped.lower()).split()
                if words:
                    openers[" ".join(words[:3])] += 1
                if not event["command"] and previous_prompt and CORRECTION_RE.search(raw[:300]):
                    corrections.append({"session": sid, "entry": event["entry"], "time": event["time"].isoformat(), "text": clipped})
                previous_prompt = True
        row["usage"] = metric_summary(session_usage)
        row["tokens_in_out"] = (sum(row["usage"][k] for k in ("input", "cache_creation", "output"))
                                if all(row["usage"][k] is not None for k in ("input", "cache_creation", "output")) else None)
        session_rows.append(row)
    prompt_rows = sorted(({"text": p["text"], "count": p["count"], "sessions": len(p["refs"]), "session_refs": sorted(p["refs"])[:10]}
                          for p in prompts.values()), key=lambda p: (-p["count"], -p["sessions"], p["text"]))
    session_rows.sort(key=lambda row: (-(row["usage"]["known"]["total"] or 0), row["id"]))
    subagent_calls = [{"source": source, "subagent_type": clip(agent), "model": clip(model) if model else None,
                       "effort": clip(effort) if effort else None, "count": count}
                      for (source, agent, model, effort), count in routing.most_common(20)]
    result = {
        "schema_version": 2, "source": args.source, "period_since_utc": since.isoformat(),
        "roots": {source: redact(root) for source, root in roots.items()}, "diagnostics": dict(diagnostics),
        "files_read": diagnostics["files_read"], "sessions_total": len(session_rows),
        "prompts_total": sum(row["prompts"] for row in session_rows),
        "codex_message_kinds": dict(message_kinds),
        "codex_spawn_observations": [{"model": model, "effort": effort, "count": count}
                                     for (model, effort), count in spawn_observations.items()],
        "note": "heuristic extraction; all event totals obey source/project/period/SDK/subagent filters; null metrics are unavailable, known sums may be partial; all historical branches count, not just active context",
        "projects_top": top(collections.Counter(row["project"] for row in session_rows), 10),
        "tools_top": top(tools, 15), "errors_top": top(errors, 15), "denials": top(denials, 10),
        "denials_by_tool": top(denial_tools, 10), "subagent_calls": subagent_calls,
        "subagent_model_set": sum(count for (_, _, model, _), count in routing.items() if model),
        "subagent_model_unset": sum(count for (_, _, model, _), count in routing.items() if not model),
        "tokens_by_model": {clip(key): metric_summary(values) for key, values in sorted(usage_groups.items())},
        "usage_routes": [{"source": source, "provider": clip(provider) if provider else None,
                          "model": clip(model) if model else None, "effort": clip(effort) if effort else None,
                          "configured_effort": clip(configured) if configured else None, "usage": metric_summary(values)}
                         for (source, provider, model, effort, configured), values in usage_routes.items()],
        "prompt_openers_top": top(openers, 15), "prompts": prompt_rows[:args.max_prompts],
        "prompts_omitted": max(0, len(prompt_rows) - args.max_prompts),
        "correction_candidates": corrections[:args.max_corrections],
        "correction_candidates_omitted": max(0, len(corrections) - args.max_corrections),
        "sessions": session_rows[:args.max_sessions], "sessions_omitted": max(0, len(session_rows) - args.max_sessions),
    }
    if args.include_subagents:
        result["output_tokens_main_vs_subagent"] = {
            kind: {clip(key): metric_summary(values)["output"] for key, values in groups.items()}
            for kind, groups in output_split.items()}
    return redact_tree(result)


def redact_tree(value):
    """Apply final redaction to metadata and evidence refs as well as excerpts."""
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, list):
        return [redact_tree(item) for item in value]
    if isinstance(value, dict):
        return {redact(str(key)): redact_tree(item) for key, item in value.items()}
    return value


def fmt_md(digest_value):
    def metric(value):
        return "unavailable" if value is None else f"{value:,}"

    def counts(values):
        return ", ".join(f"{row['name']} {row['count']}" for row in values) or "-"

    lines = [f"# Transcript digest (since {digest_value['period_since_utc']})",
             f"source: {digest_value['source']} | roots: {json.dumps(digest_value['roots'], ensure_ascii=False)} | files: {digest_value['files_read']} | sessions: {digest_value['sessions_total']} | prompts: {digest_value['prompts_total']}",
             f"_{digest_value['note']}_", "\n## Projects", counts(digest_value["projects_top"])]
    for title, key in (("Tools", "tools_top"), ("Errors (normalized)", "errors_top"),
                       ("Permission denials / rejections", "denials"), ("Denials by tool", "denials_by_tool")):
        lines.extend((f"\n## {title}", counts(digest_value[key])))
    lines.extend(("\n## Subagent routing", f"explicit model: {digest_value['subagent_model_set']} | no explicit model: {digest_value['subagent_model_unset']} (omp resolves roles/policy; Claude may inherit)"))
    for row in digest_value["subagent_calls"]:
        lines.append(f"- {row['count']}x {row['source']}:{row['subagent_type']} model={row['model'] or 'unavailable'} effort={row['effort'] or 'unavailable'}")
    for row in digest_value["codex_spawn_observations"]:
        lines.append(f"- observed Codex spawn: {row['count']}x model={row['model'] or 'unavailable'} effort={row['effort'] or 'unavailable'} (not an explicit override)")
    lines.append("\n## Tokens by source/provider/model")
    for key, usage in digest_value["tokens_by_model"].items():
        lines.append(f"- {key}: " + " | ".join(f"{name} {metric(usage[name])}" for name in METRICS) + f" | calls {usage['messages']} | known {json.dumps(usage['known'])} | missing {json.dumps(usage['missing'])}")
    lines.append("\n## Provider/model/effort observations")
    for row in digest_value["usage_routes"]:
        lines.append(f"- {row['source']}:{row['provider'] or 'unavailable'}/{row['model'] or 'unavailable'} effort={row['effort'] or 'unavailable'} configured={row['configured_effort'] or 'unavailable'} calls={row['usage']['messages']}")
    if "output_tokens_main_vs_subagent" in digest_value:
        lines.append("output main/subagent: " + json.dumps(digest_value["output_tokens_main_vs_subagent"]))
    if digest_value["codex_message_kinds"]:
        lines.append("\nCodex message kinds: " + json.dumps(digest_value["codex_message_kinds"]))
    lines.extend(("\n## Prompt openers", counts(digest_value["prompt_openers_top"]),
                  f"\n## User prompts ({digest_value['prompts_omitted']} omitted)"))
    for row in digest_value["prompts"]:
        lines.append(f"- [{row['count']}x/{row['sessions']}s; {', '.join(row['session_refs'])}] {row['text']}")
    lines.append(f"\n## Correction candidates (heuristic; {digest_value['correction_candidates_omitted']} omitted)")
    for row in digest_value["correction_candidates"]:
        lines.append(f"- {row['session']} entry={row['entry']} {row['time']}: {row['text']}")
    lines.append(f"\n## Sessions ({digest_value['sessions_omitted']} omitted)")
    for row in digest_value["sessions"]:
        lines.append(f"- {row['id']} {row['project']} {row['start']}..{row['end']} subagent={row['is_subagent']} p={row['prompts']} tools={row['tools']} err={row['errors']} deny={row['denials']} tokens={metric(row['usage']['total'])} agent={row['agent']} role={row['model_role']} resolved={row['resolved_model']} | {row['first_prompt']} | files={row['evidence_files']}")
    lines.append("\nRead diagnostics: " + json.dumps(digest_value["diagnostics"]))
    return "\n".join(lines)


def main(argv=None):
    args = parse_args(argv)
    try:
        result = digest(args)
    except ValueError as error:
        print(f"error: {redact(str(error))}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=1) if args.out == "json" else fmt_md(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
