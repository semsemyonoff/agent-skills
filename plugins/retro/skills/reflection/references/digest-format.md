# Digest format and blind spots

Transcripts live in `${CLAUDE_CONFIG_DIR:-~/.claude}/projects/<encoded-cwd>/<session-id>.jsonl`;
subagent transcripts in `<session-id>/subagents/agent-*.jsonl`. One JSON object per line; relevant
`type`s are `user` and `assistant` (others: attachment, queue-operation, cost-state, ...).

What the script reads:

- `assistant.message.content[]` blocks of type `tool_use` (name, input; `Agent`/`Task` carry
  `subagent_type` and optional `model`). Streaming writes the same `message.id` on several lines, so
  usage is deduped per message id and tool calls per tool_use id.
- `assistant.message.usage`: input, cache_creation_input, cache_read_input, output tokens, summed per
  `message.model`.
- `user.message.content`: string or blocks. `tool_result` blocks (with `is_error`) are errors or
  denials; text blocks are prompts. Skipped as non-prompts: system reminders, task notifications,
  command/caveat wrappers, interrupt markers, compaction summaries, skill-injected text, `isMeta`,
  `isSidechain`. Slash commands are kept as `/name args`.
- Denials: "denied by the Claude Code auto mode classifier ... Reason: [Category]" and "The user
  doesn't want to proceed with this tool use".

Digest sections: Projects, Tools, Errors (normalized: paths and numbers replaced), Permission
denials, Subagent routing, Tokens by model, Prompt openers (first 3 words), User prompts (deduped,
count/sessions), Correction candidates (regex heuristic), Sessions by tokens.

Blind spots:

- Sessions are included by event timestamp >= period start; files older than the period by mtime are
  skipped without parsing.
- Tool, error, subagent and token totals are not filtered by `--project` (only sessions and prompts
  are); use project-specific runs when that matters.
- Subagent tokens/tools appear only with `--include-subagents`.
- Correction markers are RU/EN keyword regexes over the first 300 characters of a prompt: expect false
  positives ("не надо" as an answer to a question) and misses (a correction with no marker).
- Redaction is pattern-based (values after password/token/secret words, Bearer, well-known key
  prefixes, long hex/base64-like runs, URL credentials). It is best effort.
- The project name is the basename of the session's `cwd`; worktrees and scratch dirs get their own
  names.
