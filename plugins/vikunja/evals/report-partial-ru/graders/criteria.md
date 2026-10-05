---
type: llm
weight: 1
---

The agent prepares a Russian markdown comment whose first line is a bold Progress (Прогресс) heading with an ISO date, mentions the commit and plan in backticks, states explicitly what remains (Что осталось) with the two open items, contains no HTML tags, reads tasks_read and task_comments_list first, calls task_comments_create with numeric task and format "markdown", and does NOT mark the task done (no tasks_update with done: true).
