---
name: vikunja
description: Work with Vikunja tasks through the mcp__vikunja__* tools — creating backlog tasks, analysing a task before doing it, writing progress reports and closing tasks, linking tasks, editing descriptions and comments. Use for ANY Vikunja work, even when the user only says "task N", "the tracker" or "the backlog". Triggers - "create a task", "add to the backlog", "look at task N and plan", "report in the linked tasks", "close task N", "vikunja", «заведи задачу», «запиши в бэклог», «запиши на будущее», «посмотри задачу N викунджа, проанализируй», «отпишись в задачах», «закрой задачу», «пройдись по проекту и отпишись в выполненных». Not for Redmine or Forgejo issues.
---

# Vikunja

Vikunja is the personal task tracker (`https://tasks.horn`), driven only through the `mcp__vikunja__*`
tools. Reply in the user's language. Write task content in Russian unless the project's existing tasks
use another language. MCP calls cannot be scripted, so the model makes them; the only script is the
offline HTML validator.

## Setup

The Vikunja tools are deferred. Load the schemas before the first call with ToolSearch, for example
`select:mcp__vikunja__projects_list,mcp__vikunja__tasks_list,mcp__vikunja__task_get,mcp__vikunja__task_create`
(add `comments_list`, `comment_create`, `comment_update`, `task_update`, `task_complete`,
`relation_create`, `labels_list` as the scenario needs). Parameter names differ per tool (`task_get`
takes `id`, most others `taskId`), so read each schema instead of assuming.

## Pick the scenario

| The user wants | Read |
| --- | --- |
| a new task recorded (backlog, "for later", a spin-off, a follow-up) | `sections/backlog.md` |
| to understand or start a task ("look at task N, plan it") | `sections/intake.md` |
| progress written into tasks, tasks closed, a sweep over a project | `sections/report.md` |
| anything else (edit a description, add a label, link tasks) | rules below, details in `references/conventions.md` |

## Rules that always apply

1. **HTML, not markdown.** Descriptions and comments are HTML: `<p>`, `<b>`, `<code>`, `<ul><li>`,
   `<ol><li>`, `<h3>`, `<a href>`. No `**`, backticks, `- ` lists or `#` headings; they show as literal
   characters. Send raw HTML: never entity-escape the tags (`&lt;p&gt;` renders as visible text), but do
   escape a literal `<`, `>`, `&` inside text.
2. **Validate before sending** anything non-trivial:
   `python3 "${CLAUDE_SKILL_DIR}/scripts/html_check.py" file.html` (or `-` for stdin). It rejects markdown
   markers and escaped tags. `--build` turns a simple section format into HTML (see its docstring).
3. **Task references** are `<a href="https://tasks.horn/tasks/N">#N</a>`; code, commits, plans and ADRs go
   in `<code>`.
4. **Numeric camelCase parameters:** `projectId`, `taskId`, `otherTaskId`, `commentId` are numbers.
5. **Search with `show: "all"`** in `projects_list` and `tasks_list`, otherwise archived projects and done
   tasks are invisible and you create duplicates or miss the task you need. `tasks_list` returns 50 by
   default; pass `limit: 0` for a full sweep.
6. **No personal data** in descriptions or comments: nicknames, logins, passwords, IPs, tokens. Rewrite
   generically; the classifier rejects such calls and the tracker is long-lived.
7. **Read every response.** After creating or editing, `task_get` the result and check it. A `relation_create`
   reply says "A is a subtask of B": confirm the direction matches your intent (see conventions).
8. **Surface errors, do not skip.** A failing label call (for example 412 "account is disabled") goes
   into the final report as is. If a call fails with "auto mode classifier gave no verdict", retry once.
9. **Writes need a mandate.** Creating a task or comment is fine when the user asked for it. Closing a
   task, deleting, or touching tasks the user did not mention needs an explicit request or confirmation.
   In an intake, change nothing until the user confirms.

## References

- `references/conventions.md`: HTML cheat sheet, relations and their direction, closing, comment
  rewriting, labels, parameter quirks, error handling.
