---
type: llm
weight: 1
---

This dry-run answer describes preflight, forge facts with per-repo merge mode, one upfront confirmation, push, PR, merge (server auto-merge plus wait only for required checks; otherwise CI gate or explicit no-CI permission), accepted-head/base verification, sync and report. It covers merged / CI failed / conflict / skipped: dirty / timeout / push failed / sync failed, never force_merge or silent conflict resolution. A real linked task is read before confirmation and gets the task-action choice there, not a final duplicate offer. With no task, there is no tracker offer or write; "Leave it" also suppresses both. This grades a proposed dry-run workflow only, not evidence of executed tool actions.

The proposed CI path uses one bounded wait-ci process per repo (guard-only for required-check presence), not model status/run polling. It distinguishes the old remote-branch wait for auto-merge, consumes accepted_head and no-checks evidence, and keeps the independent PR guard. Environment-only credentials and missing capability must be explicit, without a polling fallback. These are proposed actions only, not runtime/eval evidence.
