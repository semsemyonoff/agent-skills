# Changelog

## 0.3.0

- Track the accepted PR head and its evidence basis through merge and sync: explicit no-CI permission supports safe sync without a false CI-pass claim; head/base changes block cleanup, while required-check auto-merge remains protected.
- Diagnose the actual failed check source, including cancelled Actions runs with no failed job and external warning/failure/error statuses with no Actions logs; never perform unasked retries or check mutations.
- Align tracker evaluation with the upfront task decision and add observable behavioral scenarios for accepted-head sync, races, check diagnostics, and no-task/Leave-it handling; keep dry-run grades separate from execution evidence.

## 0.2.0

- Ship into a named integration branch: `ship.py --base` and "[branch] into <base>"; a missing target is never replaced by the default branch, and the merged PR's base is verified before sync.
- Choose the merge mode per repo from the base's status-check settings: server auto-merge only when the base requires checks; otherwise ship gates CI itself (all Actions runs for the head plus the latest status per context, fully paged) and then merges, because Forgejo's auto-merge fires on the first green status when nothing is required. The base is re-checked before every merge call.
- Start from a Vikunja task as well as a branch (`ship.py --task` finds the `<id>-<slug>` branch; `plan` reports `task`), and ask in the single confirmation whether to report into the task and close it; the vikunja skill writes the report after the merge, and a partial result is never closed.
- A PR that gets no checks no longer hangs on an auto-merge that never fires: repos approved as no-CI merge, others stay `PR open: no checks`; merged repos sync without waiting for slower ones.

## 0.1.1

- Support native Codex in the shared ship skill: discover Forgejo MCP tools, confirm in plain text when no ask tool is available, and wait with a bounded foreground fallback.
- Retain the planned root and branch for every later helper call so local sync cannot change branch detection.

## 0.1.0

- Add the ship skill: bring a plan branch to the base branch in every workspace repo on Forgejo (push, PR, server-side auto-merge when CI is green, wait, sync, branch cleanup, per-repo report, offer to report into Vikunja).
- Deterministic helper `scripts/ship.py` for discovery, push, background wait and safe local sync; CI-failure and conflict scenarios in `sections/`.
- Contract hardening before release: forge identity and base checks, CI race guard, explicit terminal statuses, upfront rebase option, AskUserQuestion-sized confirmation.
