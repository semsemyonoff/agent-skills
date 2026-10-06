---
name: orchestrate
description: 'Run explicit orchestration requests through recon, capability and complexity assessment, permitted native model/reasoning profiles, approval, delegated execution, independent verification, and a short report in Claude Code or omp. Use for /flow:orchestrate, /skill:orchestrate, "orchestrate this", "you are the orchestrator", "delegate to subagents", "use subagents by complexity", «ты оркестратор», «ты оркестратор и проверяющий», «делегируй на сабагентов», «раздай сабагентам», «сабагенты по сложности», or choosing Orchestrate after a brainstorm. Do not trigger merely because a task is large or mentions workflow; do not substitute for a separate Workflow tool.'
argument-hint: "[task]"
---

# Orchestrate

Act as coordinator, not bulk implementer: establish facts, settle the approach, obtain approval,
delegate, independently verify, and report in the user's language. Use ONE process below in both
harnesses. Categories describe required capabilities, not model cost. Separately assess each slice's
remaining decisions, uncertainty, coupling and failure cost; choose the minimum sufficient permitted
native model/reasoning profile from that assessment, not from the implementation/docs label.

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

A trivial self-contained change may be done inline when dispatch costs more than the work. Combine
related simple changes with the same ownership/contract instead of spawning a worker per edit.
Keep approval and truthful verification; do not add a separate review just to fill a template.
Nontrivial independent verification must still use a different worker, never the implementer.
Missing required delegation or profiles is a prerequisite, not a silent default-worker fallback.
Explicitly requested delegation or independent-review acceptance still applies to inline shortcuts.

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

Use `references/routing.md` and `references/templates.md`. For every slice, choose capability and
complexity separately: unresolved decisions; known approach/pattern/API/paths; change radius/coupling;
and failure cost, including security, data, public API, lifecycle and concurrency. Size and labels
alone do not classify work. State complexity plus a short reason and the minimum sufficient allowed
native profile. Show expected model/reasoning from accessible effective native configuration and
requested selection separately from actual identity, which is only reported after exposure.
Unknown metadata stays unknown; known configuration is not made unknown merely by a terse spawn
summary. Missing/unapproved profiles block that route. Generic/default dispatch needs an explicit
policy match and suitability reason; implementation never automatically means default task.

Run independent slices in parallel with disjoint edit ownership; group related simple work first.
Specify contracts and serialize only real dependencies. Assess review effort by the changed result's
risk, not by the author's category or a fixed highest model. Use one adequate separate reviewer for
compatible changed scopes rather than mandatory reviews per worker. Focus security/data/lifecycle
checks where warranted, plus executable verification. List exact external actions and approvals;
local implementation approval does not authorize them.

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

After failure, sharpen the brief or isolate the genuinely hard part before changing the route.
Reassess with the new evidence; no blind retries or fixed model ladder. Use a stronger native profile
only inside the previously authorized policy/plan, otherwise ask for exact permission. Ordinary
assignments of an already authorized matching profile need no repeated approval. Never mutate
global role/model settings between parallel dispatches, use hidden bridge overrides, or invent a
paid fallback. Compare exposed actual identity/reasoning with the requested/configured expectation;
an unexplained substitution stops affected work until resolved within policy or explicitly approved.
If no permitted route meets the requirement, report its precise prerequisite, not incomplete success.

Resuming after an interruption (stopped worker, restarted session, commits made meanwhile): before
any re-dispatch, re-inventory branches, status and commits against every in-flight brief. Tell the
user which items are already done, obsolete or still open, and re-dispatch only the open ones. An
explicit user instruction about a worker ("restart it") is answered, not silently dropped: follow
it, or say why it is unnecessary.

## 5. Independent verification

The implementer cannot act as its own independent reviewer. Dispatch the planned risk-appropriate
reviewer separately; combine compatible scope coverage and run shared gates once the edits land.
A worker's passing-check claim is not evidence, and independence does not imply highest-cost routing.

- Code: inspect changed scope, run the relevant project checks, and exercise the changed path with
  a targeted scenario/smoke run. Record actual results, not inferred success.
- Research: independently spot-check key claims against their sources.
- Review: assess every finding; accept and route fixes, or reject with a reason. Verify fixes before
  continuing. Reviewer output is input to the coordinator, not automatic approval.
- Boundaries: preserve pre-existing user changes; flag out-of-scope edits and unapproved external
  actions. Do not conceal them or destructively revert unrelated work.

For layered smoke checks, record each applicable subcheck and its actual result: browser rendering/
interaction, HTTP/API, WebSocket/transport and live deployment. HTTP 101 plus a connected protocol
frame proves transport, not browser HMR when the browser reports false/error. A neighboring pass
cannot close a required failed/unverified level: keep its concrete acceptance gap/blocker until
proved. If that level is not required, report the limitation without declaring the whole product
broken. Never hide false/error under an overall passed result.

Freeze the reviewed scope while an independent review runs: queue coordinator edits, including
small fixes found by your own checks, until the reviewer returns, so it never reviews a moving tree.
Batch fixes before the next independent review; functional/security fixes still need an adequate
separate reviewer. Obvious nonbehavioral tails (comment wording or exact documentation relocation)
may be checked by the coordinator against the diff, links and existing evidence without another
mandatory review round. Behavior/security/contract changes, substantial new risks or an explicit
user request for repeat independent review require a separate risk-appropriate reviewer; do not
silently change its model. Record the reviewed scope/version and any later coordinator-only changes.
A previous APPROVE is not approval of a version the reviewer has not seen.

If independent review is unavailable, say that it is missing and request an approved reviewer route
or a user decision. Self-checks may still be reported as self-checks, but cannot become independent
verification. A failed/empty optional review is failure, not "no findings". Run an approved second
opinion only at its agreed checkpoint, after the final tree is stable.

## 6. Report

Use `references/templates.md`: outcome; capability, complexity/reason and selected native profile;
configured/requested pair versus exposed actual model/reasoning (a full table only when a route
deviated); checks actually exercised;
reviewer findings/disposition; approved escalations; and exact blockers/unverified items. Keep it short
and in the user's language. Do not promise subscription-quota savings from API price cards.
Separate completed implementation/gates from ongoing integration; successful push does not complete
pending PR, CI or merge work.
Do not stop at a phase boundary unless phase-by-phase execution was requested or an actual blocker
requires a decision.

## Permission boundaries

The confirmed plan authorizes only its explicit scope. Pause for changed scope/approach, an unresolved
failure, or an unapproved route. Obtain explicit permission for exact outward-facing or irreversible
actions: commit/push, tracker/forge writes, installs, destructive deletions, sending messages, or
external second-opinion calls. Explicitly asking for that exact action can supply permission; a
broad "start" or autonomy instruction cannot. Routine in-scope local edits are not blanket permission
for destructive cleanup. Carry these limits into every worker brief.
