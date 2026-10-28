# Changelog

## 1.3.4

- Separate Codex user, peer, automation and injected messages; correlate tool failures with recorded causes, count spawn activity without duplicate calls, and attribute usage to recorded model/effort settings.

## 1.3.3

- Quote the `reflection` skill description so strict YAML parsers (skills.sh) no longer skip the skill for Codex and omp.

## 1.3.2

- Improve English/Russian plan-task selection and completion evidence; distinguish plan iterations from task IDs and preserve attribution completeness separately from source-read and usage coverage.
- Interpret legacy and custom review markers as logical stages, deriving review source only from uniquely matched journal evidence; document Codex child identification from structured spawn metadata and explicit child inclusion.

## 1.3.1

- Improve plan-run attribution of Claude task execution, natural-language completion evidence, Claude review rounds and external Codex review/evaluation boundaries; keep executor identity, task identity and child activity distinct, preserving unknown attribution where evidence is insufficient.

## 1.3.0

- Add native Codex CLI transcript support and a plan-run review mode for failure diagnosis, planning review and evidence-backed cost improvements.
- Document Codex cache/fallback accounting, cumulative thread totals, source availability versus read coverage, elapsed call/result timing and plan-run attribution limits; expand bilingual Codex and plan-run trigger coverage.
- Clarify measured suffix usage for partial histories and snapshot-interval precision limits for fallback window estimates.

## 1.2.0

- Add an orchestration retrospective: per orchestrated session coordinator usage around the skill load, approximate context-growth attribution, coordinator edits, workers with routing/usage, stall and follow-up signals, a same-call-sequence replay estimate, and redacted plan/report and idle-notice excerpts.

## 1.1.0

- Add an actual omp JSONL reader alongside Claude Code, with required explicit `--source claude|omp|both`, exact storage-root overrides and one source-qualified digest.
- Apply project/period/SDK/subagent filters to every aggregate; deduplicate streaming and proven copied history without merging unrelated events; preserve unknown usage as null with completeness metadata.
- Account for omp camelCase tool events, standalone model usage, branch-specific effort and child routing metadata; keep fork lineage distinct from subagent status.
- Resolve helper paths from the loaded SKILL.md in either harness, refresh bilingual scenario evals, and add invented omp fixtures plus behavioral reader coverage.
- Merge same-session file copies by recorded chronology and append-order ties; retain provider-reported totals through partial streaming updates instead of replacing them with inferred bucket sums.

## 1.0.1

- Refer to the Claude config dir generically instead of named profiles.

## 1.0.0

- Added the reflection skill: deterministic transcript digest (scripts/transcripts.py) plus a guide for mining recurring requests, friction, errors, model routing and token spend.
