# Backlog: record a new task

Use when the user asks to create a task ("заведи отдельную", "запиши на будущее", "add to the
backlog", a spin-off from the current work). The request itself is the mandate to create; do not ask
for confirmation again unless the target is ambiguous.

## Steps

1. **Resolve the project.** `projects_list` with `search` (a distinctive word from the user's phrase)
   and `show: "all"`. Exactly one match: use its id. Several: stop and list them with ids. Zero:
   the project may be named differently (a parent project, Russian name, a generic "Research" or
   "backlog") — call `projects_list` without `search`, show the user the list (with parents) and ask
   where to put it. Never guess and never create a project unasked. If the user names no project,
   infer from context (repo name, the task being discussed) and say which you picked, or ask if
   there is no clue.
2. **Check for duplicates.** `tasks_list` with `projectId`, `show: "all"` and 2-3 specific words from
   the idea, one call per word. Read the titles. If something covers it (open or done), report that
   task's link instead of creating; ask only when it is a partial overlap.
3. **Match the style.** Look at a handful of recent titles (`sortBy: "created"`, `sortDirection: "desc"`,
   `limit: 10`, `show: "all"`) and pick a title in the same scheme: short, concrete, verbs and
   nouns instead of a sentence.
4. **Write the description** in HTML with `<h3>` sections, in the project's language. Typical: problem
   (what hurts, with numbers if known), proposal, open questions, done criteria. Related tasks as
   `<a href="$VIKUNJA_URL/tasks/N">#N</a>`; say where it was split from when it is a spin-off. Strip
   personal data. Write it to a temp file and run
   `python3 "$SKILL_DIR/scripts/html_check.py" file.html` (resolve `SKILL_DIR` as in Setup);
   fix every reported problem.
5. **Create.** `task_create` with numeric `projectId`, `title`, `description`; `priority` only if the
   user stated one. Do not invent due dates.
6. **Verify.** `task_get` with the returned id; confirm title and that the description holds the raw HTML you
   sent. Then do the extras the user asked for (relation to the parent task, label) as separate calls,
   reading each reply.
7. **Report** in the user's language: link `$VIKUNJA_URL/tasks/<id>` (or the id), project id, and any
   failed extra (label errors included) verbatim.

## Pitfalls

- Skipping `show: "all"` hides the finished task that already solved this.
- Copying the user's chat phrasing into the title. Titles name the work, not the conversation.
- A description that is markdown: the tracker shows `**` and `-` literally.
- Creating several tasks from one request without listing them to the user first. One request, one
  task, unless the user enumerated more.
