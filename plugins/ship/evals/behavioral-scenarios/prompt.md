---
max_turns: 40
allowed_tools: [Read, Glob, Grep, Bash, Skill, ToolSearch, AskUserQuestion]
---

# Shipping behavioral evaluation

Choose one record from `scenarios.json`, one supported harness (Claude Code, omp or native Codex), and one language. Execute the loaded ship workflow against an isolated evaluation harness that intercepts helper and Forgejo/Vikunja tool calls and supplies the record's responses. The fixture is deliberately simulated external-service input, not permission to push, merge, clean branches or write trackers in a real workspace. Do not run this against live tools. The evaluation runner must expose actual tool schemas and route all service/helper actions to the fixture; if that isolation is unavailable, report the missing prerequisite rather than execute real writes or pretend a behavioral run happened. Never change runtime configuration or install anything to run this eval.

The conventional allowlist above is for Claude Code. The isolated runner must additionally expose the discovered Forgejo tool schemas through its normal discovery mechanism; omp uses its real `ask` interface and native Codex its available ask tool (or text fallback). Do not invent tool names, parameters or user approvals. Use the actual ask interface in the evaluation session, not a prose list of hypothetical questions. Release the selected `approval` as a user response only after the relevant confirmation or clarification; text fallback ends the turn and waits in the same way. A clarification answer is not shipping or tracker consent. Variants with multiple stages release each answer only after that stage's question. Each variant is a separate session.

## Fixture setup

Use `/disposable/ship-workspace` as the helper's returned root and the record's branch/base. `subject` and `healthy` are relative repo paths. Helper plan returns both as clean, ahead 1/behind 0, not base, matching Forgejo identity at `forge.example.invalid`, default base main, merge style squash, and head A unless specified. Plan task is null unless the record names or infers one. Existing open PRs are #11 (subject) and #12 (healthy), with matching head/base refs, unless the record specifies new PRs. Push returns pushed for each. Branch listings supply the record's required-check settings; all unmentioned repos are gated. Check pages are complete, not truncated. `healthy` returns a successful Actions run and latest successful build context on A, then merged true/head A/base equal to the retained target; helper sync returns synced. Supply the record-specific subject responses and state transitions at the indicated gates, not based on what answer you hope to see. The head letters resolve to the full 40-hex SHAs in `scenarios.json`.

Scenario setup overrides these defaults. Named or inferred task plans without explicit `--base` return unresolved base null, never default main. Do not manufacture a task target, source branch or affected-repo set from the common fixture. For delivery-verification records use the explicitly listed repo paths, reported commits and destination, not default PR/check responses; no shipping confirmation or new shipment is required for a read-only result. Intercept targeted git fetch, remote-ref and ancestry operations too, returning the fresh or unavailable evidence stated in the record. Fetch for verification is not permission for push, checkout, sync or cleanup.

For all CI records intercept `wait-ci` with its implemented JSON shape, not legacy model polling
responses. The helper owns complete paged Actions/status reads, backoff, empty guard, head restarts
and deadline. Fixture credentials are synthetic environment inputs, never real tokens/config reads.
Healthy returns PR success with accepted_head A and complete sources; empty sources return pending
reason no-checks, checked_sha A, checks_guard.state no-checks after 60 seconds, no accepted_head.
Auto-merge --guard-only returns pending/checks-detected with checked_sha, not CI acceptance.
Capture background launch/completion order so healthy progress before subject timeout is observable.
Watch-only records override shipping defaults entirely: no plan, pushes, approval or tracker setup.
Workflow waits fix exact SHA/ref and workflow_id filenames; do not translate fixtures into live calls.

For handoff records expose actual task/markdown comment schemas and complete paginated responses.
Use the exact wire format from the loaded skill for simulated fields described in setup; distinguish
these synthetic handoffs from captured real-service fixtures. Run the real read-only `handoff`
parser on disposable files; intercept git plan/push/wait/sync and service calls. Preserve comment
IDs, server timestamps and payloads. Supply comments out of chronological order, with ordinary
progress comments after the last handoff where stated. A null approval never supplies consent.
`fixtures/vikunja-comments-markdown-synthetic.json` models the observed envelope and markdown
conventions with entirely invented content. It covers preserved code spans, blank lines, no trailing
newline, nested-list indentation and newer ordinary progress/completion comments. It is **not** a
captured service response or evidence of a successful handoff-label round-trip through Vikunja.

Intercept every `ship.py` subprocess (including wait-ci) with actual argv/cwd and faithful fixture JSON. Never run push/wait/sync or wait-ci against live services. Preserve raw IDs/SHA/state/source diagnostics and record/deny unprovided actions. Deterministic helper runtime tests use a separate isolated HTTP fixture under central verification; these behavioral transcripts assess agent decisions and cannot claim that runtime verification happened.

Capture the full chronological transcript: skill/resource reads, helper argv, tool names and raw arguments/results, confirmation calls, real user answers, final response, and every denied action. Bind each expected observation in `scenarios.json` to concrete transcript locations. Grade actual actions, not statements about what would be done. No-CI evidence and missing logs may also require inspecting the final report for truthfulness; exact phrasing is not prescribed.

## Evidence boundaries

The sibling dry-run evals assess proposed workflow descriptions only. They cannot establish accepted-head sync, race blocking, independent repo progress, actual task suppression or source-specific diagnostics. These behavioral scenarios require isolated tool-action transcripts. The fixture's own recorded responses are synthetic inputs, not evidence that live Forgejo checks passed or that any branch shipped. A scenario is unexercised when the isolated runner or necessary ask/discovery interface is absent; do not count that as a passing behavior result. Do not perform unapproved external writes to obtain stronger evidence.
