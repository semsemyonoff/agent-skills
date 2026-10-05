---
name: ship
description: 'Bring an implemented plan branch to the base branch (main) in every repo of a workspace on Forgejo - push, open PR, schedule server-side auto-merge when CI is green, wait, sync the base locally, delete branches, report per repo. Use after a plan was implemented (e.g. by ralphex) and the code sits in a plan branch. Triggers - /ship:ship, /skill:ship, "ship the plan branch", "merge the plan branch into main in all repos", "open PRs and merge when green", "land this branch", «доведи ветку до main», «смержи план во всех репо», «открой PR и смержи после CI», «зашипь ветку». Not for - just creating a PR without merging, reviewing a PR, closing tracker tasks, GitHub/GitLab repos, deploys.'
argument-hint: "[branch]"
---

# Ship

Take a finished plan branch to the base branch in every repo of the workspace that has it:
push -> PR -> auto-merge when CI is green -> wait -> sync base locally -> delete branches -> report.
Forgejo only, driven through the Forgejo MCP. Reply in the user's language. PR titles/bodies use the
language of the plan/commits (default: short English title from the branch/commits, body summarises
the commits). No personal data in PR bodies.

Do not assume an install location or an environment variable for the script.
Invoking the skill already means the user wants the branch
pushed: never ask about pushing.

## Helper

Run it by the absolute path of this skill's directory (resolved from the loaded `SKILL.md`) with the
shell cwd set to the user's workspace (or pass `--root`); from any other cwd root/branch detection breaks.

`python3 <skill_dir>/scripts/ship.py <plan|push|wait|sync> [--root DIR] [--branch NAME] [--repos PATH...]`

Retain `root` and `branch` from `plan`; pass `--root <root> --branch <branch>` explicitly to every
later helper call, including retries. `sync` switches the current branch, so do not re-detect it.

- JSON to stdout, diagnostics to stderr. Exit 0 = ran (per-repo statuses in JSON); exit 2 =
  usage/environment error (no git, root not found, branch undeterminable, branch is main/master/base).
  Network git calls have timeouts and run with `GIT_TERMINAL_PROMPT=0`.
- Root: `--root`, else nearest `workspace.yml` upward, else git toplevel. Branch: `--branch` (or the
  skill argument), else current branch of the cwd repo. Discovery keeps repos that have the local
  branch.
- `plan` (read-only, no fetch): `{root, branch, repos:[{path, remote_url (userinfo redacted), host
  (ssh-config-resolved hostname; `host_alias` when the remote used an alias), owner, repo, base,
  is_base, has_ci, dirty, ahead, behind, pushed, remote_branch (origin/<branch> exists locally),
  head_sha, current_branch}]}`.
  `base` resolves origin/HEAD -> origin/main -> origin/master and may be null; `ahead`/`behind` are
  against `origin/<base>`; `has_ci` = a workflows dir (.forgejo/.gitea/.github) exists on the branch tree.
- `push [--repos]`: always pushes (idempotent); per repo `pushed | up-to-date | failed` (+`error`,
  includes porcelain `!` reject lines).
- `wait [--repos] [--timeout 1800] [--interval 15]`: polls the remote branch with backoff; branch gone
  -> `merged`; still there at timeout -> `pending` (+`remote_sha`, and `error` if ls-remote kept
  failing); undiscovered repos -> `failed`. Run it in the background when supported: Claude Code
  Bash `run_in_background`; omp's background mechanism; native Codex's yielded command session
  (`exec_command` -> `session_id`, collect with `write_stdin`) if available. Otherwise run in the
  foreground with an explicit `--timeout` within the tool's execution limit. Resume on completion;
  do not assume the harness sends a notification.
- `sync --repos PATH... [--confirmed-merged] [--head PATH=SHA ...]` (`--head`: full 40-hex sha,
  only for paths in `--repos`, else exit 2): dirty, base null or `is_base` -> `sync failed` (+`error`);
  fetch --prune; switch to base; `merge --ff-only origin/<base>` (failure -> `sync failed`, never
  reset; errors after the switch say "(worktree left on <base>)"); `branch -d`; if refused
  (squash/rebase), remote branch gone, `--confirmed-merged` AND local tip equals the expected sha (`--head`,
  else the pushed ref) -> `-D` (`deleted: forced`); otherwise `kept` (error "local commits not in
  merged PR" when the tip differs; "cannot verify local tip (no pushed ref; pass
  --head)" with neither).
  Statuses `synced | kept | sync failed`.

## Forgejo MCP

Match names and schemas to what the Forgejo MCP server actually advertises in the current harness
(e.g. `mcp__forgejo__get_repo` in native Codex, with the configured server's prefix). Load deferred
schemas with Claude Code ToolSearch or the available discovery tool in omp/native Codex.
Use `host/owner/repo` from `plan`.

- `get_repo(owner, repo)` -> `default_merge_style`.
- `list_repo_pull_requests(owner, repo, state, page, limit)`: no head filter. Find an existing open PR
  by `head.ref == branch` client-side, paging through.
- `create_pull_request(owner, repo, head, base, title, body)`.
- `merge_pull_request(owner, repo, index, style, merge_when_checks_succeed, delete_branch_after_merge,
  force_merge, ...)`: `style` is required (`merge|rebase|rebase-merge|squash`); always
  `merge_when_checks_succeed=true`, `delete_branch_after_merge=true`; NEVER `force_merge`.
- `get_pull_request_by_index(owner, repo, index)` -> `merged`, `mergeable`.
- `get_commit_statuses(owner, repo, sha)` (40-hex sha); `list_workflow_runs`, `list_action_run_jobs`,
  `get_action_job_logs` for failures (see `sections/ci-failure.md`).

If the Forgejo MCP tools are absent, report the missing connection and stop before any write. Do not
substitute gh/glab/fj/REST and do not change MCP configuration.

## Workflow

1. **Preflight.** Run `ship.py plan`. Exit 2 -> report the error and stop. No repos with the branch
   -> say so and stop. Any environment failure stops before a write.
2. **Forge facts (read-only).** Per repo: `get_repo` (merge style; a style named in the request
   overrides it). Forge identity: compare plan `host` (resolved) with the hosts of `html_url`, `ssh_url`
   and `clone_url`; owner/repo null or no host matches -> `skipped: not forgejo`. Base: PR base =
   `default_branch`; plan `base` null or
   different -> `skipped: base mismatch` (hint `git remote set-head origin -a`);
   `is_base` -> `skipped: is base`.
   Find the existing open PR for the branch and its base. No CI = plan `has_ci` false.
3. **Confirm once.** Show an action table: `repo | push? | PR new/#N | merge style | then`. Then ONE
   structured-choice call: Claude Code `AskUserQuestion`; omp `ask`; native Codex's ask tool only if
   available for confirmations. Without a suitable ask tool, ask the same questions together in plain
   text, end the turn and wait for explicit answers (silence/dismissal is not approval). Respect the limits
   (<=4 questions, 2-4 options each): one question per category listing the affected repos, never
   per repo. Only needed questions:
   - Always: "Merge into <base>?" - "Start (Recommended)" / "PRs only, no auto-merge" / "Stop"
     («Начать (рекомендуется)» / «Только PR, без автомержа» / «Стоп»).
   - Dirty repos: "Skip (Recommended)" / "Stop everything".
   - `behind > 0`: "Merge as is (Recommended)" / "Rebase first". For repos whose branch is already on
     the remote (plan `remote_branch` true) the label is "Rebase first (force-with-lease
     push)"; plain "Rebase first" when it is false. Split into two options if both kinds occur.
   - Repos without CI (auto-merge would merge at once): "Merge (Recommended)" / "PR only".
   - Existing open PR with another base: "Skip" / "Create new PR".
   If more than 3 conditional categories apply, fold the no-CI decision into the main question as the
   option "Start; PR only for repos without CI". After the answer run to the end without questions.
   "Rebase first" is part of this approval: rebase onto `origin/<base>` BEFORE the first push, in
   those repos only; for already-pushed repos this includes the force-with-lease push the label
   named (see `sections/conflict.md` for a failing rebase).
4. **Execute** (repos independently).
   1. `ship.py push --repos ...` for non-skipped repos. `failed` -> `push failed`, error verbatim.
   2. Create the PR (`create_pull_request`; error -> `PR failed`, verbatim) or reuse the existing one.
      From here on use the PR's `head.sha` (`get_pull_request_by_index`), never plan `head_sha`: it
      goes stale after an upfront rebase or a CI-fix push.
   3. "PRs only" (or PR-only repos): no merge, no `wait`/`sync`; status `PR open`.
   4. Race guard for `has_ci` repos (UNVERIFIED Forgejo behaviour: auto-merge may fire before the
      runner creates statuses): call `get_commit_statuses(<PR head.sha>)` before scheduling; if empty,
      re-check a couple of times with a short sleep (<= ~1 min total); still empty -> schedule anyway
      and note it in the report.
   5. `merge_pull_request` with auto-merge. On error re-read `get_pull_request_by_index`:
      `mergeable=false` -> `conflict`; a transient "mergeability still being checked" (405/try again
      later; unverified) -> retry once after a short sleep; else `merge not scheduled` with the error.
   6. `ship.py wait --repos ...` (only repos with a scheduled auto-merge), using the harness's wait
      mechanism or foreground `--timeout` described above; continue when it completes.
   7. Branch gone (`merged`): `get_pull_request_by_index`; `merged: true` -> `ship.py sync --repos
      <confirmed only> --confirmed-merged --head <path>=<PR head.sha> ...`;
      `merged: false` -> `PR closed`, no sync.
   8. `pending`: `get_commit_statuses(<PR head.sha>)`. Any failure/error -> `CI failed`
      (`sections/ci-failure.md`). Still running -> `timeout`, offer ONE more wait. All success but not
      merged (approvals required, auto-merge cancelled) -> `not merged` with the reason from the PR;
      no endless re-wait offer. `mergeable=false` -> `conflict` (`sections/conflict.md`).
5. **Report.** One table `repo | PR | status | next`. Statuses: `merged`, `PR open`, `PR failed`,
   `merge not scheduled`, `PR closed`, `not merged`, `CI failed`, `conflict`, `timeout`,
   `push failed`, `sync failed`, `kept` (branch kept), `skipped: dirty|not forgejo|base mismatch|is base`.
   Map script statuses: sync `synced` -> `merged`; `kept` -> `merged (branch kept: <reason>)`;
   `sync failed` -> `merged, sync failed: <error>`; wait `failed` -> `wait failed: <error>`.
   Then exactly one offer: report the result into the linked Vikunja tasks through the vikunja skill
   if available. Do not write to Vikunja yourself.

## Rules

- Repos are independent: a failure in one never stops the others.
- Errors are reported verbatim, never skipped or paraphrased away.
- Never force-merge, never reset, never push fixes or rewrite history without the user's explicit
  request/confirmation; never resolve conflicts silently.

## Sections

- `sections/ci-failure.md` - read when a PR's checks failed.
- `sections/conflict.md` - read when a PR is not mergeable or an upfront "Rebase first" fails.
