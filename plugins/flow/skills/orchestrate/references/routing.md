# Capability, complexity and permitted native routing

Choose two axes independently: what tools/authority the slice needs, and how much reasoning its
remaining uncertainty/risk needs. Model plus reasoning is the result of that assessment and the
already authorized native policy, not an effect of the word implementation. No shared model IDs,
provider ladder or second orchestration settings file.

## Capability

| Capability | Boundary |
| --- | --- |
| Research | Read-only source-grounded facts; use the real research specialist |
| Mechanics | Exact prescribed transformation with known inputs/paths and no design decisions |
| Implementation | Full editing/command capability inside assigned files; code, docs and debugging all need assessment |
| Review | Only when selected/required: separate read/verification worker, not the author; assess risk independently |
| Optional second opinion | Explicit opt-in checkpoint; no automatic review prerequisite or fallback |

Do not make a scout or mechanical specialist a generic developer to save tokens. All implementation
profiles must have the same adequate editing capability; different budgets are not different scopes.
A large exact migration can be mechanical; a one-line lifecycle/security change can be high risk.

## Assess every slice, including review

Record a concise evidence-based reason using these factors:
- remaining decisions and whether the cause/solution is known;
- known approach, established pattern, fixed API and confirmed file paths;
- change radius, coupling and dependencies, not just line/file count;
- cost of being wrong: security, data integrity, public contracts, lifecycle, focus/state ownership,
  concurrency and migration effects.

| Complexity profile | Evidence needed | Selection |
| --- | --- | --- |
| Exact | Complete mechanical spec; no unresolved judgment or hidden boundary | Minimum permitted exact-work pair; specialist capability still appropriate |
| Light | Small bounded implementation/review; approach/API/paths settled; low uncertainty and contained failure cost | Minimum permitted light pair, not a mechanical worker pretending to implement |
| Standard | Ordinary development/review with bounded local decisions or interacting known boundaries; diagnosis can start with an unknown cause when the search is contained and acceptance is observable | Permitted standard pair |
| Strong | High failure cost, complex lifecycle/concurrency, or substantial cross-boundary uncertainty such as competing subsystem hypotheses with weak observability | Permitted strong pair with adequate reasoning |

These labels are not hard-coded model families. Read the user's permitted native mappings; exact
levels/pairs come from effective profile configuration. Do not assume all development uses the
session model, all docs are mechanical, all reviews are strongest, or all task workers should be
made cheaper globally. If evidence spans classes, isolate the uncertain/high-risk part when that
reduces coupling rather than escalating the entire simple remainder.

Use standard for ordinary development with bounded engineering judgment; use light when the
approach/contracts are already settled. An unknown cause alone does not make a local reproducible
bug strong. For strong, name the concrete uncertainty or at-risk invariant and why standard is
insufficient. File count, an integration label or an unfamiliar API alone does not establish that.
High failure cost can still require strong even when the fix is known.

When a difficult contract can be settled separately, assign that decision to a strong-capable worker
and the resulting well-defined implementation to an assessed light/standard worker. Preserve the
dependency: implementation waits for the contract. Keep tightly coupled work together rather than
creating extra handoffs merely to use cheaper workers.

Illustrations, not benchmarks or measured model adequacy:
- Wiring two callers to a fixed editor API can be light when error/lifecycle behavior is already fixed.
- An onboarding/documentation change with known configuration keys can be light, despite editing files.
- Portable runtime instructions can be light with settled contracts or standard when cross-adapter
  decisions remain; the docs label decides neither.
- A reproducible local parser bug with unknown cause, contained search and observable expected output
  can be standard; an unknown distributed-state race with competing subsystem hypotheses is strong.
- Viewer focus/dialog/lifecycle ownership can warrant strong reasoning even in a small change.
- A reviewer of a public/data/lifecycle boundary may need strong despite a light author's initial estimate.
- Ordinary bounded implementation and its separate review can both be standard; reviewers assess
  the result's risk independently, not the author's model or a requirement to use another family.

## Resolve the allowed pair

1. Assess capability and complexity before naming a worker.
2. Discover enabled native profiles, tools/spawn permissions, effective overrides and the approved
   routing/budget policy. Concrete selectors stay in native configuration, never this reference.
3. Choose the least costly sufficient **allowed** profile. Record complexity/reason, native identity,
   expected configured model/reasoning when accessible, and requested profile/overrides distinctly.
   Do not turn known configuration into unknown simply because a spawn summary omits it.
4. Missing or unapproved profiles are explicit prerequisites. Never silently dispatch default task,
   mutate settings or use an internal bridge override. A generic route is legal only when policy
   expressly includes its effective capability/pair and the row explains why it matches this slice.
5. After spawn, show actual model/reasoning only from exposed result/progress metadata. A config alias
   is a requested expectation, not proof of execution. Stop unexplained substitutions outside the
   selected/authorized route; do not hide them as a successful more-expensive fallback.

## Approval and escalation

An already authorized matching profile plus exact plan approval permits ordinary assignments; no
question per worker. A configuration entry alone is not permission for a new paid fallback.
Name any permitted escalation routes/budget conditions in the plan. After failure, sharpen the brief
or split the hard part and reassess first. Escalate only within that pre-authorized policy/plan;
otherwise ask for the exact new route. No blind retries, fixed tier ladder or cross-provider fallback.
Do not change shared model roles/agent overrides between parallel calls: that is a routing race.

## Overhead and verification

Default is executor checks without a separate reviewer. Do trivial work inline when allowed and
combine related simple changes; preserve explicit delegation/review acceptance. Recommend review
for material risk, but a recommendation is not permission to launch it. When selected or required
by higher-priority rules, use one minimum-sufficient reviewer for compatible scopes; see `review.md`.
Reserve shared gates/formatters for the checks owner after edits land. Missing unselected review
blocks nothing; missing selected review stays missing and self-checks cannot be relabeled independent.
Do not promise subscription-quota savings from API prices: context, overhead and accounting differ.
