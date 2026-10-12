---
name: plan-review
description: 'Run one independent read-only review of a concrete implementation plan, then let the driver apply evidenced unambiguous corrections to that target plan only; ask for real choices before decision-dependent changes. Use for review this plan, check the plan before implementation, plan-review, «проверь план», «ревью плана», «оцени план на полноту и переусложнение», or an explicit review choice after planning. Explicit review only/no edits/«только review»/«без правок» disables driver corrections. Not for implementing the plan, running tests or automatic review loops.'
license: MIT
---

# Plan review

One separate read-only reviewer, followed by bounded driver corrections or user choices, not another
review. Reply in the user's language. Resolve bundled references from the directory of the loaded
`SKILL.md`. No fixed model, upstream template or mandatory CLAUDE.md file is required.

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
2. Load `references/runtime.md`. Invoke only this skill's bundled **read-only rules resolver** once,
   with `--name planning` and the actual project directory (`references/rules.md`). This narrow
   driver exception permits no other shell command, tests, validation gates or environment dumps.
   Retain selected rule path/provenance/content. Missing rules are normal; unreadable rules are a blocker.
3. Give a genuinely separate available read-only reviewer a complete brief: worker branch, resolved
   skill/reference paths, plan path, original task, validated decisions, actual project root, loaded
   rule path/provenance/content, relevant source locations, exact scope and uncertainty. Specify no
   tests/writes/commits/config changes, no nested spawns and no shell beyond the read-only inspection
   fallback in `references/runtime.md` when the reviewer lacks native search tools. Discover native
   availability and dispatch schema; do not install an agent, invent model fields or secretly switch
   routing.
4. Wait using the native completion mechanism for the actual report. A spawn receipt or unfinished
   worker is not a review. If unavailable, report that prerequisite and stop; the author's self-check
   cannot count as independent review. Preserve the actual verdict, reviewed plan text/sections,
   findings and limits before making any corrections.
5. Apply the driver corrections/choices below, then report the original reviewer verdict and its
   reviewed version separately from actual applied changes and unresolved findings/choices.

An explicit review request authorizes this one dispatch and the bounded target-plan corrections below,
unless review-only/no-edits was requested; do not ask again just because delegation starts. It never
authorizes implementation, other-plan/code/rules/config edits, external writes, installs, ralphex/exec,
commits, push or a paid second opinion. No automatic retry, second LLM review or revision/review loop.

## Driver corrections and choices

Check each reported finding against its cited plan section, source/rule evidence, original task and
validated decisions. A verdict is not permission to accept every suggestion. Unsupported findings or
missing facts remain explicit unresolved items; never invent evidence or decisions to make them pass.

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
driver check, not independent approval: run no project gates/tests and dispatch no second automatic
LLM review. Attribute `APPROVE`/`NEEDS REVISION` only to the text the reviewer actually saw; never
promote the original verdict to approval of unseen revised text.

Finish with: **Original review** (verdict, reviewed version/scope/limits), **Applied changes** (target
sections and evidence, or none; driver consistency-check limits), and **Unresolved** (unapplied
findings, missing facts or choices awaiting an answer). Stop after this one review and bounded
correction/choice resolution; a new independent review or execution needs an explicit new request.

## Worker branch

Use read/search/discovery tools. Only when the harness exposes no native search or listing tool, use
the read-only shell inspection fallback in `references/runtime.md`; otherwise no shell. Never helper
execution, tests, writes or configuration changes. Read the plan and original request; inspect just the relevant source/patterns and already
provided project guidance. Do not demand a CLAUDE.md file or search unrelated context files.
Read `references/criteria.md` and evaluate the actual solution, not conformance to a rigid template.

Use the planning rules supplied by the driver as criteria. Re-read the selected file via the read
tool to check its content when present; report changed/unreadable provenance as uncertainty instead
of claiming the rules were checked. Do not merge project and user rules or run the resolver in a
worker. Missing original-task/source facts limit review; do not guess them or label incomplete
coverage APPROVE. Conditional rules apply only when their actual workspace/executor conditions hold.

Return a short report:

```text
APPROVE | NEEDS REVISION — plan path
Scope/rules: checked sections/sources and selected rule provenance; exact limits.
Findings (only proven): severity; plan section; source/rule evidence; impact; minimal fix.
Unknowns: facts/capabilities that could not be established, separate from proven defects.
```

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

Adapted from [umputun/cc-thingz](https://github.com/umputun/cc-thingz), planning 3.10.2 `agents/plan-review.md`.
Upstream MIT copyright and permission notice are included in [LICENSE](LICENSE).
