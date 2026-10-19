# Read-only CI and deployment waiting

Use the bundled helper for shipping gates and natural requests such as “watch CI for PR 12”,
“wait for publication”, «дождись CI» or «последи за деплоем». It performs bounded polling locally
and returns one final JSON; the model does not drive polling rounds or repeated sleeps.

## Watch-only entry

Resolve the Forgejo instance, owner/repo and either PR index plus expected base, or exact full
40-hex SHA, target branch/ref and explicit workflow selectors. Reuse trustworthy supplied/current
read-only evidence; ask only for materially missing identity/target/selection. Never infer deployment
success from an arbitrary green workflow. For post-merge watching use the observed merge commit
SHA, not the PR head SHA; a non-main target is valid. Resolve mutable refs once, retain the fixed SHA,
and do not silently follow newer commits. No git checkout or workspace is required.

Watch-only does not run shipping preflight/approval, task discovery, push, PR creation/update,
merge scheduling, sync, branch deletion or tracker actions. A task number or branch slug in the
request is not permission for any of those. Waiting does not dispatch, rerun or cancel a workflow.
Missing MCP is not a blocker for this read-only helper; missing helper credentials/capability is.

## Commands

Resolve `<skill_dir>` from the loaded `SKILL.md`; quote all user-derived arguments as data.

PR CI (follows head changes, checks PR open and expected base):

```sh
python3 <skill_dir>/scripts/ship.py wait-ci --owner OWNER --repo REPO --pr INDEX --base REF
```

Selected publication/deployment workflows (fixed SHA and ref):

```sh
python3 <skill_dir>/scripts/ship.py wait-ci --owner OWNER --repo REPO --sha FULL40 --ref main --workflow publish.yml --workflow deploy.yml
```

Each `--workflow` is an exact Forgejo run `workflow_id` filename (for example `deploy.yml`),
not its display name, run ID or an invented path selector. Repeat it for every required workflow.
Use actual repository/workflow evidence to resolve selectors; clarify ambiguous selections.
`--ref` accepts a branch name or full `refs/heads/...`; it is normalized to the full branch ref.
Unselected workflows and commit statuses do not participate in this mode. Every selected workflow
must appear for that exact SHA/ref and every matching run must finish successfully. Missing stays
pending until timeout. `skipped` is not publication/deployment success; failure/cancellation fails,
and a separate later success does not erase an earlier matching failure.

PR-only `--guard-only` returns once complete stable sources contain any check: `status: pending`,
`reason: checks-detected`, `checks_guard.state: checks-detected` and `checked_sha`, never
`accepted_head`. This is only check-presence evidence for server auto-merge, not CI acceptance.
If sources stay empty it uses the same 60-second no-checks guard. Do not pass it in workflows mode.

Common flags: `--timeout 1800`, `--interval 30` (1.5 backoff capped at 120 seconds), `--once` for
one complete snapshot without an internal wait. A head change never extends the original monotonic
deadline. Do not implement `--once` loops in the model; use it only for a deliberate single snapshot
such as auto-merge timeout diagnostics. No `--root`, `--branch`, `--task` or `--repos` is needed.

## Credentials and capability boundary

The process must already have `FORGEJO_URL` and `FORGEJO_TOKEN` in its environment, for the intended
instance. Match the instance to the known repo host before shipping. Do not print the token, pass it
in argv, read harness/MCP config, extract stored credentials, create credentials or change config.
Real instance URLs use HTTPS; HTTP loopback is only for isolated fixtures. The exception to MCP-only
access permits this helper's read-only PR/CI GETs only, never direct API mutations or shell forge CLIs.

Missing Python/helper, URL/token, network/auth/API capability or source errors must be reported
explicitly (without secrets). Do not silently substitute repeated model/MCP polling. Usage/environment
errors exit 2; JSON `success|fail|pending|timeout` outcomes exit 0, so exit 0 alone is not CI success.
Authentication denial is an environment failure (exit 2). Network/invalid-page failures remain
conservative pending (`--once`) or timeout with source diagnostics, never partial acceptance.

## Consume evidence

JSON includes `status`, `mode` (`pr|workflows`), owner/repo, `sha`, `elapsed`, `reason`,
`evidence` (`runs`, `statuses`, `missing_workflows`), `sources` completeness/page/count/error
information and `head_changes`. Complete stable PR snapshots include `checked_sha`; only PR
success includes `accepted_head`. PR empty sources include `checks_guard` with `state: waiting|no-checks`,
elapsed and a 60-second guard. A normal wait returns `pending`, `reason: no-checks` after that
complete empty guard, never success; a shorter total deadline still times out. Shipping applies
the original explicit no-CI policy in `sections/execution.md`; watch-only merely reports no checks.

Launch waits for all applicable repos before collecting results. Use the harness's background/yielded
command mechanism, or a foreground bounded timeout within its tool execution limit. Resume/collect
completion using the actual harness interface; do not assume notifications. Retain per-repo results
and process completed healthy repos without waiting for slower ones. Never replace the helper with
model-driven check polling when background support is absent.

Report target SHA/ref or PR/base, selectors where applicable, result, elapsed, head-change and source
limitations. `fail` uses actual evidence with `sections/ci-failure.md`; timeout may offer one explicitly
bounded further wait, not an endless loop. Selected-workflow success means only “selected workflows
completed”, not global CI passed, deployed service health, availability or end-to-end deployment proof.
After shipping, use this separate fixed-SHA path only when publication/deployment watching was requested
and workflows/ref are explicitly resolved; merge success alone never selects workflows or proves deployment.
