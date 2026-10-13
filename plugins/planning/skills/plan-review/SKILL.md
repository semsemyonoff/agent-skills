---
name: plan-review
description: 'Review a concrete implementation plan with one independent read-only native pass by default and bounded target-plan corrections; explicit review chain enables at most three native/other-provider/native passes. Use for review this plan, check the plan before implementation, plan-review, review chain, «проверь план», «ревью плана», «цепочка ревью», or a selected planning review. Review-only/no-edits and no-external restrictions prevail. Not for implementation, tests or automatic approval loops.'
license: MIT
---

# Plan review

One separate read-only reviewer by default, followed by bounded driver corrections or user choices.
Only an explicit chain request or selected planning-rules opt-in enables `sections/chain.md`; load
that section before dispatch. Reply in the user's language. Resolve resources from the loaded
`SKILL.md` directory. No fixed model, upstream template or mandatory CLAUDE.md is required.

## Select driver or worker

- **Driver:** the main session receiving an explicit review request, including a selected next step.
  It prepares the brief, invokes a separate reviewer, then handles corrections/choices below.
- **Worker:** an already delegated independent reviewer whose brief/agent role identifies this review.
  Apply the worker branch below yourself. Never dispatch another reviewer recursively.

## Driver branch

1. Identify the concrete plan path and original task/design from context. Read the available plan
   inventory only when necessary; if the target remains materially ambiguous, ask one question.
   Never select an arbitrary plan or reconstruct the original requirement from the author's guesses.
   Capture explicit **review only**, **no edits**, **только review** or **без правок** restrictions
   (including equivalent wording): they disable all driver autofix, including otherwise safe findings.
2. Load `references/runtime.md`. Run the bundled read-only rules resolver once with `--name planning`
   and the actual project directory (`references/rules.md`). Keep selected path/provenance/content.
   Missing rules are normal; unreadable rules block review. Determine default versus opt-in chain;
   rules cannot override explicit no-edits/no-external or create external-disclosure permission.
3. Capture the current target with `scripts/review_state.py snapshot PLAN`. Give a genuinely separate
   available read-only reviewer the verbatim `plan_text`, absolute `plan_path` and `plan_version`,
   original task, settled decisions, project root, rule packet, relevant evidence paths and exact
   permissions/uncertainties. A path alone does not prove the reviewer saw those bytes. Specify the
   worker branch, resolved resource paths, no writes/tests/helpers/nesting and only the conditional
   inspection fallback from runtime.md. Discover actual native schema/routing; install nothing.
4. Wait for the completed canonical JSON report, not a spawn receipt. Validate it with
   `scripts/review_state.py validate PLAN --version EXPECTED` on finite stdin. Validation checks
   schema, identity and current file bytes. Unavailable/failed/empty/invalid/stale review stops with
   explicit unresolved status; no retry, author substitute or silent route change. Preserve original
   report and evidence before corrections. Recheck the same report/version immediately before fixes;
   if the target changed, stop rather than overwrite it.
   A denied or unavailable resolver/snapshot/validation helper is a terminal capability failure.
   Never substitute a manual/synthetic digest, `UNAVAILABLE`, report prose or permission to skip the
   helper. Preserve prior evidenced blockers and original acceptance in Unresolved, not only diagnostics.
5. Apply corrections/choices below, then report original verdict/version separately from applied
   changes and unresolved findings. Follow the bounded chain section only when selected.

An explicit review request authorizes one native dispatch and bounded target-plan corrections unless
review-only/no-edits applies. It does not authorize implementation, other artifacts/config edits,
external disclosure, installs, execution, commits or push. Default: exactly one independent native
pass, no retry or second review. The opt-in section alone permits its bounded additional passes.

## Driver corrections and choices

Check each reported finding against its cited plan section, source/rule evidence, original task and
validated decisions. A verdict is not permission to accept every suggestion. Unsupported findings or
missing facts remain explicit unresolved items; never invent evidence or decisions to make them pass.

**Correction prerequisite:** successful canonical validator output for the exact current snapshot,
revalidated immediately before the edit. A supplied "valid" report or an explicit safe-fix request
does not replace that check. Denied/failed validation means no corrections, no reviewer dispatch
to repair it and no continuation; report the blocker even when the intended edit is otherwise safe.

Unless review-only/no-edits applies, automatically fix only the specific review-target plan for
unambiguous evidenced corrections consistent with the original task, validated decisions and loaded
rules. Use local plan-edit tools; do not edit code, another plan, notes, rules or configuration, and do
not expand scope. No extra revision request is needed for these corrections.

Architectural/product choices, conflicting requirements, changes to agreed scope/route/budget, or
ambiguity require **2–5 concrete options**, their tradeoffs and **one recommendation**. Use the native
buttons described in `references/runtime.md` when exposed; otherwise present text options and wait.
Obtain a real user answer before treating a decision as settled or applying its dependent findings.
Timeout, redirect, cancellation, silence or a recommended/default option is not consent.

Independent safe findings may be fixed before asking; findings dependent on the unresolved decision
remain unapplied. Apply only target-plan corrections supported by the explicit answer and remaining
constraints, never execute the selected route or silently change an agreement. In review-only mode,
report findings/options without any autofix. Keep blocked choices visible if no real answer arrives.

After any changes, re-read the target plan and check local consistency of goal, scope, decisions,
dependencies, acceptance and commands against already available facts and loaded rules. This is a
driver check, not independent approval: run no project gates/tests. In default mode dispatch no second
automatic LLM review. Attribute APPROVE/NEEDS REVISION only to the exact reviewed version; unseen
revised bytes have no independent approval.

Finish with **Original review** (verdict/version/scope/limits), **Applied changes** (sections/evidence
or none; consistency-check limits), and **Unresolved** (unapplied findings, missing facts/choices).
Stop after default one-pass correction/choice resolution. In chain mode add the per-pass and final
current-version state from `sections/chain.md`; neither mode automatically starts execution.

## Worker branch

Use read/search/discovery tools. Only when the harness exposes no native search or listing tool, use
the read-only shell inspection fallback in `references/runtime.md`; otherwise no shell. Never helper
execution, tests, writes or configuration changes. Review the supplied exact snapshot, not a newer
file in its place; inspect only relevant source/patterns and provided project guidance. Do not demand
a CLAUDE.md or search unrelated context. Read `references/criteria.md`; evaluate the actual solution.

Use the planning rules supplied by the driver as criteria. Re-read the selected file via the read
tool to check its content when present; report changed/unreadable provenance as uncertainty instead
of claiming the rules were checked. Do not merge project and user rules or run the resolver in a
worker. Missing original-task/source facts limit review; do not guess them or label incomplete
coverage APPROVE. Conditional rules apply only when their actual workspace/executor conditions hold.

Return only the complete canonical JSON object (no fences, prose or duplicate keys):

```json
{"verdict":"APPROVE","plan_path":"/absolute/original/plan.md","plan_version":"<supplied SHA-256>","findings":[],"unknowns":[]}
```

Each finding has `severity` (`blocker` or `nonblocking`), nonempty `section`, `evidence`, `impact`
and `fix`. Each unknown has boolean `blocking` and nonempty `detail`. Include checked scope/rule
provenance and limitations within relevant evidence/unknown details, without invented defects.
Copy supplied path/version; never compute a substitute or run a helper. APPROVE forbids blockers
and blocking unknowns. NEEDS REVISION requires at least one blocker or blocking unknown.

Use APPROVE only when the examined plan solves the stated problem and no material proven defect or
blocking unknown remains. NEEDS REVISION is a finding about the examined text, not worker edit
permission. Do not pad a clean report with speculative findings, cosmetic headings or forced
test-count requirements. Stop after this pass; corrections and choices belong to the driver, not you.

## Resources

- `references/rules.md` — first-nonempty planning rules and driver/worker boundaries.
- `references/criteria.md` — evidence-based review criteria.
- `references/runtime.md` — native reviewer dispatch, read-only shell fallback, decision buttons and
  truthful unavailable paths.
- `agents/omp.md` — optional native omp plan-review resource, not automatically installed.
- `scripts/load_rules.py` and `scripts/test_rules.py` — driver-only resolver and offline tests.
- `scripts/review_state.py` — driver-only exact snapshot and canonical/current-version validation.
- `sections/chain.md` — opt-in bounded driver protocol, never a worker branch or default loop.
- `scripts/consult.py` — self-contained driver-only other-provider consultation; runtime constraints
  and result envelope in `references/runtime.md`.

Adapted from [umputun/cc-thingz](https://github.com/umputun/cc-thingz), planning 3.10.2 `agents/plan-review.md`.
Upstream MIT copyright and permission notice are included in [LICENSE](LICENSE).
