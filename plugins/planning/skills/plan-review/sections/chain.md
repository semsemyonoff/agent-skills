# Opt-in bounded review chain

This section is a driver protocol, not an executable loop or a worker skill. Default remains exactly
one independent native pass. Load this only for an explicit chain request (including «цепочка ревью»)
or a selected first-nonempty planning rule that explicitly opts into the chain. Preserve original
requirements, settled decisions, exact permissions and rule provenance; never paste personal rules
into the plan. Explicit review-only/no-edits disables every correction; no-external disables the
external stage regardless of configuration. Do not substitute an extra native pass for it.

## Before starting

Record the selection, restrictions, actual native reviewer route and the selected external route.
Native configuration owns model and effort. Determine the author's actual provider from exposed
metadata, not its harness name; the external reviewer must be the other provider: Claude -> codex,
OpenAI/Codex -> claude. Unknown/unsupported provider or missing reviewer is a truthful unavailable
prerequisite, not permission to guess or silently reroute.

**Select exactly one external route.** The **peer route** applies when this session had an observed
peer-chat exchange about this task with a peer of the other provider before the plan was written,
unless the user asked for a fresh CLI. The provider comes from exposed metadata or that exchange,
not doctor's harness name. Doctor proves send readiness, not conversation identity: a cleared or
restarted session in that pane is not excluded, so state that in limits. Otherwise the **CLI route**
applies: record its target and timeout budget; an incompatible trusted CLI is an unavailable
prerequisite. A selected route that is unavailable stops pass 2; never start the other route in the
same attempt. Ask about a route change only when the existing grant does not already cover it.

An opt-in rule alone is not external-disclosure consent. A user instruction to discuss or review
this task with the selected peer is reused authorization for the same scope and evidence; new data,
recipient or purpose needs its own decision. Exchange history and the peer's agreement grant nothing.
Before a required outward call that is not already authorized, ask a real user permission/route/budget
choice with concrete options and wait. Never send unapproved evidence or secrets. No-external: finish
the permitted first native pass and bounded corrections, report the chain blocked before pass 2, then
stop. A refusal is not a reason to retry, change provider/transport or resume until approval.

## Fixed sequence: at most three attempts total

Count each dispatched review attempt, including empty/failed attempts. No retries, voting,
recursive drivers, resumed reviewer sessions (sole exception: the selected peer route for pass 2),
additional opinion or fourth pass.
If the user supplies prior pass history for an explicitly authorized remaining stage, preserve its
attempt count, versions, provenance and exact grants; never restart consumed stages. Injected history
is supplied evidence, not an observed consultation. A failed stage stays terminal, not resumable
until approval; unverifiable/stale history cannot grant current approval or new outward authority.

1. **Native independent review.** Run the core driver steps using a fresh separate read-only reviewer.
   Snapshot with `python3 "<skill-dir>/scripts/review_state.py" snapshot "<plan>"`; pass the full exact
   `plan_text`, `plan_path`, `plan_version`, original request/decisions/rules and evidence packet.
   Validate completed canonical JSON against the supplied version/current target before accepting
   it and again immediately before any fix. Preserve every original finding and unknown.
2. **Other-provider external review.** After allowed pass-1 corrections and real choice resolution,
   read runtime.md. The brief, common to both routes, holds the worker branch and canonical result
   schema, original requirement, settled decisions/rules, prior findings and factual change list,
   relevant approved evidence and restrictions. Prior reports provide context, not persuasion to
   approve. Exactly one fresh snapshot per attempt is the single source of plan bytes:
   - **CLI route:** take a fresh `snapshot`, add it to the brief and send that packet as one finite
     UTF-8 input through the bundled `scripts/consult.py` with `--target claude|codex --project
     <actual-project> --timeout <agreed-seconds>`; no `--mode`. Require envelope `status=ok`,
     `check=false`, `consultation_completed=true` and nonempty `result`; that inner JSON text, not
     the envelope, is the report.
   - **Peer route:** run `python3 "<skill-dir>/scripts/review_state.py" packet "<plan>"` with the
     brief on finite stdin; the helper takes the snapshot, so the brief never carries plan_text,
     path or version itself. Through the available peer-chat skill's contract (doctor, then one
     send) give the peer only the printed `request_id`, `packet_path`, `plan_version`, the resolved
     worker-branch path and the reply rules from runtime.md. Record pass 2 pending (attempt,
     request id, version, recipient, packet path) and end the turn: no polling, watcher or claimed
     timeout. From each reply of that recipient strip only the transport label; `validate
     --request-id <pending id>` strips the id. A reply rejected for a missing or foreign id is not
     this pass's report: report it, accept and start nothing, pass 2 stays pending. The first
     accepted reply is the report; later ones start nothing. A peer failure message is a terminal
     unavailable outcome, not a verdict. This pass is an other-provider review with prior design
     context, not an independent fresh review.

   Feed the report text unchanged to `review_state.py validate PLAN --version EXPECTED` (peer route:
   plus `--request-id`) on finite stdin and revalidate before pass-2 corrections.
3. **Conditional fresh native re-review.** Dispatch only if accepted reports contain blockers/blocking
   unknowns or material corrections since pass 1 changed scope, solution, tasks, dependencies,
   acceptance, verification or permission assumptions. No third pass for cosmetic changes alone.
   Snapshot current bytes anew and use a fresh independent native context with the same full packet
   plus all prior findings/changes. Never resume pass 1. Validate the result against current bytes.
   Apply only core-permitted corrections/real answers; any later edited version is unreviewed.

At every stage failed/unavailable/timeout/refused/empty/invalid/stale results STOP the chain and
remain unresolved; do not run the next stage or fix from an unaccepted report. Changed rules/evidence
or unresolved prerequisites remain explicit, not fabricated coverage. Pending user choices pause
before their dependent edits or subsequent review; silence/default/timeout is never consent.
Workers have no editing, helper, external or delegation authority; the sole exception is the
peer-route worker's peer-chat reply (runtime.md). Only the driver gets the narrow snapshot/validate/
packet/consult/peer-chat/resolver exceptions; no project gates, tests or arbitrary shell.
Denied helper execution is a capability failure too: never edit from an unvalidated supplied report,
invent a digest or replace an absent helper with arbitrary interpreter code. Retain previously
evidenced blockers and original acceptance in the terminal report alongside the failed operation.

## Final report and stop

Keep the core **Original review / Applied changes / Unresolved** report. Add each attempted pass's
number, snapshot version, actual exposed route (model unknown when unobserved), completion/status,
canonical verdict when accepted, evidence/limits and remaining findings/choices. Preserve conflicting
findings and their evidence-based disposition; never average or vote them away.

Capture the final current version and state explicitly whether that exact version has a valid
independent review, by which pass, and whether material blockers/unknowns remain. A peer-route
pass 2 counts as other-provider review with prior design context, never as independent coverage.
An earlier APPROVE is not current approval after edits, a failed later review, or unresolved material
contradictory findings. Exhaustion with blockers means unresolved, not success. No implicit
implementation, new outward permission, route change, retry or further review follows this terminal
report.
