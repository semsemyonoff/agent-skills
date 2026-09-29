# Vikunja conventions

Learned from real sessions; each rule exists because something went wrong without it.

## HTML cheat sheet

| Need | Write |
| --- | --- |
| paragraph | `<p>text</p>` |
| bold lead line | `<p><b>Сделано: ...</b></p>` |
| section | `<h3>Проблема</h3>` |
| bullets | `<ul><li>one</li><li>two</li></ul>` |
| steps | `<ol><li>first</li><li>second</li></ol>` |
| code, commit, plan, ADR | `<code>docs/plans/completed/x.md</code>` |
| task link | `<a href="https://tasks.horn/tasks/N">#N</a>` |
| literal angle bracket in text | `&lt;branch&gt;` (inside `<code>` too) |

- Tags are sent raw. If a tool echoes content back with `&lt;p&gt;`, that is often only how the response
  is displayed; judge by whether you sent raw tags, do not "fix" blindly. If a page really shows
  visible tags, the content was escaped on the way in: rewrite it with `task_update` or `comment_update`.
- Keep one thought per `<p>`; long comments read better as a bold lead line plus a short `<ul>`.
- A validator is bundled: `scripts/html_check.py`. Example:
  `printf '%s' "$HTML" | python3 "${CLAUDE_SKILL_DIR}/scripts/html_check.py" -`.

## Style of tasks in the tracker

- Short concrete title. Look at neighbours first (`tasks_list`, `show: "all"`, `sortBy: "created"`,
  `sortDirection: "desc"`, small `limit`) and copy the project's prefix scheme. Some projects use
  wave or roadmap prefixes (`[W1]`, `[Roadmap]`), others free text; ideas often have no prefix.
- Slices of a bigger task: description starts "Срез N из #M."; spin-offs: "Выделено из #M."; dependencies:
  "Зависит от #M." Research tasks are titled "Исследование: ...".
- Description sections in `<h3>`: problem, proposal, open questions, done criteria. Do not paste
  chat history; write it so a stranger understands it in a month.

## Relations

`relation_create(taskId, otherTaskId, relationKind)`. Semantics (verified against Vikunja source and
the UI): **the kind says what `otherTaskId` is to `taskId`** — the UI of `taskId` lists `otherTaskId`
under the kind's heading. Vikunja creates the inverse relation on the other task automatically.

| Intent | Call |
| --- | --- |
| #C is a subtask of #P | `taskId=P, otherTaskId=C, subtask` (or `taskId=C, otherTaskId=P, parenttask`) |
| #A blocks #B | `taskId=A, otherTaskId=B, blocking` (or `taskId=B, otherTaskId=A, blocked`) |
| #A comes before #B | `taskId=A, otherTaskId=B, precedes` |
| loosely related | `related` (symmetric) |

**The MCP reply text is wrong for subtask/parenttask**: `taskId=P, otherTaskId=C, subtask` is answered
with "Task A (P) is a subtask of Task B (C)", while Vikunja actually stored C under P. Ignore that
sentence; trust the table. Its wording for `blocking` matches the stored relation.

- `task_get` does not show relations, so they cannot be verified through the MCP. State the intended
  direction in one line ("#525 is a subtask of #484") and give the user the parent task link to check.
- Never "fix" a relation because of the reply text.
- Do not edit or relate tasks the user did not mention.

## Closing

- Close only on an explicit request ("закрой", "close it"), never because the work looks finished.
- Order: `comment_create` with the report first, then `task_complete`. A comment on a closed task
  is easy to forget.
- Partially done: leave the task open and write a "Прогресс" comment saying what remains.

## Comments

- Before commenting or closing: `task_get` plus `comments_list`, so you do not repeat a report or
  contradict the last one.
- To fix your own comment, use `comment_update` with `commentId` and the full new HTML; do not add a
  correcting comment.

## Labels and other quirks

- Add labels only when an existing label obviously matches (`labels_list` first). Never create labels
  on your own.
- `label_add_to_task` has failed with 412 "This account is disabled". Report such errors to the
  user; do not retry in a loop and do not silently omit the label.
- `task_create` accepts title, projectId, description, priority, dates only. Labels, assignees and
  relations are separate calls. It returns just the id, so verify with `task_get`.
- `task_delete` is disabled on this server (safe mode): it marks the task done instead of deleting.
  Say so; the user deletes in the UI if needed.
- `tasks_list` search is a case-insensitive substring match over title and description; short tokens
  such as "PR" match half the project. Use 2-3 specific words.
- Project names may differ in case from what the user says ("dwe" vs "DWE"); treat a single
  case-insensitive match as a match, several or none as a stop-and-ask.
