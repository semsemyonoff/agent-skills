---
type: llm
weight: 1
---

The agent describes reading the task with tasks_read and its comments with task_comments_list, following linked tasks, then either stopping at the analysis and offering a brainstorm when the solution is not settled (the default), or, only when the task already settles it, a plan that states for each step who does it (main session or a subagent) and on which model, plus how it will be verified and open questions. It explicitly waits for confirmation and does not create, edit, comment on or close anything before it.
