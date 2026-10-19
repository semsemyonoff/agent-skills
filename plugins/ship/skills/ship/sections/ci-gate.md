# CI gate

Applies to PR CI waits and `gated` shipping repos. With no required status checks, Forgejo's
auto-merge can fire on the first green status while other jobs still run (seen live).
`ship.py wait-ci` implements this entire reduction locally; the model consumes its final JSON.
Read `wait-ci.md` for invocation and `execution.md` for shipping/no-CI/auto-merge integration.

## Sources

Both must pass; a job can have no commit status yet, so statuses alone are not enough. The gate
covers checks that have appeared; it cannot prove that no later check will start.

- Every Actions run for the exact SHA: `success`/`skipped` pass;
  `waiting`/`running`/`blocked`/`unknown` pending; `failure`/`cancelled` fail. A job rerun updates
  its own run. A failed run that a separate later run may have replaced still fails, since the
  listing cannot link them: `CI failed`, the user decides.
- The latest commit status per `context` by `created_at`:
  `success`/`skipped` pass, `pending` pending, `failure`/`error`/`warning` fail. Newer rerun
  statuses supersede older ones. On a same-second tie, terminal beats `pending` only if the
  status `target_url` names a listed run (`/actions/runs/<N>/`, same N as the run URL) that is
  terminal; otherwise it stays pending (external CI too). Failure beats success on a tie.

The helper pages both lists to the end before reducing. A failed/incomplete page makes the
snapshot pending with source diagnostics: never judge partial lists. Unknown states stay pending.
Do not repeat this algorithm in model-driven MCP calls.

## Final outcome

- `success` (at least one check) -> helper returns checked SHA as `accepted_head`; shipping records
  `CI passed`, then independently re-reads PR through MCP (open, expected base, same head) before a
  plain merge with `merge_when_checks_succeed=false`, never `force_merge`. Re-read on every retry.
  Head moved -> discard acceptance and restart with remaining original total deadline.
- `fail` -> `CI failed`; pass actual failing source(s), SHA, run ID/state or external
  context/state/description/target_url to `sections/ci-failure.md`, not a presumed failed job.
- Pending sources are polled inside the helper (30 seconds, 1.5 backoff capped at 120), not by
  model sleeps. Total default 1800 seconds -> `timeout`, offer ONE further bounded wait.
- Complete empty sources for ~60 seconds -> `pending` with `checks_guard.state: no-checks`,
  never success. Apply only `execution.md`'s original explicit no-CI permission policy; watch-only
  has no merge authority. Head changes reset that empty guard, not the overall deadline.
- Closed or retargeted PR -> failure, no write. Page/network errors -> pending/timeout with
  diagnostics, never no-CI acceptance or silent fallback to model polling.

Selected post-merge publication/deployment workflows have different scope: see `wait-ci.md`.
In that mode unrelated CI/statuses are excluded and skipped runs do not prove deployment success.

## Residual race

The MCP merge takes no expected head, so a push between the re-read and the merge is not prevented.
After the merge compare the PR `head.sha` with `accepted_head` and its base with the retained target,
as required by `SKILL.md`. A head mismatch -> `merged: ungated head <sha>`, with no sync or branch
cleanup in that repo. This also applies to a head accepted with explicit no-CI permission.
