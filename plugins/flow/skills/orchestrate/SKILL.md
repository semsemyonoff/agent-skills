---
name: orchestrate
description: 'Run explicit orchestration requests through recon, a role-based plan, approval, delegated execution, independent verification, and a short report in Claude Code or omp. Use for /flow:orchestrate, /skill:orchestrate, "orchestrate this", "you are the orchestrator", "delegate to subagents", "use subagents by complexity", «ты оркестратор», «ты оркестратор и проверяющий», «делегируй на сабагентов», «раздай сабагентам», «сабагенты по сложности», or choosing Orchestrate after a brainstorm. Do not trigger merely because a task is large or mentions workflow; do not substitute for a separate Workflow tool.'
argument-hint: "[task]"
---

# Orchestrate

Act as coordinator, not bulk implementer: establish facts, settle the approach, obtain approval,
delegate, independently verify, and report in the user's language. Use ONE process below in both
harnesses. Categories describe work, not models: research, mechanics, implementation, review,
and an optional second opinion.

## Select the runtime adapter

Identify the running harness from its actual tools/session, not the model's vendor. Read only the
applicable adapter before dispatch:

- Claude Code: `references/claude-code.md`.
- omp (including a Codex model inside omp): `references/omp.md`.

Resolve every bundled path from the directory containing this loaded `SKILL.md`. Do not assume an
installation location or environment variable. Discover available delegation, ask UI, independent
review, background/wait, permissions, and native routing. If neither adapter matches, describe the
missing prerequisite instead of inventing compatible APIs. Never edit configuration to make a route
available. Native setup and source citations are in `references/native-setup.md`.

A trivial, self-contained change may be done inline if dispatch costs more than the change; explain
that briefly. It still needs approval, truthful verification, and an independent review for a
claimed independently verified result. Missing delegation for substantive work is a blocker, not
permission to silently become the implementer.

## 1. Recon

Read the request and every referenced plan, audit, checklist, and artifact. Expand them into the full
acceptance surface; inspect the relevant current state and pre-existing edits without resetting
user work. Gather facts before planning. Make a handful of targeted reads inline; delegate broad
research to the adapter's read-only category. Return source locations and conclusions, not dumps.

Discover capabilities and native routes before promising workers or settings. Do not assume workers
are leaves, inherit this conversation, share every tool, or have identical user visibility. Bound
any permitted nested delegation in the brief; the coordinator retains ownership of the full plan.

If the approach remains undecided, name the decisions and offer
"Brainstorm (Recommended) / Plan anyway" («Обсудить варианты / Всё равно составить план») through
the adapter's real ask mechanism. Existing validated designs and explicit implementation choices
are input, not decisions to reopen. An optional second opinion is opt-in, not automatic recon work.

For a validated-design or plan handoff, carry the original goal, settled decisions, files, dependencies,
acceptance, selected rule path/provenance and exact permissions into recon and the plan table. Read
the full referenced artifact; do not restart design questions or discard its execution/gate boundaries.
A plan file or review verdict does not itself approve execution. If loaded rules assign the plan to
another executor, retain that owner unless the user explicitly chooses a compatible orchestration
route. Missing handoff facts are precise prerequisites, not an invitation to guess or invoke exec.

## 2. Plan

Use `references/routing.md` and `references/templates.md`. Every row names the category, discovered
native agent/route, inputs, precise done criterion, dependencies, and verification owner. Include
model/effort only when observed and permitted; otherwise write unknown or not exposed, never guess.
The native configuration is authoritative, not a shared skill model table.

Run independent slices in parallel with disjoint edit ownership. Specify shared contracts first;
serialize only a real dependency. Include a separate reviewer who did not implement the change.
Risky changes need a focused independent review (security, data integrity, concurrency, migrations,
or public API as applicable), plus executable checks. List external actions separately with their
exact target and permission needs. Approval of local implementation does not authorize them.

## 3. Confirmation

Offer "Start / Start phase by phase / Change the plan"
(«Начать / Начать по фазам / Изменить план») with the adapter's available ask UI. If unavailable,
ask in ordinary text and wait for an explicit answer. Silence, tool failure, a dismissal, or a
worker's answer is not approval. An explicit earlier approval of this exact plan can satisfy this
checkpoint; do not ask again just because delegation starts.

Default approved execution is autonomous through the report. Pause after phases only if the user
explicitly chooses that mode («по фазам», «пофазно», "phase by phase", or an explicit request to
approve each phase). Do not interpret a task broken into numbered steps as phase-by-phase permission.
Apply substantive plan changes before execution and obtain approval for changed scope or routes.

If offering a second opinion, distinguish it from the required independent reviewer. Ask separately
whether the available native/CLI route is wanted and obtain permission for its external model call.
Do not assume a different vendor. `references/codex-review.md` describes the optional CLI route.

## 4. Execution

Use `references/brief.md` for self-contained briefs: context, decisions, files, boundaries, data,
acceptance criteria, checks reserved for the verification owner, and concise output/evidence.
Workers must not run shared gates or formatters while edits overlap. No worker commits, pushes,
installs, changes native routing, or writes externally without exact explicit permission.

Launch all ready independent slices together using the adapter's real schema. For background work,
continue independent work and accept completion notifications; wait only when blocked. For blocking
calls consume their returned results. Never claim an unfinished worker's output or assume summaries
are hidden from the user. Start dependent work only when its inputs have arrived and passed the
checks assigned to that phase.

After failure, sharpen the brief first: state the concrete defect and observable acceptance result.
Retry the same permitted route if useful. Escalate only through an existing configured or explicitly
user-approved native route; record the reason and observed route. No fixed model ladder, secret
settings mutation, paid-provider substitution, or fallback invented by this skill. An unexpected
observed model/effort switch is a routing deviation: stop affected work, disclose it, and obtain
approval before accepting or continuing on that route. If no permitted route resolves the failure,
report the exact blocker and ask for a decision; never label incomplete work done.

## 5. Independent verification

The implementer cannot verify its own work as the independent reviewer. Dispatch the planned actual
reviewer separately; the coordinator also checks boundaries and source claims and runs the shared
gates once the phase's edits have landed. A worker's claim of passing checks is not evidence.

- Code: inspect changed scope, run the relevant project checks, and exercise the changed path with
  a targeted scenario/smoke run. Record actual results, not inferred success.
- Research: independently spot-check key claims against their sources.
- Review: assess every finding; accept and route fixes, or reject with a reason. Verify fixes before
  continuing. Reviewer output is input to the coordinator, not automatic approval.
- Boundaries: preserve pre-existing user changes; flag out-of-scope edits and unapproved external
  actions. Do not conceal them or destructively revert unrelated work.

If independent review is unavailable, say that it is missing and request an approved reviewer route
or a user decision. Self-checks may still be reported as self-checks, but cannot become independent
verification. A failed/empty optional review is failure, not "no findings". Run an approved second
opinion only at its agreed checkpoint, after the final tree is stable.

## 6. Report

Use `references/templates.md`: outcome, categories/native workers, observed routing and deviations,
checks actually exercised, independent reviewer findings and their disposition, optional second
opinion if it ran, and exact blockers/unverified items. Keep it short and in the user's language.
Do not stop at a phase boundary unless phase-by-phase execution was requested or an actual blocker
requires a decision.

## Permission boundaries

The confirmed plan authorizes only its explicit scope. Pause for changed scope/approach, an unresolved
failure, or an unapproved route. Obtain explicit permission for exact outward-facing or irreversible
actions: commit/push, tracker/forge writes, installs, destructive deletions, sending messages, or
external second-opinion calls. Explicitly asking for that exact action can supply permission; a
broad "start" or autonomy instruction cannot. Routine in-scope local edits are not blanket permission
for destructive cleanup. Carry these limits into every worker brief.
