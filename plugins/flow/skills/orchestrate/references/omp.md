# omp adapter

Use this adapter only in omp. Keep the process in the loaded `SKILL.md`; this file maps shared categories onto native capabilities. `SKILL_ROOT` is the resolved directory of that loaded file. Resolve all bundled resource paths against `SKILL_ROOT` and give workers the resolved paths. Do not use Claude-specific environment variables to locate resources.

## Discover before dispatch

Read live `task`/`ask`/`wait` schemas and the exposed roster. In the project cwd, run the read-only
helper using the loaded skill's resolved directory (pass `--profile` for a named native profile):

```sh
python3 "$SKILL_ROOT/scripts/omp_profiles.py"
```

It reads native project/user profiles and five allowlisted config keys. Use needed rows, not the
whole output, in the plan. Additional confirmed agent directories can be supplied in discovery
order (`--help`); uninspected sources, missing keys and session-only overrides remain unknown.
This is a hint: live schemas/roster and observed spawn metadata stay authoritative. Disabled agents,
spawn/depth limits, plan mode and hooks can block/alter routes. Never install or change settings.
Read `references/native-setup.md` only for native-profile setup or missing/unexpected routes. [1][4]

| Capability | Native selection after assessment | Boundary |
| --- | --- | --- |
| Research | Discovered `scout` or approved research profile | Source-grounded facts, not an editing substitute |
| Mechanics | Discovered `sonic` with a verified permitted exact-work pair | Exact known transformations only, not universal development |
| Implementation | Discovered `flow-worker-light`, `flow-worker-standard`, `flow-worker-strong` or approved equivalent | Same full editing capability; choose by uncertainty/risk, not the category name |
| Selected review | Separate discovered risk-appropriate `flow-review-*`, reviewer/security specialist or approved equivalent | Only selected/required review; minimum sufficient pair |
| Optional extra opinion | Discovered `second-opinion`, explicitly selected | No hidden native-review prerequisite |

Assess with `references/routing.md`; bundled resource files do not prove deployment. Missing
profiles/aliases are prerequisites. Omitting `agent` requires an explicit permitted effective pair
and suitability reason; discover its resolution (usually task, different for restricted parents).
Do not silently obtain a default task or substitute an unapproved alternative. [1][4]

When exposed, task-item `model` accepts a string or ordered nonempty array, never batch-top model.
Every candidate/known role expansion needs assessed policy permission. Precedence: explicit model,
`task.agentModelOverrides`, profile selector, task/session fallback; aliases use `modelRoles`.
`@default` means the live parent model (not literal `default`/`inherit`); reasoning follows native
precedence. Candidates are preferences, not a fallback allowlist. Discover public eval
`agent()`/`workpool()` model support separately. Older surfaces require a discovered suitable profile;
no hidden bridge fields or shared settings mutations. [1][4][7]
Show accessible configured/requested pairs before dispatch. Actual identity/reasoning requires
exposed `resolvedModelIdentity`, `resolvedThinkingLevel`, `resolvedModelIsFallback`, `resolvedModelRoute`;
unavailable actual stays unknown, not known configuration. Stop unexplained out-of-policy substitutions.
Never dump private profiles or credentials. [1][4][5][6]

## Native confirmation UI

Use main-session `ask` when available; inspect its live schema. The current payload has `i`
(short intent) and `html` (one semantic `<form>`). Every control needs a `name` and a wrapping
`<label>`; group choices with `<fieldset>`/`<legend>`. Use radio inputs for one choice, checkboxes
for several, select for long lists. No scripts, styles, `style=`, buttons or submit inputs: the UI
supplies Submit/Cancel. Do not add a manual Other option; the UI provides it. Example:

```json
{
  "i": "Confirming local execution",
  "html": "<form><p>Approved scope and checks go here; no commit, push or external writes.</p><fieldset><legend>Execution</legend><label><input type=\"radio\" name=\"execution\" value=\"start\">Start</label><label><input type=\"radio\" name=\"execution\" value=\"phased\">Start phase by phase</label><label><input type=\"radio\" name=\"execution\" value=\"change\" checked>Change plan / do not start</label></fieldset></form>"
}
```

Write all visible form text in the user's language and include the actual plan/permissions, not
the example's placeholder. Use a conservative non-authorizing default. When review is relevant,
add a separate named group to the existing form; do not insert a mandatory review question.
Submitted radio/select values arrive by name (e.g. `{"execution":"start"}`); checkbox groups
return arrays and unchecked controls may be omitted. Carry the actual selected value/custom text
into the next step; an omitted review choice authorizes no call.

Inspect result metadata/notices as well as values. Timeout, automatic default, cancellation,
redirect, silence or a worker answer is not consent, even if the value says Start. If provenance
cannot distinguish an explicit response from an automatic selection, ask for explicit confirmation
before acting. Absent/headless UI means ask in text and wait; do not enable UI/change timeout or
invent another payload. Phase-by-phase needs explicit choice. External/irreversible actions still
need exact permission separate from ordinary local-plan approval. [2]

Workers have no interactive approval UI; omp's child tool approval mode is headless. Give every worker the approved-action boundary and require it to return blockers instead of performing an unapproved effect. Do not rely on a worker permission dialog to stop it. [1]

## Supplemental second opinion

Only when requested or relevant, offer an additional opinion as described in `references/review.md`;
no automatic offer or call is required. Discover `second-opinion` and its permitted read-only route.
Combine any choice with plan confirmation when useful and preserve a previous yes/no. Start alone
grants no call. If an explicitly selected route is missing, name the gap; never substitute Codex CLI
or a default worker, and never silently add a native reviewer.

After explicit acceptance, launch one fresh `second-opinion` at the agreed stable checkpoint
through the live task/eval schema. Supply goal, scope, original acceptance, pre-existing edits and
observed checks. It must neither edit nor delegate. Do not require shell/tests from a read-only
profile without those capabilities. Freeze the scope; assess actual findings and apply the selected
review-mode/failure rules in `references/review.md`. Another extra round needs new permission.

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

With `async.enabled`, spawns return job/agent IDs and results auto-deliver; blocking definitions
return inline, including mixed batches. Do independent work first; use native argument-free `wait`
only when blocked. No polling. Process partial/safety-cap returns and steering, then keep waiting
for outstanding dependencies. A receipt is not completion. `agent://<id>` holds full output,
`history://<id>` the transcript; `write agent://<id>` can coordinate/resume when available. [1][3]

Before idle, follow SKILL.md's waiting notice and point to Agent Hub (`Alt+A`), pinned progress and
transcripts. These are user-visible; report material evidence in the main response too. [4]

Only for selected or higher-priority-required review, use a separate risk-appropriate reviewer;
follow `references/review.md`. Otherwise executor checks suffice. Discover tools before delegating
browser smoke; absent browser tooling means reproduce in the coordinator and delegate diagnosis.
Missing selected review remains a gap; missing unselected review does not block completion.

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
