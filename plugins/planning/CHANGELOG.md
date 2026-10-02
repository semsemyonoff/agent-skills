# Changelog

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
