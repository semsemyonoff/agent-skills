# Plan and report templates

Write headings and text in the user's language. Keep both short: they are for deciding, not reading.

## Plan

One line on the approach, then the table. Mark parallel steps in the dependencies column.

```
| # | Step | Worker / model | Input | Done when | Depends on |
| - | ---- | -------------- | ----- | --------- | ---------- |
| 1 | Map call sites of X | Explore / haiku | repo | list with path:line | - (parallel with 2) |
| 2 | Read the retry logic in Y | Explore / sonnet | internal/y | summary of current behaviour | - (parallel with 1) |
| 3 | Implement Z | general-purpose / sonnet | results of 1, 2 | tests pass | 1, 2 |
| 4 | Review 3 for data races | general-purpose / opus | diff of 3 | findings list | 3 |
```

A deviation from `routing.md` goes into the model cell: `sonnet (additive migration, known pattern)`.
After the table: what you will verify yourself, and anything that will need the user (push, external
writes, deletions).

## Final report

```
<2-5 lines: what was done and the outcome>

| # | Step | Model | Result | Escalations |
| - | ---- | ----- | ------ | ----------- |
| 1 | ... | haiku | done | - |
| 3 | ... | sonnet, then opus | done | retry, then opus: missed the empty-list case |

Deviations from plan: <what changed and why, or "none">
Not verified: <what you did not check yourself and why>
Remains: <open items, follow-ups, actions waiting for the user>
```

No retelling of the process, no per-worker narrative. Say "none" for an empty section rather than
dropping it, so the user knows it was considered.
