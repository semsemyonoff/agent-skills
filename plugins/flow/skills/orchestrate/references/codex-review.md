# Optional Codex CLI second opinion

This is an explicitly selected read-only opinion, not an automatic requirement or a reason to
launch another native reviewer. A Codex model inside omp uses omp's task tools, not this CLI merely
because it is installed. The CLI's native configuration decides its model/provider; it is not
necessarily another vendor. Apply `review.md` to selected scope, independence and findings.

Resolve `scripts/codex_review.py` from the directory of the loaded `SKILL.md`; below, `SKILL_ROOT`
is that resolved directory, not a required environment variable. Use the running adapter's real
shell/background tools. The Claude-only adapter may substitute its skill-directory variable.

## Availability and approval

In Claude Code, when this route is relevant/requested and not already declined, check locally:

```sh
python3 "$SKILL_ROOT/scripts/codex_review.py" check
```

- `available` / exit 0: CLI found and the user's configured guard allowed it; authentication/model
  availability are not proved by this local check.
- `unavailable: skip: ...`: CLI absent or `CODEX_REVIEW=off`; say so once and omit the offer.
- `unavailable: guard: ...`: quote the refusal and omit the offer. Do not bypass the guard or
  modify settings. If this review was explicitly required, either absence is a blocker until the
  user changes that requirement; do not silently finish without it.

`CODEX_REVIEW`, `CODEX_REVIEW_GUARD`, `CODEX_MODEL`, and `CODEX_REASONING_EFFORT` are user environment
choices, not skill settings. The guard is a user-supplied shell command; do not manufacture one.
In omp do not automatically run this check/guard or offer/execute a CLI call as native review.

When offering this route, combine its choice with existing confirmation: "Additional review via
Codex CLI / No additional review" («Дополнительное ревью через Codex CLI / Без дополнительного ревью»).
Reuse an explicit earlier yes/no; no mandatory offer or duplicate question. Start grants no call.
Record permission for one external model call on the final stable scope and its observed/permitted
route. Do not guess model/effort. Offer `--xhigh` only if that effort is known supported by the
configured route and the user explicitly chooses it. Record the start commit and pre-existing
`git status --short` at approval so unrelated edits are not attributed to this run. Keep an actual
changed-file/artifact inventory for accurate findings.

## Run on the stable final tree

After implementation, applicable checks and any separately selected independent review, write the
approved intent to a temporary file, then use the adapter's actual background mechanism if available:

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

Assess findings against the original acceptance and actual scope. Accept a scoped fix through the
implementation owner followed by applicable self-checks and independent re-verification only within
the selected review mode; reject with reasons. Another CLI round needs new permission. Report actual
route, outcome, findings and later unreviewed changes; failures never become clean reviews.

## Official sources

- [Codex CLI reference](https://developers.openai.com/codex/cli/reference/) documents noninteractive
  execution and invocation overrides.
- [Official exec argument definitions](https://github.com/openai/codex/blob/main/codex-rs/exec/src/cli.rs)
  document ephemeral runs, last-message output, and that `--ignore-rules` disables user/project policy
  files; this helper deliberately does not use it.
