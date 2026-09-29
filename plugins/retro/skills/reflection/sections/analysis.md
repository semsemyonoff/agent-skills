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
   - CLAUDE.md rule: a preference or constraint that is restated (language, style, "do not commit");
   - ignore: one-off or already trivial.

## Friction

Read each correction candidate in context of the session id prefix. Keep it as friction only if the
user redirected or reverted the assistant's work. Group by cause: assumed scope too large, wrong
tool or language, ignored an earlier instruction, over-engineering, missing project knowledge.
A cause that recurs in 2+ sessions becomes a rule (CLAUDE.md, or the relevant skill's rules).
Write the proposed rule text in one line, in the imperative, with the reason.

Also read: sessions with many interrupts (`int=`), many errors, or large token counts relative to
prompts - open their first prompts to see whether the task was mis-scoped or looped.

## Errors and denials

- Repeated `Exit code N` on Bash says little by itself; look for the same tool/normalized message
  repeating. Candidates: a missing tool in PATH, a Read on huge files without offset/limit (a rule or
  a helper), MCP calls against a wrong or disabled endpoint, edits with no-op replacements.
- "auto mode classifier gave no verdict" is a transient infrastructure failure, not user error;
  report the count as noise, not as a proposal.
- Classifier denials by category and tool: a denial that was then approved manually every time is a
  candidate for an explicit allow rule; a denial for something the assistant should never try
  (credential exploration, destructive git) is a candidate for a CLAUDE.md rule instead.
- "user rejected" repeated on the same tool signals the assistant proposes actions the user does not
  want; find out which and write the rule.

## Routing and spend

- Subagent calls: compare `model set` vs `unset`. Unset inherits the parent model, so exploration
  or research subagents running on the most expensive model are the usual waste. Look at which
  `subagent_type` runs unset and whether the work is read-only search (fits a cheaper model) or
  needs the strongest model (review, hard design).
- Tokens: cache_read dwarfs everything in long sessions; that is normal. Look for output-heavy
  models, sessions with huge cache_write (context churn, many `/clear`s), and the main-vs-subagent
  split when `--include-subagents` was used. Without that flag subagent tokens are not counted, so
  the model table understates cheaper models; say so.
- Do not convert tokens to dollars from memory; point to `npx ccusage` for that.

## Proposals

Rank by value (occurrences x time saved) over effort. Prefer, in order: fix an existing skill's
description, add a CLAUDE.md rule, add a permission allow rule, add a subagent `model:` default,
write a new skill or command. For each proposal give: the change, the file/place, one line of
evidence, effort (S/M/L). Stop at 3-7 items; a longer list dilutes the top ones.
