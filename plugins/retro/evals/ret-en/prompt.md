---
max_turns: 15
allowed_tools: [Read, Glob, Grep, Bash, Skill]
---

Retro time: compare my Claude Code and omp sessions for shop-api across both stores since 2000-01-01.
The synthetic Claude config is evals/fixtures/config and the omp session root is
evals/fixtures/omp-sessions, relative to this retro plugin. Include subagent activity, repeated
errors and permission denials. The Codex models here ran inside omp, not native Codex CLI.
Give me one report with source-qualified evidence, ranked proposals and honest token completeness.
Use only those fixtures; do not scan installed histories, fetch pricing or write files.
