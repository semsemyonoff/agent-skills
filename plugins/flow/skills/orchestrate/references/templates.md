# Plan and report templates

Use the user's language. Separate capability, assessed complexity and requested native profile.
Expected configuration is not actual execution. Show accessible effective model/reasoning values;
do not guess missing values, and do not omit known configured values because a spawn receipt is terse.

## Plan

State the settled approach and authorized routing/budget policy, then a compact table:

```text
| # | Capability / slice | Complexity and evidence | Requested native profile | Expected configured model + reasoning | Input / done criterion / dependencies |
| - | ------------------ | ----------------------- | ------------------------ | ------------------------------------- | ------------------------------------ |
| 1 | Research invariants | bounded fact gathering; paths known | discovered research profile | effective config value or unresolved alias | source locations + invariants; before 2/3 |
| 2 | Implement fixed callers | light: API/paths settled, contained effects | permitted light editor | effective configured pair | approved contract; parallel with 3 |
| 3 | Implement lifecycle ownership | strong: focus/state transitions cross boundaries | permitted strong editor | effective configured pair | lifecycle acceptance; after 1 |
| 4 | Independent combined review | assess highest relevant boundary risk; one scope set | separate permitted reviewer profile | effective configured pair | actual changes + acceptance; after 2/3 |
| 5 | Gates and runtime scenario | tools and scenario risk | reviewer/checker or coordinator | effective pair if delegated | stable tree + evidence packet |
```

These are examples, not a mandatory five-row decomposition or model benchmark. Inline trivial work
and combine related simple slices first. List the requested native profile and any permitted
schema-exposed invocation selector separately, including ordered candidates when used. Current omp
task items and public eval support `model`; discover the live surface rather than copying fields.
Actual identity is **not spawned yet**, never a model-name guess. Missing required profiles/aliases
are prerequisites, not silently replaced by generic/default task. A justified generic choice must
name its verified effective pair, explicit policy permission and suitability for the assessed class.

Assign integration to an existing slice owner or dedicated worker; name ownership, dependencies,
contracts, reviewer and checker. The trivial-inline exception remains.
List permitted escalation profile(s), their conditions and budget within the authorized plan; stronger
routes outside that allowance require a question. Ordinary matching-profile assignment does not.
Name exact external actions separately. Discover the supplemental route before confirmation:
Codex CLI in Claude Code, `second-opinion` in omp. It never replaces the required independent review.

Confirm using the real ask UI or text when unavailable: Start / Start phase by phase / Change plan.
In the same form, ask separately: Additional review via <route> after implementation / No additional
review. Show its scope, stable-final checkpoint and extra model call; do not embed consent in Start.
Honor prior explicit decisions for this exact plan and supplemental review independently. If only
one decision remains, ask only that question. An unavailable unsolicited route gets a brief notice,
not a substitute offer; an explicitly required unavailable review is a blocker.
Autonomous execution is default; silence, timeout/default, redirect or cancellation is not approval.

## Final report

```text
<2-5 lines: changed behavior and actual outcome>

| # | Capability + complexity / short reason | Requested native profile | Configured/requested pair | Exposed actual model + reasoning | Outcome / routing deviation |
| - | ------------------------------------- | ------------------------ | ------------------------- | ------------------------------- | --------------------------- |
| 1 | ... | ... | effective config/source or unknown | metadata value/source or unknown | ... |

Verification: <exercised commands/scenarios; applicable browser, HTTP/API, WebSocket/transport, live-deployment subchecks and actual results, not worker claims>
Independent review: <separate identity/profile, risk rationale, reviewed scope/version, findings/disposition; later nonbehavioral coordinator-only checks>
Escalations: <new evidence, narrowed brief/split, authorized route and conditions; or explicit approval>
Second opinion: <selected route; completed/failed/unavailable, findings/disposition, scope/version and later unreviewed changes; or declined>
Integration: <completed implementation/gates versus pending PR/CI/merge; push is not completion; without an applicable ship handoff, only confirmed remaining delivery steps (never a push already done; a finished stage is not a finished task)>
Not verified/blocked: <exact acceptance or capability still unavailable>
```

The routing table is required when any route deviated: substitution, escalation, missing profile,
or a worker the plan did not list. Otherwise replace it with one line naming the profiles used and
where actual identity came from (or that it was not exposed). Preserve known configured/requested
facts even when actual metadata is unavailable; mark actual unknown explicitly. Record actual substitutions, effort clamping and routing limits rather than
claiming exact execution from an alias. No incomplete done claims, failed-review-as-clean verdicts,
author self-review-as-independent claims or inferred subscription-savings percentages.

Use only applicable subchecks, not a mandatory checklist. Keep required failed/unverified levels as
concrete acceptance gaps; a neighboring pass is not proof. Report non-required failures as limits,
not whole-product failure, and never roll false/error into an undifferentiated passed result.

## Ship handoff

Gate first, before any status, remote, task-ID or target check: the handoff applies only when the
current session's skill/tool catalog lists the ship skill and the Forgejo MCP tools it needs (repo,
branches, pull request create/read, merge). Check metadata only: deferred tools need not be loaded,
one arbitrary Forgejo tool is not enough, and no forge API call is made. Loaded project rules or
context that identify a non-Forgejo forge (GitLab, GitHub) or disable the shipping handoff also fail
the gate; do not guess the forge from a remote URL. On a failed gate skip everything below silently:
no menu, command, task comment, target discovery or notice about the missing optional skill. The
final report's Integration line carries the remaining delivery steps instead. An explicit user
request for ship without the prerequisite gets a short statement of what is missing, not a command.

Decide at the end of every user turn (not after internal steps; a later "commit and push" turn and a
push done inside the approved plan both count). Offer the question only when ALL hold. Check in this
cheap-first order: 1, 4 (by local HEADs), 3, then the remote proof in 2 (`ls-remote` last).

While work is clearly not finished and the user has not explicitly chosen to hand it off, skip the
check silently. Name the reason for not offering (dirty / partial push / review pending) only in a
turn that carries the final report, a commit/push, or a user question about ship.

1. Complete: the agreed implementation and mandatory gates/independent review are done, or the user
   explicitly chose to hand off unfinished work. A failed or pending review means no offer (say what
   is missing, per the rule above) unless the user explicitly chose to hand off unfinished work; then
   Не проверено must state the review status.
2. Published: the repos come from the plan/Integration scope, and in each the current HEAD is on the
   task branch remotely. Proof is a successful push of exactly these HEADs in this turn, or a fresh
   read-only remote check (e.g. `git ls-remote origin <branch>`). Equality with the local
   remote-tracking `origin/<branch>` alone is not proof; no fetch is needed every turn. A partial
   push (any repo unpublished) means no offer; name those repos. Also check read-only the other
   workspace repos for a branch of the same name: one outside the plan/Integration scope is a
   discrepancy to resolve with the user, never silently included or ignored, and there is no offer
   until it is resolved.
3. Clean: inspect every scoped repo carrying the branch with read-only git status (staged, unstaged
   and untracked). If any is dirty or status cannot be established, omit ship choices and commands;
   name the repos and say changes need committing (or status resolving) first. The only next step is
   Continue working, in text: no one-option picker, no commit offered from the menu. This text
   answer does NOT set suppression. After a later commit+push the trigger fires on its own.
   Multiple distinct shipping branches need an explicit scope decision in text, not a guessed
   command.
4. Not suppressed. Key = task + source branch/target + ordered set of repo->HEAD. Set after Continue
   working and after a ship command was given (a command is not proof ship ran; the coordinator
   usually cannot observe that session). A repeated push without new HEADs does not lift it; new
   published HEADs or an explicit user request do. "Ship is not needed" holds for the whole task; a
   new push alone does not lift it.

Target: write the actual base from the agreed plan/Integration, the default branch included. Never
invent `main`; if the target is unknown, clarify it with the user before giving the handoff.

Take the task ID from the explicit argument/brief, else a `<id>-...` prefix. Conflicting/uncertain
IDs need resolution before a task report. With a task and an available vikunja skill, read the task
to confirm identity and show the exact proposed comment before asking. If the task cannot be read,
report that and offer the command-only menu. Use one question in the retained adapter's main-session
UI (`AskUserQuestion` in Claude Code, `ask` in omp):

- Task and vikunja available: **Report in #<id> and give ship command (Recommended)** /
  **Ship command only** / **Continue working** («Отписаться в #<id> и дать команду ship
  (рекомендуется)» / «Только команда ship» / «Продолжить работу»).
- No task or vikunja unavailable: **Ship command** / **Continue working**
  («Команда ship» / «Продолжить работу»). Say once when the skill is unavailable.
- Plan-approved final progress comment (below): drop the Report option; offer **Ship command** /
  **Continue working**, since the comment is already written.

Without the ask UI, ask the same question in text and wait for an explicit answer. Silence,
dismissal, timeout or a default selection authorizes nothing. Continue working causes no write and
no ship invocation; do not infer a new task from that choice.

Plan-approved comment: when the approved plan itself includes a tracker progress comment, only the
FINAL one, at the transition to ship, is written directly in the format below (after final
results/checks, once per HEAD set; an older report is never presented as current after new HEADs).
Intermediate progress comments are not turned into handoffs. "What changed" prose stays in the chat
report; if the plan separately requires a substantive change summary in the tracker, post it BEFORE
the handoff comment, which must be the last progress/report comment (ship treats a later
Прогресс/Сделано report as `later_report` and may trigger a delivery check).

Report selection authorizes exactly the displayed progress comment through vikunja's report flow,
not closing the task. Use its read-before-write/dedup conventions. Keep these wire labels in Russian
even in an English report; values can use the user's language. Each field occupies one line, optional
leading `- ` is allowed. Repo paths are workspace-relative (`.` for the root); one common branch:

```text
**Прогресс (YYYY-MM-DD)**

- Ветка: `<branch>`; репо: `<path>`, `<path>`
- Цель: `<base>`
- Проверено: <actual checks and results, qualified by repo; never empty>
- Не проверено: <gaps or explicit none; never empty>

**Что осталось**

- PR, CI, мерж — ship
```

Цель is always present, including the default branch. Omit neither verification field; use
`нет`/`none` when appropriate. No duplicate fields, multiline values, extra branch candidates or
permissions embedded in fields. These fields are the entire body before **Что осталось**: do not add
a change summary, paragraphs or extra list items before/between/after the fields. Pass this exact
body to vikunja report; its usual "what changed" prose belongs in the coordinator's final report, not
this handoff comment. The same contract lives independently in ship. If the comment fails, report
its actual error and give the command with the full inline handoff below so the new session loses no
facts.

After either command-producing choice, give a copyable command and explicitly say **run in a new
session in the same workspace**. Use the adapter selected at entry, never the model vendor:
Claude Code `/ship:ship <id>`, omp `/skill:ship <id>` (including Codex inside omp). Append
`into <base>` only for a non-default target (the comment and snapshot carry Цель either way).
Without a task, use the branch instead of the ID. Do not launch a new session, invoke ship, push,
open a PR, wait for CI or merge here; only an explicit user request to ship in this session
overrides that.

After a successful task comment, the task command is enough. For command-only, no task, missing
vikunja, or failed comment, append the full Ветка/Цель/Проверено/Не проверено block as multiline
skill arguments (without the Прогресс header or Что осталось). Include it even with an ID: this
inline snapshot replaces any earlier task handoff as a whole, preventing stale target/checks. Show
literal skill arguments, not a shell command; when executing any helper, pass values with safe
argument quoting. Shipping independently confirms merge, no-CI, dirty and rebase decisions.
