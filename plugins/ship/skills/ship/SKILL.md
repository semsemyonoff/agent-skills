---
name: ship
description: 'Ship implemented plan/task branches across Forgejo workspace repos: push, PR, safe CI-gated merge, sync, cleanup and optional task report. Also use for read-only waiting on Forgejo PR CI or explicitly selected publish/deploy workflows for an exact SHA/ref, without shipping. Triggers: /ship:ship, /skill:ship, "ship task 587", "land this branch", "merge when green", "watch CI for PR 12", "wait for deployment on this commit", «зашипь задачу», «доведи ветку до main», «смержи после CI», «дождись CI у PR», «последи за деплоем», «дождись публикации». Not for GitHub, standalone PR creation, CI configuration, deployment execution, service-health checks or failure diagnosis without waiting.'
argument-hint: "[branch | task] [into <base>] | watch CI/deploy <target>"
---

# Ship

For a request only to watch CI, publication or deployment, read `sections/wait-ci.md` and take its
watch-only path **before** task discovery or shipping preflight. Do not turn watching into shipping.

Take a finished plan branch to the base branch in every repo of the workspace that has it:
push -> PR -> merge when CI is green -> sync base locally -> delete branches -> report -> task.
The entry is a branch or a Vikunja task (its `<id>-<slug>` or `task/<id>-<slug>` branch), optionally with multiline handoff
fields; read `sections/task.md` before preflight for a task or handoff, including comment discovery.
Base: the user's named destination, else valid handoff target. For a named/inferred task, an
unresolved target requires clarification; never default it to main. Only non-task branch shipping
defaults to each repo's default branch. A missing named remote target is a question, not a guess.
Forgejo only: mutations use Forgejo MCP; the bounded read-only `wait-ci` API exception is below.
Reply in the user's language. PR titles/bodies use the
language of the plan/commits (default: short English title from the branch/commits, body summarises
the commits). No personal data in PR bodies.

Do not assume an install location or an environment variable for the script.
Invocation authorizes preparing the intended delivery, not inventing its source, target or scope.
Do not ask separately about pushing; resolved shipping actions use the execution approval below.

## Helper

For `plan|push|wait|sync`, run by the absolute path of this skill's directory (resolved from the
loaded `SKILL.md`) with shell cwd at the workspace (or pass `--root`). `wait-ci` needs no git
workspace, branch detection or `--root`; read `sections/wait-ci.md` for its separate interface.

`python3 <skill_dir>/scripts/ship.py <plan|push|wait|sync> [--root DIR] [--branch NAME | --task ID] [--repos PATH...]`

`--base NAME` (`plan|push|wait|sync`): the named target; must exist as `origin/NAME`, never replaced by
the default. Retain `root`, `branch` and `task` from `plan`; pass them to every later git helper
call, including retries. Task `push|wait|sync` requires `--base <resolved-target>` or exits 2.
Retain named bases for non-task runs too. `sync` switches branches, so do not re-detect it.
These git-context flags do not apply to the independent `wait-ci` interface.

- JSON to stdout, diagnostics to stderr. Exit 0 = ran (per-repo statuses in JSON); exit 2 =
  usage/environment error (no git, root not found, branch undeterminable, branch is main/master/base).
  Network git calls have timeouts and run with `GIT_TERMINAL_PROMPT=0`.
- Root: `--root`, else nearest `workspace.yml` upward, else git toplevel. Branch: `--branch` (or the
  skill argument), else the single `<id>-...`/`task/<id>-...` branch for `--task`, else current branch of the cwd repo. Discovery keeps repos that have the local
  branch.
- `plan` (read-only, no fetch): `{root, branch, task (`--task`, else `<id>` of an `<id>-...`/`task/<id>-...` branch,
  else null), repos:[{path, remote_url (userinfo redacted), host
  (ssh-config-resolved hostname; `host_alias` when the remote used an alias), owner, repo, base,
  is_base, has_ci, dirty, ahead, behind, pushed, remote_branch (origin/<branch> exists locally),
  head_sha, current_branch}]}`.
  `base` is `--base` if `origin/<base>` exists (else null). Without `--base`, task plans return
  `base: null`, `ahead: null`, `behind: null` until the target is resolved; non-task plans use
  origin/HEAD -> origin/main -> origin/master. `ahead`/`behind` are against `origin/<base>`.
  `has_ci` = a workflows dir (.forgejo/.gitea/.github) exists on the branch tree - only a hint:
  workflows may not run on PRs.
- `push [--repos]`: always pushes (idempotent); per repo `pushed | up-to-date | failed` (+`error`,
  includes porcelain `!` reject lines).
- `wait [--repos] [--timeout 1800] [--interval 15]` (auto-merge repos only): polls the remote branch with backoff; branch gone
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

- `get_repo(owner, repo)` -> `default_merge_style`, `default_branch`.
- `list_branches(owner, repo, page, limit)` -> per branch `protected`, `enable_status_check`,
  `status_check_contexts` (readable without admin; branch-protection tools need admin). Page until
  the base is found.
- `list_repo_pull_requests(owner, repo, state, page, limit)`: no head filter. Find an existing open PR
  by `head.ref == branch` and `base.ref == base` client-side, paging through.
- `create_pull_request(owner, repo, head, base, title, body)`.
- `merge_pull_request(owner, repo, index, style, merge_when_checks_succeed, delete_branch_after_merge,
  force_merge, ...)`: `style` is required (`merge|rebase|rebase-merge|squash`); always
  `delete_branch_after_merge=true`; NEVER `force_merge`. `merge_when_checks_succeed=true` only in
  auto-merge mode (below); a gated merge passes `false` after the CI gate.
- `get_pull_request_by_index(owner, repo, index)` -> `merged`, `mergeable`.
- `list_action_run_jobs`, `get_action_job_logs` for failure evidence (`sections/ci-failure.md`).
- PR/check snapshots and deterministic waits use `ship.py wait-ci` (`sections/wait-ci.md`), not
  repeated model calls to `get_commit_statuses` / `list_workflow_runs`.

If shipping needs absent Forgejo MCP tools, report the missing connection and stop before writes.
Do not substitute gh/glab/fj/REST or change MCP configuration. The only direct-API exception is
bundled `wait-ci` making read-only CI/PR GETs with process-environment credentials; it authorizes
no mutation or credential extraction. Watch-only can use that helper without MCP.

## Workflow

1. **Preflight.** Resolve task/handoff context through `sections/task.md`, then run `ship.py plan`.
   Exit 2 -> report and stop, except its multiple-task-branches recovery or missing-task-branch
   delivery check. Reported delivery also triggers that check before proposing any merge:
   fully verified work ends `already delivered`, with no shipping mutations or branch cleanup.
   If plan infers a task, read that section now. Resolve source, target and scope, then replan with
   the retained task and explicit base before Forge facts. No repos with the branch -> stop.
   Environment failures stop before writes; shared-source replacement needs explicit scope resolution.
2. **Forge facts (read-only).** Per repo: `get_repo` (merge style; a style named in the request
   overrides it). Forge identity: compare plan `host` (resolved) with the hosts of `html_url`, `ssh_url`
   and `clone_url`; owner/repo null or no host matches -> `skipped: not forgejo`. Base: the resolved
   target; `default_branch` is a fallback only for non-task shipping. Named target: plan `base`
   null or not in `list_branches` -> `skipped: base not found`. Non-task default: plan `base` null
   or different from `default_branch` -> `skipped: base mismatch` (hint `git remote set-head origin -a`).
   `is_base` -> `skipped: is base`.
   Find the existing open PR whose `head.ref` is the branch AND `base.ref` is the base.
   **Merge mode** from the base's `list_branches` entry:
   - `auto-merge`: `enable_status_check` true with non-empty `status_check_contexts`. The server
     enforces those checks; schedule the merge and `wait`.
   - `gated`: anything else. Forgejo's auto-merge then fires on the first green status while other
     jobs still run (seen live), so ship gates CI itself before a plain merge.
   No CI = plan `has_ci` false; a hint for the confirmation only, the PR's checks decide.
3. **Confirm execution once, after clarification.** Show an action table:
   `repo | source → target | target source | scope/ahead | push? | PR new/#N | style | mode | then`.
   Scope is the entire branch delta; identify extra repos from task scope resolution. Then ONE
   structured-choice call: Claude Code `AskUserQuestion`; omp `ask`; native Codex's ask tool only if
   available for confirmations. Without a suitable ask tool, ask the same questions together in plain
   text, end the turn and wait for explicit answers (silence/dismissal is not approval). Respect the limits
   (<=4 questions, 2-4 options each): one question per category listing the affected repos, never
   per repo. Only needed questions:
   - Always: "Merge <source> → <target> in these repos?" — "Merge <source> → <target>" /
     "PRs only, no merge" / "Stop". Name the actual direction in the action label, not "Start".
     Both table and question identify target provenance: user, handoff `from #<id>` («из #<id>»),
     inline `from argument`, or `repository default` (non-task only).
     Broader/shared-branch shipping uses "Merge entire <source> → <target>" and no recommended
     merge option (`sections/task.md`). Unresolved roles/scope return to clarification, never approval.
   - Dirty repos: "Skip (Recommended)" / "Stop everything".
   - `behind > 0`: "Merge as is (Recommended)" / "Rebase first". For repos whose branch is already on
     the remote (plan `remote_branch` true) the label is "Rebase first (force-with-lease
     push)"; plain "Rebase first" when it is false. Split into two options if both kinds occur.
   - Repos without CI (plan `has_ci` false, listed by name): "Merge (Recommended)" / "PR only".
   - Existing open PR with another base: "Skip" / "Create new PR".
   - A task (plan `task` or a named one): the task question from `sections/task.md`.
   Over 4 questions: fold no-CI into the main question ("Merge X → Y; PR only for repos without CI"),
   then dirty ("...; skip dirty repos"); keep the actual source/target and any "entire branch"
   scope in the action label. The main question keeps three options, and a folded policy applies
   to every option that proceeds, "PRs only" included. After approval run to the end without questions.
   "Rebase first" is part of this approval: rebase onto `origin/<base>` BEFORE the first push, in
   those repos only; for already-pushed repos this includes the force-with-lease push the label
   named (see `sections/conflict.md` for a failing rebase).
4. **Execute independently per repo.** Read `sections/execution.md` for push, PR creation/reuse,
   the shared no-check guard, server auto-merge vs deterministic gated wait, accepted-head/base/open
   guards, timeout diagnostics and sync. Start all applicable waits without holding healthy repos
   behind slow ones. Retain each repo's accepted SHA and evidence basis through cleanup.
5. **Report.** One table `repo | PR | status | next`. Statuses: `merged`, `PR open`,
   `PR open: no checks`, `PR failed`, `merge not scheduled`, `PR closed`, `not merged`,
   `merged: ungated head`, `CI failed`,
   `conflict`, `timeout`, `push failed`, `sync failed`, `kept` (branch kept),
   `skipped: dirty|not forgejo|base mismatch|base not found|is base`.
   Map script statuses: sync `synced` -> `merged`; `kept` -> `merged (branch kept: <reason>)`;
   `sync failed` -> `merged, sync failed: <error>`; wait `failed` -> `wait failed: <error>`.
   Then the task step from `sections/task.md` per the answer; with no task, nothing more.

## Rules

- Repos are independent: a failure in one never stops the others.
- Errors are reported verbatim, never skipped or paraphrased away.
- Never force-merge, never reset, never push fixes or rewrite history without the user's explicit
  request/confirmation; never resolve conflicts silently.

## Sections

- `sections/task.md` - read for a Vikunja task (named/inferred) or multiline handoff arguments.
- `sections/execution.md` - read before executing approved shipping.
- `sections/wait-ci.md` - read for any CI/deploy wait, including standalone watch-only requests.
- `sections/ci-gate.md` - read for PR check reduction and gated merge safety.
- `sections/ci-failure.md` - read when any check source fails, including cancellation or external status.
- `sections/conflict.md` - read when a PR is not mergeable or an upfront "Rebase first" fails.
