# Orchestration retrospective

Use when the user asks how orchestration (`flow:orchestrate` or another delegation skill) performed:
whether it saved context or tokens, kept the coordinator thin, routed workers sensibly, and caught
problems. It complements the general digest; it does not replace reading the `flow` skill itself.

## Run

Same scope rules and roots as `SKILL.md` §1–2; the helper reuses that discovery and redaction:

```sh
python3 "<skill-dir>/scripts/orchestration.py" --source claude --days 14 --config-dir "<root>"
```

Options: `--skill <regex>` (default `orchestrate`), `--project`, `--since`/`--days`, `--stall-minutes 20`,
`--large-context 150000`, `--max-sessions 15`, `--out json|md`. Only sessions that loaded the skill are
included; their workers are read automatically. Fix the measured version before judging behaviour: note
which skill copy/version the sessions loaded (it changes between sessions) and compare like with like.

## What the numbers mean and do not mean

- `coordinator.before/after`: model calls, processed tokens (input + cache + output), peak context and,
  for omp, recorded cost. Before/after is split at the first skill load, not at plan approval.
- `growth_share_pct`: each context delta is split equally across the tools of that call and weighted by
  how many later calls re-read it. It is an **approximate attribution**: every ordinary read counts as
  recon, git diff/show as ship. Use it to find where the coordinator's context goes, not as cost shares.
- `replay_tokens_estimate`: the same worker call sequence replayed on the coordinator context at spawn.
  Say "with the same call sequence the estimate is N× lower", never "delegation saved N tokens".
- Session totals with and without the skill differ in task and length; they do not prove or disprove an
  overall saving. Fewer tokens with more calls or a higher price is not a money saving.
- `stall_candidate`: a gap inside the worker journal (waiting for the parent's next message excluded) or
  an interrupted end. A long test run also creates a gap; confirm from the worker's last tool before
  calling it a hang.
- `large_context` uses an experimental guide (150k by default), never a replacement verdict.
- `first_table_excerpt`/`last_table_excerpt` usually hold the plan and the report; `idle_notices` are
  coordinator texts written while workers ran, followed by ≥2 idle minutes. Both are redacted excerpts.

## What to check

1. **Coordinator role.** Edits after the skill load and their files: integration/e2e/browser done inline
   by the coordinator versus a worker. Recon share: does the coordinator pre-read every slice's code?
   Language/domain skills loaded by the coordinator rather than named in briefs.
2. **Plan quality** from the first table excerpt: owner of integration, verification owner (gates and
   browser named separately), confirmed browser capability of a delegated checker, routing per slice.
   A missing owner is a plan defect even when checks were blocked.
3. **Routing.** Workers' agents, models and thinking against the assessed complexity; how often light
   profiles were used; reviewers' share of worker tokens and rounds per small change.
4. **Waiting and recovery.** Idle notices naming workers, start times and the status surface; stall
   candidates and how long the coordinator stayed idle; reused workers whose context grew large.
5. **Value.** Review findings accepted (read the last table/report), defects caught before shipping.

Report per finding with the session ref and the number; separate measured facts from interpretation.
Proposals go to the skill that owns the behaviour (`flow:orchestrate` text, its adapters or scripts),
ranked by evidence across sessions; one session is a hypothesis, not a rule change.
