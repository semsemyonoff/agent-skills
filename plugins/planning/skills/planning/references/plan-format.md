# Compact plan format

Populate only sections relevant to the actual change. The outline below is a template, not permission
to leave placeholders, invent file paths/commands or impose a new project convention. Loaded rules
may refine it. Keep implementation tasks short: a fresh execution session needs the goal, exact files,
inputs/dependencies, concrete actions, acceptance and targeted checks, not a transcript of discovery.

```markdown
# Descriptive change title

## Goal and scope
The requested consumer-visible outcome. Explicit non-goals and protected files/actions.

## Context and decisions
Selected approach, relevant files/patterns, constraints, dependencies and execution owner.
Link substantial research notes under docs/plans/notes/ rather than repeating them here.

## Acceptance criteria
Plain lists, no checkboxes in either subsection; tasks carry the checkboxes.

### Executor acceptance
Observable behavior and relevant boundary/error cases that the run proves with its own commands,
permissions and prerequisites. Nothing here may need an action the run cannot perform.

### Owner acceptance after run
Requirements the run cannot prove (live client, manual UI, external systems, actions the plan
forbids), kept as stated, each with how to check it. No task walks this section.
Omit when empty.

## Run prerequisites
Existing state the run relies on (users, rows, API visibility). Each item: an exact read-only check
through the interface and role the scenario uses, and the expected result. Checked before the run
starts and again by the first dependent task. State the run may create goes into a task instead.
Omit when none.

## Validation Commands
Exact fast targeted commands, with cwd/service context, drawn from repository evidence.
Only applicable task-local gates here when the executor reruns this section after every task.

## Implementation Steps

### Task 1: Concrete coherent outcome
Files: exact create/modify paths.
Depends on: concrete prerequisites or none.
- [ ] Implement the specified behavior within these boundaries.
- [ ] Update the affected contract/behavior checks where needed and run the named targeted gate.
Acceptance: the outcome this task must establish for its dependants.

### Task 2: Final verification and documentation
Files: actual affected documentation/check files, if any.
Depends on: all implementation tasks.
- [ ] Verify every Executor acceptance criterion using the actual changed surface; report Owner
      acceptance as pending, not passed.
- [ ] Run applicable full-suite/e2e/coverage commands and final lint, with exact commands/context.
- [ ] Update the affected docs/changelog and report actual limits.

## Execution boundaries
Explicitly allowed state-changing actions and forbidden actions; required approvals/prerequisites.
Owner acceptance and other external or manual post-completion work is informational for the run, not
silently authorized by checkboxes, but still required and kept as stated.
```

Use real sequential numbers for the actual tasks; two tasks above are illustration, not a fixed count.
Omit inapplicable check types rather than inventing a coverage/e2e requirement. Add regression cases
for consumer-visible bugs/invariants, not a new test for each function or source-text assertions.

## Execution-owner conditions

When loaded rules select ralphex, Validation Commands are the fast targeted per-task gates. Full suites,
database-backed/e2e checks, coverage and final lint belong only in the final verification task. Include
a plain execution-owner note for archival if required; never a move-to-completed task checkbox.
No planner-side execution or automatic commit accompanies the file. For a different executor, follow
its actual approved contract rather than importing ralphex assumptions silently.

Other project-specific constraints come only from the loaded rules. Apply them when the conditions
defined by those rules are confirmed, not because of the project's name or remembered conventions.
Record unestablished conditions as unknown; do not claim their constraints were checked.
