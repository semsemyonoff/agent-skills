# Native review adapter

Use one process from SKILL.md. Identify the actual harness, live delegation schema, reviewer roster
and permissions before dispatch. Keep model/effort selection in native configuration; report only
exposed facts. An unavailable worker remains unavailable, not author self-review.

## omp

The optional native resource is `agents/omp.md` relative to the loaded skill directory:
`name: plan-review`, `model: "@plan_review"`, `tools: [read, grep, glob]`, `spawns: []`.
The operator may expose it through native agent discovery and configure `modelRoles.plan_review`;
loading the skill alone installs nothing. Do not change configuration or assume a particular model.
Existing native overrides are authoritative; there is no task `model` parameter or automatic upgrade.

Prefer the actually discovered `plan-review` agent. With the usual native batch schema, use required
shared `context` and one `tasks[]` item with `agent: "plan-review"`, `task` and `solutionSpace`.
The brief explicitly selects the worker branch, passes the full plan/request/rules context and exact
resolved resource paths, and prohibits shell/tests/writes/nested dispatch. Read the real schema;
flat variants use their actual item fields. Do not use agent=task as a pretend specialist reviewer.
If the configured agent is absent/disabled/blocked, say so; use a different genuine read-only reviewer
only after an explicit compatible route choice, never a silent model/configuration change.

The native omp agent reads `skill://plan-review` through `read`, then uses the worker branch and
its relative references. That URI is omp-specific and does not appear in the shared core. Background
jobs notify on completion; do independent work or wait only when blocked. Do not poll or claim an
unfinished result; distinguish progress from the delivered reviewer findings.

## Claude Code

Discover exposed `Agent` or `Task`, its actual schema, and an independent reviewer identity rather
than assuming a fixed name or opus. Dispatch only an available reviewer whose actual contract can
perform the supplied worker branch without shell/tests/writes/nesting. An upstream reviewer that
requires its own shell rule loader or conflicting template checks is not automatically compatible;
do not silently alter its definition or advertise the author's review as independent instead.

Use only supported parameters. Supply original task, plan path, source evidence, resolved criteria
and the exact rules packet. Read the current completion/background mechanism; no omp wait API is
invented here. The operator's existing upstream Claude workflows are not replaced by this package.

## Driver decision buttons

After the actual reviewer report, apply only the driver's bounded target-plan correction rules from
SKILL.md. Never give the worker editing tools or re-dispatch it to approve the driver's changes.
For each unresolved architectural/product choice, conflict, agreed scope/route/budget change or
ambiguity, offer 2–5 concrete options with tradeoffs and one recommended option.

- **omp:** use the exposed `ask` tool with its current schema. Questions use `id`, `question`,
  options with `label`/optional `description`, and optional `multi`/`recommended`. Supply a stable
  question id; use `multi` only for compatible independent choices and mark the recommendation
  without treating it as selected. Discover the actual field shapes rather than inventing them.
- **Claude Code:** use `AskUserQuestion` only when exposed, with its actual `header`, options and
  `multiSelect` fields. A recommended label is advice, not authorization.
- **No native UI:** present the same numbered text options/tradeoffs/recommendation and wait for a
  real answer. Do not assume an unavailable tool ran or replace a necessary choice with a default.

Only an explicit user answer resolving the choice permits its dependent target-plan corrections.
`timedOut`, defaults/auto-selection, redirect, cancellation, silence or missing response never count
as approval. Independent safe findings may already be fixed; dependent findings stay unapplied until
answered. Explicit review-only/no-edits disables autofix throughout, even when options are discussed.

## Driver rules exception

Before dispatch, the driver may run the bundled read-only `scripts/load_rules.py` once with
`--name planning --project <actual-project-dir>`. It reads only the supported rule candidates and
prints their selected path/provenance/content. This exception permits no arbitrary shell, tests,
LLM review loops, external actions or settings changes. Pass the result to the worker; the worker
only reads the selected file with its native read tool and never runs the helper.
