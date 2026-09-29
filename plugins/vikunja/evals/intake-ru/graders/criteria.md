---
type: llm
weight: 1
---

The agent describes reading the task with task_get and its comments with comments_list, following linked tasks, then producing a plan that states for each step who does it (main session or a subagent) and on which model, plus how it will be verified and open questions. It explicitly waits for confirmation and does not create, edit, comment on or close anything before it.
