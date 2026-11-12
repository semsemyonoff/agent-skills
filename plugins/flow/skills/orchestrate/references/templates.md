# Plan and report templates

Use the user's language. Separate capability, assessed complexity and requested native profile.
Expected configuration is not actual execution. Show accessible effective model/reasoning values;
do not guess missing values, and do not omit known configured values because a spawn receipt is terse.

## Plan

State the settled approach and authorized routing/budget policy, then a compact table:

```text
| # | Capability / slice | Complexity and evidence | Requested native profile | Expected configured model + reasoning | Input / done criterion / dependencies |
| - | ------------------ | ----------------------- | ------------------------ | ------------------------------------- | ------------------------------------ |
| 1 | Research invariants | bounded fact gathering; paths known | discovered research profile | effective config value or unresolved alias | source locations + invariants; before 2/3 |
| 2 | Implement fixed callers | light: API/paths settled, contained effects | permitted light editor | effective configured pair | approved contract; parallel with 3 |
| 3 | Implement lifecycle ownership | strong: focus/state transitions cross boundaries | permitted strong editor | effective configured pair | lifecycle acceptance; after 1 |
| 4 | Selected independent review only | risk-based; omit when not selected/required | separate permitted reviewer profile | effective configured pair | current changes + acceptance; after 2/3 |
| 5 | Gates and runtime scenario | tools and scenario risk | reviewer/checker or coordinator | effective pair if delegated | stable tree + evidence packet |
```

These are examples, not a mandatory five-row decomposition or model benchmark. Inline trivial work
and combine related simple slices first. List the requested native profile and any permitted
schema-exposed invocation selector separately, including ordered candidates when used. Current omp
task items and public eval support `model`; discover the live surface rather than copying fields.
Actual identity is **not spawned yet**, never a model-name guess. Missing required profiles/aliases
are prerequisites, not silently replaced by generic/default task. A justified generic choice must
name its verified effective pair, explicit policy permission and suitability for the assessed class.

Assign integration to an existing slice owner or dedicated worker; name ownership, dependencies,
contracts and checks owner. Include a reviewer only when selected or required by higher-priority
instructions. The trivial-inline exception remains.
List permitted escalation profiles and conditions; outside routes require a question. Exact external
actions need separate authorization. Confirm through the actual ask UI or text fallback: Start /
Start phase by phase / Change plan. Autonomous is default; silence, timeout/default, redirect or
cancellation is not approval.

Default review mode: executor checks, no separate reviewer. If material risk warrants a review
recommendation, give a brief reason and combine the choice with confirmation. Do not add a
mandatory review/extra-opinion question to every small task. Preserve actual choices; follow
`review.md` only when review is relevant. No extra opinion enables an unchosen native reviewer.

## Final report

```text
<2-5 lines: changed behavior and actual outcome>

| # | Capability + complexity / short reason | Requested native profile | Configured/requested pair | Exposed actual model + reasoning | Outcome / routing deviation |
| - | ------------------------------------- | ------------------------ | ------------------------- | ------------------------------- | --------------------------- |
| 1 | ... | ... | effective config/source or unknown | metadata value/source or unknown | ... |

Executor checks: <actual commands/scenarios and outcomes, with required gaps distinguished>
Independent review: <not selected, or selected identity/profile, current scope, outcome/findings>
Escalations: <only actual deviations/approvals>
Extra opinion: <only if selected/declined; actual status and later unreviewed changes, never assumed>
Integration: <completed implementation/gates versus pending PR/CI/merge; push is not completion; without an applicable ship handoff, only confirmed remaining delivery steps (never a push already done; a finished stage is not a finished task)>
Not verified/blocked: <exact acceptance or capability still unavailable>
```

The routing table is required when any route deviated: substitution, escalation, missing profile,
or a worker the plan did not list. Otherwise replace it with one line naming the profiles used and
where actual identity came from (or that it was not exposed). Preserve known configured/requested
facts even when actual metadata is unavailable; mark actual unknown explicitly. Record actual substitutions, effort clamping and routing limits rather than
claiming exact execution from an alias. No incomplete done claims, failed-review-as-clean verdicts,
author self-review-as-independent claims or inferred subscription-savings percentages.

Use only applicable subchecks, not a mandatory checklist. Keep required failed/unverified levels as
concrete acceptance gaps; a neighboring pass is not proof. Report non-required failures as limits,
not whole-product failure, and never roll false/error into an undifferentiated passed result.

For an actual transfer/stop or ship checkpoint, read `handoff.md`; do not create a handoff after
every phase or load its detailed ship branch for ordinary implementation.

