# Claude Code adapter

Use this adapter only in Claude Code. Keep the process in the loaded `SKILL.md`; this file supplies native capabilities, not another workflow. `SKILL_ROOT` is the resolved directory of that loaded file, not the repository or current working directory. Resolve every bundled resource path against `SKILL_ROOT`. `${CLAUDE_SKILL_DIR}` may identify that directory in Claude Code; pass the resolved location explicitly to workers.

## Discover before dispatch

Discover the exposed native delegation tool: some Claude Code surfaces call it `Agent`, others `Task`. Read the actual tool's schema and available subagent descriptions, enabled plugin identity, and applicable native definitions/overrides; absence of the name `Agent` alone is not missing delegation. Plugin agents use scoped identifiers, normally `flow:flow-research`, `flow:flow-mechanics`, `flow:flow-implementation`, and `flow:flow-review`; treat these as expected names, not proof that they loaded. Use the actual discovered `subagent_type` only when supported. The @-mention typeahead exposes loaded scoped names; `/agents` behavior is version-dependent and is not a reliable universal listing UI. See `references/native-setup.md` for native override precedence. [1][3]

| Shared category | Native definition | Typical plugin default | Capability |
| --- | --- | --- | --- |
| Research | `flow-research` | `haiku` | Read/search sources, no edits or shell |
| Mechanics | `flow-mechanics` | `haiku` | Exact specified file transformations, no shell |
| Implementation | `flow-implementation` | `sonnet` | Approved implementation and scoped commands |
| Review | `flow-review` | `opus` | Separate reviewer; inspect and exercise the result |
| Optional second opinion | A discovered, user-approved reviewer or explicit CLI review | No fixed default | Supplement, not replace independent verification |

These defaults belong to Claude-native frontmatter, not the shared routing policy. Native user/project/session definitions or a permitted, user-approved delegation `model` parameter can change the selection without editing `SKILL.md`, only when exposed by that tool's schema. Do not force these aliases over an existing approved override. They are aliases, not evidence of a concrete model/version or effort. Native allowlists omit both `Agent` and `Task`, making these workers leaves by policy; current Claude Code supports nested subagents generally. Do not describe leaf behavior as a runtime impossibility. [1]

Record the selected category, discovered agent identity, and allowed selection. Record actual model/effort only when the runtime exposes them; otherwise use `unknown`. `/tasks` can show a running subagent's model and, in supported versions, explicit effort. Definition values describe requested defaults, not necessarily execution: invocation overrides, forced subagent environment settings, alias resolution, organization restrictions, and fallbacks can change them. Inspect only relevant non-secret configuration; never dump settings, environment variables, or private routing profiles into the plan/report. [1][2]

If an observed model substitution is outside the approved selection/fallback permissions, do not accept its output as an approved step. Stop affected dispatch, disclose the requested versus observed difference, and obtain exact approval or use an already-approved available route. Do not mutate settings to bypass the restriction. If identity remains unavailable, keep it `unknown` rather than asserting a model guarantee.

## Native confirmation UI

Use main-session `AskUserQuestion` when available. Follow its live schema: Claude's picker uses question text, `header`, option `label`/`description`, and `multiSelect`; do not send omp's `id`, `multi`, or `recommended` fields. Put the complete plan and authorization boundary before the question. Offer concise choices in the user's language:

- English: **Start approved plan**, **Start phase by phase**, **Change plan**, **Do not start**.
- Russian: **Запустить согласованный план**, **Запустить по фазам**, **Изменить план**, **Не запускать**.

A request for phase-by-phase execution is an explicit user choice, not the default. Interpret custom text/notes literally, including requests to wait. Subagents cannot use `AskUserQuestion`; workers report blockers to the orchestrator. If the tool is absent, present the same question in chat and wait for an explicit answer. Never treat a missing answer, cancellation, or question auto-continue timeout as permission. Exact external/irreversible actions require their own explicit authorization even when local execution is approved. Native permission dialogs remain additional safeguards; they do not replace the shared approval contract. [1][4]

## Dispatch, completion, and review

Use the discovered native delegation tool (`Agent` or `Task`) and its actual schema with the approved discovered subagent identity and a self-contained brief from `references/brief.md`; include source paths, assigned files, approved actions, acceptance criteria, and dependencies. Do not rename a tool call, invent a wrapper, or copy fields from the other surface. Normally let the native definition/configuration resolve the model. Pass a per-call `model` only when the exposed schema supports it and the particular override is already allowed. Do not invent effort parameters: frontmatter effort is documented, while invocation fields must come from the live schema. Do not use conversation forks as independent workers/reviewers. [1]

Non-fork workers start in separate context windows without the conversation history or previously loaded skills. Native context may include CLAUDE.md files, a git snapshot, explicitly preloaded skills, and a conditional sibling roster; the brief must still be complete. If the discovered delegation schema exposes `name`, avoid using it merely as a label when agent teams are enabled: it can launch a teammate instead. Use ordinary subagent dispatch unless a different native mechanism has been explicitly agreed. [1][4]

Foreground calls block; background calls notify the parent on completion. Availability and defaults vary with runtime version, fork mode, and background-task settings. Do useful independent work while waiting; do not poll, sleep-loop, or claim an unfinished result. There is no omp `wait` API here: use only the waiting/completion mechanism the current tool description exposes. `TaskOutput` is deprecated in current docs; if full output is needed, read the actual output path returned by the runtime, not a guessed path. `/tasks` exposes worker status/transcripts to the user, so do not claim workers are invisible. Relay the material result and evidence in the final report. [1][4]

Dispatch verification to an actual separate `flow-review` instance (or an already-approved discovered equivalent) after implementation. Give it the acceptance criteria, actual changed surface, and permitted verification commands, not only the implementer's summary. Its Bash capability is not a read-only sandbox: prohibit modifying commands and unapproved external/irreversible effects in the brief. A missing/disabled reviewer or insufficient verification tools is a blocker to claiming independently verified completion, not permission to self-review. Return findings, exercised evidence, and limitations to the orchestrator for disposition.

Sharpen a failing brief first. Escalate only through a discovered, configured or user-approved native route; there is no fixed model-tier ladder. Optional Claude-to-Codex read-only CLI review follows `references/codex-review.md` only after opt-in and relevant data-sharing permission; a second opinion need not use another vendor.

## Sources

1. [Claude Code subagents: scopes, fields, model resolution, tools, context, lifecycle](https://code.claude.com/docs/en/sub-agents.md).
2. [Claude Code model configuration: aliases, restrictions, environment overrides](https://code.claude.com/docs/en/model-config.md).
3. [Claude plugin components: scoped agents and supported frontmatter](https://code.claude.com/docs/en/plugins/components.md#agents).
4. [Claude tools reference: Agent, AskUserQuestion, TaskOutput](https://code.claude.com/docs/en/tools-reference.md).

Documentation inspected on 2026-10-01. Version-specific documentation is not proof of capabilities in the current session; the loaded tool schema and observed result remain authoritative.

Observed local registration smoke on Claude Code 2.1.286 exposed `Task` and no `AskUserQuestion`
in print-mode `system.init.tools`, while loading `flow:orchestrate` and all four scoped Flow agents.
This confirms registration/tool naming, not an LLM turn, dispatch schema, model support, or completed
orchestration. Discover the live schema; use explicit text confirmation when the picker is absent.
