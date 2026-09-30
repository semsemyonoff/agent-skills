# agent-skills

Skills for everyday agent work in Claude Code and Codex: running a task through subagents, keeping a
task tracker in order, writing to Redmine without surprises, learning from past sessions. Skills are
written in English and react to prompts in English and Russian. Conventions for contributors:
[AGENTS.md](AGENTS.md).

## Install

```sh
# Claude Code
claude plugin marketplace add semsemyonoff/agent-skills
claude plugin install <plugin>@semsemyonoff

# Codex (only the skills in codex/)
npx skills add semsemyonoff/agent-skills/codex -a codex -g
```

## Plugins

### flow — `orchestrate`

For tasks too big for one pass but small enough for one session. The main session becomes an
orchestrator: a short recon, a plan where every step gets a worker and a model (haiku for search and
mechanical edits, sonnet for implementation by a clear spec, opus for design, risky backend and
review), your confirmation, execution through subagents, verification of each step by the
orchestrator itself (diff, tests, lint), and a short report. Stops only for plan deviations, repeated
failures and outward actions such as push. If the solution is not settled yet, it offers a brainstorm
before planning. Optionally ends with an independent Codex review of the whole change.

`/flow:orchestrate <task>`; add "phase by phase" to stop after each phase.

### vikunja — `vikunja`

Working with [Vikunja](https://vikunja.io) through its MCP server without the usual agent mistakes:
markdown instead of HTML in descriptions, relations created in the wrong direction, duplicates,
tasks closed without being asked. Three scenarios:

- `/vikunja:backlog <idea>` — find the project, check for duplicates, create a task in the project's
  style with a validated HTML description;
- `/vikunja:intake <id>` — read the task, its comments and related tasks, analyse; propose a
  brainstorm on open decisions, or a plan with delegation when the task already settles the solution;
- `/vikunja:report <id>` — write progress or a completion report into linked tasks; close only when
  asked.

### redmine — `redmine`

For comments a manager or client will read. Drafts the reply in Textile in an `<id>-drafts.md` file,
follows a plain house style (first person, no salutation, numbered questions, options with
consequences, estimates as an upper bound), has an independent subagent fact-check every claim, and
sends only after an explicit "send it". `/redmine:reply <issue>`.

### retro — `reflection`

A retrospective over past Claude Code sessions. A script extracts a compact digest from the transcripts
(prompts, tool errors, permission denials, subagent models, token spend); the model groups recurring
requests, finds friction and proposes a few concrete changes: a new skill, a CLAUDE.md rule, a
permission, a routing fix. Ask for "a retro for the week" or «рефлексия по сессиям».

### gdocs — `gdoc-import`

Turns Google Docs/Sheets (for example, the spec linked from a Redmine issue) into normalized markdown
in the repository, with an index README, extracted JSON examples and a list of discrepancies between
documents, so later sessions read the snapshot instead of going back to Drive.

### peer — `peer-chat`

A peer conversation between Claude Code and Codex running side by side in an
agterm split (macOS). The Codex side lives in
`codex/peer-chat`.

## Task flow

```
/vikunja:intake <id>         analysis; open decisions → brainstorm, settled solution → plan
/brainstorm                  design, section by section; can hand over to orchestrate at the end
/flow:orchestrate <task>     recon → plan with models → confirm → execute → verify → report
/vikunja:report <id>         report into the task; closes only when asked
```

`/brainstorm` comes from [umputun/cc-thingz](https://github.com/umputun/cc-thingz).

## Environment

All optional. `flow:orchestrate` offers the Codex review only when the `codex` CLI is installed.

| Variable | Effect |
| --- | --- |
| `VIKUNJA_URL` | base address of the Vikunja instance, used for task links (plain `#N` without it) |
| `CODEX_REVIEW=off` | never offer the review |
| `CODEX_REVIEW_GUARD` | shell command that must exit 0 before the review runs |
| `CODEX_MODEL`, `CODEX_REASONING_EFFORT` | override the model / reasoning effort from the Codex config |
