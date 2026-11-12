# Native review adapter

Use the driver/worker process from SKILL.md; default one native pass, additional passes only through
the selected sections/chain.md protocol. Identify actual harness, live delegation schema, reviewer
roster and permissions. Native configuration owns model/effort; report only exposed facts.
Unavailable review remains unavailable, never author self-review.

## omp

The optional native resource is `agents/omp.md` relative to the loaded skill directory:
`name: plan-review`, `model: "@plan_review"`, `tools: [read, grep, glob]`, `spawns: []`.
The operator may expose it through native agent discovery and configure `modelRoles.plan_review`;
loading the skill alone installs nothing. Do not change configuration or assume a particular model.
Existing native overrides are authoritative; there is no task `model` parameter or automatic upgrade.

Prefer the actually discovered `plan-review` agent. With the usual native batch schema, use required
shared `context` and one `tasks[]` item with `agent: "plan-review"`, `task` and `solutionSpace`.
The brief selects the worker branch and includes verbatim snapshot plan_text/path/version,
original request/decisions/rules/evidence and resolved resource paths; prohibit helpers/tests/writes/
nested dispatch. Read the real schema; flat variants use their actual item fields.
Do not use agent=task as a pretend specialist reviewer. Each native pass needs a fresh separate
context; only the chain's peer-route stage 2 reuses an existing session.
If the configured agent is absent/disabled/blocked, say so; use a different genuine read-only reviewer
only after an explicit compatible route choice, never a silent model/configuration change.

The native omp agent reads `skill://plan-review` through `read`, then uses the worker branch and
its relative references. That URI is omp-specific and does not appear in the shared core. Background
jobs notify on completion; do independent work or wait only when blocked. Do not poll or claim an
unfinished result; distinguish progress from the delivered reviewer findings.

## Claude Code

Discover exposed `Agent` or `Task`, its actual schema, and an independent reviewer identity rather
than assuming a fixed name or opus. Dispatch only an available reviewer whose actual contract can
perform the supplied worker branch without tests/writes/nesting. Claude Code may expose Bash instead
of Grep/Glob; then state the read-only shell inspection fallback below in the brief. Read-only is
enforced by that brief, not by the tool list, so say so in the reported limits. An upstream reviewer
that requires its own shell rule loader or conflicting template checks is not automatically compatible;
do not silently alter its definition or advertise the author's review as independent instead.

Use only supported parameters. Supply original task, plan path, source evidence, resolved criteria
and the exact rules packet. Read the current completion/background mechanism; no omp wait API is
invented here. The operator's existing upstream Claude workflows are not replaced by this package.

## Read-only shell inspection fallback

Applies only to a worker whose harness exposes file reading but no native search or listing tool.
With native read/grep/glob available, use them and no shell. Judge each command by what it does,
not by its name; a command whose effect is unclear is not run, and the gap is reported as uncertainty.

- **Allowed:** `rg --no-config` and `grep` searches, `find` listings, `ls`, `cat`, `head`, `tail`,
  `wc`, `sed -n '<range>p'`, and git only as `git --no-pager` with `ls-files`, `grep`, or
  `log`/`show`/`diff` plus `--no-ext-diff --no-textconv`; pipes between these. Configuration can
  otherwise start helpers implicitly (a ripgrep config `--pre`, git textconv, external diff or pager).
  Scope: the actual project root, the resolved skill/rule paths from the brief and, for a peer-route
  worker, the exact supplied `packet_path`.
- **Forbidden:** output redirection (`>`, `>>`, `tee`), `sed -i` or `sed` `e`/`w` commands,
  `rg --pre`/`--pre-glob`, `git --output`, `find -exec`/`-execdir`/`-ok`/`-okdir`/`-delete`/
  `-fprint*`, `xargs`, command or process substitution, interpreters, project scripts or helpers,
  tests, builds, package managers, network, environment or credential dumps, and git commands that
  change refs, the index or the working tree.

Report the fallback in Scope/limits. It never extends to the driver; the only driver shell/helper
exceptions are the bundled resolver, snapshot/validate, selected-chain consult or peer packet and
the peer-chat doctor/send described below.

## Driver decision buttons

Apply only the driver's bounded target-plan correction rules from SKILL.md. Never give the worker
editing tools; selected chain re-review uses a fresh reviewer and current exact snapshot.
For each unresolved architectural/product choice, conflict, agreed scope/route/budget change or
ambiguity, offer 2–5 concrete options with tradeoffs and one recommended option.

- **omp:** discover the live `ask` schema. Current inputs are `i` (short intent) and `html`,
  one semantic `<form>` with named, labeled controls. Group choices with `<fieldset>`/`<legend>`;
  use radios for one choice and checkboxes only for compatible independent choices. No scripts,
  styles, buttons or submit inputs: the UI supplies Submit/Cancel and Other for eligible groups.
  Write visible text in the user's language. Read named values and result metadata; carry the
  explicit chosen value or custom text into the dependent correction or selected workflow. If
  explicit response provenance is unclear, ask for confirmation; recommendation is not selection.
- **Claude Code:** use `AskUserQuestion` only when exposed, with its actual `header`, options and
  `multiSelect` fields. A recommended label is advice, not authorization.
- **No native UI:** present the same numbered text options/tradeoffs/recommendation and wait for a
  real answer. Do not assume an unavailable tool ran or replace a necessary choice with a default.

Only an explicit user answer resolving the choice permits its dependent target-plan corrections.
`timedOut`, defaults/auto-selection, redirect, cancellation, silence or missing response never count
as approval. Independent safe findings may already be fixed; dependent findings stay unapplied until
answered. Explicit review-only/no-edits disables autofix throughout, even when options are discussed.

## Narrow driver helper exceptions

Resolve helpers from the loaded skill directory. The driver may run read-only `scripts/load_rules.py`
once with `--name planning --project <actual-project-dir>`. It prints selected path/provenance/content;
the worker only re-reads the selected file with its read tool. No worker executes any helper.

```sh
python3 "<skill-dir>/scripts/review_state.py" snapshot "<plan>"
python3 "<skill-dir>/scripts/review_state.py" validate "<plan>" --version "<expected-sha256>" \
  [--request-id "<pending-peer-request-id>"]
```

Snapshot returns absolute original `plan_path` (not symlink-resolved), SHA-256 `plan_version` of exact
UTF-8 bytes and verbatim `plan_text`, including CRLF/BOM when present. Pass this snapshot unchanged.
Validation consumes canonical UTF-8 JSON on finite noninteractive stdin (30-second EOF deadline,
32 MiB limit), requires exact key sets and lowercase 64-hex expected digest, rejects duplicate keys/
schema/verdict inconsistency and checks exact path/version plus current file digest. Success exits 0
with only canonical parsed JSON; failure exits 1 with a diagnostic and no accepted stdout. Never
repair a rejected report or compute a different version to fit. Revalidate after reports/before fixes;
snapshot anew before each pass. Nonregular plans and changes during snapshot collection fail.

Read the completed canonical object with the native read tool and send that exact text on finite
stdin; a quoted heredoc delimiter can close stdin without changing the JSON. Invoke only the
documented bundled script command, not `python -c`/`-I` extraction, interpreter snippets, pipelines
or echo wrappers. Those are not driver helper exceptions and can be denied by the native allowlist.
On a denied/unavailable helper, stop with no plan edit, synthetic digest, manual acceptance or
repair review. The validator's successful stdout, not a user's description of a supplied report,
is the correction precondition. Do not relax permissions or change native configuration to continue.

These exceptions permit no arbitrary shell, project scripts, tests/gates, settings changes or edits
by helpers. `scripts/consult.py` and `packet` are permitted only for the selected chain stage 2 and
authorized disclosure.

## Self-contained external consultation

This skill's bundled adapter is independent at runtime: do not load/import/read another skill to
consult. The route is one native CLI process, never a direct-CLI fallback. The existing-peer route
below is a separately selected stage-2 transport, never a fallback for this one or the reverse.

The bundled adapter uses Python 3 standard library and POSIX process groups (macOS/Linux);
synthetic native-control tests require Python 3.11+ for tomllib. Neither helper installs dependencies.

```sh
python3 "<skill-dir>/scripts/consult.py" --target claude|codex \
  --project "<actual-project-dir>" --timeout 600 [--check]
```

Replace placeholders, choose the other provider from actual author metadata and retain the approved
timeout budget; there is no `--mode`, model/effort override, passthrough, retry or fallback. Normal
request: nonempty finite UTF-8 stdin ending at EOF (at most 4 MiB). The positive timeout covers input,
capability inspection and the single request. `--check` consumes no input and requests no model:
preflight success proves controls were discovered, not auth/capacity/source access or completed review.

Stdout is a JSON envelope with `status` (`ok|unavailable|error|timeout`), `target`, `route_source`,
`model` (observed runtime string or null), `result` (exact final text or null), `error`, `check` and
`consultation_completed`. Accept only ok + check=false + consultation_completed=true + nonempty
result, then validate the inner JSON via review_state.py. Never treat transport success as approval.
Exit 0 can be preflight or completed consultation; unavailable/error is nonzero, timeout is 124,
argument errors are 2. Failed/empty/malformed/incomplete/stale reports stop without relaunch.

### Trusted native deployment, not a whole-process sandbox

Use only an already installed trusted CLI environment compatible with existing permissions.
Native auth/credential refresh, launchers, logs/cache/network and administrative policy effects
are outside the model-tool restriction. Evidence travels through native provider/auth: disclose
only approved evidence, never secrets merely because tools are read-only. Unknown/incompatible
deployment stops; no alternate auth directory, install, setting change or bypass.

- **Claude:** safe mode preserves native auth/model/permissions while suppressing ordinary
  instructions, skills/plugins/hooks/agents/MCP/LSP/memory. Managed hooks, status-line/file-suggestion
  commands and policy helpers can still run; non-managed disableAllHooks cannot disable them.
  This is a model-tool boundary, not an OS sandbox or proof of zero startup side effects.
  The adapter restricts availability to Read/Grep/Glob (`--tools`, not merely `--allowedTools`),
  strict empty MCP and mcp__* denial, dontAsk/no permission prompts, no Chrome/skills/commands/session
  persistence, ordinary hooks disabled and empty fallback chain. Invocation-local controls suppress
  ordinary background/advisor/memory/IDE/update and API retry/watchdog work without replacing native
  model/effort/auth. Installed help and live init tools are checked; only Read/Grep/Glob plus a
  non-actionable EndConversation are allowed. Prohibited calls/retry events/incomplete results fail.
  Controls were researched on Claude Code 2.1.296; unsupported observable contracts fail closed.
- **Codex:** no release is pinned; sources were researched on codex-cli 0.162.1. The native CLI
  silently ignores unknown `-c` keys and feature names, so a build is accepted only when it passes
  local checks: required `exec --help` flags; `codex features list` with the exact overrides lists
  each disabled feature once, at an applied stage and `false`; each plain key probed alone with a
  wrongly typed value fails config loading with exit 1 and the `invalid type`/`unknown variant`
  diagnostic for that exact key path (success means ignored; any other failure proves nothing).
  A failed check is unavailable, never a fallback. Native exec uses read-only sandbox, JSON, ephemeral, ignore-rules and strict-config. Invocation
  overrides forbid approval escalation/web search/login shell; suppress ordinary docs/skill autoload,
  notification commands, hooks/apps/plugins/remote plugins/multi-agent/code-mode/shell snapshots/goals/
  memories/skill MCP dependency installation. Native MCP inventory is used to disable every inherited
  server via one complete TOML-value table preserving exact names/transport fields; inventory again
  refuses remaining enabled servers. It never prints inventory credentials or changes native config.
  Authentication/profile/model/effort and usual trusted project/Git prerequisite remain native.
  Source search uses sandboxed read-only shell, not Claude built-ins; the packet forbids tests,
  project execution/helpers/nesting/arbitrary commands and permits only the inspection fallback.
  That instruction is not an enforced shell allowlist; inherited MCP/hooks are not OS-sandboxed.
  Observed MCP/web/write/collaboration events, model-reroute notices and incomplete/error turns fail.
  Native provider transport retries may occur; the adapter itself invokes consultation only once.

Finite stdin, bounded output/diagnostics and direct argv (no shell=True) constrain lifecycle. On
timeout/interruption/protocol failure/exit the adapter attempts bounded POSIX group TERM/KILL cleanup
and reaps its child. Unresolved cleanup is a separate error and cannot accept success; escaped groups
are outside this boundary. Do not claim every descendant stopped or the CLI had no state effects.
Native model is unknown unless the stream exposes it; configured model/effort is not observed identity.
Source controls adapted locally from the repository's native consultation implementation with its
attribution/license retained; consult.py has no runtime dependency on ask-other or peer-chat.

## Existing peer route (chain stage 2)

Selected only by the rule in `sections/chain.md`. The driver uses the available peer-chat skill by its
own contract (doctor, then send) and never imports, copies or reads that skill's bundled files. No
peer-chat skill, refused doctor or refused send makes the stage unavailable; the consult route does
not need peer-chat at all.

```sh
python3 "<skill-dir>/scripts/review_state.py" packet "<plan>"   # brief on finite stdin
```

`packet` reads the nonempty UTF-8 brief to EOF (same limits as validate), snapshots the plan, writes
`{plan_path, plan_version, plan_text, brief, request_id}` once to `packet.json` in a fresh 0700 temp
directory (file 0600, exclusive create) and prints `request_id`, `plan_path`, `plan_version` and
`packet_path`. The random `request_id` ties a reply to this packet; a digest alone cannot tell a late
reply to an earlier packet of the same bytes from the pending one. A temp path
with whitespace, which peer-chat would alter, fails. On failure it removes only its unfinished
artifacts and prints no success. This packet is the only artifact besides the target plan the
driver may create; keep it unchanged until the reply is handled. The peer reads the packet, not the
mutable plan; a packet unreadable from the peer's workspace means unavailable.

The brief carries everything the CLI packet would except the snapshot, which only the helper takes:
worker branch and canonical schema, original requirement, settled decisions, rules packet with
provenance, prior findings and factual change list, approved evidence paths and restrictions.
Shortening the outgoing chat message never drops them.

**Peer worker exception.** The peer applies the worker branch with its own read tools and may run
peer-chat doctor plus exactly one send to the driver, nothing else: no further consultations, writes,
helpers or tests. Read-only is requested by the brief, not enforced. The reply is the canonical object
on one line, preceded by the packet's `request_id` and one space. peer-chat collapses every whitespace
run into one space, so inside string values write newlines, tabs and carriage returns as JSON
escapes, any non-ASCII whitespace as `\uXXXX`, and each space of a run of two or more spaces as
`\u0020`; single spaces survive unchanged. If the packet
cannot be read or reviewed, the peer sends a plain failure message with the `request_id` instead of
inventing a verdict.

The driver strips only the incoming transport label and pipes the rest unchanged to `validate
--request-id <pending id>`; never re-encode, unescape or repair it. The helper requires the exact id,
one space, then the report. A reply rejected for a missing or foreign id is not this pass's report:
report it, accept and start nothing. Any other rejection is a failed stage like any other.
