# Sending

Only after the user explicitly says to send («отправляй», "send it", "публикуй"). If unsure whether a
phrase is approval, ask.

## Resolve first, never guess ids

- Status: `list_redmine_issue_statuses`, pick by name (commonly Feedback / «Обратная связь»). Names may be
  localized; if two match or none, ask the user.
- Assignee: take the id from the issue's journal/author data or from the user. Commonly the manager who
  asked. If it cannot be resolved from the data, ask.
- Change status or assignee only if the user asked for it in this conversation.

## Send

`update_redmine_issue(issue_id=N, fields={...})` — the standard Redmine fields go inside `fields`, not
top-level: `notes` = the Textile body exactly as in the approved draft (without the ```textile fence);
`status_id` / `assigned_to_id` only as requested (this server also accepts `status_name` in `fields`, but
prefer a resolved `status_id`). This matches the redmine-mcp-server schema; if the loaded tool schema
differs, follow the schema. A changed
description is a separate write: show the new description in full and get approval for it specifically.
Do not retry blindly on error: re-read the issue to see whether the write went through, then report.

## After

- Mark the section in the drafts file as published (date; journal id if the response gives it).
- Tell the user what was sent: issue id, that a comment was added, new status and assignee if changed.
  If a field was not changed, say so. Report failures as they are.
