---
type: llm
weight: 1
---

The answer lists the flow plan (preflight, forge facts, one confirmation, push, PR plus auto-merge, background wait, confirm merged, sync, report) with the report statuses merged / CI failed / conflict / skipped: dirty / timeout / push failed / sync failed. It never uses force_merge, never offers to resolve conflicts silently, and ends with a single offer to report into linked Vikunja tasks without writing to Vikunja itself.
