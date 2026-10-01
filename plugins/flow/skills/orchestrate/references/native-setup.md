# Native setup and overrides (read-only guidance)

This reference explains existing native configuration; it is not an installer or permission to change settings. Keep one shared process in the loaded `SKILL.md`. `SKILL_ROOT` is the resolved directory of that loaded file. Load `references/claude-code.md` or `references/omp.md` for the active runtime, resolving these paths against `SKILL_ROOT`. The plugin's Claude agent files are at `../../agents/flow-research.md`, `../../agents/flow-mechanics.md`, `../../agents/flow-implementation.md`, and `../../agents/flow-review.md`, relative to `SKILL_ROOT`.

Discover loaded capabilities before planning. Inspect relevant non-secret fields only; never open credential stores, print the environment, dump whole settings files, probe credentials, or publish private model-routing profiles. A readable definition/catalog entry is not proof of an available model, permitted spawn, resolved effort, or independent reviewer. Record model/effort as `unknown` unless actually exposed and allowed to be reported. An unknown identity cannot support a claim of exact-model execution.

## Claude Code

**Bundled surface.** The plugin `agents/` directory contains four native Markdown definitions. They use only documented `name`, `description`, `model`, and `tools` frontmatter. See the Claude adapter for category/default mapping. No plugin hooks, MCP servers, permission modes, persistent memory, or hidden settings are added. The allowlists omit both delegation names, `Agent` and `Task`; research has no shell or edit tools. Review permits Bash for approved verification commands, which is not filesystem/network containment. [C1][C3]

**Discover the actual identity.** Plugin subagents have `<plugin>:<name>` scoped identifiers, also shown in @-mention typeahead. Resolve the active plugin prefix and loaded descriptions rather than assuming a bare name or hard-coded scope. `/agents` no longer opens a creation/library wizard in current documentation (v2.1.198+); older installations differ. A plugin manifest's `agents` field can replace the default directory scan. A missing/disabled or unusable independent reviewer is a completion blocker, not an invitation to install one during the run. [C1][C3]

**Discover the actual delegation tool.** Current documentation calls it `Agent`, but an observed Claude Code 2.1.286 print-mode surface exposed `Task` instead while registering all four Flow agents. Use whichever tool the runtime exposes and inspect its genuine schema. Do not declare delegation unavailable solely because `Agent` is absent, assume equivalent optional fields, or invent model/effort/permission parameters. Print-mode `AskUserQuestion` may also be absent; the Claude adapter's explicit text-confirmation fallback applies.

**Native overrides without changing the shared skill.** Claude documents agent-definition priority as managed definitions, `--agents` session definitions, project `.claude/agents/`, user `~/.claude/agents/`, then plugin definitions. Scope collisions, scoped plugin identifiers, and version behavior must be checked against the actual loaded roster: do not assume a same-looking local name changed an explicitly scoped plugin dispatch. A user can supply a native definition at the appropriate scope or a session `--agents` JSON definition; Flow then maps the category to that discovered approved identity. Flow does not create/edit these files or launch a replacement session on its own. [C1]

For a subagent's model, current documented precedence is per-invocation Agent `model`, agent `model` frontmatter, `CLAUDE_CODE_SUBAGENT_MODEL`, then the main conversation's model. A discovered `Task` surface may use equivalent selection only if its actual schema exposes it; do not infer that parameter from the tool name. `inherit` is an explicit frontmatter option. Before v2.1.251 the environment override came first; in v2.1.257+ `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` can force all subagents and disable per-call choices. Relevant alias-family environment mappings and organization `availableModels` restrictions can also alter resolution. Inspect only those fields when needed, never unrelated env/config. Effort can be set in native frontmatter and otherwise inherits the session; actual support depends on model/version. Use only currently supported, permitted invocation fields. [C1][C2]

**Observe instead of assuming.** `/tasks` can show actual worker models and supported explicit effort. An alias/default is a requested selection, not a concrete execution identity. Current docs describe warnings and fallback substitutions for blocked subagent models; do not accept an observed unapproved substitution silently. Keep unavailable metadata `unknown`, stop affected work when a substitution violates the agreed route, and ask for exact approval or an already-approved available route. [C1][C2]

Do not suggest `/model <name>` as a no-write override in an interactive session: it normally saves the selection to user settings. The documented picker `s` action is session-only in current versions, and `--model` is startup-session-only, but neither automatically overrides a custom worker's explicit model. Merely document these mechanisms; do not invoke them or alter definitions/settings during a Flow run. [C2]

## omp

**Bundled surface.** Use native `scout`, `sonic`, omitted default implementation `agent`, and `reviewer`/`security-reviewer`, after confirming discovery and spawn permission. Agent discovery is exact-name first-wins: native project, native user, enabled extension roots, enabled Claude-plugin roots, then bundled agents. Direct `.claude/agents/` is not a native omp agent root. Claude-dialect plugin `model` frontmatter is discarded; the Claude aliases in Flow definitions must never become omp model selectors. [O1][O2]

**Native override mechanisms.** `task.agentModelOverrides[agentName]` overrides native agent frontmatter; role aliases in either source expand through `modelRoles`. Native role assignments belong in `config.yml`, not provider-definition `models.yml`. omp's native default/fallback resolution then supplies remaining selection. The `task` wire has no `model`; normally omit `agent` for implementation. The omitted default can differ under a restricted parent spawn policy. Do not use a hidden eval override to evade this contract. [O1][O2][O3]

Existing configuration layers apply in this order, low to high: built-ins, global active-profile config, process-cwd project config, `--config` overlays, runtime overrides, registered setting environment overrides. `--config` loads an existing one-shot overlay without persisting it; subsequent task dispatch reloads persisted settings while preserving runtime overrides. A user may maintain native agent definitions, `task.agentModelOverrides`, and role mappings without touching `SKILL.md`; Flow only reads the current effective choice. No additional orchestration config or model profile is needed. [O2][O4]

Read-only inspection commands for a user/operator, using the same profile/cwd/overlays as the session:

```bash
omp config path
omp config get task.agentModelOverrides --json
omp config get modelRoles --json
omp config get task.disabledAgents --json
omp config get task.enableEffort --json
omp models --json
```

Inspect these outputs locally and retain only the relevant allowed selection/capability facts. Do not paste the entire role/override records or model catalog into a plan. A separate shell command cannot recover session-only in-memory overrides; use the live roster/tool schema and exposed result metadata for the running session. Catalog availability is not an online credential check; do not run refresh/login/probes just to prepare Flow. Do not use `config set/reset`, role-picker save actions, model presets, provider enablement, or config-file edits. Even explicit single-key config reads can expose unmasked credentials, so never query credential keys. [O3][O4]

**Observe instead of assuming.** Task result/progress metadata and Agent Hub can expose the actual model and thinking level. Hooks, retry fallbacks, and prewalk can change runtime selection. Only exposed model/effort belong in the shared plan/report; leave them unknown when absent. An observed route outside approval is a blocker until explicitly permitted or replaced by an already-approved native route. Effort hints exist only if the current schema exposes them; do not enable settings or invent params. Isolation is also conditional and can perform commits/cherry-picks under branch mode, so do not opt into it without exact permission. [O1][O2]

## Sources

- C1: [Official Claude Code subagents](https://code.claude.com/docs/en/sub-agents.md): scopes, model precedence/force, tool allowlists, current `/agents` behavior, runtime observation.
- C2: [Official Claude Code model configuration](https://code.claude.com/docs/en/model-config.md): aliases, settings/env, restrictions, persistence and session-only selection.
- C3: [Official Claude plugin components](https://code.claude.com/docs/en/plugins/components.md#agents): scoped native definitions, supported/ignored frontmatter, agent scan.
- O1: [Authorized omp task reference](omp://tools/task.md): actual wire, result metadata, isolation, headless workers.
- O2: [Authorized omp task agent discovery](omp://task-agent-discovery.md): discovery/availability, native override priority, role aliases, Claude model-field removal.
- O3: [Authorized omp models reference](omp://models.md): catalogs, role configuration, availability and runtime selection.
- O4: [Authorized omp settings reference](omp://settings.md): layers, read-only CLI, overlays, persistence and credential-read caution.

Sources inspected on 2026-10-01; loaded capabilities and observed results decide what is usable in a particular session. This reference installs nothing and changes no configuration.
