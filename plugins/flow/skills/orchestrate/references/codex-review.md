# Optional Codex review

An independent second opinion from another vendor's model on the whole change set, after the
orchestrator's own verification and before the report. Optional: offered only when available and
allowed, run only when the user picks it.

## Availability (check during recon, silently)

Offer the step only if all hold:

```sh
command -v codex >/dev/null                                   # Codex CLI installed
[ "${CODEX_REVIEW:-}" != "off" ]                              # not disabled for this environment
[ -z "${CODEX_REVIEW_GUARD:-}" ] || sh -c "$CODEX_REVIEW_GUARD"   # user-defined guard passes
```

`CODEX_REVIEW` and `CODEX_REVIEW_GUARD` are set by the user's environment (e.g. per Claude profile),
not by this skill. If the CLI is missing or `CODEX_REVIEW=off`, do not mention the step. If only the
guard fails, mention in one line that Codex review is unavailable here and why (the guard's output).

## Asking

Add a second question to the plan confirmation (same AskUserQuestion call):
"Codex review at the end?" — "Yes" / "Yes, xhigh reasoning" / "No". Record `git rev-parse HEAD` at
that moment as the start ref.

## Running

After all steps passed your verification:

```sh
codex review --uncommitted \
  ${CODEX_MODEL:+-c model="$CODEX_MODEL"} \
  ${EFFORT:+-c model_reasoning_effort="$EFFORT"} \
  "Review these changes for correctness, regressions and missed edge cases. Intent: <one-paragraph summary of the confirmed plan>" \
  < /dev/null
```

- `EFFORT` = `xhigh` if the user picked it, else `$CODEX_REASONING_EFFORT` if set, else omit — the
  model and effort then come from the user's Codex config. Never hardcode a model.
- If the working tree was already dirty at the start ref, say so: `--uncommitted` includes those
  changes too.
- If the run produced commits, review them with `--base <start ref>` instead of `--uncommitted`
  (if the CLI rejects a SHA there, review each commit with `--commit <sha>`).
- Always end with `< /dev/null`: Codex otherwise waits for stdin when run in the background.
- Run it in the background (Bash `run_in_background`) and wait for the completion notice; it takes
  several minutes. Give up after ~15 minutes and say so in the report.
- `codex review` is read-only. Never run Codex with a write-capable sandbox from this skill.

## Findings

Treat them like an opus review: input, not a verdict. For each finding decide yourself:

- **accept** — fix through a worker (same brief rules and verification), then re-run your checks;
- **reject** — with a one-line reason (wrong, out of scope, already handled).

No second Codex round unless the user asks. In the report add a block: "Codex: N findings — accepted
K (what was fixed), rejected M (why)". If Codex failed or timed out, report that as is.
