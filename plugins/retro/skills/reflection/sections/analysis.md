# Analysis playbook

Work from the digest top to bottom. Keep notes as short evidence lines; the report comes after.

## Recurring intents (prompts, openers, slash commands)

1. Cluster the "User prompts" list and the "Prompt openers" by intent, not by wording: "merge the PR
   and clean up the branch", "смерджи и удали ветку" and "мердж" are one intent. Sum the counts.
2. Slash commands (`/clear`, `/mcp`, `/effort`, custom ones) show up as prompts. Frequent custom
   commands are already automated; frequent built-ins like `/clear` say little. Long boilerplate
   prompts repeated across sessions (same opener, same instructions pasted) are the strongest
   skill/command candidates.
3. Ignore terse replies ("да", "ок", "продолжай") for clustering, but a high count of them in
   one session hints at over-asking by the assistant (many confirmations that a rule or permission
   could have skipped).
4. Verdict per cluster:
   - existing skill/command covers it: name it, then find why it did not fire (description lacks the
     user's phrasing? user does not know it exists?);
   - new skill candidate: 3+ occurrences over 2+ sessions and a multi-step, stable workflow;
   - project instruction rule: a preference or constraint that is restated (language, style, "do not commit");
   - ignore: one-off or already trivial.

## Friction

Read each correction candidate with its source-qualified session ref and excerpt. Keep it as friction
only if the evidence shows that the user redirected or reverted work; mark missing context uncertain
rather than opening private raw logs. Group by cause: assumed scope too large, wrong tool/language,
ignored instructions, over-engineering, missing project knowledge. A cause in 2+ sessions can justify
a project rule (CLAUDE.md for Claude Code, AGENTS.md or the applicable context file for omp).
Write the proposed rule text in one line, in the imperative, with the reason.

Also compare sessions with many interrupts, errors, or high known usage relative to prompts.
Use the redacted first prompts already in the digest; do not expand private transcript bodies.

## Errors and denials

- Repeated `Exit code N` on Bash says little by itself; look for the same tool/normalized message
  repeating. Candidates: a missing tool in PATH, a Read on huge files without offset/limit (a rule or
  a helper), MCP calls against a wrong or disabled endpoint, edits with no-op replacements.
- "auto mode classifier gave no verdict" is a transient infrastructure failure, not user error;
  report the count as noise, not as a proposal.
- Classifier denials by category and tool: a denial that was then approved manually every time is a
  candidate for an explicit allow rule; a denial for something the assistant should never try
  (credential exploration, destructive git) is a candidate for a project instruction rule instead.
- "user rejected" repeated on the same tool signals the assistant proposes actions the user does not
  want; find out which and write the rule.

## Routing and spend

- Separate the harness source from the provider/model: an openai-codex model in omp is still an omp
  session. Never infer source, provider or effort from a model name alone.
- Subagent calls: compare explicit versus missing model arguments. In Claude Code a missing model
  may inherit the parent; in omp the agent definition, configured role and policy can resolve it.
  Use child `agent`, `model_role`, `resolved_model` and observed usage routes when available rather
  than claiming inheritance. A configured effort selector such as auto differs from resolved high/low.
- Tokens: null/unavailable means unknown. Inspect `known` subtotals and `missing` call counts before
  comparing spend. Report incomplete sums as partial, never zero. Cache reads dominate many long
  sessions; that is normal. Look for output-heavy models or context churn and the main/child split.
- Child tokens/tools/errors appear only with `--include-subagents`; delegated tasks are not user
  prompts. Standalone omp model_usage calls contribute usage, not conversation turns. All totals
  already obey the selected source, project and period. Row caps limit evidence, not totals.
- Do not guess dollars or run a pricing/dashboard tool unasked. ccusage is an optional Claude-only
  pricing route; omp stats is an optional omp usage surface, not a required report dependency.

## Proposals

Rank by value (occurrences x time saved) over effort. Prefer, in order: fix an existing skill's
description, add a relevant project rule, add a permission allow rule, adjust verified subagent
routing, write a new skill or command. For each proposal give the change, file/place, one line of
source-qualified evidence, effort (S/M/L). Stop at 3-7 items; a longer list dilutes the top ones.
