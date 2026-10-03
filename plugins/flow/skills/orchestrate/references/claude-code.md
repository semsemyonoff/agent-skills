# Claude Code adapter

Use this adapter only in Claude Code. Keep the process in the loaded `SKILL.md`; this file supplies native capabilities, not another workflow. `SKILL_ROOT` is the resolved directory of that loaded file, not the repository or current working directory. Resolve every bundled resource path against `SKILL_ROOT`. `${CLAUDE_SKILL_DIR}` may identify that directory in Claude Code; pass the resolved location explicitly to workers.

## Discover before dispatch

Discover the exposed native delegation tool: some Claude Code surfaces call it `Agent`, others `Task`. Read the actual tool's schema and available subagent descriptions, enabled plugin identity, and applicable native definitions/overrides; absence of the name `Agent` alone is not missing delegation. Plugin agents use scoped identifiers, normally `flow:flow-research`, `flow:flow-mechanics`, `flow:flow-implementation`, and `flow:flow-review`; treat these as expected names, not proof that they loaded. Use the actual discovered `subagent_type` only when supported. The @-mention typeahead exposes loaded scoped names; `/agents` behavior is version-dependent and is not a reliable universal listing UI. See `references/native-setup.md` for native override precedence. [1][3]

| Capability template | Native definition | Historical template default, not routing policy | Capability |
| --- | --- | --- | --- |
| Research | `flow-research` | `haiku` | Source reading, no editing/shell |
| Mechanics | `flow-mechanics` | `haiku` | Exact known transformations |
| Full editing | `flow-implementation` | `sonnet` | Same implementation capability across permitted complexity profiles |
| Independent review | `flow-review` | `opus` | Separate read/verification; assess budget by risk, not this default |
| Optional opinion | Discovered user-selected reviewer/CLI route | No fixed default | Supplemental only |

These native templates establish capabilities, not a blanket implementation→sonnet or review→opus
budget rule. Apply `references/routing.md` first. Native user/project/session definitions can provide
same-capability light/standard/strong profiles with supported model/effort selectors. A live Agent/Task
schema may instead permit a model selection covered by the already authorized routing policy/plan;
ordinary matching assignments need no new question. Do not invent invocation effort fields or force
template aliases over approved overrides. Missing permitted profile/pair is a prerequisite, not a
silent expensive template default. Native allowlists omit Agent/Task, making these workers leaves
by policy rather than claiming the harness forbids nesting. [1][2]

Record accessible effective **configured/requested** model and reasoning in the plan after complexity
assessment, separately from **actual** metadata after spawn. `/tasks` can expose running identity or
effort in supported versions; unavailable actual stays unknown, not known configuration. Model defaults,
invocation overrides, forced environment settings, alias resolution, restrictions and fallbacks can
differ. Inspect only relevant non-secret fields, never whole settings/environment/private profiles. [1][2]

If an observed model substitution is outside the approved selection/fallback permissions, do not accept its output as an approved step. Stop affected dispatch, disclose the requested versus observed difference, and obtain exact approval or use an already-approved available route. Do not mutate settings to bypass the restriction. If identity remains unavailable, keep it `unknown` rather than asserting a model guarantee.

## Native confirmation UI

Use main-session `AskUserQuestion` when available. Follow its live schema: Claude's picker uses question text, `header`, option `label`/`description`, and `multiSelect`; do not send omp's `id`, `multi`, or `recommended` fields. Put the complete plan and authorization boundary before the question. Offer concise choices in the user's language:

- English: **Start approved plan**, **Start phase by phase**, **Change plan**, **Do not start**.
- Russian: **Запустить согласованный план**, **Запустить по фазам**, **Изменить план**, **Не запускать**.

A request for phase-by-phase execution is an explicit user choice, not the default. Interpret custom text/notes literally, including requests to wait. Subagents cannot use `AskUserQuestion`; workers report blockers to the orchestrator. If the tool is absent, present the same question in chat and wait for an explicit answer. Never treat a missing answer, cancellation, or question auto-continue timeout as permission. Exact external/irreversible actions require their own explicit authorization even when local execution is approved. Native permission dialogs remain additional safeguards; they do not replace the shared approval contract. [1][4]

## Dispatch, completion, and review

Use the discovered Agent/Task schema with the selected permitted profile/subagent identity and the
full brief (capability, complexity/reason, expected pair, scope, acceptance and routing allowance).
Do not copy fields from another tool surface or invent a wrapper. Native definitions or supported
per-call model selection implement the assessed pair; only pre-authorized policy/plan choices are
routine. Use effort only through actually supported native controls; otherwise require a matching
native profile rather than inheriting a guessed expensive setting. No conversation forks as
independent workers/reviewers. [1][2]

Non-fork workers start in separate context windows without the conversation history or previously loaded skills. Native context may include CLAUDE.md files, a git snapshot, explicitly preloaded skills, and a conditional sibling roster; the brief must still be complete. If the discovered delegation schema exposes `name`, avoid using it merely as a label when agent teams are enabled: it can launch a teammate instead. Use ordinary subagent dispatch unless a different native mechanism has been explicitly agreed. [1][4]

Foreground calls block; background calls notify the parent on completion. Availability and defaults vary with runtime version, fork mode, and background-task settings. Do useful independent work while waiting; do not poll, sleep-loop, or claim an unfinished result. There is no omp `wait` API here: use only the waiting/completion mechanism the current tool description exposes. `TaskOutput` is deprecated in current docs; if full output is needed, read the actual output path returned by the runtime, not a guessed path. `/tasks` exposes worker status/transcripts to the user, so do not claim workers are invisible. Relay the material result and evidence in the final report. [1][4]

Dispatch a separate risk-appropriate review profile or approved equivalent after implementation,
not automatically the highest default for every worker. One reviewer may cover compatible scopes.
Give original acceptance, actual changed surface and permitted verification commands. Its Bash
capability is not a sandbox: prohibit source/config changes and unapproved external effects.
Missing reviewer/pair/tool capability is a blocker, not permission to self-review.

Sharpen the brief or isolate the hard part and reassess first. Stronger profiles must stay within
the pre-authorized policy/plan; otherwise ask for the exact route/budget. No fixed ladder, blind
retries, settings writes or paid fallback. Optional read-only Codex review remains explicit and
supplemental under `references/codex-review.md`, not necessarily another vendor.

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
