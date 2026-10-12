# Changelog

## 2.1.1

- Clarify instruction-only Codex command restrictions and require runtime references before
  proposing technical guarantees; preflight does not certify authentication or provider quota.
- Preserve explicitly confirmed same-provider targets through the existing helper without
  claiming that a separate process necessarily uses a different model.
- Add behavioral evals for these proposal, confirmation and preflight boundaries.

## 2.1.0

- Add shared `ask-other` for one user-authorized cross-vendor debug, adversarial
  code-review or plan-review consultation through existing native Claude/Codex CLI routing.
- Constrain Claude to read/search tools and Codex to its native read-only sandbox;
  suppress normal external/nested customizations while documenting trusted native
  authorization/administrative effects separately from model-tool guarantees.
- Bundle deterministic JSON preflight/results, finite stdin, deadline/process-group
  cleanup, structured review/evidence validation and permanent synthetic boundary tests.
- Add bilingual behavior/trigger evals without changing peer-chat or planning workflows.
- Reject native Codex model-reroute notices without rejecting unrelated warnings;
  suppress automatic skill instructions and active code-mode execution, and safely
  disable inherited MCP servers with one exact-name, transport-preserving TOML value overlay.
- Preserve original stream and nonzero-exit auth/provider/interruption failures when
  teardown encounters denied signals; separately report unconfirmed cleanup and
  refuse successful consultation results when cleanup remains unresolved.

## 2.0.6

- Treat Codex's dimmed empty-composer hints as an empty composer, so delivery to
  an idle Codex no longer refuses as occupied; the caret check still guards drafts.

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
