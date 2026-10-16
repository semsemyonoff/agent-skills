# Native consultation runtime

Read this before invoking `scripts/consult.py`. Resolve both files from the loaded
skill directory; do not assume an installation location. The helper uses Python 3
standard library only and requires POSIX process groups (macOS/Linux). It never
installs a CLI, changes authentication/configuration, starts a peer, retries a
consultation or silently changes provider/model/effort.

## Trusted deployment prerequisite

Use an already installed, **trusted native CLI environment**. Native authorization,
credential helpers, administrative policy, CLI launchers and the CLI's own
state/cache/network effects are outside this helper's model-tool boundary. They
must be acceptable under the user's existing permissions. The user-approved
boundary is restricted consultant tools plus suppression of normal autoload, **not
zero side effects from the entire CLI process**. There is no attestation flag or
fictional automated proof of this prerequisite.

In particular:

- Claude `--safe-mode` preserves native authentication, model selection and
  permissions. It suppresses ordinary CLAUDE.md, skills, plugins, hooks, commands,
  agents, workflows, MCP, LSP and memory customizations. **Managed hooks, managed
  status-line/file-suggestion commands and a policy helper can still run.**
  Non-managed `disableAllHooks` cannot disable managed hooks. Remote policy can
  change during startup, and a cached policy is not proof of the active policy.
- Codex's read-only shell sandbox does not sandbox inherited MCP services,
  notification commands or lifecycle hooks. The helper disables the documented
  ordinary features, notification command and enumerated MCP servers for its
  invocation. Administrative requirements/cloud policy can constrain those
  overrides; require a compatible trusted deployment rather than bypassing policy.
- CLI authentication can refresh tokens or invoke configured credential helpers;
  ephemeral/no-session-persistence does not prevent all native logs, caches or
  administrative effects. Do not call this an OS sandbox around the whole CLI.
- Model evidence is sent through the existing native provider/auth route. Use only
  evidence the user authorized sharing. Secrets are not made safe by read-only tools.

If the deployment is unknown or incompatible, stop and explain the prerequisite.
Do not replace it with `--bare`, `--restricted`, an alternate auth directory, an
external sandbox, a guessed setting, or permission bypasses.

## Fixed interface

```text
python3 /absolute/loaded/skill/scripts/consult.py \
  --target claude|codex --mode debug|code-review|plan-review \
  --project /absolute/project --timeout 600 [--check]
```

Normal requests receive one selected consultation packet on stdin. Use a closed
file or a finite pipe that reaches EOF. Do not leave an inherited/background input
pipe open; the helper refuses interactive stdin and times out while waiting for EOF.
Input must be nonempty UTF-8, at most 4 MiB. The positive finite timeout (default
600 seconds) covers input collection, capability inspection and the single request.
`--check` does not consume stdin or send any model request.

There are no pass-through arguments, model/effort options, fallback providers,
peer options or permission-bypass flags. Native routing/auth variables and config
remain in place. This is a new process, not a continuation of the author's session;
its native CLI defaults need not equal the author's harness model.

Stdout is one JSON envelope:

```json
{
  "status": "ok",
  "target": "claude",
  "mode": "debug",
  "route_source": "native-cli-configuration",
  "model": "observed-runtime-model-or-null",
  "result": "consultant final text or null",
  "error": null,
  "check": false,
  "consultation_completed": true
}
```

The stable core fields are `status`, `target`, `mode`, `route_source`, `model`,
`result`, `error`. Additional factual fields include `cli_version`, requested
controls, disabled MCP count, `trust_boundary` and, when cleanup cannot be confirmed,
`cleanup_error`. `model` is an observed runtime
string or JSON null, never a guessed model from an argv/config/profile. Codex's
current JSONL examples do not expose a model; null is expected. Neither CLI's
configured reasoning effort is fabricated as an observed runtime value.

`status` is `ok`, `unavailable`, `error` or `timeout`. Exit 0 means either successful
**preflight** or a complete consultation, distinguished by `check` and
`consultation_completed`. Exit 1 means unavailable/error; exit 124 means timeout.
Invalid CLI arguments use argparse's normal exit 2 and usage diagnostics.

- For a request, require `status=ok`, `check=false`,
  `consultation_completed=true` and a nonempty `result` before interpreting it.
- For `--check`, `result=null`, `model=null`, `consultation_completed=false` even
  when `status=ok`. This says the required CLI controls were found, **not** that
  authentication, provider capacity, source access or a review succeeded.
- `unavailable` covers missing/unstartable CLI, unsupported flags/version,
  unconfirmed Codex features or keys and inability to inspect/disable inherited MCP. An existing-neighbor route is not
  implemented by this helper: missing peer never authorizes switching transport.
- Failure, refusal, invalid/truncated/ambiguous JSON, missing final completion,
  empty final text, contradictory runtime capability and provider/auth failures
  produce nonzero errors with no accepted result. No fallback or relaunch occurs.
- Human stderr diagnostics contain helper-owned categories, not raw vendor stderr,
  credentials or captured evidence. Do not interpret a diagnostic as a finding.

## Claude controls

The driver uses `claude --print --safe-mode` with explicit built-in tool availability
`--tools Read,Grep,Glob`. `--allowedTools Read,Grep,Glob` only pre-approves those
reads; **it is not the availability restriction**. Separate MCP controls are
`--strict-mcp-config --mcp-config {"mcpServers":{}} --disallowedTools mcp__*`.
It also uses `dontAsk`, `--permission-prompts none`, no Chrome, no skills/commands,
no session persistence and JSONL/verbose output. Invocation-only settings request
ordinary hooks disabled and an empty fallback chain; no native model/effort is set.

Documented process-local environment controls disable ordinary background work,
advisor access, auto memory/IDE connection, automatic updates and API retry/watchdog
behavior. Model/effort/auth variables are not replaced. Managed policy remains the
trusted prerequisite above.

The helper checks installed help for every required flag and validates the stream's
`system/init` tool list before accepting a result: Read, Grep and Glob must exist,
MCP must be absent and no other actionable tool may be exposed. Current Claude can
retain `EndConversation` when other tools remain; this turn-ending tool is allowed,
not treated as shell/write/nesting capability. A subsequent prohibited tool call,
API-retry event or incomplete/error result is rejected. Runtime detection is not a
retroactive prevention of native startup effects.

Source/help research used Claude Code **2.1.296**. Newer builds must still expose
these flags and the same observable tool/result contract, otherwise the helper
fails closed. The consultant has no Bash, edits/writes, MCP or nested agent tools.
It cannot prepare a Git diff or run checks: the authorized driver supplies the diff
and records its evidence version separately.

## Codex controls

The helper does not pin a Codex release; sources were researched on codex-cli
0.162.1 and 0.163.0. A newer build is accepted only when it passes the same local
checks, so it can still be unavailable. The native CLI silently ignores unknown
`-c` keys and feature names, so no override is trusted by being passed:

- Required flags must appear in `exec --help`.
- `codex features list` with the exact overrides must list each disabled feature
  exactly once, at an applied stage (`stable`, `experimental`, `under development`
  or `deprecated`) and `false`. Native config skips `removed` flags entirely, and an
  unknown stage, duplicate or malformed row is unconfirmed.
- Each plain key is probed alone with a wrongly typed value through
  `codex features list`. A probe that succeeds means the key is ignored. A failed
  probe counts as recognition only as the native config-load exit 1 with the
  `invalid type`/`unknown variant` diagnostic followed by ``in `<exact key path>` ``;
  any other failure (auth, panic, signal, another exit code or key path) is
  unavailable, and diagnostics are never echoed.
  Incomplete process-group cleanup is unavailable in every case. This proves
  recognition, not the effective value: managed policy above the CLI layer remains
  a trusted prerequisite.
- Inherited MCP servers are inventoried and confirmed disabled as described below.

Any unconfirmed control returns unavailable before a model request. None of these
checks is replaced by the read-only sandbox or event rejection: `notify` commands
run outside the sandbox, and a JSONL event reports an action after it happened.

The helper uses `codex exec --sandbox read-only --json --ephemeral --ignore-rules
--strict-config` with invocation-only documented overrides:

- `approval_policy="never"`, `default_permissions=":read-only"` and
  `web_search="disabled"`; no escalation/bypass flags.
- `notify=[]`, `allow_login_shell=false`, `project_doc_max_bytes=0` and
  `skills.include_instructions=false` (suppresses the automatic skill instructions
  block, not a security claim about every possible explicit source read).
- Features disabled: hooks, apps, plugins, remote_plugin, multi_agent,
  multi_agent_v2, code_mode, shell_snapshot, shell_snapshot_v2, goals, memories
  and skill_mcp_dependency_install. `code_mode` is the active code-execution feature
  in this release; the removed `js_repl` switch is a no-op and is not used.
  `memories` is canonical; the obsolete `memory_tool` alias is not added.
- In the same project/native config context, `codex mcp list --json` inventories
  inherited servers. Build one root override whose **TOML value** holds every
  exact native name, for example
  `mcp_servers={"writer"={enabled=false},"team.service"={enabled=false}}`.
  Names can contain `.`, `/`, `:`, `@`, `-` and `_` as well as ASCII letters/numbers.
  The native CLI splits the override's left-hand path literally on dots: quoted
  left-hand path segments are not TOML key syntax and must not be used. Quoted
  names belong inside the parsed right-hand TOML table. Native table merging
  retains inherited transport fields and changes only each server's `enabled`.
  Use one complete table, not repeated root overrides that replace one another
  inside the CLI layer. Inventory again using the exact resulting controls and
  refuse any still-enabled server; an empty map is not assumed to clear inheritance.
  Inventory credentials/transport
  details are captured privately, never printed. Inventory can inspect native
  auth/HTTP capability; it does not invoke a consultant model or an MCP model tool.

Codex config/auth/profile remain native: no `--ignore-user-config`, new CODEX_HOME,
model or effort override. The CLI requires its usual trusted project/Git context;
this helper does not bypass the Git repository check.

**Codex uses sandboxed shell for source read/search**, unlike Claude's built-in
Read/Grep/Glob. The packet expressly forbids tests/builds, project-code execution,
nesting and arbitrary commands. This instruction is not a shell syntax allowlist
or proof that every possible read-only command is harmless. The enforced boundary
is native read-only command execution with no approval escalation and ordinary
external/nested capabilities disabled through the confirmed controls above. The helper rejects observed MCP/web/write/
collaboration events and the native `item.completed` error-item notice
`model rerouted: ...`, even if a subsequent replacement model provides a valid
approval. Other nonfatal configuration/deprecation warnings do not imply rerouting
and remain nonfatal. One completed turn and nonempty final text are required.
The JSONL stream does not prove the entire process was effect-free.
Codex may perform native transport-level retries under its existing provider
configuration; the helper makes one consultation invocation and never retries it.

## Result completeness and source evidence

Debug/plan results remain final text; a complete transport result is not a correct
or independently proven diagnosis. The driver checks scope/evidence and preserves
uncertainties. Proposed commands in findings are not executed checks.

Code-review final text must be the strict JSON contract in `sections/modes.md`:
verdict, nonempty summary, findings, next_steps and optional uncertainties. The
helper rejects missing fields, Markdown fences, duplicate keys, non-finite numbers,
unsupported severity, invalid line/confidence types and approvals with findings.
Located findings must name existing project-relative UTF-8 source files and line
ranges within those files; paths escaping the project are refused. The original
validated JSON string is preserved, not rewritten or repaired. These coordinate
checks cannot prove the claimed failure mechanism: the driver must establish the
finding's source support and that the evidence version is still current. Keep
unlocated concerns in uncertainties rather than invented findings.

## Lifecycle and verification

The helper owns finite stdin and uses direct subprocess argv, never `shell=True`.
It concurrently drains bounded stdout (32 MiB) and stderr (1 MiB), parses JSONL as
it arrives, and attempts to terminate its spawned POSIX process group on timeout,
interruption, protocol failure or exit. Cleanup sends TERM then KILL, including
descendants that ignore TERM even after the group leader exits, and reaps the
directly owned leader. A denied group signal is not silently ignored: only a final
probe showing that the group no longer exists resolves that signaling error.
Otherwise `cleanup_error` reports the unresolved operation/errno separately from
the original provider/auth/interruption diagnostic. Unresolved cleanup can never
accept an otherwise successful consultation; do not claim all descendants stopped.
Group cleanup is bounded and can add a short teardown interval after the request
deadline. A process deliberately escaping the group is not covered; trusted native
deployment remains required. Only process artifacts/native CLI state are intentional;
no source modification is requested.

Permanent synthetic tests are in `scripts/test_consult.py`; no provider/model calls
are made by that suite. Tests require Python **3.11+** for stdlib `tomllib`, used to
exercise the native override value grammar rather than echo expected argv strings.
The helper itself does not import or require `tomllib`. Run from the script directory
with a compatible interpreter's `-m unittest` in the coordinator's stable verification
phase. Fake CLIs exercise successful requests,
preflight without consultation, missing/unsupported capability, native route
preservation, ignored MCP restrictions, malformed/empty/error output, structured
findings/evidence bounds, provider limits, finite stdin, SIGINT/SIGTERM descendant
cleanup, timeout cleanup, stream-auth and nonzero-exit auth/provider diagnostics under
denied cleanup, model reroute versus nonfatal warnings, exact native MCP names,
TOML-value/literal-path parsing with transport-preserving merges, and ordinary
skill/code-mode controls.
A fake-CLI test is not independent review or live CLI enforcement evidence.

## Source references

Flag/help/version research was performed without a model request. References:

- [Claude CLI reference](https://code.claude.com/docs/en/cli-reference): tool
  availability versus allowedTools, safe mode, MCP, permission/ephemeral controls.
- [Claude programmatic mode](https://code.claude.com/docs/en/headless): JSONL init,
  error/final results, auth-preserving versus bare mode and retry events.
- [Claude settings reference](https://code.claude.com/docs/en/settings-reference):
  managed disableAllHooks and fallback chain behavior.
- [Claude managed settings](https://code.claude.com/docs/en/managed-settings) and
  [server-managed settings](https://code.claude.com/docs/en/server-managed-settings):
  startup policy/helper effects and dynamic delivery; local inspection is not proof.
- [Claude environment controls](https://code.claude.com/docs/en/env-vars):
  process-local retry/background/advisor/update controls.
- [Codex noninteractive mode](https://developers.openai.com/codex/noninteractive):
  read-only sandbox, JSONL completion and native auth.
- [Codex config reference](https://developers.openai.com/codex/config-reference),
  [configuration basics](https://developers.openai.com/codex/config-basic),
  [MCP](https://developers.openai.com/codex/mcp),
  [hooks](https://developers.openai.com/codex/hooks) and
  [managed configuration](https://developers.openai.com/codex/enterprise/managed-configuration).
- [Codex 0.162.1 schema](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/core/config.schema.json)
  [MCP listing implementation](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/cli/src/mcp_cmd.rs),
  [feature registry](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/features/src/lib.rs):
  actual feature/key support, code_mode versus removed js_repl, canonical memories,
  native name validation, merged server inventory and `enabled` JSON fields.
- [Codex CLI value parser](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/utils/cli/src/config_override.rs),
  [literal override paths](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/config/src/overrides.rs),
  [table merge](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/config/src/merge.rs)
  and [native loader](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/config/src/loader/mod.rs):
  only the override RHS is TOML; a single root enabled-only overlay preserves exact
  MCP names and inherited transports.

Documentation is evidence of intended behavior, not a substitute for the required
coordinator-owned live read/search/prohibited-action smoke and cross-harness evals.
