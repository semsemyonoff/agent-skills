# Native setup and overrides (read-only guidance)

This reference explains existing native configuration; it is not an installer or permission to change settings. Keep one shared process in the loaded `SKILL.md`. `SKILL_ROOT` is the resolved directory of that loaded file. Load `references/claude-code.md` or `references/omp.md` for the active runtime, resolving these paths against `SKILL_ROOT`. The plugin's Claude agent files are at `../../agents/flow-research.md`, `../../agents/flow-mechanics.md`, `../../agents/flow-implementation.md`, and `../../agents/flow-review.md`, relative to `SKILL_ROOT`.

Discover capabilities and complexity-appropriate profiles before planning. Inspect relevant non-secret fields only; never read credentials, dump whole settings/environment or publish private routing profiles. Record accessible configured/requested model and reasoning separately from actual execution. A readable definition/catalog is not proof of deployment, allowed spawn or resolved actual identity; missing actual metadata stays unknown, but known configuration must not be hidden behind that label.

## Claude Code

**Bundled surface.** The plugin `agents/` directory contains four native Markdown definitions. They use only documented `name`, `description`, `model`, and `tools` frontmatter. See the Claude adapter for category/default mapping. No plugin hooks, MCP servers, permission modes, persistent memory, or hidden settings are added. The allowlists omit both delegation names, `Agent` and `Task`; research has no shell or edit tools. Review permits Bash for approved verification commands, which is not filesystem/network containment. [C1][C3]

**Discover the actual identity.** Plugin subagents have `<plugin>:<name>` scoped identifiers, also shown in @-mention typeahead. Resolve the active plugin prefix and loaded descriptions rather than assuming a bare name or hard-coded scope. `/agents` no longer opens a creation/library wizard in current documentation (v2.1.198+); older installations differ. A plugin manifest's `agents` field can replace the default directory scan. A missing/disabled or unusable independent reviewer is a completion blocker, not an invitation to install one during the run. [C1][C3]

**Discover the actual delegation tool.** Current documentation calls it `Agent`, but an observed Claude Code 2.1.286 print-mode surface exposed `Task` instead while registering all four Flow agents. Use whichever tool the runtime exposes and inspect its genuine schema. Do not declare delegation unavailable solely because `Agent` is absent, assume equivalent optional fields, or invent model/effort/permission parameters. Print-mode `AskUserQuestion` may also be absent; the Claude adapter's explicit text-confirmation fallback applies.

**Native overrides without changing the shared skill.** Claude documents agent-definition priority as managed definitions, `--agents` session definitions, project `.claude/agents/`, user `~/.claude/agents/`, then plugin definitions. Scope collisions, scoped plugin identifiers, and version behavior must be checked against the actual loaded roster: do not assume a same-looking local name changed an explicitly scoped plugin dispatch. A user can supply a native definition at the appropriate scope or a session `--agents` JSON definition; Flow then maps the category to that discovered approved identity. Flow does not create/edit these files or launch a replacement session on its own. [C1]

For a subagent's model, current documented precedence is per-invocation Agent `model`, agent `model` frontmatter, `CLAUDE_CODE_SUBAGENT_MODEL`, then the main conversation's model. A discovered `Task` surface may use equivalent selection only if its actual schema exposes it; do not infer that parameter from the tool name. `inherit` is an explicit frontmatter option. Before v2.1.251 the environment override came first; in v2.1.257+ `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` can force all subagents and disable per-call choices. Relevant alias-family environment mappings and organization `availableModels` restrictions can also alter resolution. Inspect only those fields when needed, never unrelated env/config. Effort can be set in native frontmatter and otherwise inherits the session; actual support depends on model/version. Use only currently supported, permitted invocation fields. [C1][C2]

**Observe instead of assuming.** `/tasks` can show actual worker models and supported explicit effort. An alias/default is a requested selection, not a concrete execution identity. Current docs describe warnings and fallback substitutions for blocked subagent models; do not accept an observed unapproved substitution silently. Keep unavailable metadata `unknown`, stop affected work when a substitution violates the agreed route, and ask for exact approval or an already-approved available route. [C1][C2]

Do not suggest `/model <name>` as a no-write override in an interactive session: it normally saves the selection to user settings. The documented picker `s` action is session-only in current versions, and `--model` is startup-session-only, but neither automatically overrides a custom worker's explicit model. Merely document these mechanisms; do not invoke them or alter definitions/settings during a Flow run. [C2]

## omp

**Capability and budget are separate.** Keep `scout` for source research and `sonic` for exact mechanics only when its effective pair matches the permitted policy. For implementation, select a discovered full editing profile by assessed complexity instead of automatically omitting agent. For review, select a separate risk-appropriate read/verification profile or approved security specialist. Agent discovery is exact-name first-wins: project, user, enabled extensions/plugins, bundled agents. Claude-dialect plugin model fields are discarded, so the Claude agent files are not native omp profile selectors. [O1][O2]

**Native model priority.** When exposed by the live schema, an explicit task-item `model` selector
precedes `task.agentModelOverrides[agentName]`, native agent model frontmatter and the configured
task/session fallback. Role aliases expand through `modelRoles` in native `config.yml`, not
provider-definition `models.yml`. Batch `model` belongs on each `tasks[]` item, never the container.
Current public eval `agent()` and `workpool()` also expose `model`; inspect their own API rather
than copying task fields. A selector may be a string or ordered nonempty array. Every candidate and
known role expansion must be within the assessed authorized policy. Ordered candidates are
preferences, not a closed execution allowlist: native runtime fallbacks can still alter the actual
route, which must be observed and checked. Use `@default` for the live parent model, not ambiguous
`default`/`inherit`; a parent model does not guarantee inherited reasoning. Do not use internal
bridge fields. Generic agent omission remains exceptional: verify its effective default (possibly
changed by parent spawn restrictions), authorized pair and explicit complexity suitability. [O1][O2][O3][O5]

Configuration layers remain built-ins, active-profile global, cwd project, explicit overlays, runtime and registered setting environment overrides. Flow reads effective policy only; it never mutates role/agent overrides between parallel calls or changes live settings to make a route exist. Native definitions and role mappings provide profiles, without a second orchestration.yml. Separate shell inspection cannot recover session-only overrides. [O2][O4]

### Optional native resource contract (deployment is separate)

Resources are under `agents/omp/` relative to the **loaded orchestrate SKILL.md directory**, not the
plugin's Claude `agents/` directory. An operator can expose those files through native omp agent
discovery, for example native project/user agent links. Skills installation alone does not activate
the resources, resolve aliases or authorize paid routes. This reference performs no installation.

| Native resource basename / agent name | Model role alias | Fixed native thinking-level | Capability |
| --- | --- | --- | --- |
| flow-worker-light | @flow_light | medium | Full editing |
| flow-worker-standard | @flow_standard | medium | Same full editing |
| flow-worker-strong | @flow_strong | high | Same full editing |
| flow-review-light | @flow_light | medium | Separate read/verification |
| flow-review-standard | @flow_standard | medium | Same read/verification |
| flow-review-strong | @flow_strong | high | Same read/verification |

Each file is `<basename>.md`. Bind `modelRoles.flow_light`, `modelRoles.flow_standard` and
`modelRoles.flow_strong` to the user's permitted native model selectors. No concrete selectors are
distributed here. The three workers have identical read/grep/glob/edit/write/bash/lsp tools;
reviewers have read/grep/glob/bash/lsp and prohibit source/config writes and mutating LSP actions.
LSP requires actual authorization/enabling/server availability; no server or configuration is promised
or installed by these resources. All profiles have no spawns.
The model roles choose the permitted model; documented `thinking-level` supplies precise reasoning.
Review independence is a different instance/ownership, not a fixed highest profile. A suitable
native security specialist may replace a review profile only with its own assessed permitted pair.

Avoid contradictory thinking suffixes/overrides in those bindings; confirm the effective pair rather
than assuming an inherited default's high selector became medium merely from a profile label.

Verify effective per-agent overrides, ceilings, model support, hooks and authorized fallback policy
before promising a pair; a role entry alone is not paid/escalation permission. Overrides must preserve
the assessed allowed pair or be disclosed and authorized. Keep existing main/default/task/scout/sonic
routes unchanged unless the operator deliberately deploys an approved policy outside this workflow.
Missing required resource/alias or incompatible reasoning support is a prerequisite, not a silent
default-task fallback. Alternative discovered profiles with the same capabilities and permitted pairs
are valid; names alone are not adequacy evidence.

`task.enableEffort` does not select the model. Profiles work with it disabled. If enabled, lo/med/hi
are relative model-supported ladder positions, not literal low/medium/high, and override configured
thinking. Do not send them merely to imitate a precise medium profile. `solutionSpace` is the thinking
classifier input only for auto selectors; it is not a model router or a fixed-profile effort control.
Configured ceilings/fallbacks can clamp reasoning; actual values require exposed runtime metadata.

Read-only inspection commands for a user/operator, using the same profile/cwd/overlays as the session:

```bash
omp config path
omp config get task.agentModelOverrides --json
omp config get modelRoles --json
omp config get task.disabledAgents --json
omp config get task.enableEffort --json
omp config get task.maxEffort --json
omp models --json
```

Inspect these outputs locally and retain only the relevant allowed selection/capability facts. Do not paste the entire role/override records or model catalog into a plan. A separate shell command cannot recover session-only in-memory overrides; use the live roster/tool schema and exposed result metadata for the running session. Catalog availability is not an online credential check; do not run refresh/login/probes just to prepare Flow. Do not use `config set/reset`, role-picker save actions, model presets, provider enablement, or config-file edits. Even explicit single-key config reads can expose unmasked credentials, so never query credential keys. [O3][O4]

**Expected versus actual.** Effective config gives the plan's expected/requested pair; exposed task metadata or Agent Hub can give actual model and reasoning after spawn. Keep these distinct and report unexpected model/effort/fallback substitutions against the selected policy. No hidden enabling of effort hints, providers, profiles, prewalk or settings. Isolation may create commits/cherry-picks and requires exact permission. [O1][O2]

## Sources

- C1: [Official Claude Code subagents](https://code.claude.com/docs/en/sub-agents.md): scopes, model precedence/force, tool allowlists, current `/agents` behavior, runtime observation.
- C2: [Official Claude Code model configuration](https://code.claude.com/docs/en/model-config.md): aliases, settings/env, restrictions, persistence and session-only selection.
- C3: [Official Claude plugin components](https://code.claude.com/docs/en/plugins/components.md#agents): scoped native definitions, supported/ignored frontmatter, agent scan.
- O1: [Authorized omp task reference](omp://tools/task.md): actual wire, result metadata, isolation, headless workers.
- O2: [Authorized omp task agent discovery](omp://task-agent-discovery.md): discovery/availability, native override priority, role aliases, Claude model-field removal.
- O3: [Authorized omp models reference](omp://models.md): catalogs, role configuration, availability and runtime selection.
- O4: [Authorized omp settings reference](omp://settings.md): layers, read-only CLI, overlays, persistence and credential-read caution.
- O5: [Public eval agent/workpool contract](xd://eval/agents): discovered agent and schema-exposed per-call model selection.

Source contracts are version-sensitive; loaded schemas and effective native policy decide what is usable. This reference installs nothing and changes no live settings.
