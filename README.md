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

# Shared peer-chat for native Codex CLI and omp (~/.agents/skills)
npx skills add semsemyonoff/agent-skills/plugins/peer -a codex -g
```

## Plugins

### planning — `brainstorm`, `planning`, `plan-review`

Portable adaptations of [umputun/cc-thingz](https://github.com/umputun/cc-thingz): incremental design,
compact `docs/plans/YYYYMMDD-name.md` creation, and one independent read-only plan review followed
by bounded driver corrections to that plan. Each skill is self-contained, with its own rule
resolver/resources and upstream MIT notice. No exec workflow, automatic implementation, commit,
install or review loop.

In omp, load these three skills from the shared `.agents/skills` tree via skills.sh, or point native
skill discovery at `plugins/planning/skills`. Invoke `/skill:brainstorm`, `/skill:planning` or
`/skill:plan-review`. Loading skills does not automatically expose native agent resources.
Existing Claude setups using `brainstorm@umputun-cc-thingz` and `planning@umputun-cc-thingz` can keep
those workflows and custom data unchanged; do not enable a second conflicting planning plugin merely
to connect the omp skills. This repository does not modify the upstream install.

Custom rules: first nonempty `.agents/<name>-rules.md`, then `.claude/<name>-rules.md` in the actual
project directory, otherwise `${XDG_CONFIG_HOME:-$HOME/.config}/agent-skills/<name>-rules.md`.
Use `brainstorm` or `planning` as the name; plan review loads planning rules. No merging, no personal
rules embedded in shared files, and no required Claude plugin environment variables. The read-only
resolver reports the selected path/provenance/content; no rules is normal, unreadable rules is an
explicit blocker. User-rule symlinks preserve the existing source without copying it into the repo.

The optional omp agent resource is
[`plugins/planning/skills/plan-review/agents/omp.md`](plugins/planning/skills/plan-review/agents/omp.md):
native name `plan-review`, model role `@plan_review`, tools `read`, `grep`, `glob`, no spawns.
An operator can expose that file through native agent discovery and route `modelRoles.plan_review`
to an approved selector/role; the skill never installs it or changes models. The driver may call its
bundled read-only resolver once; the reviewer worker never runs a shell, helper or tests.

Brainstorm preserves loaded next-step rules and passes validated decisions/files without re-design.
Planning honors the loaded execution owner (including ralphex when selected), fast targeted
Validation Commands and a final verification task. Project-specific restrictions come only from
loaded custom rules, with applicability established from conditions defined by those rules;
unknown conditions remain unknown rather than checked.
Plan creation starts neither ralphex nor orchestrate. The separate reviewer returns `APPROVE` or
`NEEDS REVISION` with evidenced findings and never edits. After its actual report, the driver checks
the evidence and automatically fixes only the review-target plan for unambiguous corrections
consistent with the original task, validated decisions and loaded rules. Explicit **review only**,
**no edits**, **только review** or **без правок** disables all autofix.

Architectural/product choices, conflicting requirements, agreed scope/route/budget changes or
ambiguity get 2–5 concrete options with tradeoffs and one recommendation: native omp `ask` buttons,
Claude `AskUserQuestion` only if exposed, otherwise text options and a real answer before dependent
edits. Timeout, redirect, cancellation, silence and defaults are not consent. Independent safe fixes
may precede the question; dependent findings remain unapplied. No code, other plans, rules/config
changes, project gates, implementation or automatic second review. The driver re-reads changed plan
text for local consistency and reports the **original reviewer verdict**, **actual applied changes**
and **unresolved choices** separately, never attributing reviewer approval to unseen revisions.
An absent independent reviewer remains a blocker, not a successful author self-review.

### flow — `orchestrate`

For tasks too big for one pass but small enough for one session. One shared Claude Code/omp process:
recon → plan → confirmation → execution → independent verification → report. Choose **capability**
and **complexity/risk** separately for every slice, including review: remaining decisions, known
pattern/API/paths, coupling and failure cost. Then choose the minimum sufficient **permitted native
model + reasoning profile**; implementation or docs is not a fixed expensive default-task route.
Plans show complexity/reason, selected profile and accessible configured/requested pair; actual
identity/reasoning is separately reported only when exposed. Missing profiles are prerequisites,
not silent fallbacks. Native configuration owns selectors, not another orchestration.yml.

Approved execution stays autonomous; phase-by-phase only on request. Sharpen the brief or isolate
the hard part before escalating within an already authorized policy/plan; outside routes/budgets
need explicit permission. Do not mutate shared settings between parallel calls. Trivial work may be
inline; combine related simple work and use one risk-appropriate independent reviewer for compatible
changes, not automatically highest reasoning or a review per worker. Explicit review requirements
still apply. Optional second opinion remains chosen, read-only and supplemental, never paid fallback.

Bounded replacement briefs cover runtime consumers and default/fallback/environment precedence,
not just literals. Batch review fixes; coordinators may check obvious nonbehavioral tails locally,
but substantive changes still need independent review. Report the reviewed scope/version and later
coordinator-only changes separately. Smoke evidence distinguishes browser, HTTP/API, transport and
deployment: a neighboring pass does not close a required gap. Non-required failures remain explicit
limits; completed implementation/gates and pending PR/CI/merge are separate outcomes.

`/flow:orchestrate <task>`; add "phase by phase" to stop after each phase.

In omp, add this repository's `plugins/flow/skills` to native `skills.customDirectories`, then
invoke `/skill:orchestrate`. Add `plugins/retro/skills` for `/skill:reflection`; restart or reload
skills after changing that configuration. Each skill resolves bundled files relative to its loaded
`SKILL.md`. Loading a skill does not install agent definitions, select models or change permissions.
Keep routing in the native harness settings; no shared `orchestration.yml` is needed.

Optional native omp resources are under `plugins/flow/skills/orchestrate/agents/omp/`:
`flow-worker-{light,standard,strong}` have the same full editing tools including permitted LSP;
separate `flow-review-{light,standard,strong}` have read/verification and read-only LSP navigation/
diagnostics, never mutating code actions or rename. LSP still requires actual enabling/authorization
and an available server; source resources neither install one nor promise availability. Native aliases:
`@flow_light`, `@flow_standard`, `@flow_strong`, with fixed `thinking-level` medium/medium/high.
An operator must expose those resources in native agent discovery and bind `modelRoles.flow_*` to
permitted selectors; no profiles or role mappings are activated by these source changes. Existing
scout/sonic remain research/exact-mechanics specialists. Generic default dispatch requires a verified
allowed pair and explicit suitability reason. Task/public eval have no model-override argument;
optional relative lo/med/hi hints do not select the model or guarantee literal medium. See the native
setup reference below for deployment and override/ceiling boundaries. No quota-savings percentage
is inferred from API prices.

See [flow native setup](plugins/flow/skills/orchestrate/references/native-setup.md) for Claude
Code's agent-definition/model-selection mechanism and omp's existing
`task.agentModelOverrides` / `modelRoles` routing. Optional second opinions need an explicit
checkpoint; a failed worker never authorizes a hidden provider or model switch.

### vikunja — `vikunja`

Working with [Vikunja](https://vikunja.io) 2.7+ through its built-in MCP server without the usual
agent mistakes: markdown sent without `format: "markdown"`, relations created in the wrong direction,
duplicates, tasks closed without being asked. Three scenarios:

- `/vikunja:backlog <idea>` — find the project, check for duplicates, create a task in the project's
  style with a markdown description;
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
Claude Code's deferred ToolSearch remains supported. Bundled references resolve relative to the
loaded `SKILL.md`, with no required Claude environment variables. Set `VIKUNJA_URL` for clickable task links; no tokens belong in skill files.

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

A single shared skill for chatting, discussing or reviewing with Claude Code, native Codex CLI or
omp already running in a neighboring kitty tab pane or agterm split. Either pane can run any
supported harness; an omp session sends as omp even when its model is Codex or Claude.
The bundled Python 3 standard-library script discovers recipients, offers a read-only doctor and
refuses unsafe composers/dialogs. Replies go through the script; no agent launching or reply watchers.

Claude Code: install `peer@semsemyonoff` using the marketplace commands above and invoke
`/peer:peer-chat`. Native Codex CLI and omp: use the shared install command above, sourced from
`plugins/peer`, to place `peer-chat` in `~/.agents/skills`. In omp invoke `/skill:peer-chat`, or point
native skill discovery at `plugins/peer/skills` instead. Do not enable two copies in one harness.

Before replacing an older package, remove its old installed `peer-chat` skill (including any
harness-specific copy or symlink) from that harness's skill search path, then install the shared
package and reload skills/restart the session. These are operator instructions; this repository
does not install or remove anything on your behalf.

kitty requires remote control plus `KITTY_WINDOW_ID` and `KITTY_LISTEN_ON`; agterm requires known
source-session/pane identity and a visible split. The default recipient keys are Claude Return
(may interrupt), Codex Tab (queues), and omp Ctrl+Q (follow-up, or normal submit when idle).
Customized mappings must match these defaults; do not bypass a refusal with alternate keys.
Native Codex CLI's sandbox may need user-selected
`-c sandbox_workspace_write.network_access=true` to reach kitty's socket; this is not an omp
setting or authorization for an unsandboxed retry. See the
[shared skill](plugins/peer/skills/peer-chat/SKILL.md) for prerequisites and safe handling.

## Task flow

```
/vikunja:intake <id>         analysis; open decisions → brainstorm, settled solution → plan
/brainstorm                  validate design; selected route → orchestrate or durable planning
/flow:orchestrate <task>     recon → plan with native agents → confirm → execute → verify → report
/vikunja:report <id>         report into the task; closes only when asked
```

Portable omp chain:

```
/skill:brainstorm            validated decisions + files + rules provenance
  → /skill:orchestrate       explicit one-session choice; retains execution approval
  → /skill:planning         explicit durable-plan choice; writes docs/plans/YYYYMMDD-name.md
      → /skill:plan-review  one read-only reviewer + target-plan driver fixes/choices; only when selected
      → ralphex             completed plan path/instructions; no automatic launch
```

The existing Claude brainstorm/planning workflows and the portable adaptations above originate from
[umputun/cc-thingz](https://github.com/umputun/cc-thingz). Selecting a next workflow is not blanket
permission for implementation, model switches, external writes or commits.

## Environment

All optional. Claude Code's `flow:orchestrate` offers the read-only Codex CLI review only when the
`codex` CLI is installed and review is allowed. omp does not automatically launch that CLI branch.

| Variable | Effect |
| --- | --- |
| `VIKUNJA_URL` | base address of the Vikunja instance, used for task links (plain `#N` without it) |
| `CODEX_REVIEW=off` | never offer the review |
| `CODEX_REVIEW_GUARD` | shell command that must exit 0 before the review runs |
| `CODEX_MODEL`, `CODEX_REASONING_EFFORT` | override the model / reasoning effort from the Codex config |
