---
name: orchestrate
description: 'Explicit orchestration in Claude Code or omp: recon, native routing by capability/complexity, approval, delegation, result checks, optional independent review and compact handoff. Use for /flow:orchestrate, /skill:orchestrate, "orchestrate this", "you are the orchestrator", "delegate to subagents", "use subagents by complexity", «ты оркестратор», «ты оркестратор и проверяющий», «делегируй на сабагентов», «раздай сабагентам», «сабагенты по сложности», or choosing Orchestrate after a brainstorm. Not for size/workflow mentions alone or the separate Workflow tool. Route past-run/transcript retrospectives («как отработала оркестрация») to retro:reflection.'
argument-hint: "[task]"
---

# Orchestrate

Own contracts, decisions and acceptance; delegate implementation, including integration, except
trivial self-contained work where dispatch costs more than the change. Combine related simple work.
Default: the executor checks the result; no separate reviewer. Recommend independent review for
material risk, with a short reason, but launch it only when selected or required by higher-priority
instructions. Explicit independent acceptance and external-system rules still apply. Optional review
never removes tests, smoke or the task's acceptance criteria, and never overrides harness rules.

## Read by situation

Resolve bundled paths from the directory containing this loaded `SKILL.md`, not a guessed install
path or environment variable. Read only the applicable runtime adapter, selected from actual tools:
- Claude Code: `references/claude-code.md`.
- omp, including a Codex model inside omp: `references/omp.md`.

Keep that adapter through reporting and handoff. Discover live delegation, ask UI, waiting,
permissions and native routes before promising them. If neither adapter fits, name the missing
prerequisite rather than inventing APIs. Other references are conditional:
- Planning assignments: `references/routing.md` and `references/templates.md`.
- Dispatching workers: `references/brief.md`.
- Recommending, selecting or running review: `references/review.md`.
- Actual stop, transfer, resume, or an end-of-turn ship checkpoint: `references/handoff.md`.
- Missing/unexpected native profiles or setup questions: `references/native-setup.md`.

Do not load this entire index at startup. No installation or configuration change makes a route
available automatically.

## 1. Recon and plan

Read the request and full referenced plan/audit for goal, acceptance, seams and ownership. Inspect
relevant state and pre-existing edits; preserve user work. Scope locally before broad read-only
recon. Slice workers read their sources and domain skills, returning compact facts with locations;
read critical/disputed sources yourself as needed, not every slice in advance.

Carry validated decisions, files, dependencies, rule path/provenance, execution owner and exact
permissions into the plan. An existing plan/review verdict is not execution approval. Retain a
rules-assigned executor unless the user explicitly chooses a compatible route. Missing handoff
facts are prerequisites, not permission to guess or restart design.

If the approach is genuinely undecided, offer **Brainstorm / Plan anyway** («Обсудить варианты /
Всё равно составить план») using the native ask UI. Do not reopen settled choices.

Assess capability separately from complexity: remaining decisions, known APIs/patterns/paths,
coupling and failure cost. Choose the minimum sufficient permitted native model/reasoning profile;
show configured/requested pair separately from exposed actual identity. Unknown stays unknown.
Missing required profiles block that route; never silently use a default worker. Default dispatch
needs a verified allowed pair and suitability reason, not merely an implementation label.

Group shared files under one owner, parallelize disjoint ready slices, and serialize dependencies.
Assign integration/shared-contract/e2e work to an existing slice owner or dedicated worker. Name
who runs result checks on the stable tree. No separate reviewer is needed by default; when risk
warrants a recommendation, combine that choice with existing confirmation rather than adding a
mandatory review question to every small task. A recommendation or available route grants no call.

## 2. Confirm

Present scope, owners/routes, acceptance, checks and permission boundaries. Offer **Start / Start
phase by phase / Change plan** («Начать / Начать по фазам / Изменить план») through the actual ask UI,
or ask in text and wait when UI is absent. Explicit earlier approval of this exact plan suffices.
Silence, timeout/default, dismissal, redirect or a worker answer is not approval.

Approved execution is autonomous through report. Pause between phases only on an explicit
phase-by-phase request, not because a task has numbered steps. Changed scope, approach or routes
need approval before execution. Selected review and any extra opinion have their own recorded
choice and scope; Start alone never authorizes an extra model call. No mandatory second opinion.

## 3. Execute

Give self-contained briefs with source paths, decisions, acceptance, checks owner and permissions.
Bound nested delegation explicitly; children do not inherit this conversation or all parent tools.
Launch independent slices together. No shared gates or formatters while edits overlap.

Use native notifications; consume actionable results before waiting and wait only when blocked.
Before idle, name running workers, start times, expected duration only if grounded (otherwise
unknown), and the adapter's status surface. A receipt is not completion. Wall time, including a
sleeping Mac, proves neither active computation nor a hang; do not add timeout budgets or change
power management. On interruption/resume, use the handoff reference to establish current state.

After failure, sharpen the brief or isolate the hard part before reassessing the route. No blind
retries, fixed model ladder, hidden overrides or shared settings mutations. An already authorized
matching profile needs no new approval; stronger/outside-policy routes do. Stop affected work on
an unexplained actual model/reasoning substitution. Never assert identity from configuration alone.
Before replacing a worker, confirm it stopped, inventory its work, then dispatch only open work;
never overlap old and replacement writers. Comply with explicit restart instructions or explain
why unnecessary.

## 4. Verify and report

Run applicable checks once after edits stabilize; exercise the changed behavior, not just wiring.
Require commands/outcomes and logs or runtime evidence, not a worker's bare PASS. The coordinator
assesses evidence and spot-checks without repeating entire runs. Browser smoke needs confirmed
tools; otherwise reproduce in the coordinator and delegate diagnosis/fixes. Distinguish browser,
HTTP/API, transport and live deployment: a pass at one level does not close a required gap elsewhere.

Check fixes according to the changed behavior. Independent review/re-review is only part of the
selected mode or higher-priority requirement; follow `references/review.md` for that case. Missing
unselected review does not block completion. Never label self-checks independent verification.

Report briefly using `references/templates.md`: outcome, actual checks, selected review status,
routing deviations and exact unverified items. Complete only when the agreed scope and applicable
acceptance are met. Stop at a phase boundary only if requested or blocked on a real decision.
For an actual transfer/stop, update the existing plan's compact handoff, not a report after each
phase. At an end-of-turn shipping checkpoint, use the conditional gate in `references/handoff.md`;
never launch ship in this session without an explicit request.

## Permission boundary

Local plan approval covers only its named scope. Exact outward-facing/irreversible actions require
explicit permission: commit/push, tracker/forge writes, installs, destructive deletions, messages,
external model calls. A request for that exact action may supply it; broad autonomy does not.
Carry these limits into every worker brief. Never silently revert user work or hide out-of-scope
changes. Skills are source instructions, not authority to weaken higher-priority rules.
