---
name: ship
description: 'Bring an implemented plan branch or the branch of a Vikunja task to the base branch (main, or a named integration branch) in every repo of a workspace on Forgejo - push, open PR, merge once CI is green, sync the base locally, delete branches, report per repo, then optionally report into the task and close it. Use after a plan or task was implemented (e.g. by ralphex) and the code sits in a branch. Triggers - /ship:ship, /skill:ship, "ship the plan branch", "merge the plan branch into main in all repos", "ship X into release-branch", "open PRs and merge when green", "land this branch", "ship task 587", «доведи ветку до main», «смержи план во всех репо», «открой PR и смержи после CI», «зашипь ветку», «влей ветку в общую ветку», «зашипь задачу 587», «доведи задачу 587 до main». Not for - just creating a PR without merging, reviewing a PR, reporting or closing a task without shipping, GitHub/GitLab repos, deploys.'
argument-hint: "[branch | task] [into <base>]"
---

# Ship

Take a finished plan branch to the base branch in every repo of the workspace that has it:
push -> PR -> merge when CI is green -> sync base locally -> delete branches -> report -> task.
The entry is a branch or a Vikunja task (its `<id>-<slug>` branch), optionally with multiline handoff
fields; read `sections/task.md` before preflight for a task or handoff, including comment discovery.
Base: the branch the user names as the target ("into X", «в X», «общая ветка X»), else each repo's
default branch. A named target that is not an existing remote branch is a question, not a guess.
Forgejo only, driven through the Forgejo MCP. Reply in the user's language. PR titles/bodies use the
language of the plan/commits (default: short English title from the branch/commits, body summarises
the commits). No personal data in PR bodies.

Do not assume an install location or an environment variable for the script.
Invoking the skill already means the user wants the branch pushed: never ask about pushing.

## Helper

Run it by the absolute path of this skill's directory (resolved from the loaded `SKILL.md`) with the
shell cwd set to the user's workspace (or pass `--root`); from any other cwd root/branch detection breaks.

`python3 <skill_dir>/scripts/ship.py <plan|push|wait|sync> [--root DIR] [--branch NAME | --task ID] [--repos PATH...]`

`--base NAME` (all subcommands): the named target; must exist as `origin/NAME`, never replaced by
the default. Retain `root` and `branch` from `plan`; pass `--root <root> --branch <branch>` (and
`--base` when named) explicitly to every later helper call, including retries. `sync` switches the
current branch, so do not re-detect it.

- JSON to stdout, diagnostics to stderr. Exit 0 = ran (per-repo statuses in JSON); exit 2 =
  usage/environment error (no git, root not found, branch undeterminable, branch is main/master/base).
  Network git calls have timeouts and run with `GIT_TERMINAL_PROMPT=0`.
- Root: `--root`, else nearest `workspace.yml` upward, else git toplevel. Branch: `--branch` (or the
  skill argument), else the single `<id>-...` branch for `--task`, else current branch of the cwd repo. Discovery keeps repos that have the local
  branch.
- `plan` (read-only, no fetch): `{root, branch, task (`--task`, else `<id>` of an `<id>-...` branch,
  else null), repos:[{path, remote_url (userinfo redacted), host
  (ssh-config-resolved hostname; `host_alias` when the remote used an alias), owner, repo, base,
  is_base, has_ci, dirty, ahead, behind, pushed, remote_branch (origin/<branch> exists locally),
  head_sha, current_branch}]}`.
  `base` is `--base` if `origin/<base>` exists, else origin/HEAD -> origin/main -> origin/master; it
  may be null. `ahead`/`behind` are against `origin/<base>`. `has_ci` = a workflows dir
  (.forgejo/.gitea/.github) exists on the branch tree - only a hint: workflows may not run on PRs.
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
- `get_commit_statuses(owner, repo, sha)` (40-hex sha); `list_workflow_runs(owner, repo, head_sha)`
  -> one aggregate status per Actions run (covers jobs that have no commit status yet, e.g. a matrix
  expanded later); `list_action_run_jobs`, `get_action_job_logs` for failures
  (see `sections/ci-failure.md`).

If the Forgejo MCP tools are absent, report the missing connection and stop before any write. Do not
substitute gh/glab/fj/REST and do not change MCP configuration.

## Workflow

1. **Preflight.** Resolve handoff candidates through `sections/task.md`, then run `ship.py plan`.
   Exit 2 -> report the error and stop, except its narrowly defined multiple-task-branches recovery.
   If plan first discovers an inferred task, read that section now and replan with any candidate base
   before Forge facts. No repos with the branch
   -> say so and stop. Any environment failure stops before a write.
2. **Forge facts (read-only).** Per repo: `get_repo` (merge style; a style named in the request
   overrides it). Forge identity: compare plan `host` (resolved) with the hosts of `html_url`, `ssh_url`
   and `clone_url`; owner/repo null or no host matches -> `skipped: not forgejo`. Base: the named
   target, else `default_branch`. Named target: plan `base` null or not in `list_branches` ->
   `skipped: base not found`. Default: plan `base` null or different from `default_branch` ->
   `skipped: base mismatch` (hint `git remote set-head origin -a`). `is_base` -> `skipped: is base`.
   Find the existing open PR whose `head.ref` is the branch AND `base.ref` is the base.
   **Merge mode** from the base's `list_branches` entry:
   - `auto-merge`: `enable_status_check` true with non-empty `status_check_contexts`. The server
     enforces those checks; schedule the merge and `wait`.
   - `gated`: anything else. Forgejo's auto-merge then fires on the first green status while other
     jobs still run (seen live), so ship gates CI itself before a plain merge.
   No CI = plan `has_ci` false; a hint for the confirmation only, the PR's checks decide.
3. **Confirm once.** Show an action table: `repo | base | push? | PR new/#N | merge style | mode |
   then`. Then ONE
   structured-choice call: Claude Code `AskUserQuestion`; omp `ask`; native Codex's ask tool only if
   available for confirmations. Without a suitable ask tool, ask the same questions together in plain
   text, end the turn and wait for explicit answers (silence/dismissal is not approval). Respect the limits
   (<=4 questions, 2-4 options each): one question per category listing the affected repos, never
   per repo. Only needed questions:
   - Always: "Merge into <base>?" - "Start (Recommended)" / "PRs only, no merge" / "Stop"
     («Начать (рекомендуется)» / «Только PR, без мержа» / «Стоп»).
     When the base came from task handoff, both table and question identify its source:
     "Merge into X (from #<id>)?" / «Merge into X (из #<id>)». Inline handoff says "from argument".
   - Dirty repos: "Skip (Recommended)" / "Stop everything".
   - `behind > 0`: "Merge as is (Recommended)" / "Rebase first". For repos whose branch is already on
     the remote (plan `remote_branch` true) the label is "Rebase first (force-with-lease
     push)"; plain "Rebase first" when it is false. Split into two options if both kinds occur.
   - Repos without CI (plan `has_ci` false, listed by name): "Merge (Recommended)" / "PR only".
   - Existing open PR with another base: "Skip" / "Create new PR".
   - A task (plan `task` or a named one): the task question from `sections/task.md`.
   Over 4 questions: fold no-CI into the main question ("Start; PR only for repos without CI"),
   then dirty ("...; skip dirty repos"); the main question keeps three options, and a folded policy
   applies to every option that proceeds, "PRs only" included. After the answer run to the end
   without questions.
   "Rebase first" is part of this approval: rebase onto `origin/<base>` BEFORE the first push, in
   those repos only; for already-pushed repos this includes the force-with-lease push the label
   named (see `sections/conflict.md` for a failing rebase).
4. **Execute** (repos independently).
   1. `ship.py push --repos ...` for non-skipped repos. `failed` -> `push failed`, error verbatim.
   2. Create the PR (`create_pull_request`; error -> `PR failed`, verbatim) or reuse the existing one.
      With a valid handoff, append verification only to a new PR (`sections/task.md`); for a reused
      PR report that verification was not added to existing PR #N, without updating its body.
      From here on use the PR's `head.sha` (`get_pull_request_by_index`), never plan `head_sha`: it
      goes stale after an upfront rebase or a CI-fix push.
      Keep lightweight per-repo run state: target base, candidate head, and `accepted_head` with
      `evidence_basis` (`CI passed` or `explicit no-CI permission`). Acceptance is tied to a SHA,
      not a branch name; discard it on a head change. Never call no-CI permission a CI pass.
   3. "PRs only" (or PR-only repos): no merge, no `wait`/`sync`; status `PR open`.
   4. Checks guard, every repo (external CI posts statuses without a workflows dir):
      `get_commit_statuses` and `list_workflow_runs` on the PR `head.sha`; if both are empty,
      re-check a couple of times with a short sleep (<= ~1 min total; Forgejo creates the run and
      "Waiting to run" statuses when the run is queued). Still both empty -> no checks on this
      PR, and an auto-merge would never fire. In `gated` mode only, a repo explicitly approved in
      the no-CI question may snapshot this checked SHA as `accepted_head` with evidence basis
      `explicit no-CI permission`; proceed to step 5's shared pre-merge guard, without merging yet.
      In `auto-merge` mode instead: `not merged: required checks never reported`, even with no-CI
      permission. Any other repo -> `PR open: no checks`, no merge call: an empty minute does not
      prove there is no CI, so merging it is the user's call afterwards.
   5. Merge. Before every merge call and retry re-read the PR: it must be open with `base.ref` equal
      to the base (retargeted -> `not merged: base changed`, no write). Gated/no-CI head changed ->
      clear acceptance and restart the checks guard/gate on the new SHA before merging. On a merge error re-read
      `get_pull_request_by_index`: `mergeable=false` -> `conflict`; a transient "mergeability still
      being checked" (405/try again later; unverified) -> retry once after a short sleep; else
      `merge not scheduled` with the error.
      With valid `explicit no-CI permission` acceptance, plain merge once using
      `merge_when_checks_succeed=false`; on success go directly to step 7, skipping both mode
      branches below and `wait`. Never run the CI gate or merge again for that completed merge.
      a. `auto-merge`: snapshot the re-read PR head as the candidate immediately before scheduling
         `merge_pull_request` with `merge_when_checks_succeed=true`, then `ship.py wait --repos
         <auto-merge repos>` using the harness's wait mechanism or foreground `--timeout` described
         above. When the PR confirms merged on that same candidate, record `accepted_head` and
         `CI passed` (server-enforced required checks). A changed head is not accepted by this run.
      b. `gated`: run the CI gate from `sections/ci-gate.md` on the PR `head.sha`, all gated repos
         per round; it ends in a plain merge, `CI failed`, `timeout` or `merged: ungated head`. Sync
         each repo as soon as it merges; do not hold it for slower ones.
   6. `wait` `pending` (auto-merge): re-read the PR, then collect both paged check sources for its
      current head using `sections/ci-gate.md` source reduction. Any failing run or status ->
      `CI failed`; pass its actual source/state/context to `sections/ci-failure.md`. Still running ->
      `timeout`, offer ONE more wait. All success but not
      merged (approvals required, auto-merge cancelled) -> `not merged` with the reason from the PR;
      no endless re-wait offer. `mergeable=false` -> `conflict` (`sections/conflict.md`).
   7. Before sync, per repo: `get_pull_request_by_index` must show `merged: true`, `base.ref` equal
      to the retained target and `head.sha` equal to `accepted_head`, with its evidence basis
      retained; then `ship.py sync --repos <confirmed only> --confirmed-merged
      --head <path>=<accepted_head> ...` (plus `--base`). Closed unmerged -> `PR closed`, no sync.
      A merged head mismatch or missing acceptance -> `merged: ungated head <sha>`, no sync or
      cleanup; a base mismatch -> `not merged: base changed`, no sync or cleanup. The helper's
      branch-deletion check is additional safety, not a substitute for this PR check.
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
- `sections/ci-gate.md` - read when a repo is in `gated` mode.
- `sections/ci-failure.md` - read when any check source fails, including cancellation or external status.
- `sections/conflict.md` - read when a PR is not mergeable or an upfront "Rebase first" fails.
