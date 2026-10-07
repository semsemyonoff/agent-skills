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
Integration: <completed implementation/gates versus pending PR/CI/merge; push is not completion>
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

Only when Integration has a branch still to ship, inspect every workspace repo carrying that branch
with read-only git status (including staged, unstaged and untracked files). If any is dirty or status
cannot be established, omit ship choices and commands; name the repos and say changes need committing
(or status needs resolving) before shipping. The only next step is Continue working, stated in text:
do not invent a one-option picker or offer/authorize a commit. Multiple distinct shipping branches
need an explicit scope decision in text, not a guessed single command.

For a clean branch, take the task ID from the explicit argument/brief, else a `<id>-...` prefix.
Conflicting/uncertain IDs need resolution before a task report. With a task and an available vikunja
skill, read the task to confirm identity and show the exact proposed comment before asking. If the
task cannot be read, report that and offer the command-only menu. Use one question in the retained
adapter's main-session UI (`AskUserQuestion` in Claude Code, `ask` in omp):

- Task and vikunja available: **Report in #<id> and give ship command (Recommended)** /
  **Ship command only** / **Continue working** («Отписаться в #<id> и дать команду ship
  (рекомендуется)» / «Только команда ship» / «Продолжить работу»).
- No task or vikunja unavailable: **Ship command** / **Continue working**
  («Команда ship» / «Продолжить работу»). Say once when the skill is unavailable.

Without the ask UI, ask the same question in text and wait for an explicit answer. Silence,
dismissal, timeout or a default selection authorizes nothing. Continue working causes no write and
no ship invocation; do not infer a new task from that choice.

Report selection authorizes exactly the displayed progress comment through vikunja's report flow,
not closing the task. Use its read-before-write/dedup conventions. Keep these wire labels in Russian
even in an English report; values can use the user's language. Each field occupies one line, optional
leading `- ` is allowed. Repo paths are workspace-relative (`.` for the root); one common branch:

```text
**Прогресс (YYYY-MM-DD)**

- Ветка: `<branch>`; репо: `<path>`, `<path>`
- Цель: `<non-default-base>`
- Проверено: <actual checks and results, qualified by repo; never empty>
- Не проверено: <gaps or explicit none; never empty>

**Что осталось**

- PR, CI, мерж — ship
```

Omit Цель entirely for the default base. Omit neither verification field; use `нет`/`none` when
appropriate. No duplicate fields, multiline values, extra branch candidates or permissions embedded
in fields. These fields are the entire body before **Что осталось**: do not add a change summary,
paragraphs or extra list items before/between/after the fields. Pass this exact body to vikunja report;
its usual "what changed" prose belongs in the coordinator's final report, not this handoff comment.
The same contract lives independently in ship. If the comment fails, report its actual
error and give the command with the full inline handoff below so the new session loses no facts.

After either command-producing choice, give a copyable command and explicitly say **run in a new
session in the same workspace**. Use the adapter selected at entry, never the model vendor:
Claude Code `/ship:ship <id>`, omp `/skill:ship <id>` (including Codex inside omp). Append
`into <base>` only for a non-default target. Without a task, use the branch instead of the ID.
Do not launch a new session, invoke ship, push, open a PR, wait for CI or merge here.

After a successful task comment, the task command is enough. For command-only, no task, missing
vikunja, or failed comment, append the full Ветка/optional Цель/Проверено/Не проверено block as
multiline skill arguments (without the Прогресс header or Что осталось). Include it even with an ID:
this inline snapshot replaces any earlier task handoff as a whole, preventing stale target/checks.
Show literal skill arguments, not a shell command; when executing any helper, pass values with safe
argument quoting. Shipping independently confirms merge, no-CI, dirty and rebase decisions.
