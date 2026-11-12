# Handoff and resume

Read at an actual stop, transfer, resume or shipping checkpoint, not after every phase. Prefer a
compact block in the existing task plan. Without a plan, use one `handoff.md` in the task's already
accepted directory; do not create a second plan or state registry. Keep sensitive data out; link
local evidence rather than copying client content.

## Compact state

Include only known applicable facts; label unknowns:

```text
Goal / current stage:
Done / remaining:
Code: repository, branch, revision and relevant local edits; data origin when applicable.
Checks: command/scenario, observed result and log path; limits on reusing evidence.
Processes/workers: identity, last observed state, output location; what is still running/unknown.
Permissions: approved scope/routes/actions, selected review mode, explicit prohibitions.
Next step: one concrete action or decision; do not execute it merely because it is written here.
```

Distinguish **command issued**, **command executed**, and **result verified**. A queued command,
dispatch receipt or running process is not a successful result. State which observations are old.
Retain pending review/approval requirements; handoff itself grants no new permissions.

## Resume

Read the existing plan/handoff and relevant instructions; retain settled decisions and executor.
Establish current code, data/environment and process/worker state with available evidence before
continuing dependent work. After interruptions or intervening commits, inventory against in-flight
briefs and classify done/obsolete/open work. Confirm old writers stopped before replacements.
Reuse checks only when still applicable to current code, data and environment; changed or unknown
conditions cannot inherit an old PASS. Rerun only affected checks, not a mandatory whole-project
suite or hash census. Unknown state after sleep is neither a hang nor success. No automatic
restart, timeout budget, power-management change or new approval loop follows from elapsed time.

## Ship handoff

Gate first, before any status, remote, task-ID or target check: the handoff applies only when the
current session's skill/tool catalog lists the ship skill and the Forgejo MCP tools it needs (repo,
branches, pull request create/read, merge). Check metadata only: deferred tools need not be loaded
(in omp, MCP tools may be listed only in the `xd://` device listing; reading it is a metadata check),
one arbitrary Forgejo tool is not enough, and no forge API call is made. Loaded project rules or
context that identify a non-Forgejo forge (GitLab, GitHub) or disable the shipping handoff also fail
the gate; do not guess the forge from a remote URL. On a failed gate skip everything below: no menu,
command, task comment or target discovery. The final report's Integration line carries the
remaining delivery steps instead. Whether to mention it depends on the cause:

- Ship skill not listed, or loaded rules name another forge or disable the handoff: say nothing
  about ship or the missing optional skill.
- Ship listed but the needed Forgejo tools are not found: at the first checkpoint turn (below) of
  the task in this session, add one line naming that (e.g. «Handoff в ship не предлагается: в сессии
  не найдены Forgejo MCP-инструменты для PR/merge.»). Repeat it only when the user asks about ship
  or tool availability changes, not on every new commit. Do not load, configure or call MCP to fix it.

An explicit user request for ship without the prerequisite gets a short statement of what is
missing, not a command.

Decide at the end of every user turn (not after internal steps; a later "commit and push" turn and a
push done inside the approved plan both count). Offer the question only when ALL hold. Check in this
cheap-first order: 1, 4 (by local HEADs), 3, then the remote proof in 2 (`ls-remote` last).

Checkpoint turns are those that carry the final report, a commit/push of the task branch, or a user
question about ship; every other turn is an ordinary working turn. In an ordinary working turn
while work is clearly not finished (and the user has not chosen to hand it off), skip the check
silently. A checkpoint turn always shows the outcome: the question, or one line naming why it is not
offered (dirty / partial push / review pending), even when work is unfinished. Ending a checkpoint
turn with neither is a defect. Exceptions, where no line is needed: a gate failure that calls for
silence or whose notice was already given (above), suppression (4), and "ship is not needed".

1. Complete: implementation and applicable checks are done, plus any selected or higher-priority-
   required review. No unselected reviewer is a gate. A failed/pending selected review prevents
   the offer unless the user explicitly hands off unfinished work; then Не проверено names it.
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
leading `- ` is allowed. Repo paths are relative to the workspace the ship session runs in (`.` for
its root); ship rejects a path leaving it (`../…`). When the task branch also lives in a repo of
another workspace (e.g. a sibling deploy checkout), keep that repo out of this handoff and give it a
separate command, ALWAYS with its own full inline handoff (below) even after a successful task
comment, to run in a new session in that workspace. With more than one command, name the workspace
of each. Never post a second handoff comment for it: ship takes the latest handoff comment of the
task, so it would replace the first. One common branch:

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
session in the same workspace** (for a sibling-workspace command, in that workspace). Use the adapter selected at entry, never the model vendor:
Claude Code `/ship:ship <id>`, omp `/skill:ship <id>` (including Codex inside omp). Append
`into <base>` only for a non-default target (the comment and snapshot carry Цель either way).
Without a task, use the branch instead of the ID. Do not launch a new session, invoke ship, push,
open a PR, wait for CI or merge here; only an explicit user request to ship in this session
overrides that.

After a successful task comment, the task command is enough for the comment's workspace (a
sibling-workspace command stays inline). For command-only, no task, missing
vikunja, or failed comment, append the full Ветка/Цель/Проверено/Не проверено block as multiline
skill arguments (without the Прогресс header or Что осталось). Include it even with an ID: this
inline snapshot replaces any earlier task handoff as a whole, preventing stale target/checks. Show
literal skill arguments, not a shell command; when executing any helper, pass values with safe
argument quoting. Shipping independently confirms merge, no-CI, dirty and rebase decisions.
