# Plan and report templates

Use the user's language. Keep headings and descriptions short; show actionable decisions, not
worker transcripts. Native route identity is required; model/effort is optional observational data.
Do not fill unknown values from customary defaults or the name of a work category.

## Plan

State the settled approach, then:

```text
| # | Step/category | Native worker | Model/effort (observed) | Input | Done when | Depends on |
| - | ------------- | ------------- | ----------------------- | ----- | --------- | ---------- |
| 1 | Research call sites | <discovered read-only agent> | unknown | repo | locations + invariant summary | parallel with 2 |
| 2 | Research existing parser | <discovered read-only agent> | unknown | parser path | edge cases established | parallel with 1 |
| 3 | Implement agreed change | <native implementation agent> | unknown | 1, 2 | required cases handled | 1, 2 |
| 4 | Independent review | <different reviewer identity> | unknown | change + acceptance criteria | actionable findings with disposition | 3 |
| 5 | Checks + scenario | coordinator | session route if exposed | stable tree | observed gate and changed-path results | 4 |
```

Add precise file ownership/shared contracts and phase verification owner. Name permitted escalation
routes only if configured or user-approved. Mark missing capabilities before approval; a reviewer
cannot be invented. State what local work is approved, which exact external/irreversible actions
still need permission, and any optional second-opinion route/checkpoint the user may choose.

Confirmation options: "Start / Start phase by phase / Change the plan"
(«Начать / Начать по фазам / Изменить план»). Use the actual ask tool; if absent, ask in text and
wait. A previously explicit approval of this exact plan is enough. Autonomous execution is the
default after approval, not permission for scope/routing changes or external writes.

## Final report

```text
<2-5 lines: changed behavior and actual outcome>

| # | Category/native worker | Observed route | Result | Deviations/retries |
| - | ---------------------- | -------------- | ------ | ------------------ |
| 1 | ... | unknown if not exposed | ... | ... |

Verification: <commands/scenarios actually exercised and results, separate from worker claims>
Independent review: <reviewer identity; findings accepted/rejected and reasons, or exact blocker>
Second opinion: <only if chosen; result/failure and disposition; do not imply different vendor>
Deviations: <scope/routes/permissions changed, or none>
Not verified: <missing runtime/capability and why, or none>
Blocked/remaining: <exact unresolved acceptance or action awaiting permission, or none>
```

Do not label unfinished work done or report a failed/empty review as "no findings". Distinguish local
self-checks from independent review and suggested commands from commands actually run. An unknown
model is honest evidence, not a gap to fill with a guess. Do not repeat the process story.
