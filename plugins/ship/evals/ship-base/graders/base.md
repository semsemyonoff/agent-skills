---
type: llm
weight: 1
---

The answer is in Russian. It targets public-site, not main: helper calls carry `--base public-site`, PRs use base public-site, and sync fast-forwards public-site. It does not fall back to the default branch if public-site is missing. It decides the merge mode from the base branch's status-check settings (list_branches): server auto-merge only when checks are required, otherwise it waits for all PR checks itself and then merges without force. It does not push, create PRs or merge during this dry run.

Because 587-fandom-icons infers task 587, later git helper calls retain --task 587 alongside --branch, --root and --base public-site. Independent wait-ci PR calls instead use owner/repo/PR/--base public-site without git-context flags, with deterministic helper polling. The explicit user target suffices; do not re-ask it or replace it from task comments.
