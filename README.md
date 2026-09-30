# agent-skills

Personal skills for Claude Code and Codex. Conventions: [AGENTS.md](AGENTS.md).

```sh
# Claude Code
claude plugin marketplace add semsemyonoff/agent-skills
claude plugin install <plugin>@semsemyonoff

# Codex
npx skills add semsemyonoff/agent-skills/codex -a codex -g
```

Per-profile enablement is managed in chezmoi.

## Plugins

| Plugin | Skill / commands | Profile |
| --- | --- | --- |
| `flow` | `orchestrate` — plan with per-step model routing, delegate, verify, report | personal, work |
| `vikunja` | `vikunja` + `/vikunja:backlog`, `/vikunja:intake`, `/vikunja:report` | personal |
| `redmine` | `redmine` + `/redmine:reply` — Textile drafts, fact-check, send on approval | work |
| `retro` | `reflection` — retrospective over session transcripts | personal, work |
| `gdocs` | `gdoc-import` — Google Docs/Sheets into the repo as markdown | work |
| `peer` | `peer-chat` — conversation with Codex in an agterm split (macOS) | personal |

## Task flow

```
/vikunja:intake <id>         analysis; open decisions → brainstorm, settled solution → plan
/brainstorm                  design, section by section
/flow:orchestrate <task>     short recon → plan with models → confirm → execute → verify → report
/vikunja:report <id>         report into the task; closes only when asked
```

A plan comes only after the solution is settled: if the task leaves design decisions open, brainstorm
first. Add «по фазам» / "phase by phase" to `/flow:orchestrate` to stop after each phase.
