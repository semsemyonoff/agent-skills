# Tracker task

Applies when the run has a Vikunja task: the user named it (`#587`, «задача 587», "task 587", a
`.../tasks/587` link) or plan `task` came from a `<id>-<slug>` branch. Only Vikunja is supported.
Ship never writes to Vikunja itself; the vikunja skill does, with its own comment conventions.

## Before the confirmation

- Named task without a branch: `ship.py plan --task <id>` finds the single local `<id>-...` branch
  across the workspace (none or several -> exit 2; show the error, ask for the branch).
- The vikunja skill is not available in this harness -> no task question; the report says once that
  task #<id> was not updated because the vikunja skill is missing.
- A branch prefix is only a candidate (`2026-release` may or may not be task 2026). Load the vikunja
  skill and read the task (read-only) before the confirmation. Not found or unreadable -> no task
  question, one line saying so. Found -> show `#<id> <title> (<project>)` above the action table,
  and note when it is already done. For an inferred task, compare the title with the branch slug,
  commit subjects and any plan file; if they do not match, say so and recommend "Leave it".
- Add to the single confirmation: "Task #<id> after the merge?" -
  "Report and close (Recommended)" / "Report only" / "Leave it"
  («Отписаться и закрыть (рекомендуется)» / «Только отписаться» / «Не трогать»). For a task that is
  already done, drop "close" and recommend "Leave it". The user may also answer that the inferred
  task is not this work: then "Leave it". "Stop" in the main question -> no task work.

## After the report table

"Report and close" or "Report only": load the vikunja skill and follow its report section, passing
an explicit request built from the answer and the per-repo results.

- Outcome: complete only when at least one repo merged and every repo that has the branch ended
  `merged` (including `merged (branch kept: ...)` and `merged, sync failed`). Skipped repos count
  as unshipped work (`skipped: dirty`, `base mismatch`, `base not found`, `not forgejo`), unless
  the user explicitly excluded them from the task; `skipped: is base` carries no work. Anything
  else, including `merged: ungated head`, `PR open` or "PRs only", is partial.
- Complete: a «Сделано» comment; close only if the answer was "Report and close".
- Partial: a «Прогресс» comment with «Что осталось» naming each unmerged or skipped repo, its PR and
  status; never close, even if "Report and close" was chosen, and say why in the final message.
  Nothing merged and no PR opened -> no comment; say so in the final message.
- Content: base branch, PR links, merge commits, CI evidence, notable statuses. No personal data.

Relay the vikunja skill's result (comment link, closed or left open, failed calls verbatim) in the
final message. "Leave it": nothing, no offer.
