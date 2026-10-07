# Worker brief

Supply a self-contained brief; do not assume conversation history. Workers read their slice's source;
the coordinator supplies acceptance, contracts and seams, and retains plan ownership. Use English or
the user's language as appropriate.

## Template

```text
Goal: <what must be true when done>
Capability + requested native profile: <required tools/authority; discovered permitted profile>
Complexity and reason: <remaining decisions, known pattern/API/paths, coupling, failure cost>
Configured/requested model + reasoning: <accessible effective pair/source, or unknown; not actual>
Routing allowance: <approved profile(s), escalation conditions/budget; no silent default fallback>

Context:
- Skills to load: <slice's language/domain skills; workers read them for their own work>.
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
- Compact facts/findings/changes with paths and source locations; no source dumps.
- Checks: tree version/state (including dirty changes), scenario/environment, command + exit code
  (or browser tool + returned status),
  full log/screenshot paths and unverified items. Distinguish suggested checks from observed results.
- Uncertainties, changed complexity/risk, missing capabilities and precise blockers.
- Requested/configured pair versus exposed actual model/reasoning; never infer actual from a profile.
```

For bounded address/configuration replacements, specify the real runtime entrypoints and consumers
(including fallback entrypoints), plus default/fallback/environment-override precedence, not merely
literal strings or a file list. Ground that contract in source locations; keep the assigned ownership
and permissions unchanged. Before marking done, use available reads to check the full agreed contract
and report missing evidence as a gap, not success. These reads do not replace the verification owner's
runtime checks or authorize worker shared gates; do not add source-text/incidental tests for them.

A small fix in familiar scope may reuse its worker. Consider a fresh worker for a changed task,
large exposed context or repeated failure. Around 150k is an experimental guide, not a hard limit;
weigh progress, remaining work and new-brief cost. After failure, diagnose anew or sharpen the brief
before retry/replacement. Follow SKILL.md's stop -> inventory -> replace order. Changed risk or
missing capabilities must be reported; no worker may widen permissions or switch routes/settings.

## Example

```text
Goal: Enforce the approved 10 MiB upload limit.
Capability/complexity: implementation; high failure cost at an untrusted boundary; preserve stream ownership.
Route: discovered permitted strong editor; record effective configured pair, not guessed actual identity.
Context/ownership: internal/http/upload.go, internal/http/upload_test.go, internal/config/config.go;
use existing body-limit/error/config patterns. Preserve unrelated edits; no other files.
Change: enforce the limit using existing body-limit/error handling.
Boundaries: no gates/formatters mid-flight, nested delegation, external writes, commits/push,
installs, destructive cleanup or routing/settings changes. Report gaps before escalation.
Verification owner: assigned checker or coordinator; run project gates and upload scenarios on stable tree.
Acceptance: exactly 10 MiB succeeds; 10 MiB + 1 byte gets HTTP 413 without storing the oversized body.
Return: changed paths, source-grounded facts, risks/unverified items and observed evidence as above.
```
