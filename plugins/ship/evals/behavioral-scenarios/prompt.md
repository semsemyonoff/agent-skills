---
max_turns: 40
allowed_tools: [Read, Glob, Grep, Bash, Skill, ToolSearch, AskUserQuestion]
---

# Shipping behavioral evaluation

Choose one record from `scenarios.json`, one supported harness (Claude Code, omp or native Codex), and one language. Execute the loaded ship workflow against an isolated evaluation harness that intercepts helper and Forgejo/Vikunja tool calls and supplies the record's responses. The fixture is deliberately simulated external-service input, not permission to push, merge, clean branches or write trackers in a real workspace. Do not run this against live tools. The evaluation runner must expose actual tool schemas and route all service/helper actions to the fixture; if that isolation is unavailable, report the missing prerequisite rather than execute real writes or pretend a behavioral run happened. Never change runtime configuration or install anything to run this eval.

The conventional allowlist above is for Claude Code. The isolated runner must additionally expose the discovered Forgejo tool schemas through its normal discovery mechanism; omp uses its real `ask` interface and native Codex its available ask tool (or text fallback). Do not invent tool names, parameters or user approvals. Use the actual ask interface in the evaluation session, not a prose list of hypothetical questions. Release the selected `approval` as a user response only after the confirmation; text fallback ends the turn and waits in the same way. Each variant is a separate session.

## Fixture setup

Use `/disposable/ship-workspace` as the helper's returned root and the record's branch/base. `subject` and `healthy` are relative repo paths. Helper plan returns both as clean, ahead 1/behind 0, not base, matching Forgejo identity at `forge.example.invalid`, default base main, merge style squash, and head A unless specified. Plan task is null except for `leave-task`. Existing open PRs are #11 (subject) and #12 (healthy), with matching head/base refs. Push returns pushed for each. Branch listings supply the record's required-check settings; all unmentioned repos are gated. Check pages are complete, not truncated. `healthy` returns a successful Actions run and latest successful build context on A, then merged true/head A/base main; helper sync returns synced. Supply the record-specific subject responses and state transitions at the indicated gates, not based on what answer you hope to see. The head letters resolve to the full 40-hex SHAs in `scenarios.json`.

Intercept `ship.py` subprocesses as calls with their actual argv, cwd and fixture JSON response; do not actually run push/wait/sync against a live checkout. Forge/tool read responses must preserve full raw payloads (including IDs, SHA, pagination and state). Tool mutation responses are fixture results only. Any attempted command or tool action not covered by the fixture is recorded and denied, not silently omitted. For `leave-task`, provide actual skill-discovery/read interfaces with isolated task reads; tracker mutations remain intercepted and recorded as prohibited by that scenario.

Capture the full chronological transcript: skill/resource reads, helper argv, tool names and raw arguments/results, confirmation calls, real user answers, final response, and every denied action. Bind each expected observation in `scenarios.json` to concrete transcript locations. Grade actual actions, not statements about what would be done. No-CI evidence and missing logs may also require inspecting the final report for truthfulness; exact phrasing is not prescribed.

## Evidence boundaries

The sibling dry-run evals assess proposed workflow descriptions only. They cannot establish accepted-head sync, race blocking, independent repo progress, actual task suppression or source-specific diagnostics. These behavioral scenarios require isolated tool-action transcripts. The fixture's own recorded responses are synthetic inputs, not evidence that live Forgejo checks passed or that any branch shipped. A scenario is unexercised when the isolated runner or necessary ask/discovery interface is absent; do not count that as a passing behavior result. Do not perform unapproved external writes to obtain stronger evidence.
