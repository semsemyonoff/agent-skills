# Model routing

Default for every worker. Deviating is allowed, but the plan row must say why in one line.

| Model | Use for | Not for |
| --- | --- | --- |
| haiku | search and listings; reading with summarisation; fact gathering by a checklist; bulk mechanical edits by an exact spec (rename, replace a pattern, add a field everywhere) | anything that needs judgment |
| sonnet | implementation from a clear spec; tests; docs; CSS and markup; texts and copy; log and transcript analysis; ordinary refactoring | architectural forks; final review of risky changes |
| opus | architecture and design; risky backend (migrations, concurrency, security, data integrity); review of other workers' output; murky debugging without a hypothesis | CSS, copy, small doc edits |

The orchestrator itself runs on the session model: it plans, verifies and decides.

## Why this matters

A worker launched without `model` inherits the session model, usually opus. In past sessions most
opus spend was justified; the waste was CSS tweaks, copy rewrites and small doc edits run on opus. The
table exists to catch exactly those.

## Picking in unclear cases

- **Mixed step** (a migration plus the handler that uses it): split it, or route by the hardest part.
- **Unsure between two models:** take the cheaper one; verification and escalation catch a miss.
  Exception: risky backend goes to opus from the start, because a subtle bug there may pass tests
  and slip past a quick diff read.
- **Spec quality decides as much as the task.** "Add endpoint X exactly like Y" is sonnet; "figure out
  how X should work" is opus. If a sonnet step needs design decisions, make them in the plan first.
- **Review is a separate step on a different worker**, not self-review by the implementer.

## Deviation examples

- `sonnet` for a migration: "additive column with a default, no backfill, pattern copied from 0042".
- `opus` for a doc: "ADR that has to weigh three storage designs".
- `haiku` for tests: "parametrised cases added to an existing table, exact inputs listed in the brief".
