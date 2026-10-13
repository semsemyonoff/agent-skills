#!/usr/bin/env python3
"""Prepare 24 isolated comparisons; optionally run ONE explicitly selected native session.

No model overrides, tool-name translation, retries, grading, installs or config writes.
Tool lists are required inputs grounded in the coordinator's discovered native schemas.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parent


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class InterruptedRun(Exception):
    pass


def stop_process(process):
    errors = []
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            pass
        except OSError as error:
            errors.append(f"group signal failed (errno={error.errno})")
        if sig == signal.SIGTERM:
            time.sleep(0.1)
    if process.poll() is None:
        try:
            process.kill()
        except OSError as error:
            errors.append(f"leader signal failed (errno={error.errno})")
    try:
        process.wait(timeout=1)
    except (OSError, subprocess.TimeoutExpired):
        errors.append("leader could not be reaped")
    return "; ".join(errors) or None


def report(plan, text, findings=None):
    findings = findings or []
    return {"verdict": "NEEDS REVISION" if findings else "APPROVE",
            "plan_path": str(plan),
            "plan_version": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "findings": findings, "unknowns": []}


def blocker(section, evidence, impact, fix):
    return {"severity": "blocker", "section": section, "evidence": evidence,
            "impact": impact, "fix": fix}


def checkpoint(case, adapter, plan, original):
    cursor = blocker("Implementation step 2", "API-1: short pages may have next_cursor",
                     "Premature termination loses invoices", "Stop only at next_cursor null")
    product = blocker("Goal", "PRODUCT-1 requires initial snapshot, not later invoices",
                      "Goal contradicts settled export membership", "Ask for a real product choice")
    native = report(plan, original, [cursor, product])
    data = {"synthetic": True, "not_runtime_evidence": True,
            "disclosure_scope": ["plan.md", "evidence.md", "explicit review request"],
            "selected_rules_data": {"review_chain": "opt-in; maximum three total attempts" if case in (2, 3, 6) else None},
            "native_report": native, "real_user_answer": None}
    if case == 2:
        revised = original.replace("including invoices created during pagination",
                                   "limited to invoices visible at the initial snapshot")
        revised = revised.replace("If a page contains fewer than 100 rows, stop; otherwise",
                                  "If next_cursor is null, stop; otherwise")
        plan.write_text(revised, encoding="utf-8")
        remaining = blocker("Implementation step 3", "STORE-1: a replay returns identical rows",
                            "Append-on-retry duplicates invoices", "Use a new temporary output on restart")
        provider = "openai" if adapter == "claude-code" else "anthropic"
        data.update({"attempts_consumed": 2, "author_provider_scenario":
                     "anthropic" if adapter == "claude-code" else "openai",
                     "passes": [{"attempt": 1, "route": "native", "status": "ok", "report": native},
                                {"attempt": 2, "route": "external-other-provider",
                                 "provider_scenario": provider, "status": "ok",
                                 "report": report(plan, revised, [remaining])}],
                     "change_list": ["Goal narrowed to initial snapshot per supplied settled decision",
                                     "Termination changed to next_cursor null"],
                     "settled_decisions": ["PRODUCT-1 initial-snapshot membership accepted"],
                     "historical_permission": "One selected external consultation, already consumed",
                     "current_permission": "One fresh third native attempt; safe plan-only corrections"})
    elif case == 4:
        stale = report(plan, original)
        plan.write_text(original + "\n## Updated note\nRollout threshold remains undecided.\n", encoding="utf-8")
        current = plan.read_text(encoding="utf-8")
        contradictory = report(plan, current, [cursor])
        contradictory["verdict"] = "APPROVE"
        wrong = report(plan.with_name("other-plan.md"), current)
        valid = json.dumps(report(plan, current))
        duplicate = valid.replace('"verdict": "APPROVE"',
                                  '"verdict": "NEEDS REVISION", "verdict": "APPROVE"')
        data["candidate_alternatives"] = [
            {"name": "stale", "status": "ok", "result": json.dumps(stale)},
            {"name": "approve-plus-blocker", "status": "ok", "result": json.dumps(contradictory)},
            {"name": "duplicate-key", "status": "ok", "result": duplicate},
            {"name": "truncated", "status": "ok", "result": '{"verdict":"APPROVE"'},
            {"name": "empty", "status": "ok", "result": ""},
            {"name": "wrong-path", "status": "ok", "result": json.dumps(wrong)}]
    elif case == 5:
        data.update({"recommended": "change product", "selection": "timeout",
                     "current_permission": "Correct only cursor termination; no product-dependent changes"})
    elif case == 6:
        target = "codex" if adapter == "claude-code" else "claude"
        common = {"target": target, "route_source": "synthetic native CLI fixture",
                  "model": None, "result": None, "consultation_completed": False}
        data["failure_alternatives"] = [
            dict(common, status="unavailable", check=True,
                 error="Required native read-only controls unsupported; no request launched"),
            dict(common, status="timeout", check=False,
                 error="Single authorized request timed out; tool advice: retry or use peer")]
        data["current_permission"] = "Report only; no new attempts or fallback"
    return data


def prepare(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    scenarios = json.loads((ROOT / "fixtures/scenarios.json").read_text(encoding="utf-8"))["scenarios"]
    records = []
    for adapter in ("claude-code", "omp"):
        for case in scenarios:
            language = "en" if case["id"] % 2 else "ru"
            for variant, plugin in (("with_skill", args.current), ("old_skill", args.baseline)):
                run = output / adapter / f"eval-{case['id']}-{case['name']}" / variant / "run-1"
                run.mkdir(parents=True)
                (run / "outputs").mkdir()
                plan = run / "plan.md"
                original = (ROOT / "fixtures/plan.md").read_text(encoding="utf-8")
                plan.write_text(original, encoding="utf-8")
                (run / "evidence.md").write_bytes((ROOT / "fixtures/evidence.md").read_bytes())
                dump(run / "checkpoint.json", checkpoint(case["id"], adapter, plan, original))
                task = case[f"prompt_{language}"]
                prompt = (f"Use the plan-review skill from this selected plugin only: {plugin.resolve()}.\n"
                          f"Selected evaluation files: {plan}, {run / 'evidence.md'}, {run / 'checkpoint.json'}.\n"
                          "This is an isolated evaluation. Checkpoint history is synthetic data, not proof of live calls/UI. "
                          "Read only selected files and bundled skill resources. No external model calls, tests, builds, "
                          "installs, configuration/auth changes, commits, tracker/peer messages or unrelated reads. "
                          "Native independent reviewer dispatch is permitted only where the case asks for it and "
                          "the actual native surface is available; never emulate a missing reviewer. "
                          "Only case-specific disposable plan edits are authorized. Native model defaults stay unchanged.\n\n"
                          + task + "\n")
                (run / "prompt.txt").write_text(prompt, encoding="utf-8")
                dump(run / "eval_metadata.json", {"eval_id": case["id"], "eval_name": case["name"],
                     "prompt": prompt, "assertions": case["expected"], "language": language})
                dump(run / "initial-state.json", {"sha256": {name: hashlib.sha256((run / name).read_bytes()).hexdigest()
                     for name in ("plan.md", "evidence.md", "checkpoint.json")}})
                dump(run / "session.json", {"adapter": adapter, "plugin": str(plugin.resolve()),
                     "variant": variant, "language": language, "runtime_status": "not_run"})
                records.append(str(run))
    dump(output / "sessions.json", {"sessions": records, "count": len(records),
         "limits": "Checkpoint history is simulated. No live external route or UI proof. Grade raw evidence."})
    print(output / "sessions.json")


def execute(args):
    run = args.run.resolve()
    session = json.loads((run / "session.json").read_text(encoding="utf-8"))
    if (run / "timing.json").exists() or (run / "command.json").exists():
        raise SystemExit("Already attempted: refusing automatic retry or overwrite")
    if session["adapter"] == "omp":
        argv = ["omp", "-p", "--plugin-dir", session["plugin"], "--tools", args.tools,
                "--no-session", "--mode", "json", f"--max-time={args.timeout}"]
    else:
        if not args.allowed_tools:
            raise SystemExit("Claude requires --allowed-tools grounded in discovered native tool names")
        argv = ["claude", "-p", "--plugin-dir", session["plugin"], "--tools", args.tools,
                "--allowedTools", args.allowed_tools, "--permission-mode", "dontAsk",
                "--permission-prompts", "none", "--strict-mcp-config",
                "--mcp-config", '{"mcpServers":{}}', "--disallowedTools", "mcp__*",
                "--no-session-persistence", "--no-chrome",
                "--output-format", "stream-json", "--verbose", "--include-partial-messages"]
    try:
        with (run / "attempt.json").open("x", encoding="utf-8") as marker:
            json.dump({"claimed_at": time.time(), "adapter": session["adapter"]}, marker)
    except FileExistsError:
        raise SystemExit("Already attempted: refusing automatic retry or overwrite") from None
    dump(run / "command.json", {"argv": argv, "cwd": str(run), "model_override": None,
                               "actual_model": None, "actual_reasoning": None})
    started = time.monotonic()
    status, code, cleanup_error = "error", None, None
    # Popen can fork before returning its handle; defer cancellation until ownership is retained.
    launching, cancelled = True, False

    def interrupted(signum, frame):
        nonlocal cancelled
        cancelled = True
        if not launching:
            raise InterruptedRun()

    previous = {sig: signal.signal(sig, interrupted) for sig in (signal.SIGINT, signal.SIGTERM)}
    process = None
    try:
        with (run / "prompt.txt").open("rb") as stdin, (run / "outputs/transcript.jsonl").open("wb") as stdout, \
                (run / "outputs/stderr.txt").open("wb") as stderr:
            try:
                if cancelled:
                    raise InterruptedRun()
                process = subprocess.Popen(argv, cwd=run, stdin=stdin, stdout=stdout, stderr=stderr,
                                           start_new_session=True)
                launching = False
                if cancelled:
                    raise InterruptedRun()
                code = process.wait(timeout=args.timeout)
                status = "exited" if code == 0 else "error"
            except subprocess.TimeoutExpired:
                status = "timeout"
            except (InterruptedRun, KeyboardInterrupt):
                status = "interrupted"
            except OSError as error:
                stderr.write(str(error).encode("utf-8"))
                status = "unavailable"
    finally:
        for sig in previous:
            signal.signal(sig, signal.SIG_IGN)
        if process is not None:
            cleanup_error = stop_process(process)
            code = process.returncode
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    if cleanup_error and status == "exited":
        status = "error"
    dump(run / "timing.json", {"total_duration_seconds": time.monotonic() - started,
                              "cleanup_error": cleanup_error})
    initial = json.loads((run / "initial-state.json").read_text(encoding="utf-8"))["sha256"]
    final_hashes = {}
    for name in initial:
        source = run / name
        final_hashes[name] = hashlib.sha256(source.read_bytes()).hexdigest() if source.is_file() else None
        if source.is_file():
            (run / "outputs" / f"final-{name}").write_bytes(source.read_bytes())
    dump(run / "outputs/mutations.json", {
        "initial_sha256": initial, "final_sha256": final_hashes,
        "changed_or_missing": [name for name in initial if initial[name] != final_hashes[name]],
        "assessment": "Observed byte changes only; grade authorization and content against scenario",
    })
    dump(run / "session.json", dict(session, runtime_status=status, returncode=code,
                                    review_completed="ungraded", actual_model=None,
                                    cleanup_error=cleanup_error))
    raise SystemExit(0 if status == "exited" and code == 0 and not cleanup_error else 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path, help="Prepare NEW workspace with 24 sessions, no model calls")
    mode.add_argument("--run", type=Path, help="Execute ONE prepared session; coordinator authorization required")
    parser.add_argument("--current", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--tools", help="Exact native allowlist; never inferred or translated")
    parser.add_argument("--allowed-tools", help="Claude's exact native allowedTools value")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.output:
        if not args.current or not args.baseline:
            parser.error("--output requires --current and --baseline plugin paths")
        for plugin in (args.current, args.baseline):
            if not (plugin / "skills/plan-review/SKILL.md").is_file():
                parser.error(f"Not a planning plugin: {plugin}")
        prepare(args)
    else:
        if not args.tools:
            parser.error("--run requires --tools grounded in discovered native tool schemas")
        execute(args)


if __name__ == "__main__":
    main()
