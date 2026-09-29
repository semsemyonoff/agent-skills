# Report: write results into tasks, close when asked

Use after work is done or when the user says "отпишись в N", "отпишись в связанных задачах",
"пройдись по проекту, отпишись в выполненных, закрой полностью выполненные", "report in the tasks".

## Find the right tasks

- The user named tasks: use exactly those.
- "Linked tasks": derive them from evidence, not from guesses. Sources: the plan file
  (`docs/plans/...`, its header and task list often name `#N`), commit messages and branch names,
  the conversation. Confirm each candidate with `task_get`; if a candidate is unclear, list it and ask.
- A sweep over a project: `tasks_list` with `projectId`, `show: "incomplete"`, `limit: 0`, then match
  open tasks to finished work using commits and plans. Say which tasks you will touch before writing
  when the sweep is broad.

## Write the comment

1. `task_get` and `comments_list` first: do not repeat an earlier report and keep numbering consistent.
2. Compose HTML. The first line is bold and states the outcome, then the date in ISO form:
   - `<p><b>Сделано (2026-09-29)</b></p>` when the task is complete;
   - `<p><b>Прогресс (2026-09-29)</b></p>` when partial;
   - `<p><b>Решение (2026-09-29)</b></p>` when the outcome is a decision or a "won't do".
3. Body: what changed and why, in a short `<ul>`; commits, plans, ADRs, files as `<code>`; links to other
   tasks as `<a href="https://tasks.horn/tasks/N">#N</a>`.
4. If anything is still open, add an explicit `<p><b>Что осталось</b></p>` with a list. Be specific:
   items the reader can act on.
5. Validate with `python3 "${CLAUDE_SKILL_DIR}/scripts/html_check.py" file.html`, then `comment_create`
   with numeric `taskId`.
6. Read back with `comments_list`/`comment_get` if the content was long; fix a mistake with
   `comment_update` (`commentId` plus the full HTML).

## Closing

- Close only on an explicit request ("закрой", "close"). "Отпишись" alone means comment only.
- Complete and requested: comment first, then `task_complete`.
- Partial: never close. Leave it open with a Прогресс comment and the remainder, for example
  "задача остаётся открытой ради п. 3".
- Sweeps ("закрой полностью выполненные"): close only tasks whose acceptance criteria are all met by
  evidence; list the tasks you closed and the ones you left open with a reason.

## Final message to the user

Links to every comment or task touched, which were closed, which stayed open and why, and any failed
call verbatim.

## Pitfalls

- Closing before commenting, or closing on your own judgment.
- A comment that says only "done": name the commits or plan so it can be traced.
- Reporting into related tasks the user never mentioned without saying so.
