# Optional Codex CLI second opinion

This is an extra, explicitly chosen read-only review at the approved checkpoint, not the required
native independent reviewer. A Codex model inside omp still uses omp's task tools; do not launch the
CLI merely because it is installed or because the session model comes from OpenAI. The CLI's native
configuration decides its model/provider, so this is not necessarily another vendor's model.

Resolve `scripts/codex_review.py` from the directory of the loaded `SKILL.md`; below, `SKILL_ROOT`
is that resolved directory, not a required environment variable. Use the running adapter's real
shell/background tools. The Claude-only adapter may substitute its skill-directory variable.

## Availability and approval

When the user is interested in this route (or the Claude adapter offers the optional route), check:

```sh
python3 "$SKILL_ROOT/scripts/codex_review.py" check
```

- `available` / exit 0: CLI found and the user's configured guard allowed it; authentication/model
  availability are not proved by this local check.
- `unavailable: skip: ...`: CLI absent or `CODEX_REVIEW=off`; omit an unsolicited offer, or explain
  unavailability if the user requested it.
- `unavailable: guard: ...`: quote the refusal. Do not bypass the guard or modify settings.

`CODEX_REVIEW`, `CODEX_REVIEW_GUARD`, `CODEX_MODEL`, and `CODEX_REASONING_EFFORT` are user environment
choices, not skill settings. The guard is a user-supplied shell command; do not manufacture one.
In omp do not automatically run this check/guard or offer/execute a CLI call as native review.

Ask "Codex CLI second opinion at the end? / No"
(«Дополнительное ревью через Codex CLI в конце? / Нет»). Record explicit permission for the external
model call and its observed/permitted route. Do not guess model/effort. Offer `--xhigh` only if that
effort is known supported by the configured route and the user explicitly chooses it.
Record the start commit and pre-existing `git status --short` at approval so unrelated edits are
not attributed to this run. Keep an actual changed-file/artifact inventory for accurate findings.

## Run on the stable final tree

After all implementation and required independent review/checks finish, write the approved intent
to a local temporary file, then run through the adapter's actual background mechanism if available:

```sh
python3 "$SKILL_ROOT/scripts/codex_review.py" run \
  --repo "$REPO" --start "$START_SHA" --intent-file "$INTENT_FILE"
```

Add `--dirty-at-start "$STATUS_AT_START"` if needed; add `--xhigh` only as separately approved above.
`--timeout MINUTES` defaults to 15. The helper re-checks availability and calls `codex exec` with
`--sandbox read-only`, invocation-local `approval_policy="never"`, `--ephemeral`, and closed stdin.
It does not disable the user's execpolicy rules or write model settings. The prompt covers commits
since the recorded start plus staged/unstaged/untracked changes and identifies pre-existing edits.
Review findings touching pre-existing work require scope attribution, not automatic fixes.

Model and effort inherit native Codex configuration unless the user sets the documented environment
overrides; `--xhigh` supplies the explicitly approved invocation override. No retries on another
model/provider or weaker sandbox if rejected. If the CLI reports an unexpected native model switch,
disclose and treat it as a routing deviation rather than accepting review as approved-route evidence.
The helper cannot prevent a provider's internal routing; read its logs/notices and report any
unobserved model/effort as unknown. Do not promise a model identity based on configuration alone.

## Results

The helper prints an artifacts directory with `review.md`, `stdout.log`, `stderr.log`, `exit-code`,
and `error.txt` on failure. Use background completion notification/wait according to the actual
adapter; do not poll while other work remains. Read the artifacts after completion.

- Exit 0 and non-empty `review.md`: review completed; it can legitimately have zero findings.
- 124: timeout; the process group was terminated.
- 2: invalid repository/start commit.
- Any other nonzero status or an empty final message: failed review, never "no findings".

Assess every finding against the approved acceptance criteria and actual run scope. Accept by
routing a scoped fix through an implementation worker followed by independent review/checks;
reject with a concrete reason. Do not start a second CLI round without user approval. Report route
if observed, accepted/rejected findings, and any timeout/failure/unverified scope truthfully.

## Official sources

- [Codex CLI reference](https://developers.openai.com/codex/cli/reference/) documents noninteractive
  execution and invocation overrides.
- [Official exec argument definitions](https://github.com/openai/codex/blob/main/codex-rs/exec/src/cli.rs)
  document ephemeral runs, last-message output, and that `--ignore-rules` disables user/project policy
  files; this helper deliberately does not use it.
