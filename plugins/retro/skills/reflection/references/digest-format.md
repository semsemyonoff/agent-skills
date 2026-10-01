# Digest format, roots and blind spots

## CLI and storage selection

Python 3, standard library only. `--source claude|omp|both` is **required**; the helper never guesses
from model names, environment variables or which directory happens to exist. The skill supplies the
current harness explicitly by default. `both` is a user-requested combined run, not automatic discovery.
Native Codex CLI session files are not supported; `openai-codex` inside omp is an omp provider.

- `--config-dir <root>`: Claude config root containing `projects/`. Defaults to `CLAUDE_CONFIG_DIR`
  or `~/.claude`. Main transcripts: `projects/<bucket>/*.jsonl`; optional children:
  `projects/<bucket>/<parent>/subagents/*.jsonl`.
- `--omp-sessions-dir <root>`: exact omp session storage root. Defaults to `~/.omp/agent/sessions`.
  Recursively reads `.jsonl` files below that root, including child artifact journals when enabled.
  omp's normal project file is `<bucket>/<timestamp>_<sessionId>.jsonl`; child journals live below
  its sibling artifact directory `<timestamp>_<sessionId>/<agentId>.jsonl`.
- `--since YYYY-MM-DD` (inclusive local midnight, normalized to UTC) or `--days N` (rolling days;
  default 7). These options are mutually exclusive. Event timestamps, **not file mtimes**, select data.
- `--project <substring>` matches recorded cwd or project bucket, case-insensitively. The source,
  project, period, SDK and child filters apply to **all** prompt/tool/error/routing/usage totals.
- `--include-subagents` adds child tools/errors/usage; child task text never becomes a user prompt.
  Claude `--include-sdk` adds sdk-* automation; that option has no meaning for omp.
- `--out json|md`, `--max-prompts 80`, `--max-sessions 25`, `--max-corrections 30`. Caps limit displayed
  rows, not totals; omitted counts are explicit. Negative caps and invalid dates fail with exit 2.
  A missing selected root also exits 2. An unselected root is never accessed.

### Active omp profile/custom/XDG roots

Always pass the actual active root explicitly outside the default layout. The extractor does not
load profiles, dotenv, credentials, settings or databases, and never performs storage migrations.
Current omp directory resolver mappings (read-only schema research, 2026-10-01):

- Config root: `~/.omp` (or `PI_CONFIG_DIR`, a directory name relative to home in omp's resolver).
- Named profile: `<config-root>/profiles/<name>/agent/sessions`.
- Default profile custom `PI_CODING_AGENT_DIR`: `<agent-dir>/sessions`; named profiles ignore that
  override. Active profile selection uses `OMP_PROFILE`, falling back to `PI_PROFILE` only when the
  former is absent; these are **not** automatically interpreted by this helper.
- Initialized XDG data root on Linux/macOS: `$XDG_DATA_HOME/omp/sessions`; named profiles use
  `$XDG_DATA_HOME/omp/profiles/<name>/sessions` only when that profile directory exists. An explicit
  custom agent dir bypasses XDG. Consult available active-session metadata when choosing the root.
- An omp `--session-dir`/custom session location can be supplied directly as `--omp-sessions-dir`.
  Files outside the selected root, remote/index-only sessions and temporary orphan child logs are
  not read. Passing a root does not authorize following a lineage path outside it.

## Persisted formats

### Claude Code

Relevant top-level records: `user` and `assistant`, with `timestamp`, optional `uuid`, `sessionId`,
`cwd`, `entrypoint`, `isMeta` and `isSidechain`. Assistant blocks use `tool_use` (`id`, `name`,
`input`); Agent/Task calls include `subagent_type` and optionally `model`. User `tool_result` blocks
use `tool_use_id`, `is_error`, `content`. Usage fields are `input_tokens`,
`cache_creation_input_tokens`, `cache_read_input_tokens`, `output_tokens`, optionally `total_tokens`.
Provider/effort are recorded only when explicit, not inferred from a Claude model spelling.

Streaming repeats `message.id`: merge records by recorded timestamp, then append position for ties
and a payload tie-break across file copies, never by filename. Untimed partial appends keep their
position after the preceding timed record without inventing an event timestamp. Latest known
components replace earlier components; the last explicitly provider-reported total survives a
partial update until a new reported total arrives. Derive totals only when none was reported.
Stable tool-use ids count once. A user UUID identifies a prompt/result event; absent UUIDs retain
file/line identity rather than collapsing unrelated content. Child identity includes its parent
artifact directory and agent filename, because Claude child records can retain the parent's sessionId.

### omp (session version 3 and older readable shapes)

Physical JSONL may start with a fixed-width **256-byte `type: "title"` slot**, then the logical
`type: "session"` header (`id`, `timestamp`, `cwd`, optional `parentSession`). Legacy files can start
directly with that header. The title is metadata, never a prompt. Invalid/missing leading headers
are skipped and reported. Malformed JSON lines, non-objects and interrupted final appends are skipped.

Non-header entries have `type`, stable `id`, `parentId`, `timestamp`. Relevant shapes:

- `message.message.role`: `user`, `assistant`, **`toolResult`**. An assistant's content contains
  **`toolCall`** blocks (`id`, `name`, `arguments`), not a `tool_call` role. Results carry `toolCallId`,
  `toolName`, `isError`, text/image content. Never lowercase these camelCase discriminants.
- Assistant `usage`: `input`, `output`, `cacheRead`, `cacheWrite`, `totalTokens`. `provider` and
  `model` are explicit. Provider-reported totals can include orchestration tokens beyond the four
  conversation buckets; preserve the reported total, deriving the sum only when no total exists
  and every conversation bucket is known.
- `model_usage`: standalone calls (`purpose`, optional `role`, `provider`, `model`, `usage`,
  optional `errorMessage`) contribute usage/errors, not prompts or transcript turns.
- `model_change`: `model` in `provider/model` form, optional role; the default role updates default
  model state. `thinking_level_change`: `thinkingLevel`, optional `configured` (e.g. `auto`).
  State follows each entry's `parentId` path, not the last unrelated branch. Missing/null levels stay
  unknown in a retrospective rather than pretending the transcript reported zero effort.
- `session_init` is the child revival contract: `agent`, `modelRole`, `resolvedModel`, task/tools
  and other replay metadata. The extractor exports routing metadata, not system prompts/task bodies.
  A session_init or a journal nested in a known parent's artifact directory identifies a child.
  **`parentSession` alone does not**: it is opaque fork lineage, either an id or path.
- Compaction/reset/branch summaries, title/model-state records and custom extension content are not
  user requests. No raw thinking or assistant prose is included. Standalone `!` executions are not
  model tool calls and are currently not counted.

## Normalized digest (schema_version 2)

- `source`, `roots`, `period_since_utc`, read `diagnostics`, `files_read`, sessions/prompts totals.
- `sessions[].id` and prompt/correction refs use full **source-qualified** identities (`claude:...`,
  `omp:...`), so ids from mixed stores cannot collide. Rows carry cwd/project, relative evidence
  filenames (up to 3), child status, known child agent/model-role/resolved-model, event dates and counts.
- Prompt rows group complete redacted normalized text, preserving counts and distinct session refs
  (up to 10 refs). Clipped identical prefixes do not merge distinct prompts. Slash commands remain
  `/name args`; meta/sidechain/interrupt/skill-injected text and child tasks are excluded.
- `tools_top`, `errors_top` (paths/numbers normalized), denials/by-tool, subagent invocation counts,
  prompt openers and RU/EN correction candidates. omp batch task calls count each task item. Missing
  explicit model means unresolved policy/role in omp, **not necessarily inherited parent model**.
- `tokens_by_model` keys are `source:provider/model`; an unknown provider/model is spelled `unknown`
  in a key, while structured `usage_routes` metadata uses null. Routes retain effort/configured effort
  where known. `model_usage` calls count in usage `messages` (accounted calls), not prompt counts.
- Metrics: `input`, `cache_creation`, `cache_read`, `output`, `total`. Missing fields remain **null**;
  each aggregate also exposes `known` subtotals and per-metric `missing` call counts. A sum is complete
  only when every selected call reports that metric. No calls means unavailable, not measured zero.
  Legacy `tokens_in_out` means input + cache creation + output, excluding cache reads; `usage.total`
  is the total-token accounting field. Markdown prints unavailable and shows completeness metadata.
- With child inclusion, `output_tokens_main_vs_subagent` gives complete output sums per group or null.
  Display caps do not alter this split or any other totals.

### Deduplication and scope

Within a session, stable entry/message/tool ids identify events, not excerpt text. Distinct result
entry ids for the same tool call remain distinct consumer events. Multiple file copies with the same
source-qualified session id merge. Claude stable message/tool ids suppress parent-context copies
within proven artifact families; unrelated Claude sessions with colliding ids remain separate.
omp's short entry ids are **not globally unique**: cross-session copies require a known lineage or
artifact-parent relationship **and identical persisted record payloads**. Shared opaque lineage
markers can prove sibling-fork copies even if the origin is absent; they never prove child status.
Unrelated sessions with colliding short ids retain their events. No-id legacy entries cannot safely
prove cross-session copies. The first eligible session owns each proven copy; sessions with only
copied/no in-scope events contribute no session row. All historical branch events count exactly once;
this is an activity retrospective, not reconstruction of only the active leaf/context.

The same chronological/partial-field merge rules apply to repeated omp entries and same-session
file copies. Period eligibility uses the merged event's last recorded timestamp, not a stale copy.

## Limits and safe interpretation

- No pricing, runtime configuration changes, database writes or model calls. Read diagnostics report
  malformed records, invalid headers, unreadable files, untimed events and skipped copies. Scanned
  file counts/diagnostics can include out-of-scope files; behavioral totals cannot.
- Corrections are keyword matches over the first 300 characters; ambiguous replies are not proven
  friction. Subagent calls via arbitrary eval code are not statically interpreted; child session_init
  still supplies recorded routing metadata when child journals are present.
- Redaction covers secret-key values, Bearer/Basic, common credential prefixes, long hex/base64-like
  runs and URL credentials, including metadata and refs. It is best effort; paraphrase private data.
- The project name is the cwd basename. Worktrees/scratch dirs can be separate projects. Missing
  cwd uses the bucket name; custom roots without buckets depend on recorded cwd for project matching.
- In-memory sessions, compressed archives, externalized blobs, remote storage, unknown extension
  records and files outside explicit roots are not read. Parsing holds each session's normalized
  records in memory; there is no unbounded raw transcript expansion in the report.

## Schema research sources

Read `omp://session.md` plus the linked current source types/writers, not private transcript content:

- [Session format and tree semantics](https://github.com/can1357/oh-my-pi/blob/main/docs/session.md)
- [Header/entry/title-slot/session_init types](https://github.com/can1357/oh-my-pi/blob/main/packages/coding-agent/src/session/session-entries.ts)
- [CamelCase message/tool-call types](https://github.com/can1357/oh-my-pi/blob/main/packages/ai/src/types.ts)
- [Usage buckets and reported totals](https://github.com/can1357/oh-my-pi/blob/main/packages/catalog/src/types.ts)
- [Profile/XDG/custom directory resolver](https://github.com/can1357/oh-my-pi/blob/main/packages/utils/src/dirs.ts)
- [Project session layout](https://github.com/can1357/oh-my-pi/blob/main/packages/coding-agent/src/session/session-paths.ts)
- [Child journal and session_init writer](https://github.com/can1357/oh-my-pi/blob/main/packages/coding-agent/src/task/executor.ts)

All bundled reader tests/fixtures are invented structural examples. No private transcripts were used.
