# Digest format, roots and blind spots

## CLI and storage selection

Python 3, standard library only. `--source claude|omp|both|codex` is **required**; the helper never
guesses from model names, environment variables or which directory happens to exist. The skill
supplies the current harness explicitly. `both` is a user-requested Claude+omp combined run only;
Codex is selected explicitly, not included by `both`.
Native Codex CLI is supported explicitly with `--source codex`; an OpenAI/Codex model inside omp
remains an omp session.

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
- `--out json|md`, `--max-prompts 80`, `--max-sessions 25`, `--max-corrections 30`. Caps limit
  displayed rows, not totals; omitted counts are explicit. Negative caps and invalid dates fail with
  exit 2. A missing selected root also exits 2. An unselected root is never accessed.

### Native Codex CLI

- `--include-subagents` adds proven child tools/errors/usage; child task text never becomes a user
  prompt. A native Codex child is identified only by explicit
  `session_meta.payload.source.subagent.thread_spawn` metadata containing nonempty `parent_thread_id`.
  The report preserves `codex_source`, records `is_subagent`, immediate
  `parent_thread_id`/`parent_lineage`, `root_lineage` (the raw recorded `session_id`, not inferred
  ancestry), and typed spawn metadata (`subagent_depth` as a nonnegative integer; `agent_path`,
  `agent_nickname` and `agent_role` as strings) when present. Missing/null role is not inferred from
  nickname. Missing/malformed spawn metadata, bare `session_id` differences, `history_base`, or
  opaque fork lineage do not establish child status. Proven child prompts are excluded from user
  prompts even when child activity is included. Child usage remains distinct and is not added to
  root/task usage. `--include-exec` includes automation only when `originator == codex_exec` or
  `source == exec`; child inclusion does not override that filter, so automation children may require
  both options.
- Codex user-role records are classified: `user`, `peer` (`Chat from Claude|Codex|omp` peer-chat
  messages), `automation` (exec/automation sessions and markers) and `injected` (AGENTS.md,
  environment/permission context). Only `user` becomes a prompt; `codex_message_kinds` counts all
  four. Spawn calls feed `subagent_calls` and `codex_spawn_observations` (observed model/effort);
  spawns recorded only in `codex_exec` sessions appear only with `--include-exec`, so an empty
  routing section without it is not lost data. Both fields stay empty for other sources.
- Failed Codex tool items are joined to their calls by item id and carry the recorded cause; when
  none is recorded the error keeps the exit code with "diagnostic cause unavailable".
- When a recorded call output/completion timestamp is available, Codex tool `duration_seconds` is
  call-to-result elapsed time (`duration_source: call_to_result_elapsed`), not process runtime.
- Usage events come from per-response `token_usage_record.usage`; never sum cumulative turn/thread
  snapshots. `cache_read = cached_input_tokens`; `cache_creation = cache_write_input_tokens`;
  `input = input_tokens - cached_input_tokens - cache_write_input_tokens` (unknown if a required
  value is missing or the result is negative); output and total use the reported output and total.
  For older files without `token_usage_record`, consecutive cumulative `total_token_usage` snapshots
  provide deltas, with each later event's `usage_interval_start` set to the preceding snapshot.
  The first non-null snapshot is only a baseline (`usage_baseline_time`), not a usage event or
  billable work. `usage_coverage_end` records the last snapshot time. A missing baseline or one
  later than the selected window's start sets `coverage_missing`: aggregate metrics are null,
  `known` retains the measured subtotal, and completeness is partial (or unknown with no usage).
  Even with an earlier baseline, fallback sums are snapshot-interval estimates: a delta can include
  pre-window work when its interval crosses the start, and work after the last in-window snapshot
  can be omitted. Do not treat these estimates as exact window cost or billing measurements.
  `thread_total` is cumulative thread metadata, never a usage event or an addition to sums.
- Python 3.14+ provides stdlib `compression.zstd`; otherwise compressed files are skipped and
  `zst_skipped` records the omission. `unknown_codex_records` counts unrecognized record types and
  `unjoined_tool_failures` counts failed items without a joined call; neither implies success.

## Plan-run report

Run `scripts/plan_run.py` with `--plan PATH` and/or `--progress FILE`; `--project-root` defaults
to cwd, `--tz` to the system zone, `--planning-days` to 3 (nonnegative), and `--out json|md`
defaults to md. Source roots are `--config-dir`, `--omp-sessions-dir` and `--codex-sessions-dir`,
with the same defaults described above. The tool loads Claude, omp and Codex sources once each;
missing roots are reported unavailable in diagnostics rather than making missing evidence zero.

Source availability and read coverage are separate in `diagnostics.sources[<source>]`: `status`
is `available` or `unavailable`, while `coverage` is `observed`, `partial` or `unknown`.
Unavailable roots have unknown coverage. Available roots can still be partial when files were
skipped or lost; `evidence_loss` and per-source `diagnostics` identify `zst_skipped`,
`unreadable_files`, `malformed_records` and `invalid_headers`. Lost records cannot be reliably
excluded by project or time, so coverage loss makes affected report totals/completeness partial;
do not interpret root availability as proof of complete reads.

JSON top-level fields are `run`, `plan`, `tasks`, `reviews`, `planning`, `other_in_run`, `totals`
and `diagnostics`. `run` reports status, failed state, timing, header, terminals, restarts,
resume lines, failures, `matched_by` and `other_progress`. Plan-run rows expose three separate
completeness dimensions: `read_completeness` (`observed`, `partial` or `unknown`) describes source
availability/read loss; `usage_completeness` (`observed`, `partial` or `unknown`) describes coverage
of measured usage events; and `attribution_completeness` (`observed` or `partial`) describes whether
all actual iteration/review windows are uniquely linked to a primary session, iteration task IDs
are explicit and belong to the plan, and run bounds are known. No iterations and no reviews is
partial attribution, not proof of complete attribution. At task level, no iterations is partial.
The existing `completeness` remains the conservative combined status. These fields appear on
run/totals and applicable window, task, phase and task-summary rows. Readable roots and non-null
measured root usage do not establish complete attribution or prove full-window cost. Preserve
measured `known` subtotals and report unlinked activity separately; missing metrics remain unknown,
not zero.

Task rows carry number/title/check counts, iterations, usage, duration, outcome, calls/errors,
models, slow commands, failure excerpt and completeness. Each iteration distinguishes its iteration
`number` from nullable `task_number`, and reports `task_identity` (`explicit-progress`, `ambiguous`
or `unknown`), `task_evidence`, `link_status` (`linked`, `ambiguous` or `unlinked`), candidates,
usage, models, calls/errors, slow commands, completeness and `time_source`. Task evidence includes
`status` (`completed` or `started`). English and Russian selection/completion statements can
identify tasks using either `Task N` or `Задача N`: for example, `Selected Task N`, `Выбрана
задача N`, `Task N completed`, and `Задача N завершена`. Explicit completion takes precedence
over an earlier incorrect
selection or a started/in-progress mention; conflicting completed IDs remain ambiguous. An
iteration number is never a task number. Completion without a task number supports run outcome,
not task identity.

Review rows are `kind: phase`. `review_role` is `review`, `external-review` or `evaluation`;
`review_round` is an integer or null when the boundary is a round. `review_label` preserves the
original marker content without its boundary dashes. Recognized boundaries include legacy
Claude-review/evaluation names, external Codex review and iteration markers, and custom
external-review/review-iteration markers. These labels identify stages, not actual actors or models.
`review_provider` is the matched unique primary session's recorded `source`, or null if it cannot be
uniquely established; marker wording and model name never constrain or establish the source. Review
windows do not overlap; same-time introduction/round markers coalesce. Generic
`starting <name> phase` boundaries remain supported. Unknown task identity and ambiguous candidates
stay distinct rather than being guessed.

Codex review activity matched to an external-review boundary is review activity, not task execution;
native Codex execution remains supported when progress/session evidence identifies it as execution.
For usage attribution, explicitly proven child sessions are not alternate primary candidates and
child activity is not rolled up into root/task usage. Their distinct activity remains in
`other_in_run`/unlinked, including unique child usage; this unlinked child usage alone does not make
a successfully attributed primary stage partial.
Proven parent/artifact families suppress copies only with source-appropriate identity proof: Claude
requires a stable message ID (or stable UUID fallback), matching record type and identical normalized
message payload; wrapper metadata is ignored. Omp and Codex require matching event kind/key and
identical full persisted payload.
`diagnostics.copied_events_skipped` reports suppressed copies. Unknown child cost is not measured
task cost. A moved plan remains selectable explicitly with `--plan PATH`; no plan autodiscovery is
promised.

Review/planning links carry session/source/cwd/time and `linked_by`/confidence evidence. Linked
session usage/calls/errors/models may include `partial_history` and cumulative `thread_total`; do
not add thread totals to window cost. `totals.by_phase` contains metric summaries and completeness;
`totals.by_task` is a list of task summaries; `observed_in_run`, `unlinked`, `unlinked_share` and
completeness describe coverage. When `coverage_missing` is true, metric totals are null while
`known` retains measured subtotals, with `usage_completeness: partial` (or `unknown` without usage
events). `partial_history` is a separate history limitation: loaded suffix usage can retain non-null
totals and `usage_completeness: observed`, while combined candidate/run completeness remains
`partial`. `read_completeness` may remain `observed` when the available files were fully read.
Those totals measure the loaded events, not proven full-window cost; an inherited prefix may contain
unobserved work. `attribution_completeness` can be partial even when the source was fully read and
usage is observed, because windows or task iterations may remain unlinked/unknown.

Codex candidate links also expose `usage_baseline_time` and `usage_coverage_end` (UTC ISO strings
or null), `usage_completeness` (`observed`, `partial` or `unknown`), and `evidence_coverage`
(`observed` or `partial`). Fallback totals with a missing/late baseline or source read loss are null
while `known` retains measured subtotals; incompleteness propagates through candidate, iteration,
task, phase and run metrics. Codex `slowest_commands` include `result_time` and
`duration_source: call_to_result_elapsed`; the elapsed duration is between recorded call and result
timestamps, independent of status certainty, and is not process runtime.
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
- Codex `is_subagent` is true only with structured spawn proof: a nonempty
  `session_meta.payload.source.subagent.thread_spawn.parent_thread_id`. Opaque fork/session lineage,
  `history_base`, or a different `session_id` alone does not establish a child. Missing metadata
  remains unknown; inherited prefixes are not loaded. On Python versions before 3.14, `.zst` rollouts
  are skipped (reported by `zst_skipped`).

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
