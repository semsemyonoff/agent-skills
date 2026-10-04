# Worker brief

Assume no conversation history unless the actual harness proves otherwise. Put everything needed
in a self-contained brief. The coordinator owns the complete plan even if the native worker is
allowed to delegate. Write in English or the user's language as appropriate for the surrounding code.

## Template

```text
Goal: <what must be true when done>
Capability + requested native profile: <required tools/authority; discovered permitted profile>
Complexity and reason: <remaining decisions, known pattern/API/paths, coupling, failure cost>
Configured/requested model + reasoning: <accessible effective pair/source, or unknown; not actual>
Routing allowance: <approved profile(s), escalation conditions/budget; no silent default fallback>

Context:
- <workspace, exact files/entry points, input artifact paths and relevant source locations>
- <approved approach, contracts, constraints, versions, decisions already settled>
- <pre-existing edits to preserve and facts already learned>

Change/questions:
- <specific edits, APIs, cases, or research/review questions>
- <mechanical example when appropriate; review candidate diff and original acceptance criteria>

Boundaries:
- May touch: <exact file ownership; read-only for research/review>
- Do not touch: <other owners' files, unrelated edits, external systems/configuration>
- LSP only when already authorized and actually available. Review uses navigation/diagnostics only:
  no mutating code actions, rename, formatting or LSP edits. Do not install servers or change settings.
- Skip shared gates, model evals, smoke runs, and formatters during concurrent implementation.
  Verification owner: <coordinator or independent assigned checker>; commands: <central checks>.
- No commits, push, installs, destructive deletion, tracker/forge writes, external messages,
  model/settings mutations, or unapproved second-opinion calls.
- Nested delegation: <forbidden for this slice, or actual permitted capabilities and bounded scope>.
  Never assume nesting is available; preserve these permissions in any child brief.

Acceptance: <observable consumer behavior/boundaries, not just files present or tests written>

Return compactly:
- Findings/changes with exact paths and source locations.
- Evidence actually observed; commands suggested but not run must be identified as such.
- Uncertainties, changed complexity/risk, missing capabilities and precise blockers.
- Requested/configured pair versus exposed actual model/reasoning; never infer actual from a profile.
```

For bounded address/configuration replacements, specify the real runtime entrypoints and consumers
(including fallback entrypoints), plus default/fallback/environment-override precedence, not merely
literal strings or a file list. Ground that contract in source locations; keep the assigned ownership
and permissions unchanged. Before marking done, use available reads to check the full agreed contract
and report missing evidence as a gap, not success. These reads do not replace the verification owner's
runtime checks or authorize worker shared gates; do not add source-text/incidental tests for them.

On failure, sharpen the brief or isolate the hard part with evidence and an observable acceptance
result before reassessing the route. A worker whose uncertainty/risk no longer fits the approved
profile reports the gap; it does not widen permissions or switch models/settings. Use stronger
profiles only within the authorized policy/plan, otherwise ask. Independent review uses a separate
worker; choose its profile by review risk rather than always inheriting the author's or highest pair.

## Example

```text
Goal: Upload bodies over the approved 10 MiB limit get HTTP 413; smaller bodies still upload.
Capability: implementation; requested profile: the discovered permitted strong editor.
Complexity: high failure cost at an untrusted-input/public boundary; stream ownership must be preserved.
Configured/requested pair: effective native strong profile; exact values only from available config.
Routing allowance: this profile only; sharpen/split before any explicitly authorized stronger route.
Context: internal/http/upload.go handler; internal/config/config.go follows existing timeout pattern.
Change: use the service's current body-limit pattern and error helper; cover exact-limit and over-limit.
May touch: internal/http/upload.go, internal/http/upload_test.go, internal/config/config.go.
Do not change other handlers, dependencies, native routing, or pre-existing unrelated edits.
Skip checks/formatters mid-flight; coordinator will run project gates and exercise upload requests.
No external writes/commits/push/installs; no nested delegation for this slice.
Acceptance: 10 MiB succeeds; 10 MiB + 1 byte receives 413 without storing the oversized body.
Return: changed paths, unchecked assumptions, suggested central scenario commands.
```
