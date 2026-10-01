# Changelog

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
