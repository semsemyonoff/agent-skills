# Changelog

## 1.5.0

- Preserve compact stop/resume state, settled decisions and permission provenance in the existing plan; handoff does not start execution or grant new permissions.
- Update the self-contained omp question adapters for semantic HTML forms, explicit answers and text fallback while preserving Claude and opt-in independent plan review. Add bilingual behavioral handoff and question scenarios.

## 1.4.0

- Plan format separates Executor acceptance (proved by the run) from Owner acceptance after run (kept as stated, never walked by a task) and adds optional Run prerequisites with read-only checks; the final task verifies only Executor acceptance. Plan-review blocks unreachable executor criteria, tasks walking owner acceptance, weakened owner requirements and undeclared live-state dependencies; a live-state prerequisite must be an exact read-only check through the scenario's interface and role, rerun by the first dependent task; four eval cases added (three blockers, one negative control).

## 1.3.1

- Plan-review `consult.py` no longer pins codex-cli 0.162.1: any Codex build is accepted when `codex features list` confirms every disabled feature and each config key is recognized by a wrongly typed probe (ported from peer `ask-other`).

## 1.3.0

- Rules resolver: optional `AGENT_SKILLS_PROFILE` (`[a-z0-9-]+`) makes the user layer read `<name>-rules.<profile>.md` instead of the common file, with no fallback; the JSON result gains a `profile` field.

## 1.2.0

- Plan-review chain: when the task was discussed with a peer of the other provider through peer-chat before planning, stage 2 is reviewed by that peer instead of a fresh `consult.py` CLI. The peer reads an exact snapshot packet (`review_state.py packet`), replies through peer-chat with the packet's request id and whitespace-safe canonical JSON and is reported as review with prior design context, not independent coverage. An unavailable peer stops the stage without falling back to consult.

## 1.1.1

- Brainstorm writes native ask questions, options and handoffs in the user's language, not the language of the skill, its handoff or the task.

## 1.1.0 (Unreleased)

- Add an opt-in plan-review driver section: native independent review, one other-provider consultation, then conditional fresh native re-review, with at most three attempts and no retry/vote/recursive approval loop. Default remains one independent native pass.
- Bind canonical verdicts to exact UTF-8 plan snapshots and validate schema/current path/version before accepting reports or fixing; stop on unavailable, failed, empty, invalid or stale results and never approve unseen corrections.
- Bundle a self-contained native external adapter, preserving native routing/auth and documenting trusted deployment limits, read-only tool boundaries and truthful unavailable routes without another skill's runtime dependency.
- Preserve explicit no-edits/no-external restrictions, real disclosure/choice approval, target-only safe corrections, read-only workers and the conditional shell inspection fallback through planning handoffs.
- Add bilingual behavioral/trigger evals and isolated baseline comparison tooling; atomically consume each session attempt and stop owned CLI process groups on timeout or cancellation. Regression tests cover finite-file stdin, stale verdicts, cancellation and duplicate attempts.

## 1.0.3 (Unreleased)

- Let the plan reviewer inspect files through a narrow read-only shell fallback when the harness has no native search or listing tool (Claude Code exposes Bash instead of Grep/Glob); writes, helpers, tests and network stay forbidden, and the fallback is reported in the review limits.

## 1.0.2 (Unreleased)

- Keep one separate plan reviewer read-only; after its actual report, the driver checks evidence and automatically corrects only the target plan for unambiguous task/decision/rule-consistent findings, unless explicit review-only/no-edits was requested.
- Require 2–5 concrete options, tradeoffs, one recommendation and a real user answer for choices/conflicts/ambiguity or agreed scope/route/budget changes; use native question buttons when exposed, otherwise wait in text. Independent safe fixes may precede the question; dependent findings stay unapplied without consent.
- Carry correction permissions through planning handoffs and native guidance; re-read changed plan text locally, without gates, implementation or a second automatic review, and report the original verdict separately from applied changes and unresolved choices.

## 1.0.1 (Unreleased)

- Keep project-specific execution policy exclusively in custom rules; shared planning/review resources apply only loaded constraints whose rule-defined conditions are confirmed, without inferring applicability from project names or presenting unknowns as checked.

## 1.0.0 (Unreleased)

- Adapt upstream umputun/cc-thingz brainstorm, planning and plan-review into three self-contained portable skill directories, preserving MIT copyright/license and existing upstream Claude installations.
- Load first-nonempty project .agents/.claude or XDG user rules without merging, embedding personal rules or requiring Claude environment variables; include small read-only resolvers and deterministic precedence/empty/missing/XDG tests.
- Carry validated decisions into selected planning/orchestration routes without repeated design; create compact plans with real targeted/final verification and conditional loaded-rule constraints, never automatic execution or commits.
- Add one-pass independent read-only plan review with explicit driver/worker branches and optional native omp plan-review resource using @plan_review, read/grep/glob and no spawns; no exec, auto-review loops, model switching or installs.
