---
type: llm
weight: 1
---

The answer is in Russian. It resolves the branch from the task (`ship.py plan --task 587`, a `587-...` branch) instead of guessing. Its single confirmation includes a task question with report-and-close, report-only and leave-it options. After the merge it hands the report to the vikunja skill rather than writing to Vikunja itself, and it closes the task only when that option was chosen and every repo merged; a partial result gets a progress comment and stays open. It does not push, create PRs, merge or write to Vikunja during this dry run.
