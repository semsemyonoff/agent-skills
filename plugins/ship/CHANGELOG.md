# Changelog

## 0.5.2

- Resolve `--task N` and derive the task from `task/<id>-<slug>` branches as well as `<id>-<slug>`; both forms at once stay ambiguous.

## 0.5.1

- Reject URI-scheme values (such as omp `local://`) for `handoff --comments`/`--argument` with an actionable error; task flow now requires real temp files for helper input.
- Align the duplicated handoff contract with producers that always write `Цель` (including the default branch); handoffs without it stay valid but the target must still be clarified.
- Add behavioral scenarios for handoff `Цель: main`, legacy handoffs without `Цель`, and omp file materialization.

## 0.5.0

- Resolve task destinations explicitly instead of falling back to the repository default: unresolved task plans expose a null base, and task push/wait/sync require `--base`.
- Check reported task commits against fresh remote target history before proposing a merge; fully verified delivery preserves shared branches and permits only separately approved tracker reporting.
- Treat shared-source or extra-repository shipping as a scope change, with explicit whole-branch source-to-target approval rather than a recommended generic Start.
- Add isolated Git regression coverage and bilingual evaluation scenarios for already-delivered work, incomplete evidence, ambiguous targets, and scope expansion.

## 0.4.0

- Read and validate task/inline handoffs before confirmation, resolve branch ambiguity and candidate targets with provenance, and carry historical verification into new PRs and task reports without granting merge or CI authority.
- Show the handoff timestamp and any later progress/completion report before confirmation without changing candidate selection.
- Add Russian/English behavioral handoff scenarios and deterministic parser coverage.

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
