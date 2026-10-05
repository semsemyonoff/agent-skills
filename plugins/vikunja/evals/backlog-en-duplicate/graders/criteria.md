---
type: llm
weight: 1
---

The agent describes searching for an existing similar task before creating one, without a done = false filter (so done tasks are visible) and several specific search words rather than one short token, reading the results, and reporting the existing task instead of creating a duplicate when one matches. It resolves the project by projects_list and stops if there is no single match.
