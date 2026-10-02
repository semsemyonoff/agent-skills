---
name: brainstorm
description: 'Develop and validate a design through incremental discussion before planning or implementation. Use for brainstorm, think through, help me design, explore options, «мозговой штурм», «давай обсудим варианты», «продумай решение», «помоги спроектировать». Preserve loaded custom rules and hand off the validated design to the selected workflow. Not for re-designing an already approved plan, executing it, or reviewing a finished plan.'
license: MIT
---

# Brainstorm

Turn the request into an agreed design, not code. Reply in the user's language. Keep one shared
process in Claude Code and omp; identify the actual harness from its tools, not the model name.
Read `references/runtime.md` for the native question/handoff mechanism.

## 1. Load rules and context

Resolve resources from the directory of this loaded `SKILL.md`, not the project cwd or an assumed
installation. Invoke the bundled read-only resolver once with `--name brainstorm` and the actual
project directory, as described in `references/rules.md`. Apply the selected first-nonempty rules;
retain their path/provenance in context. Missing rules are normal; unreadable rules are a blocker.
Do not copy personal rules into the design or modify rules/configuration during ordinary use.

Read the task, existing design/plan, and relevant repository facts first. Separate decisions already
made from unresolved questions. Do not ask the user for information available from the repository.
A complete validated design is input for handoff, not an excuse to repeat the design discussion.

## 2. Resolve only necessary decisions

Ask one materially necessary question at a time, with concise choices and tradeoffs when useful.
Use the native ask UI if available; otherwise ask in text and wait. A timeout/default, redirect,
cancellation or silence is not an answer or approval. Never require a specific picker or plan-mode tool.
Skip questions whose answers are already supplied, and do not impose a goal/scope/title questionnaire.

For genuinely open design choices, present two or three viable approaches with concrete costs,
risks and benefits; lead with the recommendation. Do not manufacture alternatives to a settled choice.
Keep the design proportionate: boring existing conventions beat speculative frameworks.

## 3. Validate incrementally

Discuss short coherent sections rather than a large unapproved design dump. Cover only the relevant
architecture, behavior, boundaries, dependencies, failure cases and verification. Resolve feedback
before advancing; do not ask for repeated confirmation of unchanged decisions. Mark unresolved facts
and assumptions explicitly instead of declaring them validated.

Conclude with a compact validated-design packet:
- original goal and scope/non-goals;
- selected approach, decisions and constraints;
- discovered files/patterns and source evidence;
- dependencies, consumer-visible acceptance and proportionate verification;
- loaded rule path/provenance, unresolved prerequisites and authorized actions.

## 4. Choose the next workflow

Apply loaded routing rules, including any recommendation, step thresholds or option ordering.
Offer only meaningful available choices; do not secretly enter implementation:
- **Orchestrate** for bounded multi-step work when that is the chosen one-session route. Pass the
  entire validated-design packet to the available orchestrate workflow for short recon and its plan
  table, without re-asking resolved design questions. Choosing it does not bypass its execution approval.
- **Write plan** for durable or multi-session work. Pass the same packet to the available planning
  workflow to create a plan file without repeating discovery/design decisions.
- **Start now** only for trivial scoped work and explicit permission to execute it.
- **Stop** to leave the validated design without further action.

Use the current adapter to translate historical workflow names in rules, not an invented slash API.
If the chosen workflow is unavailable, give the exact missing capability and the design packet;
do not install anything, substitute a different executor, or claim a handoff ran. A plan-mode tool
is optional only if explicitly requested and actually available. No exec workflow or automatic
commits, pushes, external writes or rules/configuration changes.

## Resources

- `references/rules.md` — precedence, loader output and explicit rules management.
- `references/runtime.md` — native question UI and workflow handoffs.
- `scripts/load_rules.py` — read-only resolver; `scripts/test_rules.py` — offline behavioral checks.

Adapted from [umputun/cc-thingz](https://github.com/umputun/cc-thingz), brainstorm workflow.
Upstream MIT copyright and permission notice are included in [LICENSE](LICENSE).
