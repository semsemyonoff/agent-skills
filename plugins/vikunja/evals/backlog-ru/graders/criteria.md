---
type: llm
weight: 1
---

The agent uses the vikunja skill and lays out the backlog flow: projects_list with show "all" and stop on 0 or several matches, a duplicate search with show "all" and 2-3 specific words, a title matching neighbour style, then task_create with numeric projectId and task_get verification, and reports a https://tasks.horn/tasks/<id> link. The drafted description is Russian HTML with h3 sections (p, ul, li, code) and contains no markdown markers (**, backticks, "- " lists) and no entity-escaped tags.
