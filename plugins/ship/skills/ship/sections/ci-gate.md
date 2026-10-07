# CI gate

Applies to `gated` repos: the base requires no status checks, so Forgejo's auto-merge would fire on
the first green status while other jobs still run (seen live). Ship waits for CI itself and then
merges. Run it for all gated repos per round, on each PR's `head.sha`.

## Sources

Both must pass; a job can have no commit status yet, so statuses alone are not enough. The gate
covers checks that have appeared; it cannot prove that no later check will start.

- Every `list_workflow_runs(head_sha)` run: `success`/`skipped` pass;
  `waiting`/`running`/`blocked`/`unknown` pending; `failure`/`cancelled` fail. A job rerun updates
  its own run. A failed run that a separate later run may have replaced still fails, since the
  listing cannot link them: `CI failed`, the user decides.
- The latest commit status per `context` by `created_at` (the MCP exposes no status index):
  `success`/`skipped` pass, `pending` pending, `failure`/`error`/`warning` fail. Newer rerun
  statuses supersede older ones. On a same-second tie, terminal beats `pending` only if the
  status `target_url` names a listed run (`/actions/runs/<N>/`, same N as the run URL) that is
  terminal; otherwise it stays pending (external CI too). Failure beats success on a tie.

Page both lists to the end (`limit` 50, next `page` until a short page) before reducing. A failed
page fetch makes the round pending: never judge partial lists.

## Round outcome

- All pass (at least one check; empty sources go through the checks guard, never count as passing)
  -> snapshot the checked SHA as `accepted_head`, evidence basis `CI passed`; then the pre-merge
  re-read from `SKILL.md` (open, `base.ref`, same `head.sha`). If the head moved, clear acceptance
  and restart the checks guard/gate on the new SHA. Otherwise `merge_pull_request` with
  `merge_when_checks_succeed=false`, never `force_merge`. Re-read again on every retry.
- Any fail -> `CI failed`; pass the actual failing source(s), head SHA, run ID/state or external
  context/state/description/target_url to `sections/ci-failure.md`, not a presumed failed job.
- Anything pending -> pause with the harness's wait mechanism (e.g. a background `sleep`), 30 s
  growing to 120 s; 1800 s total -> `timeout`, offer ONE more round.

## Residual race

The MCP merge takes no expected head, so a push between the re-read and the merge is not prevented.
After the merge compare the PR `head.sha` with `accepted_head` and its base with the retained target,
as required by `SKILL.md`. A head mismatch -> `merged: ungated head <sha>`, with no sync or branch
cleanup in that repo. This also applies to a head accepted with explicit no-CI permission.
