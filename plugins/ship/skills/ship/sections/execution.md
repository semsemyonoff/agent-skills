# Approved shipping execution

Read after shipping approval; watch-only requests use `wait-ci.md` instead. All git helper calls
retain planned root/branch/task/base. `wait-ci` uses its independent owner/repo/PR/base interface.
Keep per-repo target base, candidate head and `accepted_head` with `evidence_basis` (`CI passed`
or `explicit no-CI permission`). Acceptance belongs to a SHA, not a branch; discard it when head changes.
Retain each repo's original PR-wait start/deadline (default 1800 seconds). When an independent
pre-merge read forces another helper invocation, pass only that deadline's remaining `--timeout`;
never renew the budget for a moving head or merge retry.

Never label no-CI permission a CI pass. Repos proceed independently.

1. Run `ship.py push --repos ...` for non-skipped repos. `failed` -> `push failed`, error verbatim.
2. Create or reuse the resolved PR. Creation error -> `PR failed`, verbatim. With a valid handoff,
   append verification only to a new PR (`task.md`); do not update reused PR bodies, and disclose
   that omission. Read current PR `head.sha`, never stale plan `head_sha` after a rebase/fix push.
3. PRs-only repos end `PR open`: no CI wait, merge, remote-branch wait or sync.
4. Start read-only helper waits for all mergeable repos (`wait-ci.md`). Gated mode uses the normal
   PR wait; auto-merge mode uses PR `--guard-only` to establish check presence without waiting for
   all CI before server scheduling. This shared checks guard applies even when plan `has_ci` is
   false: external CI can post statuses without a workflows directory. Do not model-poll either
   source or reproduce helper reduction. A normal gated success records returned `accepted_head`
   with `CI passed`; failures use `ci-failure.md`; pending/timeout is not acceptance.
5. Complete empty sources for about 60 seconds return `pending` with `checks_guard.state: no-checks`.
   This is evidence of no checks reported, not a CI pass. Only a gated repo explicitly approved in
   the no-CI question may accept that complete stable `checked_sha` with `explicit no-CI permission`. Auto-merge
   instead ends `not merged: required checks never reported`, even with no-CI permission. Other
   repos end `PR open: no checks`. Incomplete/error sources never authorize this exception.
6. Before **every** merge call or retry independently re-read the PR through MCP: it must be open,
   with `base.ref` equal to retained target; retargeted -> `not merged: base changed`, no write;
   closed unmerged -> `PR closed`. Gated/no-CI head differs from accepted SHA -> clear acceptance
   and restart helper guard/gate on the new head with only the remaining original deadline, not
   a fresh 1800 seconds. Helper-internal head changes also never extend that deadline.
   - Explicit no-CI acceptance: plain merge once with `merge_when_checks_succeed=false`, never
     `force_merge`. On success proceed directly to step 9: do not gate, wait or merge again.
   - Gated CI success: plain merge with `merge_when_checks_succeed=false`, never `force_merge`.
     See `ci-gate.md` for full reduction and residual-race semantics.
   - Auto-merge with observed checks: snapshot the freshly re-read candidate head, schedule
     `merge_when_checks_succeed=true`, `delete_branch_after_merge=true`, never `force_merge`.
     Then use existing `ship.py wait --repos <auto-merge repos>` for remote-branch deletion,
     not `wait-ci` as a substitute. Accept candidate head as `CI passed` (server-enforced required
     checks) only after the PR confirms merged on that same head.
7. On merge error re-read PR: `mergeable=false` -> `conflict` (`conflict.md`); transient
   “mergeability still being checked” (405/try again later; unverified) -> retry once after short
   sleep, repeating the full pre-merge guard. Otherwise `merge not scheduled` with the error.
8. Remote-branch `wait` pending (auto-merge): re-read PR, then use **one** PR `wait-ci --once`
   snapshot for current-head diagnostics, retaining expected base. If PR is closed/merged,
   respect its state and accepted-head rules rather than inventing a check result. Actual failing
   sources -> `CI failed`, diagnose their exact source/state/context (`ci-failure.md`). Incomplete
   source diagnostics are unavailable evidence, never “all green”. Still running -> `timeout`,
   offer ONE further bounded wait. All checks success but not merged -> `not merged` with observed
   reason (e.g. approvals required or auto-merge cancelled), no endless re-wait offer.
   `mergeable=false` -> `conflict`. A completed branch wait alone is not merged-PR proof.
9. Before sync, read PR through MCP: `merged:true`, target base matches and `head.sha` equals
   `accepted_head`, retaining its evidence basis. Closed unmerged -> `PR closed`, no sync.
   Merged head mismatch or missing acceptance -> `merged: ungated head <sha>`, no sync/cleanup;
   base mismatch -> `not merged: base changed`, no sync/cleanup. This catches the residual race
   because MCP merge has no expected-head condition. The script's branch deletion safeguard is
   additional safety, not a substitute for this check.
10. Sync confirmed repos immediately with `ship.py sync --repos <confirmed only> --confirmed-merged
    --head <path>=<accepted_head> ...` plus retained root/branch/task/base. Do not wait for slow repos.
    Report each result through the core status table, then only the previously authorized task step.

Helper exit 2 or credential/API capability failures are explicit per-repo failures, not permission
to use direct write APIs or silently fall back to model polling. Preserve other repos' progress.
Any requested post-merge publication/deploy wait is separate: observed merge SHA, explicit target
ref and selected workflow filenames, following `wait-ci.md`; shipping does not itself prove deployment.
