# CI failure

Applies to failing check sources from a PR gate or selected workflow wait: Actions
`failure`/`cancelled`, or latest PR external status `failure`/`error`/`warning`. Use helper JSON's
actual source, SHA and state, not an assumed failed job. Watch-only diagnosis remains read-only.

1. For an Actions source, retain database run `id`, state and `url` from helper evidence for that
   SHA (`url` is sanitized from API `html_url`). Web number `index_in_repo` is not necessarily the ID.
   `list_action_run_jobs(owner, repo, run_id)` -> inspect actual failed or cancelled jobs.
   Fetch `get_action_job_logs(owner, repo, job_id)` only for an existing relevant job, with default
   `max_bytes` (32768), no `offset` (tail); page backward only if needed. A cancelled run may have
   no failed job or logs: report its cancellation and available run/job evidence, not a guessed
   test failure. Missing/unavailable logs are an evidence limitation, not invented log lines.
2. For an external status, report the actual context, state, description and `target_url` (or their
   absence). Do not search for an unrelated failed Actions run or call job/log tools without an
   associated run/job. If its URL identifies a listed Actions run for the same SHA, inspect that
   run as above; otherwise use the external evidence and state what diagnosis it cannot support.
3. Diagnose from available evidence: quote decisive log lines and failing step only when observed;
   otherwise quote the run state or external description, distinguish likely cause from unknown,
   and propose an appropriate next action. Retain multiple failing sources rather than hiding one.
4. Do not retry/rerun/cancel checks, edit statuses, commit or push fixes unless explicitly asked.
   Reading evidence is not permission for those writes. Other repos continue independently.

After an explicitly requested fix is pushed, clear acceptance and re-check the PR with
`get_pull_request_by_index`. `gated` repos: restart `wait-ci` guard/gate on the new head.
`auto-merge` repos: check whether auto-merge remains scheduled, retain the new candidate head
before a new `ship.py wait`, and accept it only on same-head confirmed server-enforced merge.
If auto-merge was dropped, report it and ask before scheduling it again. Continue only through
the normal accepted-head/base pre-sync check, passing `--head <path>=<accepted_head>`.
