# agent-skills

Skills for everyday agent work in Claude Code, omp and native Codex CLI: running a task through
subagents, keeping a task tracker in order, writing to Redmine without surprises, learning from past
sessions. Skills are
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

For tasks too big for one pass but small enough for one session. One shared workflow for Claude Code
and omp: recon → plan → confirmation → execution → independent verification → report. Plan workers
by category (research, mechanics, implementation, review), with models resolved by each harness's
native configuration rather than a shared model ladder. Execute the approved plan autonomously;
phase-by-phase only on request. Scope changes and external actions require explicit permission.
Open design decisions lead to a brainstorm before planning. Missing reviewer or tool capabilities
are reported, not replaced by a pretend successful check. Claude Code can optionally use a read-only
Codex CLI second opinion; omp uses an available independent reviewer and only an explicitly
approved second-opinion checkpoint.

`/flow:orchestrate <task>`; add "phase by phase" to stop after each phase.

In omp, add this repository's `plugins/flow/skills` to native `skills.customDirectories`, then
invoke `/skill:orchestrate`. Add `plugins/retro/skills` for `/skill:reflection`; restart or reload
skills after changing that configuration. Each skill resolves bundled files relative to its loaded
`SKILL.md`. Loading a skill does not install agent definitions, select models or change permissions.
Keep routing in the native harness settings; no shared `orchestration.yml` is needed.

See [flow native setup](plugins/flow/skills/orchestrate/references/native-setup.md) for Claude
Code's agent-definition/model-selection mechanism and omp's existing
`task.agentModelOverrides` / `modelRoles` routing. Optional second opinions need an explicit
checkpoint; a failed worker never authorizes a hidden provider or model switch.

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

The Vikunja skill also works in omp with any supported model provider. Point omp's
`skills.customDirectories` at this repository's `plugins/vikunja/skills` directory (the parent of
`vikunja/`), then invoke `/skill:vikunja` or use a natural prompt. This custom-directory entry
overrides older same-named installed copies. The namespaced commands above are Claude Code aliases.
Connect the Vikunja MCP separately using the harness's configuration, then reload MCP or restart
the session. The skill discovers actual tool names/schemas and supports omp's `xd://` devices;
Claude Code's deferred ToolSearch remains supported. Bundled references and the offline Python 3
HTML validator resolve relative to the loaded `SKILL.md`, with no required Claude environment
variables. Set `VIKUNJA_URL` for clickable task links; no tokens belong in skill files.

### redmine — `redmine`

For work that lives in Redmine issues. Two scenarios:

- `/redmine:intake <issue>` — read the issue with its journal, related issues and attachments, and
  summarise: what is asked, what was already decided, who waits for what, open points. Read-only; ends
  with a choice of brainstorm, reply or plan.
- `/redmine:reply <issue>` — for comments a manager or client will read: a Textile draft in an
  `<id>-drafts.md` file, a plain house style (first person, no salutation, numbered questions, options with
  consequences, estimates as an upper bound), an independent fact-check of every claim, and sending only
  after an explicit "send it".

Project specifics — where specs and documents live, what may be checked on a stand, where drafts go — are
described by the project itself in `.claude/redmine-rules.md`.

### retro — `reflection`

A retrospective over explicitly selected Claude Code sessions, omp sessions, or both. A script
normalizes a compact, redacted digest (RU/EN prompts, tool errors, permission denials, provider/model
and effort where recorded, token usage). The skill defaults to the current harness, not the current
model's name. Project/time filters apply to aggregate totals; missing metrics remain unknown.
The model groups recurring requests, finds friction and proposes concrete changes to skills,
project rules, permissions or native routing. Ask for "a retro for the week" or «рефлексия по сессиям».
Native Codex CLI transcripts are outside this reader's scope; Codex running inside omp uses omp format.

The extractor requires `--source claude|omp|both`; there is no implicit scan of both stores:

```sh
python3 plugins/retro/skills/reflection/scripts/transcripts.py --source omp --days 7
python3 plugins/retro/skills/reflection/scripts/transcripts.py --source both --days 7 --include-subagents --out json
```

Use `--config-dir` for another Claude configuration and `--omp-sessions-dir` for the exact omp
sessions root, including profile/custom roots. See the [digest contract](plugins/retro/skills/reflection/references/digest-format.md)
for normalized evidence references, deduplication, partial metric accounting and reader limits.

### gdocs — `gdoc-import`

Turns Google Docs/Sheets (for example, the spec linked from a Redmine issue) into normalized markdown
in the repository, with an index README, extracted JSON examples and a list of discrepancies between
documents, so later sessions read the snapshot instead of going back to Drive.

### peer — `peer-chat`

A peer conversation between Claude Code and Codex running side by side in a
kitty tab (Linux, remote control enabled) or an agterm split (macOS). The Codex side lives in
`codex/peer-chat`; in kitty that Codex needs `-c sandbox_workspace_write.network_access=true`
to reach kitty's socket.

## Task flow

```
/vikunja:intake <id>         analysis; open decisions → brainstorm, settled solution → plan
/brainstorm                  design, section by section; can hand over to orchestrate at the end
/flow:orchestrate <task>     recon → plan with native agents → confirm → execute → verify → report
/vikunja:report <id>         report into the task; closes only when asked
```

`/brainstorm` comes from [umputun/cc-thingz](https://github.com/umputun/cc-thingz).

## Environment

All optional. Claude Code's `flow:orchestrate` offers the read-only Codex CLI review only when the
`codex` CLI is installed and review is allowed. omp does not automatically launch that CLI branch.

| Variable | Effect |
| --- | --- |
| `VIKUNJA_URL` | base address of the Vikunja instance, used for task links (plain `#N` without it) |
| `CODEX_REVIEW=off` | never offer the review |
| `CODEX_REVIEW_GUARD` | shell command that must exit 0 before the review runs |
| `CODEX_MODEL`, `CODEX_REASONING_EFFORT` | override the model / reasoning effort from the Codex config |
