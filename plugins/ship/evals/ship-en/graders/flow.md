---
type: llm
weight: 1
---

The answer lists the flow plan (preflight, forge facts including a per-repo merge mode, one confirmation, push, PR, merge — server auto-merge plus background wait only when the base requires status checks, otherwise its own CI gate before a plain merge — confirm merged, sync, report) with the report statuses merged / CI failed / conflict / skipped: dirty / timeout / push failed / sync failed. It never uses force_merge, never offers to resolve conflicts silently, and ends with a single offer to report into linked Vikunja tasks without writing to Vikunja itself.
