# Changelog

## 2.0.5

- Recognize omp's short leading rule before a session-titled composer in either
  terminal, without treating TODO-card closers as composer borders.

## 2.0.4

- Confirm long-message acceptance when Claude has cleared the composer but still
  displays its transient paste hint; keep all pre-write and dialog checks.

## 2.0.3

- Recognize Claude's transient `paste again to expand` hint only beside a numbered
  paste token, so long messages can submit without relaxing dialog checks.

## 2.0.2

- Verify Claude Code's numbered `[Pasted text #N]` composer token for long bracketed
  pastes, only after an empty-composer preflight; never overwrite an existing paste.

## 2.0.1

- Recognize Claude Code's auto-mode status footer when verifying wrapped peer messages;
  keep submission withheld for dialogs and unverified text.

## 2.0.0

- One portable peer-chat skill for Claude Code, native Codex CLI and omp, on kitty and agterm;
  either pane can run any supported harness.
- Explicit actual-harness sender labels, automatic recipient discovery and a read-only doctor.
- Document default recipient keys, safe refusal handling and replies through the bundled script.
- Shared installation now comes from `plugins/peer`; removed the separate Codex skill/script copy.
- Added bilingual skill-evaluation prompts for routing, missing environment and incoming replies.

## 1.1.0

- kitty backend for Linux; the send script now ships with the skill instead of chezmoi.

## 1.0.0

- Moved the Claude side of peer-chat from chezmoi. At this release, the separate Codex side lived
  in `codex/peer-chat` (removed in 2.0.0).
