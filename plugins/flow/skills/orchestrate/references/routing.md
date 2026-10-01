# Work categories and native routing

Use this table to split work. Choose the actual native agent from the loaded runtime adapter;
model selection belongs to that harness's configuration. Do not translate categories into a
cross-harness model ladder or maintain a second routing settings file.

| Category | Work | Boundary |
| --- | --- | --- |
| Research | File discovery, source reading, fact gathering, recon with source locations | Read-only; use interpretation-capable research when needed, not an editing worker |
| Mechanics | Exact, bounded transformations with a worked example and complete spec | No unresolved design choices; split out judgment work |
| Implementation | Features, refactors, tests, docs, or debugging requiring decisions within the agreed design | Disjoint files/contracts; no unapproved scope expansion |
| Review | Independent correctness, regression, boundary, security, or data-integrity analysis | A different worker from the implementer; findings require disposition |
| Second opinion (optional) | A specifically approved additional checkpoint on the stable result | Not a substitute for mandatory review; need not be another vendor |

The coordinator plans, manages dependencies/approval, evaluates findings, and runs shared checks.
An implementer may perform local self-checks if its brief allows them, but these are never independent
review. For parallel changes reserve shared gates/formatters for the phase's verification owner.

## Choosing a route

1. Classify each slice by required capabilities, not size alone. Split mixed mechanics/design work.
2. Discover the adapter's enabled agents and effective native overrides. Check tool permissions,
   edit/read boundaries, available reviewer, background support, and nesting limits.
3. Record the native worker identity in the plan. Record model/effort only if observed and permitted;
   an alias is an alias, not evidence of a resolved model. Use unknown when not exposed.
4. If the configured worker cannot do the work, sharpen/split the brief before proposing a different
   approved native route. Do not guess more expensive or different-provider fallback models.
5. If a native system reports an unexpected substitution, stop affected work and disclose the
   routing deviation. Obtain approval before continuing or accepting substituted output.

Examples: an exact rename is mechanics; designing the replacement API is implementation/design;
analyzing a migration for lost data is review. Risky backend work needs a focused independent review
regardless of which model native configuration assigns. Lack of a configured reviewer remains a
capability gap, not an invitation for the implementer or coordinator to call self-review independent.
