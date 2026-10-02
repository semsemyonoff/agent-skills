---
name: planning
description: 'Create a compact implementation plan in docs/plans from a task or validated design, preserving loaded custom planning rules. Use for write an implementation plan, plan this change, create a plan file, «составь план реализации», «запиши план», «создай файл плана», or a Write plan choice after brainstorm. Not for executing a plan, automatically committing it, or independently reviewing it; use the selected executor or plan-review workflow for those actions.'
license: MIT
---

# Planning

Create a runnable, proportionate plan, not its implementation. Reply in the user's language.
Read `references/runtime.md` for native questions and selected handoffs. Resolve all resources
against the directory of the loaded `SKILL.md`, never an assumed installation or Claude variable.

## 1. Load rules and reuse decisions

Invoke the bundled read-only resolver once with `--name planning` and the actual project directory
(`references/rules.md`). Keep selected path/provenance/content in context and apply only that
first-nonempty file. Missing rules are normal; unreadable rules are a blocker, not permission to
ignore them. Do not copy personal rules into a plan or change rules/configuration during ordinary use.

Read the original task and any validated design/plan. Carry decisions, files, scope, dependencies,
acceptance and permissions forward. Do short targeted repository discovery for missing facts;
use existing project conventions and declared commands. Do not fan out agents to implement anything.
Ask one materially necessary question only when repository/context cannot answer it; no fixed
questionnaire about goals, titles or testing. Do not re-open validated choices. Explore tradeoffs
only for a genuinely unresolved decision, and obtain its answer before treating it as settled.

## 2. Write the plan

Use the actual current date and a short descriptive slug: `docs/plans/YYYYMMDD-name.md`.
Discover existing plans before writing; do not overwrite an unrelated plan. An explicit request to
create a plan authorizes that local artifact, not code changes, commits or execution. Put substantive
research inventories/notes in `docs/plans/notes/<plan-name>.md` only when needed and link from tasks;
do not put another notes Markdown file among runnable plans.

Follow `references/plan-format.md`. Include the real goal, scope/non-goals, known constraints,
selected approach, files, dependencies, consumer-visible acceptance and actual verification commands.
Tasks are coherent outcomes with enough context to execute independently, not one checkbox per
function or exactly five checkboxes. Reuse existing checks; add permanent tests for plausible
behavioral boundaries, not wording/wiring or every touched function. No universal backwards-
compatibility shim policy: state the required contract and follow the user's cutover choice.

Verify proposed commands against available repository/configuration evidence or real read-only
help/schema. Do not run gates while planning, invent command ids/flags or describe unknown commands
as validated. Name missing prerequisites explicitly. Separate fast task-local gates from final
full-suite/e2e/coverage/lint verification when loaded rules require that split. Implementation tasks
must not repeatedly run the full acceptance suite under a cheap-sounding Validation Commands label.

Apply execution-specific rules conditionally, not to every repository:
- When loaded rules assign `docs/plans` to **ralphex**, keep that execution owner and its compact
  plan/Validation Commands contract. Full suites/e2e/coverage plus final lint belong in the final
  verification task. No checkbox moving the plan into completed: the execution owner handles
  reviews/finalization and archival. Creating the plan never starts ralphex.
- Apply other project-specific restrictions only from the loaded rules and only when their own
  stated conditions are confirmed. Do not infer applicability from the project's name or a remembered
  profile. If a required condition cannot be established, report it as unknown rather than checked.

Check the completed artifact against the request and loaded rules before handing it off; this is
an author's consistency check, not independent plan review. Do not publish a placeholder plan or
silently replace blocked requirements with a smaller scope.

## 3. Select a next step and stop

Report the created path, goal and unresolved prerequisites. Offer only relevant next steps:
- **One independent plan-review**, only on explicit selection. Pass the plan path, original request,
  design/decisions, project root, rule path/provenance/content, source evidence and permissions,
  including any review-only/no-edits restriction. Its reviewer stays read-only; its driver may correct
  only the target plan for evidenced unambiguous findings and must ask before decision-dependent edits.
- **Ready for ralphex**, when it is the configured execution owner: give the completed plan path.
  Give an invocation only after inspecting its actual help/schema; no invented flags or automatic run.
- **Orchestrate**, only if the user selects a compatible one-session route. Pass the full plan/design;
  do not bypass orchestration's approval or silently override an execution owner from loaded rules.
- **Stop**, leaving the plan without further action.

No exec workflow, implementation launch, automatic review/retry loop, installs, commits or push.
Selecting review includes bounded target-plan driver corrections unless **review only**, **no edits**,
**только review** or **без правок** was requested. Choices need a real answer; it is not permission to
expand scope, edit other artifacts or execute the plan. The review handoff reports the original
reviewer verdict separately from applied changes and unresolved choices, with no automatic re-review.

## Resources

- `references/rules.md` — portable rule selection and provenance.
- `references/plan-format.md` — compact, execution-aware artifact structure.
- `references/runtime.md` — native questions and workflow translation.
- `scripts/load_rules.py` and `scripts/test_rules.py` — offline read-only resolver and behavioral tests.

Adapted from [umputun/cc-thingz](https://github.com/umputun/cc-thingz), planning 3.10.2 `commands/make.md`.
Upstream MIT copyright and permission notice are included in [LICENSE](LICENSE).
