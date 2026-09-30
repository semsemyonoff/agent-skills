# Optional Codex review

An independent second opinion from another vendor's model on everything the run changed, after the
orchestrator's own verification and before the report. Offered only when available and allowed, run
only when the user picks it. All mechanics live in `scripts/codex_review.py`.

## Availability (during recon, silently)

```sh
python3 "${CLAUDE_SKILL_DIR}/scripts/codex_review.py" check
```

- `available` (exit 0) — offer the step.
- `unavailable: skip: ...` — no Codex CLI or `CODEX_REVIEW=off`: do not mention the step at all.
- `unavailable: guard: ...` — the user's `CODEX_REVIEW_GUARD` refused: say in one line that Codex
  review is unavailable here and quote the reason.

`CODEX_REVIEW`, `CODEX_REVIEW_GUARD`, `CODEX_MODEL`, `CODEX_REASONING_EFFORT` come from the user's
environment, not from this skill.

## Asking

Second question in the plan confirmation call: "Codex review at the end?" — "Yes" /
"Yes, xhigh reasoning" / "No". At that moment record the start commit (`git rev-parse HEAD`) and,
if non-empty, `git status --short` (changes that existed before the run).

## Running

After all steps passed your verification and no worker is still running (the review must see the
final tree), write a one-paragraph summary of the confirmed plan to a temp file and run in the
background (Bash `run_in_background`):

```sh
python3 "${CLAUDE_SKILL_DIR}/scripts/codex_review.py" run \
  --repo "$REPO" --start "$START_SHA" --intent-file "$INTENT_FILE" \
  [--dirty-at-start "$STATUS_AT_START"] [--xhigh]
```

The script re-checks availability, then runs `codex exec` with `--sandbox read-only`,
`approval_policy="never"`, `--ignore-rules`, `--ephemeral`, stdin from `/dev/null`, and a prompt
that scopes the review to commits since the start commit plus staged, unstaged and untracked changes.
Model and effort come from Codex's config unless `CODEX_MODEL` / `CODEX_REASONING_EFFORT` are set;
`--xhigh` forces `model_reasoning_effort="xhigh"`. After `--timeout` minutes (default 15) it
terminates the whole process group, SIGKILL included.

It prints the artifacts directory: `review.md` (final message), `stdout.log`, `stderr.log`,
`exit-code` (the script's final status) and, on failure, `error.txt` with the reason. Wait for the
completion notice, then read `review.md`.

- Exit 0 with a non-empty `review.md` — the review ran; findings may be zero.
- 124 — timed out; 2 — bad repo or start commit; any other nonzero or an empty `review.md` — the
  review failed. A failed review is reported as failed, never as "no findings".
- Do not substitute settings silently: if Codex rejects the model or effort, report the error from
  `stderr.log`.
- Never run Codex with a write-capable sandbox or bypass flags from this skill; preset
  `codex review --uncommitted|--base|--commit` is not used because it cannot take the intent prompt.

## Findings

Treat them like an opus review: input, not a verdict. For each finding decide yourself:

- **accept** — fix through a worker (same brief rules and verification), then re-run your checks;
- **reject** — with a one-line reason (wrong, out of scope, already handled, pre-existing change).

No second Codex round unless the user asks. In the report add a block: "Codex: N findings — accepted
K (what was fixed), rejected M (why)", or that the review failed / timed out and why.
