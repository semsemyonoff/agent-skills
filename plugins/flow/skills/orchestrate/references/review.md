# Selected independent review

Read when recommending, selecting, running or resolving a review. Default is executor checks with
no separate reviewer. Review is opt-in unless higher-priority instructions require it. Preserve
explicit independent acceptance and external-system fact-check rules; this code-review default
does not weaken them.

## Choice and scope

For material risk, briefly explain the at-risk invariant and recommend the minimum sufficient
review profile using `routing.md`. A recommendation is not permission to dispatch. Combine the
choice with an existing approval question when useful; do not ask every small task an extra review
question. Honor an existing explicit choice, including no review or no extra opinion.

Record the user's actual choice, reviewed scope and checkpoint. Silence, automatic defaults,
timeout, dismissal or Start without a review choice authorizes no review call. A higher-priority
requirement is recorded with its source, not falsely attributed to the user. Changing a selected
mode needs a user decision and cannot override such a requirement.

A selected unavailable reviewer remains an explicit acceptance gap. Report reachable work and
checks, then request a permitted route or decision; never replace it with self-review or silently
install/enable a profile. An unavailable reviewer that was not selected blocks nothing.

## Independent result

Use a different worker instance from the implementer, with a risk-appropriate permitted pair and
a self-contained brief (`brief.md`). One reviewer may cover compatible scopes and run checks.
Independence is ownership separation, not highest reasoning or a different vendor. Confirm tools
before delegating browser work; shell permission alone proves no browser capability or sandbox.

Freeze the reviewed scope while the reviewer runs; queue even small edits until it returns. Supply
goal, acceptance, changed scope/version, pre-existing edits, observed checks and exact permissions.
A baseline revision plus the described local changes is enough; do not require hashes of every
artifact. Demand source locations, failure scenarios, severity and evidence, not a token APPROVE.

Assess findings yourself. Accept in-scope fixes or reject with reasons. Batch accepted fixes, then
run applicable self-checks. Behavioral/security/contract changes need independent re-verification
within the selected review mode; do not silently drop that mode after the first verdict. Obvious
nonbehavioral tails may be checked locally against changes/links and existing evidence; disclose
that they postdate the review. An earlier APPROVE never covers unseen changes.

If review fails, is empty or unavailable, record that outcome; it is not "no findings" or PASS.
Report executor checks separately from selected review and remaining acceptance gaps. Review
output informs coordinator acceptance rather than automatically granting it.

## Optional extra opinion

An extra opinion is never mandatory and does not secretly enable a native reviewer. When wanted,
discover the adapter's route: existing Codex CLI in Claude Code, `second-opinion` in omp. Do not
substitute a vendor/CLI/profile. Offer it only when relevant or requested, separately from Start;
record exact permission for one read-only call over the final scope. Do not repeat a declined offer.
An unavailable explicitly requested route is a blocker until the user changes the requirement.

Default checkpoint: stable final result after applicable checks and any separately selected review.
Use a new instance distinct from implementer and any selected reviewer. The adapter describes the
actual invocation; only Claude's CLI route needs `codex-review.md`. Do not run a probe model call.

Assess each finding. Accepted behavioral fixes return through implementation, self-checks and any
selected independent re-verification. A second extra-opinion round needs new permission. Report
its actual outcome and later changes it did not review. A failed/empty call is a failed call, not a
completed clean review. After an observed supplemental failure, the user may waive that exact extra
requirement; record both failure and waiver, never PASS. This waives no separately selected review
or higher-priority requirement. A standalone selected extra opinion requires no hidden other pass.
