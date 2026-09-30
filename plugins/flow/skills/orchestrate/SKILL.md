---
name: orchestrate
description: Run a task as orchestrator and reviewer - recon, a plan that picks haiku/sonnet/opus per step, user confirmation, execution through subagents with the model always set explicitly, verification by the main session itself, short report. Use ONLY when the user explicitly asks for this mode - /flow:orchestrate, "orchestrate this", "you are the orchestrator", "delegate to subagents", "use subagents by complexity", "subagents on haiku/sonnet/opus", «ты оркестратор», «ты оркестратор и проверяющий», «делегируй на сабагентов», «раздай сабагентам», «сабагенты по сложности», «сабагенты на хайку/сонет/опус», or when "Orchestrate" is picked as the next step after a brainstorm (use the validated design as input). Do not trigger just because a task is big, and not for "workflow" or "ultracode" requests (that is the Workflow tool).
argument-hint: "[task]"
---

# Orchestrate

The main session becomes the orchestrator: it plans, delegates each step to a subagent (a worker) with
an explicitly chosen model, checks the workers' output itself and reports. It does not write large
chunks of code; it decides and verifies. Reply in the user's language.

If the task is 1-2 steps, say in one line that doing it directly is cheaper, and do it.

## Harness facts

- **Always pass `model`** (`haiku`, `sonnet`, `opus`) in every Agent call. Without it the worker
  inherits the session model, which is usually opus, silently. `subagent_type: "fork"` ignores
  `model`, so never use forks as workers. Use a read-only type (for example `Explore`) for pure
  search, `general-purpose` for anything that edits.
- **Workers are leaves.** Subagents cannot spawn subagents, so each brief is one self-contained task;
  any fan-out is the orchestrator's job.
- **Agents run in the background** and notify on completion. Do not poll, sleep or read their output
  files; do other independent work or wait for the notification.
- **The user does not see worker reports.** Relay what matters in your own words.
- **Never claim results of a worker that has not reported.** If asked mid-run, say it is still running.

## Phases

### 1. Recon

Gather facts before planning. Cheap workers (haiku, or sonnet when reading needs interpretation) run
in parallel and return conclusions with `path:line` references, not file dumps: the orchestrator's
context is the scarce resource. Threshold: 1-2 targeted reads or a couple-line edit, do it yourself;
broad sweeps, bulk implementation, independent verification go to a worker.

### 2. Plan

A plan comes only after the solution is settled. If recon shows open design decisions (several ways
to do it, unclear scope, no agreed approach) and no brainstorm or design discussion preceded this
run, stop after recon: list the open decisions and offer a brainstorm with AskUserQuestion (buttons:
"Brainstorm (Recommended)" / "Plan anyway"). Plan directly only
when the approach is already decided — in the conversation, a design, or the task itself.

Present the plan as a table (template in `references/templates.md`): step, worker + model, input,
done-criterion, dependencies. Mark independent steps as parallel. Pick models by
`references/routing.md`; when you deviate from it, give a one-line reason in the row. Risky parts
(migrations, concurrency, security, data integrity, public API changes) get an explicit opus review
step after the implementing step.

Parallel steps that edit code must not touch the same files; if they would, make them sequential.

### 3. Confirmation

Ask with AskUserQuestion, not a text question: "Start" / "Start phase by phase" / "Change the plan"
(free-text answers still come through "Other"). Apply plan changes before starting, and show the
changed rows if the edit was more than cosmetic.

### 4. Execution

Each worker gets a self-contained brief built from `references/brief.md`: the worker does not see
this conversation. Launch independent steps together (several Agent calls in one message); start a
dependent step only after its inputs have reported and passed verification.

Default: run the whole confirmed plan autonomously to the report. Phase-by-phase mode only when the
user explicitly asks («по фазам», «пофазно», "step by step", "phase by phase"): after each phase stop
with a short summary and wait for the go-ahead.

### 5. Verification

Done by the orchestrator, never delegated to the worker that did the step:

- **Code:** read the diff yourself (`git diff`, `git status`) and run the project's tests, lint and
  build yourself. A worker's "tests pass" is a claim, not evidence.
- **Research and analysis:** spot-check 1-2 key claims against the source (open the file, run the
  query). If a claim does not hold, treat the whole report as suspect.
- **Boundaries:** check the worker touched only what its brief allowed (files outside scope, commits,
  external writes). Work outside the brief fails the step, even if it looks useful.
- **Review steps:** an opus review worker's findings are input, not a verdict; decide on each yourself.

On failure:

1. Retry once on the same model with a sharper brief: name what was wrong and what "done" means.
2. Second failure: escalate one model up (haiku to sonnet, sonnet to opus) and note it for the report.
3. Escalation fails, or opus already failed twice: stop and ask the user.

### 6. Report

In the user's language, short, using the template in `references/templates.md`: what was done (2-5
lines); table of steps (worker, model, result, escalations); deviations from the plan and why; what
was not verified; what remains. No retelling of the process.

## When to stop and ask

The confirmed plan is the mandate. Outside it, stop only for:

- a deviation from the confirmed plan (new step, changed scope, different approach);
- a failure after escalation;
- any outward-facing or irreversible action: push, writes to trackers or forges, deletions, sending
  messages. These always need the user, even if the plan implied them.

Workers never commit or push; the orchestrator commits only if the user asked for it.

## References

- `references/routing.md` - which model for which work, and how to justify a deviation.
- `references/brief.md` - worker brief template with a filled-in example.
- `references/templates.md` - plan table and final report templates.
