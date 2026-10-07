# omp adapter

Use this adapter only in omp. Keep the process in the loaded `SKILL.md`; this file maps shared categories onto native capabilities. `SKILL_ROOT` is the resolved directory of that loaded file. Resolve all bundled resource paths against `SKILL_ROOT` and give workers the resolved paths. Do not use Claude-specific environment variables to locate resources.

## Discover before dispatch

Read the current `task`, `ask`, and `wait` descriptions/schemas and exposed agent roster. Inspect only relevant non-secret native routing information, as described in `references/native-setup.md`. Discovery is not availability: disabled agents, parent spawn policy, recursion depth, plan mode, tools, and extension hooks can block or alter execution. Execution-time discovery/settings reload can differ from the initial description. A missing agent error reports available alternatives; select one only within the approved category and permissions. Do not install agents, enable providers, or change configuration. [1][4]

| Capability | Native selection after assessment | Boundary |
| --- | --- | --- |
| Research | Discovered `scout` or approved research profile | Source-grounded facts, not an editing substitute |
| Mechanics | Discovered `sonic` with a verified permitted exact-work pair | Exact known transformations only, not universal development |
| Implementation | Discovered `flow-worker-light`, `flow-worker-standard`, `flow-worker-strong` or approved equivalent | Same full editing capability; choose by uncertainty/risk, not the category name |
| Review | Separate discovered risk-appropriate `flow-review-*`, reviewer/security specialist or approved equivalent | Assess required pair independently; combine compatible coverage |
| Optional second opinion | Discovered `second-opinion` agent, explicitly selected by the user | Separate supplemental instance after required review, not its replacement |

Read `references/routing.md` before choosing a profile. Native resources and their role contract are
in `references/native-setup.md`; files being present here does not mean they are deployed or enabled.
Missing profiles/aliases are prerequisites. Do not silently omit `agent` and obtain a default task.
Omission is legal only if the authorized policy expressly includes that effective default pair and
the plan gives a capability/complexity suitability reason. Discover omission's actual resolution:
usually task for unrestricted parents, potentially another agent for restricted parents. [1][4]

The current task wire exposes per-item `model` (string or ordered nonempty array); never put it
on the batch container. Use it only when the live schema exposes it and every candidate/known role
expansion fits the assessed authorized policy. Explicit selection precedes native
`task.agentModelOverrides`, profile model selectors and configured task/session fallback; role aliases
expand through `modelRoles`. Use `@default`, not ambiguous literal `default`/`inherit`, for the live
parent model; reasoning still follows native precedence. Ordered candidates are preferences, not
a closed allowlist: configured runtime fallback behavior can alter the actual route.
Current public eval `agent()`/`workpool()` also expose `model`; discover that API independently.
Older surfaces may not: use an appropriate discovered profile instead, never hidden bridge arguments
or shared role/agent settings mutations between parallel calls. [1][4][7]
Choose the profile by assessment and show the accessible effective configured/requested pair first.
After spawn show actual identity/reasoning only from exposed fields such as `resolvedModelIdentity`,
`resolvedThinkingLevel`, `resolvedModelIsFallback` and `resolvedModelRoute`; keep unavailable actual
metadata unknown, not known configuration. Stop unexplained substitutions outside the selected
authorized route. Never dump private profiles or credentials. [1][4][5][6]

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

## Supplemental second opinion

At plan confirmation, offer "Additional review via second-opinion / No additional review"
(«Дополнительное ревью через second-opinion / Без дополнительного ревью») as a separate question
in the same `ask` form when available. Discover the exact `second-opinion` agent, its read-only
capability and permitted native route; do not inspect credentials or launch a probe model call.
This is a separate context, not a promise of another provider/model. Honor an earlier explicit
decision. If the agent is missing or blocked, disclose that and omit its offer; do not substitute
Codex CLI, a default worker or the required reviewer. An explicitly required unavailable opinion
remains a blocker until the user chooses otherwise.

After explicit acceptance, launch one new `second-opinion` instance at the agreed stable-final
checkpoint through the actual task/eval schema. Supply goal, acceptance, final changed-file/artifact
inventory, scope/version, pre-existing edits, observed verification evidence and a read-only brief.
It must neither edit nor delegate; request material findings with source locations and remaining
verification gaps, not a token APPROVE. Do not demand shell/tests from a read-only profile without
those capabilities. Freeze its scope until the result arrives. Apply the shared finding-disposition,
mandatory re-verification and no-automatic-second-round rules. No approval, no supplemental call.

## Dispatch, completion, and review

Use the live task schema: batch requires shared `context` and `tasks[]`, each with self-contained
`task`, `solutionSpace` and the selected discovered profile `agent`; flat uses the actual item shape.
Never add top-level batch agent/model, a made-up label or hidden bridge fields. Omit generic agent
only for the explicit justified policy match above. `solutionSpace` describes unresolved causes or
design choices, not volume; it drives thinking classification only when the child's selector is
`auto`. It does not route the model and does not change a fixed profile's reasoning. [1][4]

Precise reasoning comes from the native profile selector/`thinking-level` and effective policy.
`task.enableEffort` only exposes optional `lo`/`med`/`hi` hints; it does not choose a model. Those are
relative lowest/middle/highest supported levels: `med` is not necessarily literal `medium`.
Profiles here work with that option disabled; do not turn it on. If exposed hints are used, they
override configured thinking and must be supported, assessed and already authorized, including
clamping/fallback limits. Do not request isolation without exact permission; branch mode may
commit/cherry-pick and is outside ordinary local editing. [1][4]

Children have separate sessions, not parent conversation history. Carry-over includes workspace/skills/context files, shared `local://` root, and an approved-plan reference when present; supply a complete brief from `references/brief.md` nonetheless. Spawn depth/policy and explicit tools govern child spawning and messaging. Keep workers leaves by instruction; do not claim omp universally forbids nesting. Give disjoint file ownership to parallel editors. [1][4]

For editing slices, follow the native edit protocol: read the ranges to change and use small exact
patches. After a tool rejection, re-read affected ranges and correct the rejected boundary/arguments;
do not resend the same oversized or invalid payload. This sharpens execution, not the model route.

With `async.enabled`, ordinary spawns return job/agent identifiers and results auto-deliver; blocking agent definitions can instead return inline results, including in mixed batches. Do useful work while waiting. Call `wait` only when blocked with nothing else to do; its native schema has no arguments and no job selector. Do not poll. On a partial/safety-cap return or steering interrupt, process the notice and keep waiting if dependent work is still outstanding. Never report a spawn receipt as a completed result. Full output is available at the returned `agent://<id>`; `history://<id>` exposes the transcript, and `write agent://<id>` can coordinate/resume an existing agent when available. [1][3]

The user can inspect native Agent Hub (`Alt+A`), pinned subagent progress, and transcripts; do not assert that workers are invisible. Report the evidence and material findings in the main response regardless of UI visibility. [4]

Use a separately instantiated risk-appropriate reviewer profile or approved security specialist,
never the implementer. One reviewer may cover compatible changed scopes; do not multiply mandatory
reviews per implementation item. Give acceptance, actual changes, source paths and explicitly
permitted verification commands. Require observed evidence and limits, not a copied worker summary.
Missing independent capability remains a blocker; author/coordinator self-checks do not replace it.
For fix batching and coordinator-only mechanical tails, follow `SKILL.md` §5; preserve review provenance.

Sharpen the failing brief or isolate its genuinely hard part first, then reassess. A stronger profile
within the already authorized policy/plan needs no redundant question; a new route/budget outside it
needs exact permission. No blind retries, fixed ladder, hidden override, shared settings mutation or
paid fallback. Supplemental review uses the explicit `second-opinion` choice above; do not
probe or automatically invoke Codex. Read `references/codex-review.md` only if the user explicitly
requests that different CLI route and grants its data-sharing permission.

## Authorized native sources

1. [`task`: schema, results, child context, headless permissions, isolation](omp://tools/task.md).
2. [`ask`: UI, answer metadata, timeout behavior](omp://tools/ask.md).
3. [`wait`: availability, automatic delivery, wake behavior](omp://tools/wait.md).
4. [Task agent discovery, precedence, native model overrides, Agent Hub](omp://task-agent-discovery.md).
5. [Model/provider configuration, model roles, selectors, availability](omp://models.md).
6. [Settings layers, read-only inspection, overlays, persistence](omp://settings.md).
7. [Public eval agent/workpool API and its schema-exposed model selector](xd://eval/agents).

Task/eval model-selection contracts rechecked on 2026-10-07; other native references inspected on
2026-10-01. The current loaded schema and observed execution remain authoritative.
