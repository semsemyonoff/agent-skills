# Plan-run review

Use this mode for a specific ralphex plan execution, including “why did the plan fail?” and a retrospective after completion. Resolve `<skill-dir>` from the loaded `SKILL.md`; do not depend on the project cwd to locate bundled scripts.

## Run and interpret

Choose a progress log or plan; combine them when both are available. Pass actual session roots
explicitly when non-default or unavailable from the standard locations:

```sh
python3 "<skill-dir>/scripts/plan_run.py" --progress "<progress-file>" --project-root "<project-root>" --out md
python3 "<skill-dir>/scripts/plan_run.py" --plan "<plan-file>" --project-root "<project-root>" --planning-days 3 --out json
```

`--tz <zone>` interprets zoneless progress timestamps (default: system zone). Source overrides are
`--config-dir`, `--omp-sessions-dir` and `--codex-sessions-dir`; `--planning-days` sets planning
lookback (default 3). For JSON output, consult `references/digest-format.md` for the exact report
contract. State unavailable sources and diagnostic counts; missing data is unknown, not zero or
success. Executor/review/planning links are approximate: time windows and recorded cwd/path evidence
do not prove causality. With partial Codex history, non-null totals measure only the loaded suffix;
read, usage and attribution completeness are distinct, and full-window cost is not proven.
Fallback token-count estimates follow snapshot intervals and can include
pre-window work or omit work after the last in-window snapshot. A Codex session's `thread_total`
may include work before this run; window cost uses usage events, not that cumulative total.

### Task identity and review markers

Progress may identify task selection/completion in English or Russian. Examples include `Selected
Task N`, `Выбран Task N`/`Выбрана Task N`, and affirmative completions such as `Task N completed`,
`Task N выполнена`, `Task N выполнен` or `Task N завершена`. Completion evidence takes precedence
over an earlier incorrect selection or a started/in-progress reference; conflicting completed task
numbers remain ambiguous. A plan iteration number is not a task number: when no explicit task number
is identified, leave it unlinked rather than borrowing the iteration number.

Review marker text identifies a logical stage, not its actor or model. Legacy labels such as
`claude review`, `claude evaluating codex findings`, external Codex review markers, and custom
external-review/review-iteration markers describe review/evaluation boundaries regardless of which
tool actually ran them. The report's `review_label` preserves the marker label; `review_provider`
comes only from a uniquely matched primary session's recorded source, and is null when that source
cannot be established uniquely. Round numbers come from round markers, not task or iteration IDs.
Do not infer the harness or model from marker wording. Generic `starting <name> phase` boundaries
remain valid.

Review-link completeness is separate from read coverage. `read_completeness` describes whether
source data was fully read; `usage_completeness` describes measured usage-event coverage; and
`attribution_completeness` describes whether required windows are uniquely linked and task iterations
explicitly identified. A readable source or measured root usage does not prove complete attribution
or full-run cost. Keep observed subtotals and unlinked activity visible; do not represent unknown
usage as zero.

Native Codex child attribution requires structured `session_meta.payload.source.subagent.thread_spawn`
metadata with a nonempty `parent_thread_id`. Such a session is a child, with its immediate parent
recorded explicitly; `session_id` lineage, `history_base`, or opaque fork relationships alone do not
prove child status. Missing or malformed metadata remains unknown, and nickname or role must not be
inferred. Child activity is excluded by default; `--include-subagents` includes its activity, but
does not turn child prompts into user prompts or roll child usage into root/task usage. Unique child
usage can therefore remain unlinked.

External review accounting depends on the matched session and recorded usage, not the marker label.
If an external runner omits usage metadata (for example, a custom invocation using `--no-session`),
its cost is unknown, not zero; do not recommend changing remote configuration unless asked.

Links remain approximate: timing, cwd/path evidence, and a review marker do not prove causality.
With partial Codex history, non-null totals measure only the loaded suffix, not proven full-window
cost. Fallback token-count estimates follow snapshot intervals and can include pre-window work or
omit work after the last in-window snapshot. A Codex session's `thread_total` may include work before
this run; window cost uses usage events, not that cumulative total. Explicitly pass a moved plan with
`--plan <path>`; plan autodiscovery is not promised.
Never add the thread total to window usage.
## Diagnose a failed run

1. Locate the failed task and the failure excerpt; quote only a short, redacted evidence snippet.
2. Classify the likely cause: manual step/permission, flaky dependency, unavailable tool, plan defect, bug caught by a check, or executor infrastructure. Separate evidence from inference and mark ambiguous causes uncertain.
3. Explain the concrete fix needed before a restart. Inspect the printed resume command as evidence and describe it; **never execute ralphex or its resume command**.
4. Scan the remaining tasks for the same cause or missing prerequisite. Distinguish a confirmed repeated defect from a risk to check.
5. If the run restarted, compare before/after evidence and say whether the apparent fix addressed the diagnosed cause.

For successful runs, do not invent a failure; report the terminal outcome and still note unresolved or unlinked evidence.

## Review the plan and execution

Assess review rounds and their findings: which defect was caught, which could reasonably have been caught earlier, and whether review changed the plan. Compare fixes or plan edits made after execution began with the original plan. Identify risks only when supported by the plan, progress log, or linked sessions.

Seek cost reductions that preserve coverage and quality. Consider plan size relative to iterations, expensive or redundant Validation Commands, repeated task iterations, and review phases with no findings. Explain evidence and trade-offs; do not recommend deleting a check solely because it costs time.

## Proposals, not edits

Offer 3–5 ranked, evidence-backed proposals across relevant targets: planning rules, the planning/plan-review/orchestrate skills, the project environment, or ralphex configuration. For each, state the observation, the proposed change and target, expected benefit, and quality/safety trade-off. Do not edit files, configuration, or workflows unless the user explicitly asks.