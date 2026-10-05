---
name: vikunja
description: Work with Vikunja tasks through the available Vikunja MCP tools in Claude Code, omp, or another MCP-capable harness — creating backlog tasks, analysing a task before doing it, writing progress reports and closing tasks, linking tasks, editing descriptions and comments. Use for ANY Vikunja work, even when the user only says "task N", "the tracker" or "the backlog". Triggers - "create a task", "add to the backlog", "look at task N and plan", "report in the linked tasks", "close task N", "vikunja", «заведи задачу», «запиши в бэклог», «запиши на будущее», «посмотри задачу N викунджа, проанализируй», «отпишись в задачах», «закрой задачу», «пройдись по проекту и отпишись в выполненных». Not for Redmine or Forgejo issues.
---

# Vikunja

Vikunja (2.7+) is driven only through its built-in MCP server, regardless of model provider or
harness. Reply in the user's language. Write task content in the language the project's existing
tasks use; if unclear, in the user's language.

Web links need the instance address, which the MCP does not expose: read `VIKUNJA_URL` once
(`echo "$VIKUNJA_URL"`, e.g. `https://vikunja.example.com`). Task links are then
`$VIKUNJA_URL/tasks/<id>`. If it is unset, write references as plain `#<id>`, give the user task ids
instead of links, and mention once that setting `VIKUNJA_URL` enables links. Make MCP calls through
the harness, not through a replacement REST client or scripts.

## Setup

1. Discover the connected Vikunja tools using the current harness's tool registry. Operation names
   below (`tasks_read`, `task_comments_create`, etc.) are the server's tool names, not full callable
   names. Match them to actual advertised tools; read each input schema before calling.
   - **Claude Code:** when tools are deferred and ToolSearch is available, use it to load the needed
     schemas. Names look like `mcp__vikunja__tasks_read`; use the names actually returned.
   - **omp:** inspect the available tool definitions and `read("xd://")` device listing. For a
     listed MCP device, read its exact `xd://<tool>` URI for docs/schema, then write the JSON
     arguments object to that URI. If exposed as a top-level tool or through Eval instead, use
     that advertised interface. Runtime names may look like `mcp__vikunja_tasks_read`; the server
     name and presentation can differ. Discovery is read-only; never invoke a write to probe.
   - **Other harnesses:** use their advertised MCP discovery/schema/call interface.
   If the required tools are absent, report the missing connection/operation and stop tracker work.
   Do not substitute another tracker, invent results, or change MCP configuration.
2. The server exposes core tools directly (projects, tasks, comments, labels, assignees). Everything
   else — relations, labels on a task, project-scoped task lists, bulk operations — is an *action*:
   `find_action` with `action` or `resource` returns its input schema, `do_action` with `action` and
   `arguments` runs it. `find_action` lists only what the token is allowed to do.
3. Load only operations needed by the scenario: reads first; creation, updates, comments,
   completion, relations and labels only when needed and authorized. Parameter names are not uniform
   (`tasks_read` takes `task`, `projects_read` takes `id`, `tasks_relations_delete` takes
   camelCase `otherTask`), so read each schema.
4. Paths in this skill are relative to the directory containing this `SKILL.md`.

## Pick the scenario

| The user wants | Read |
| --- | --- |
| a new task recorded (backlog, "for later", a spin-off, a follow-up) | `sections/backlog.md` |
| to understand or start a task ("look at task N"): analysis, then brainstorm, or a plan if the solution is settled | `sections/intake.md` |
| progress written into tasks, tasks closed, a sweep over a project | `sections/report.md` |
| anything else (edit a description, add a label, link tasks) | rules below, details in `references/conventions.md` |

## Rules that always apply

1. **Markdown via `format: "markdown"`.** Pass `format: "markdown"` on every call that reads or writes
   a description or comment (`tasks_*`, `task_comments_*`, `project_tasks_list`, ...). Write GFM:
   `###` sections, `-` lists, `**bold**`, backticks. Without the flag the server treats input as
   HTML and markdown markers show up literally; never mix HTML tags into markdown input.
2. **Task ids, not indexes.** A task has a global `id` (used in calls and URLs) and a per-project
   `index`/`identifier` (`#12`) shown in the UI. "Task N" from the user is the `id`; if a read fails or
   the title does not fit, ask. References are `[#<id>]($VIKUNJA_URL/tasks/<id>)` (plain `#<id>`
   without the URL); code, commits, plans and ADRs go in backticks.
3. **Numeric ids:** `task`, `project`, `other_task_id`, `label_id`, `commentid` are integers.
4. **Done tasks and archived projects.** Task lists include done tasks unless you filter
   `done = false`; `projects_list` hides archived projects unless `is_archived: true`. Searching for
   duplicates or a project, include both. Lists are paginated (`page`, `per_page`, capped by the
   server); for a full sweep keep fetching until `page` reaches `total_pages`.
5. **No personal data** in descriptions or comments: nicknames, logins, passwords, IPs, tokens. Rewrite
   generically; the classifier rejects such calls and the tracker is long-lived. No `@username`
   mentions either: comments parse them and notify people.
6. **Read every response.** After creating or editing, `tasks_read` the result and check it.
   `related_tasks` in the task shows relations, so verify those too.
7. **Partial updates.** `tasks_update` changes only the fields you pass: send `task` plus the fields to
   change, never a whole task copied from a read.
8. **Surface errors, do not skip.** A failing call goes into the final report as is. If a call fails
   with "auto mode classifier gave no verdict", retry once.
9. **Writes need a mandate.** Creating a task or comment is fine when the user asked for it. Closing a
   task, deleting, or touching tasks the user did not mention needs an explicit request or confirmation.
   In an intake, change nothing until the user confirms.

## References

- `references/conventions.md`: markdown cheat sheet, task style, relations and their direction,
  closing, comment rewriting, labels, search and other quirks.
