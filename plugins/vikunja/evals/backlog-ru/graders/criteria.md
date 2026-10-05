---
type: llm
weight: 1
---

The agent uses the vikunja skill and lays out the backlog flow: projects_list including archived projects and stop on 0 or several matches, a duplicate search in the project that includes done tasks and uses 2-3 specific words, a title matching neighbour style, then tasks_create with numeric project and format "markdown" and tasks_read verification, and reports the task link built from VIKUNJA_URL (or the task id when it is unset). The drafted description is Russian markdown with ### sections and lists, with no HTML tags.
