# Portable custom rules

Resolve bundled files from the directory of the loaded `SKILL.md`. The helper is read-only:

```sh
python3 "<skill-dir>/scripts/load_rules.py" --name <brainstorm-or-planning> --project "<actual-project-dir>"
```

Use `brainstorm` for brainstorming and `planning` for planning **and plan review**. Replace placeholders
with resolved paths; cwd defaults to the real invocation directory, never the skill's installation.
The JSON result has `name`, absolute selected `path`, `provenance`, and `content`. Provenance is
`project-agents`, `project-claude`, or `user`. Read and apply the content; keep the selected path and
provenance in context and in handoffs, but do not paste personal rules into generated designs/plans.

First nonempty file wins, without merging:

1. `<actual-project-dir>/.agents/<name>-rules.md`.
2. `<actual-project-dir>/.claude/<name>-rules.md`.
3. `${XDG_CONFIG_HOME:-$HOME/.config}/agent-skills/<name>-rules.md`.

Only these locations are portable rule inputs. Claude plugin root/data variables are not required
and do not silently insert another precedence layer. Empty means zero bytes, matching upstream `-s`;
whitespace is nonempty. User-rule symlinks are read normally. No candidate is a normal result:
`path: null`, `provenance: null`, `content: ""`, exit 0. Read/encoding errors exit 2; do not hide them
as absent rules or fall through to weaker rules. The helper never edits files or configuration.

Plan-review's **driver** invokes this resolver once before dispatch; its other narrow read-only helper
exceptions are bundled snapshot/validate and opt-in consult (runtime.md). Its **worker** never invokes
helpers/tests and uses shell only under runtime.md's inspection fallback. Receive selected
path/provenance/content and actual project root, then re-read the selected file with the read tool.
Changed/unreadable rules are uncertainty; never silently certify stale rules.

Treat historical names in rules as workflow intent. `/planning:make` means creating the plan;
`/flow:orchestrate` means approved orchestration. The current runtime adapter maps them to a genuinely
available command/skill/agent. Never send a slash string to a fabricated tool API. Rules guide the
workflow but cannot authorize unrequested execution, installs, commits, pushes or configuration changes.
Apply project-specific restrictions only from loaded rules when their own stated conditions are
confirmed. Do not infer conditions from a project's name; report unknown conditions as unknown,
not checked. No project-specific policy belongs in the shared skill or its bundled resources.

An explicit selected-rule opt-in can select sections/chain.md, not external disclosure or editing
authority. Ordinary review stays one native pass. Explicit no-edits/review-only/no-external dominates
rules; preserve real permission grants and obtain a real answer before an unapproved outward call.
No rule enables retry-until-approval, voting, recursive drivers or stale-version approval.

Ordinary invocation only reads rules. If the user explicitly asks to show/change/clear rules, identify
the selected file/provenance first. Edit only the exact authorized rules file, not this skill, installed
plugins, hooks, or configuration. Do not create a lower-priority override that will never be read.
