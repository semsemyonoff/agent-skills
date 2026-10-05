# CI failure

Applies to a repo whose commit statuses for the PR `head.sha` show failure/error (status `CI failed`).

1. `list_workflow_runs(owner, repo, head_sha=<PR head.sha>)` -> pick the failed run.
2. `list_action_run_jobs(owner, repo, run_id)` -> pick the failed job(s).
3. `get_action_job_logs(owner, repo, job_id)` with the default `max_bytes` (32768) and no `offset`:
   that returns the tail. Page backward only if the error is not in the tail.
4. Diagnose: quote the failing step and the decisive log lines, state the likely cause, propose a fix.
5. Do not commit or push a fix unless the user asks. Other repos continue independently.

After a fix is pushed, re-check the PR with `get_pull_request_by_index` (the auto-merge may still be
scheduled) and include the repo in a new background `ship.py wait`, then continue the normal flow
(confirm `merged: true`, then `sync --confirmed-merged --head <path>=<PR head.sha>`). If the auto-merge was dropped, report it and
ask before scheduling it again.
