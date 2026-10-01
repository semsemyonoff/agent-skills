# omp adapter

Use this adapter only in omp. Keep the process in the loaded `SKILL.md`; this file maps shared categories onto native capabilities. `SKILL_ROOT` is the resolved directory of that loaded file. Resolve all bundled resource paths against `SKILL_ROOT` and give workers the resolved paths. Do not use Claude-specific environment variables to locate resources.

## Discover before dispatch

Read the current `task`, `ask`, and `wait` descriptions/schemas and exposed agent roster. Inspect only relevant non-secret native routing information, as described in `references/native-setup.md`. Discovery is not availability: disabled agents, parent spawn policy, recursion depth, plan mode, tools, and extension hooks can block or alter execution. Execution-time discovery/settings reload can differ from the initial description. A missing agent error reports available alternatives; select one only within the approved category and permissions. Do not install agents, enable providers, or change configuration. [1][4]

| Shared category | Native selection | Boundary |
| --- | --- | --- |
| Research | `agent: "scout"` | Gather source-grounded facts, not unresolved design judgment |
| Mechanics | `agent: "sonic"` | Exact specified transformations, not open-ended reasoning |
| Implementation | Omit `agent` normally | Use the native default spawn policy; do not redundantly send `agent: "task"` |
| Review | `agent: "reviewer"`; `security-reviewer` for security-focused scope | Actual separate reviewer with relevant tools |
| Optional second opinion | Discovered, user-approved native reviewer | Additional perspective, not automatic Codex invocation |

Confirm what omission resolves to: unrestricted parents normally default to `task`, while a restricted parent's default is its first permitted agent. If that agent cannot implement the approved work, surface the mismatch rather than silently dispatching it. Native agent definitions and `task.agentModelOverrides`/`modelRoles` own the model mapping; do not copy Claude defaults here or into shared routing. Claude-dialect plugin agent model fields are discarded by omp discovery, so imported Flow agents are not evidence of an omp model selection. [4]

The `task` wire has **no `model` field**. Per-agent overrides resolve before frontmatter model selectors; role aliases expand through `modelRoles`, with native fallback/session policy after that. Settings, hooks, prewalk, and request fallbacks can affect the observed model. Record only exposed actual model/effort metadata, otherwise `unknown`; never infer them from agent names. Result metadata may include `resolvedModelIdentity`, `resolvedThinkingLevel`, `resolvedModelIsFallback`, and `resolvedModelRoute`. Do not dump private model profiles, credentials, or unrelated settings into briefs or reports. Reject an observed substitution outside approved routing/fallback permissions: stop affected dispatch and obtain exact permission or use an already-approved route. Do not try to disable native fallbacks or overwrite settings covertly. [1][4][5][6]

## Native confirmation UI

Use main-session `ask` when available. It takes `questions`, each with unique `id`, `question`, and `options` (`label`, optional `description`/`preview`), plus optional `header`, `multi`, and `recommended` (zero-based index). Do not send Claude's `multiSelect` field. Present the complete plan and authorization boundary first. Example question body, using the current tool schema:

```json
{
  "questions": [{
    "id": "plan-approval",
    "question": "Start the approved local plan? / Запустить согласованный локальный план?",
    "options": [
      {"label": "Start approved plan / Запустить план"},
      {"label": "Start phase by phase / Запустить по фазам"},
      {"label": "Change plan / Изменить план"},
      {"label": "Do not start / Не запускать"}
    ],
    "multi": false
  }]
}
```

Local rich UI may show a multi-question form, notes/custom answers, previews, images, or a chat redirect; fallback UI is a selector/editor. Both are native omp surfaces, not Claude buttons. Inspect the actual selected/custom answer and notes. A `chatRedirect` is not consent. Configured timeouts can auto-select a recommended or first option: any `timedOut` result or auto-selected-after-timeout notice is **not authorization**, even if its label says Start. Cancellation and absent UI also do not authorize. If `ask` is absent/headless, ask in chat and wait for an explicit user answer; do not enable it or change the timeout. Phase-by-phase execution requires an explicit request. External/irreversible actions need exact explicit permission separate from ordinary local-plan approval. [2]

Workers have no interactive approval UI; omp's child tool approval mode is headless. Give every worker the approved-action boundary and require it to return blockers instead of performing an unapproved effect. Do not rely on a worker permission dialog to stop it. [1]

## Dispatch, completion, and review

Use the live `task` schema, not a guessed wrapper. With the usual batch shape, send required shared `context` and `tasks[]`; each item has self-contained `task` and `solutionSpace` plus optional native `agent`/`name`. `solutionSpace` describes which causes/designs remain open, not task size. With flat schema, send one item and put shared context in a referenced `local://` artifact if needed. Never add top-level batch `agent`, `model`, or a made-up label. `effort` exists only when exposed by `task.enableEffort`; its supported coarse values are `lo`, `med`, `hi`, and omission keeps native policy. Do not turn that setting on. Do not request isolation without an approved, understood native policy: branch-mode isolation can create commits/cherry-picks and is outside ordinary local-edit permission. [1][4]

Children have separate sessions, not parent conversation history. Carry-over includes workspace/skills/context files, shared `local://` root, and an approved-plan reference when present; supply a complete brief from `references/brief.md` nonetheless. Spawn depth/policy and explicit tools govern child spawning and messaging. Keep workers leaves by instruction; do not claim omp universally forbids nesting. Give disjoint file ownership to parallel editors. [1][4]

With `async.enabled`, ordinary spawns return job/agent identifiers and results auto-deliver; blocking agent definitions can instead return inline results, including in mixed batches. Do useful work while waiting. Call `wait` only when blocked with nothing else to do; its native schema has no arguments and no job selector. Do not poll. On a partial/safety-cap return or steering interrupt, process the notice and keep waiting if dependent work is still outstanding. Never report a spawn receipt as a completed result. Full output is available at the returned `agent://<id>`; `history://<id>` exposes the transcript, and `write agent://<id>` can coordinate/resume an existing agent when available. [1][3]

The user can inspect native Agent Hub (`Alt+A`), pinned subagent progress, and transcripts; do not assert that workers are invisible. Report the evidence and material findings in the main response regardless of UI visibility. [4]

Dispatch independent verification to an actual separate `reviewer`/`security-reviewer` instance or an approved discovered equivalent, never the implementer. Include the acceptance criteria, actual changed surface, source paths, and permitted verification commands. Require executed evidence and limits, not an echo of the implementer's summary. Missing reviewer capability, insufficient tools, or a blocked spawn prevents a claim of independently verified completion; the orchestrator cannot substitute self-review.

Sharpen a failing brief first; use only configured or user-approved native escalation, not a fixed tier ladder, hidden eval override, or a model name in `task` parameters. Optional second opinion does not imply another vendor. Do not probe or automatically invoke Codex in omp; consult `references/codex-review.md` only when the user explicitly opts into that CLI path and permits the relevant data sharing.

## Authorized native sources

1. [`task`: schema, results, child context, headless permissions, isolation](omp://tools/task.md).
2. [`ask`: UI, answer metadata, timeout behavior](omp://tools/ask.md).
3. [`wait`: availability, automatic delivery, wake behavior](omp://tools/wait.md).
4. [Task agent discovery, precedence, native model overrides, Agent Hub](omp://task-agent-discovery.md).
5. [Model/provider configuration, model roles, selectors, availability](omp://models.md).
6. [Settings layers, read-only inspection, overlays, persistence](omp://settings.md).

Documentation inspected on 2026-10-01. These authorized internal references describe the harness; use the current loaded schema and observed execution for the current session.
