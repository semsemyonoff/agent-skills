---
name: reflection
description: Retrospective over past Claude Code session transcripts of the current profile - finds recurring requests that should become skills/commands, repeated corrections that should become CLAUDE.md rules, tool errors, permission denials, wasted effort, subagent model routing and token spend. Use for "reflect on my sessions", "retro for the week", "analyze transcripts", "what can I automate", "what do I keep repeating", "review how I use Claude", «проанализируй сессии», «проанализируй транскрипты», «рефлексия», «ретро за неделю», «что можно автоматизировать», «что я постоянно повторяю», «где я теряю время с Claude». Not for summarizing a single current conversation or for cost dashboards alone (use ccusage).
---

# Reflection over session transcripts

Goal: turn what already happened in past sessions into a few concrete, evidence-backed changes to the
user's setup (skills, commands, CLAUDE.md rules, permissions, model routing). Reply in the user's
language. Transcripts contain secrets: never quote credentials, tokens or private data, even if a
redaction slipped through; paraphrase instead.

## 1. Scope

- Period: default the last 7 days. If the user gave a period ("за месяц", "since Monday"), use it
  (`--days N` or `--since YYYY-MM-DD`). If the request is vague about both period and project, state
  the default in one line and proceed; ask only when the choice changes the result materially.
- Project: default all projects. Use `--project <substring>` when the user names one.
- Profile: the script reads `${CLAUDE_CONFIG_DIR:-~/.claude}/projects/`, so it analyzes whichever
  profile this session runs in. To look at the other profile, pass `--config-dir` (personal `~/.claude`,
  work `~/.claude-work`) and say which one you read.

## 2. Extract

```sh
python3 "${CLAUDE_SKILL_DIR}/scripts/transcripts.py" --days 7
```

Options: `--since`, `--days`, `--project`, `--config-dir`, `--include-subagents` (adds subagent tokens,
tools and errors; slower), `--include-sdk` (non-interactive sdk sessions are skipped by default as
automation noise), `--out json|md` (md default, compact), `--max-prompts`, `--max-sessions`.
The digest is already redacted, truncated and capped; never open raw `.jsonl` files to "get more" -
if a lead needs detail, grep a single session by its id prefix and read a few lines with `jq`/`python`.

If the digest shows 0 sessions, check the period, project filter and `--config-dir` before concluding
anything. Details of what the script counts and its blind spots: `references/digest-format.md`.

## 3. Analyze

Read `sections/analysis.md` and work through it: recurring intents, friction, errors and denials,
routing and spend. Rules that keep the analysis honest:

- The digest is a heuristic sample, not ground truth. Correction candidates are regex hits: read each
  and drop the ones that are just "no" answers to a question or approvals with a side note.
- Every finding needs evidence: a short quote (under ~15 words) plus a session id prefix, or a count.
  No evidence, no finding.
- Before proposing a new skill, check what already exists (installed skills and plugins, the
  user's CLAUDE.md, this repo's skills if you are in it). Say "already covered by X, but not triggered
  because ..." when that is the real problem - a description fix beats a new skill.
- Distinguish one-off tasks from recurring ones: a prompt pattern needs 3+ occurrences across 2+
  sessions before it is a skill candidate.

## 4. Report

Structure (in the user's language, compact, no filler):

1. Scope line: period, profile, project filter, sessions and prompts analyzed.
2. Recurring intents: table with intent, count, verdict (existing skill covers / new skill candidate /
   CLAUDE.md rule / ignore).
3. Friction with evidence: quote + session id prefix, and the rule or fix that would prevent it.
4. Errors and denials: what repeats, what a permission rule or hook would remove.
5. Routing and spend: subagent model mix (set vs inherited), tokens per model, obvious waste. For
   dollar figures suggest `npx ccusage` (optional; do not run it without asking, it fetches pricing).
6. 3-7 proposals ranked by value/effort. Each: what to create or change, where it lives, the
   evidence that justifies it, rough effort.

Then offer to save the report (for example `docs/retro/YYYY-MM-DD.md` in a repo the user picks) or to
implement a proposal. Do not write files or edit CLAUDE.md/skills unasked; writes happen only after
the user confirms.

## Files

- `sections/analysis.md` - how to group prompts, judge friction, read errors, denials and routing.
- `references/digest-format.md` - digest fields, transcript format notes, known blind spots.
- `scripts/transcripts.py` - the extractor; `scripts/test_transcripts.py` - its unit tests.
