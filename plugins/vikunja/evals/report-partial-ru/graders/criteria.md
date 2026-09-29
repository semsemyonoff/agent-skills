---
type: llm
weight: 1
---

The agent prepares a Russian HTML comment whose first line is a bold Progress (Прогресс) heading with an ISO date, mentions the commit and plan in code tags, states explicitly what remains (Что осталось) with the two open items, uses no markdown markers or escaped tags, reads task_get and comments_list first, calls comment_create with numeric taskId, and does NOT call task_complete.
