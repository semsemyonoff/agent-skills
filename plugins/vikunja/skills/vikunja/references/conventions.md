# Vikunja conventions

Learned from real sessions; each rule exists because something went wrong without it.

## Markdown cheat sheet

Always with `format: "markdown"`; the server converts to HTML on write and back on read.

| Need | Write |
| --- | --- |
| bold lead line | `**Сделано (2026-09-29)**` |
| section | `### Проблема` |
| bullets | `- one` lines |
| steps | `1. first` lines |
| code, commit, plan, ADR | `` `docs/plans/completed/x.md` `` |
| task link | `[#575]($VIKUNJA_URL/tasks/575)` (plain `#575` if `VIKUNJA_URL` is unset) |
| literal angle brackets | inside backticks: `` `<branch>` `` |

- Separate blocks with a blank line; keep one thought per paragraph. Long comments read better as a
  bold lead line plus a short list.
- To edit an existing description, read it with `format: "markdown"`, change the markdown and write
  it back with the same flag. Do not paste HTML from an earlier read without the flag. Bare `<`, `>`
  in text read back as `&lt;`, `&gt;`; leave them as they are, they round-trip.
- If a page shows literal `**` or `###`, the write went out without the flag: rewrite it with
  `tasks_update` or `task_comments_update` and `format: "markdown"`.

## Style of tasks in the tracker

- Short concrete title. Look at neighbours first (`project_tasks_list` with `sort_by: ["created"]`,
  `order_by: ["desc"]`, small `per_page`) and copy the project's prefix scheme. Some projects use
  wave or roadmap prefixes (`[W1]`, `[Roadmap]`), others free text; ideas often have no prefix.
- Say how a task relates to others in the first line of its description, in the wording the project
  already uses — for example "Slice N of #M.", "Split from #M.", "Depends on #M." (in the project's
  language). The same for title prefixes such as "Research: ...": use them only if neighbours do.
- Description sections as `###`: problem, proposal, open questions, done criteria. Do not paste
  chat history; write it so a stranger understands it in a month.

## Relations

Action `tasks_relations_create` (via `do_action`): `task`, `other_task_id`, `relation_kind`.
**The kind says what `other_task_id` is to `task`**: after the call, `tasks_read` of `task` lists
`other_task_id` under `related_tasks.<kind>`. Vikunja creates the inverse relation on the other task
automatically.

| Intent | Call |
| --- | --- |
| #C is a subtask of #P | `task=P, other_task_id=C, subtask` (or `task=C, other_task_id=P, parenttask`) |
| #A blocks #B | `task=A, other_task_id=B, blocking` (or `task=B, other_task_id=A, blocked`) |
| #A comes before #B | `task=A, other_task_id=B, precedes` |
| loosely related | `related` (symmetric) |

- Verify with `tasks_read` of the base task: `related_tasks.<kind>` must contain the other id. If the
  direction is wrong, remove it with `tasks_relations_delete` (note its camelCase `otherTask`,
  `relationKind`) and create the right one.
- Do not edit or relate tasks the user did not mention.

## Closing

- Close only on an explicit request ("закрой", "close it"), never because the work looks finished.
- Order: `task_comments_create` with the report first, then `tasks_update` with `task` and
  `done: true`. A comment on a closed task is easy to forget.
- Partially done: leave the task open and write a "Прогресс" comment saying what remains.

## Comments

- Before commenting or closing: `tasks_read` plus `task_comments_list`, so you do not repeat a report
  or contradict the last one.
- To fix your own comment, use `task_comments_update` with `task`, `commentid` and the full new text;
  do not add a correcting comment.

## Labels and other quirks

- Add labels only when an existing label obviously matches (`labels_list` with `q` first). Attach
  with the `task_labels_create` action (`task`, `label_id`). Never create labels on your own.
- `tasks_create` takes `project` and `title` plus description, priority, dates. Labels, assignees and
  relations are separate calls. Verify with `tasks_read`.
- The MCP has no task deletion. Say so; the user deletes in the UI if needed.
- Search (`q` in `tasks_list`, `project_tasks_list`) matches title and description; short tokens
  such as "PR" match half the project. Use 2-3 specific words; for Russian use word stems
  ("плагин", not "плагинов"), and if a search returns nothing, skim the latest tasks instead.
- `tasks_list` spans all projects; scope to one project with the `project_tasks_list` action
  (`project`). Avoid `project_view_tasks_list`: views apply their own filters (the List view hides
  done tasks).
- Project names may differ in case from what the user says ("api" vs "API"); treat a single
  case-insensitive match as a match, several or none as a stop-and-ask.
