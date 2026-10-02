---
name: plan-review
description: 'Run one independent read-only review of a concrete implementation plan against its original task, repository evidence and loaded planning rules. Use for review this plan, check the plan before implementation, plan-review, «проверь план», «ревью плана», «оцени план на полноту и переусложнение», or an explicit review choice after planning. Not for creating/editing the plan, implementing it, running tests or automatic review loops.'
license: MIT
---

# Plan review

One read-only pass over the actual plan and original problem. Reply in the user's language.
Resolve all bundled references from the directory of the loaded `SKILL.md`. No fixed model,
upstream command template, mandatory CLAUDE.md file or recurring review loop is required.

## Select driver or worker

- **Driver:** the main session receiving an explicit review request, including a selected next step.
  It prepares the brief and invokes a separate reviewer; it does not replace that review with its own.
- **Worker:** an already delegated independent reviewer whose brief/agent role identifies this review.
  Apply the worker branch below yourself. Never dispatch another reviewer recursively.

## Driver branch

1. Identify the concrete plan path and original task/design from context. Read the available plan
   inventory only when necessary; if the target remains materially ambiguous, ask one question.
   Never select an arbitrary plan or reconstruct the original requirement from the author's guesses.
2. Load `references/runtime.md`. Invoke only this skill's bundled **read-only rules resolver** once,
   with `--name planning` and the actual project directory (`references/rules.md`). This narrow
   driver exception permits no other shell command, tests, validation gates or environment dumps.
   Retain selected rule path/provenance/content. Missing rules are normal; unreadable rules are a blocker.
3. Give a genuinely separate available read-only reviewer a complete brief: worker branch, resolved
   skill/reference paths, plan path, original task, validated decisions, actual project root, loaded
   rule path/provenance/content, relevant source locations, exact scope and uncertainty. Specify no
   shell/tests/writes/commits/config changes and no nested spawns. Discover native availability and
   dispatch schema; do not install an agent, invent model fields or secretly switch routing.
4. Wait using the native completion mechanism and relay the actual result, findings and limits. A
   spawn receipt or unfinished worker is not a review. If unavailable, report that prerequisite;
   the author's self-check cannot count as independent review. No automatic retry or revision loop.

Explicitly requesting this review supplies its approval; do not ask again just because delegation
starts. It does not authorize implementation, plan edits, external writes or a paid second opinion.

## Worker branch

Use only read/search/discovery tools. No helper execution, shell, tests, writes or configuration
changes. Read the plan and original request; inspect just the relevant source/patterns and already
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
blocking unknown remains. NEEDS REVISION does not grant permission to edit anything. Do not pad a
clean report with speculative findings, cosmetic headings or forced test-count requirements. Stop
after this pass; any revision/re-review requires an explicit new choice.

## Resources

- `references/rules.md` — first-nonempty planning rules and driver/worker boundaries.
- `references/criteria.md` — evidence-based review criteria.
- `references/runtime.md` — native reviewer discovery/dispatch and truthful unavailable paths.
- `agents/omp.md` — optional native omp plan-review resource, not automatically installed.
- `scripts/load_rules.py` and `scripts/test_rules.py` — driver-only resolver and offline tests.

Adapted from [umputun/cc-thingz](https://github.com/umputun/cc-thingz), planning 3.10.2 `agents/plan-review.md`.
Upstream MIT copyright and permission notice are included in [LICENSE](LICENSE).
