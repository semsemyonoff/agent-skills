---
name: orchestrate
description: 'Explicit orchestration in Claude Code or omp: recon, native routing by capability/complexity, approval, delegation, independent verification and report. Use for /flow:orchestrate, /skill:orchestrate, "orchestrate this", "you are the orchestrator", "delegate to subagents", "use subagents by complexity", «ты оркестратор», «ты оркестратор и проверяющий», «делегируй на сабагентов», «раздай сабагентам», «сабагенты по сложности», or choosing Orchestrate after a brainstorm. Not for size/workflow mentions alone or the separate Workflow tool. Route past-run/transcript retrospectives («как отработала оркестрация») to retro:reflection.'
argument-hint: "[task]"
---

# Orchestrate

Own contracts, decisions and acceptance; delegate implementation, including integration, except
trivial inline work below. Independently verify. Categories express capabilities, not cost;
assess remaining decisions, uncertainty, coupling and failure cost per slice. Choose the minimum
sufficient permitted native model/reasoning profile.

## Select the runtime adapter

Identify the running harness from its actual tools/session, not the model's vendor. Read only the
applicable adapter before dispatch:

- Claude Code: `references/claude-code.md`.
- omp (including a Codex model inside omp): `references/omp.md`.

Retain this selected adapter through the final report and ship handoff.

Resolve every bundled path from the directory containing this loaded `SKILL.md`. Do not assume an
installation location or environment variable. Discover available delegation, ask UI, independent
review, background/wait, permissions, and native routing. If neither adapter matches, describe the
missing prerequisite instead of inventing compatible APIs. Never edit configuration to make a route
available. Read `references/native-setup.md` only for native-profile setup or missing/unexpected routes.

A trivial self-contained change may be done inline when dispatch costs more than the work. Combine
related simple changes with the same ownership/contract instead of spawning a worker per edit.
Keep approval and truthful verification; do not add a separate review just to fill a template.
Nontrivial independent verification must still use a different worker, never the implementer.
Missing required delegation or profiles is a prerequisite, not a silent default-worker fallback.
Explicitly requested delegation or independent-review acceptance still applies to inline shortcuts.

## 1. Recon

Read the request and referenced plans/audits/checklists/artifacts for acceptance, ownership,
contracts and seams. Inspect relevant state and pre-existing edits; preserve user work. Delegate
broad recon to read-only workers; slice workers read their source and return compact facts with
locations. Read disputed/critical sources as needed to plan, without pre-reading every slice.
Name language/domain skills in slice briefs; workers load them. Load one yourself only for your
own contract, routing or acceptance decision.

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

Group simple work; parallelize disjoint files and serialize dependencies. Assign wiring,
shared-contract implementation and e2e to an existing slice owner or dedicated integration worker;
keep it off the coordinator except trivial inline work. Wait for integration inputs.
Use one separate reviewer for compatible scopes, sized by result risk rather than author/category
or highest model; focus security/data/lifecycle checks where warranted, plus executable verification.
Name the verification owner and exact external actions/approvals; local approval excludes those effects.

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

At this checkpoint, offer an additional read-only second opinion when its route is available:
**Claude Code — Codex CLI; omp — the discovered `second-opinion` agent**. Ask a separate question,
in the same approval form when possible: "Additional review via <route> after implementation? /
No additional review". Explain that the required independent reviewer still runs either way.
Choosing Start does not answer this question or authorize the extra model call. Record the chosen
route, exact reviewed scope and checkpoint; honor an explicit earlier yes/no without asking again.
The default checkpoint is the stable final result after mandatory independent review and checks.
Use the active adapter's discovery and invocation instructions; do not assume a different vendor.
If the route is unavailable, say so once and omit its offer, never substitute another agent/CLI.
An explicitly requested unavailable review is a blocker until the user changes that requirement.
Timeout, dismissal, redirect and silence are not consent; use a text question only when ask UI
is absent. `references/codex-review.md` describes the Claude CLI route.

## 4. Execution

Use `references/brief.md` for self-contained briefs: context, decisions, files, boundaries, data,
acceptance criteria, checks reserved for the verification owner, and concise output/evidence.
Workers must not run shared gates or formatters while edits overlap. No worker commits, pushes,
installs, changes native routing, or writes externally without exact explicit permission.

Launch ready independent slices together using the real schema. Consume blocking results; accept
background notifications and wait only when blocked. Before going idle, name running workers,
start times, expected duration with a basis (otherwise unknown), and the adapter's status surface.
This is transparent waiting, not stall detection; runtime stall notifications require harness support.
Never claim unfinished results. Start dependent work only after inputs pass their assigned checks.

After failure, sharpen the brief or isolate the genuinely hard part before changing the route.
Reassess with the new evidence; no blind retries or fixed model ladder. Use a stronger native profile
only inside the previously authorized policy/plan, otherwise ask for exact permission. Ordinary
assignments of an already authorized matching profile need no repeated approval. Never mutate
global role/model settings between parallel dispatches, use hidden bridge overrides, or invent a
paid fallback. Compare exposed actual identity/reasoning with the requested/configured expectation;
an unexplained substitution stops affected work until resolved within policy or explicitly approved.
If no permitted route meets the requirement, report its precise prerequisite, not incomplete success.

For reuse/replacement, follow `references/brief.md`: confirm the old writer stopped, inventory the
tree, then dispatch its replacement; never overlap old and new writers.
After interruptions/restarts or intervening commits, inventory branches/status/commits against all
in-flight briefs; report done/obsolete/open items and re-dispatch only open work. Answer explicit
worker instructions ("restart it"): comply or explain why unnecessary.

## 5. Independent verification

Use a separate risk-appropriate reviewer; implementers cannot independently review their own work.
Assign stable-tree gates/smoke to a checker or coordinator; a capable reviewer can also check.
Require the `references/brief.md` evidence packet, not PASS; implementer claims are not verification.
The coordinator assesses evidence and spot-checks without repeating whole runs. Delegate browser
smoke only with confirmed tools; otherwise reproduce in the coordinator and delegate diagnosis/fixes.
Follow adapter capability limits.

- Code: inspect changed scope, run relevant checks and exercise the changed behavior.
- Research: independently spot-check key claims against sources.
- Findings: accept and route fixes or reject with reasons; verify fixes before proceeding.
- Boundaries: preserve user work; disclose out-of-scope edits/unapproved effects, never silently revert.
Reviewer output informs coordinator acceptance; it is not automatic approval.

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
verification. A failed/empty optional review is failure, not "no findings". Run the selected extra
review once at its agreed checkpoint on a frozen result, using a different instance from the
implementer and required reviewer. Supply original acceptance, changed scope/version, pre-existing
edits and observed checks. Assess every finding; accepted in-scope behavioral fixes return through
implementation and mandatory independent verification. A second supplemental round needs new
permission. Report its actual outcome and any later changes it did not review; never label a failed
or unavailable chosen review as completed.
After an observed supplemental failure, the user may explicitly waive that extra requirement;
record the failure and waiver, never a passing review. Mandatory independent verification remains.

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

At the end of any user turn, offer the **Ship handoff** in `references/templates.md` when its gate
and state trigger hold (not only after the report; a later commit/push turn counts). Check the gate
before any git/remote check: without the ship skill (or with rules naming another forge), skip
silently. A checkpoint turn (final report, commit/push of the task branch, ship question) ends with
the question or a one-line reason; the exceptions and the one-time missing-Forgejo notice are in
the template. Give a command for a new session; run ship here only on an explicit user request.

## Permission boundaries

The confirmed plan authorizes only its explicit scope. Pause for changed scope/approach, an unresolved
failure, or an unapproved route. Obtain explicit permission for exact outward-facing or irreversible
actions: commit/push, tracker/forge writes, installs, destructive deletions, sending messages, or
external second-opinion calls. Explicitly asking for that exact action can supply permission; a
broad "start" or autonomy instruction cannot. Routine in-scope local edits are not blanket permission
for destructive cleanup. Carry these limits into every worker brief.
