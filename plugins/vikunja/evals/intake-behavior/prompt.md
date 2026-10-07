---
max_turns: 30
allowed_tools: [Read, Glob, Grep, Skill, ToolSearch, AskUserQuestion]
---

# Intake action evaluation

Select one record from `../intake-scenarios.json`, one language (`prompt_en` or `prompt_ru`) and one real adapter (Claude Code or omp). Run all records separately for both adapters and both languages when those harnesses are available; absent capability is not evidence that it ran. The allowlist above is Claude-specific; omp uses actual advertised tools, including `ask`, not guessed equivalents. For trivial-explicit-start only, enable the real local edit tool for a disposable workspace. Never grant tracker mutations, shell execution, installs, settings changes, commits, pushes or external review.

Read `../fixtures/intake-tasks.json` as read-only harness input. This is clearly simulated tracker data for evaluation only, not a production MCP fallback. Supply the selected task, every comment and linked task 951903 to the agent as fixture-backed read responses through a test-only tracker interface if the evaluator supports one. Otherwise explicitly tell the agent: “This evaluation uses supplied synthetic tracker data instead of a connected tracker. Read the fixture with Read; perform the actual next-action ask and available workflow handoff, not a description of what you would do. Do not call a live tracker for these ids.” Record which mode was used. No fixture mode may fake the ask, user response, Skill/workflow invocation or worker outcome. MCP discovery/pagination correctness needs a separate connected-tool run; this fixture run tests the ask/handoff defect without requiring a live tracker.

Expose the scenario's capability limits through the harness's actual registry, not by instructing the agent to pretend a tool is absent. Supply available workflow definitions normally; do not invent mocks for missing skills. If a real required capability is unavailable, report the limitation instead of counting an unexercised handoff as passing. Missing-workflow and no-UI records intentionally remove those capabilities and grade the safe alternative.

Release the selected scenario's followup only at its stated gate, as an actual user message or actual UI choice. For cancellation/timeout scenarios supply the native ask outcome with cancellation or timeout metadata, not an affirmative user message. Do not synthesize approval in records without followups. English/Russian variants are separate runs.

Capture complete raw tool calls/results, user messages, available capability discovery, workflow invocation inputs/outputs, local diff where permitted, and final response. Grade actual action order and exact handoff content using `graders/criteria.md` plus the selected record's expected observations. No generic source-text validator is required. A summary that says it would ask, a synthetic claimed invocation, or passive plan-and-wait fails the actual-ask records.

For the two typo scenarios only, create a disposable workspace with `docs/export.md` containing `CSV export retentoin is 24 hours.`. Keep the checked-in fixture unchanged. The explicit-start run may change only that typo to `retention`; the timeout run must leave it untouched. Inspect actual file content and action permissions, not a report claiming the edit. No command execution is needed.

Keep `../intake-ru/` separate: it explicitly requests an MCP-unavailable hypothetical explanation and cannot demonstrate that a ready-design intake makes a real ask. `../trigger-evals.json` tests bilingual activation separately from these action scenarios. Do not run external model evals without separate authorization.
