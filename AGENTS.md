# Repository Guidelines

Personal skills for Claude Code (plugin marketplace), omp (compatible plugin skill directories), and
native Codex CLI (the separate `codex/` tree via skills.sh).

## Layout

```
.claude-plugin/marketplace.json     # marketplace "semsemyonoff", one entry per plugin
plugins/<plugin>/
  .claude-plugin/plugin.json        # name, description, version
  CHANGELOG.md
  commands/<command>.md             # optional thin aliases: /<plugin>:<command>
  skills/<skill>/
    SKILL.md                        # thin core: triggers, rules, index of sections
    sections/*.md                   # scenarios, read only when the situation applies
    references/*.md                 # conventions, API gotchas, templates
    scripts/                        # deterministic helpers (lookups, builders, validators)
codex/<skill>/                      # Codex-only skills, installed via skills.sh subpath
scripts/check.py                    # repo validation, run locally and in CI
```

Plugins are grouped by theme (`planning`, `flow`, `vikunja`, `redmine`, `retro`, `gdocs`, `peer`). Which plugins a
given Claude setup enables is up to whoever installs them; nothing in this repo assumes a particular
setup, so keep machine- and account-specific details out of it.

Claude gets the plugin workflows; omp can load harness-compatible skills from their plugin skill
directories (currently `brainstorm`, `planning`, `plan-review`, `orchestrate`, `reflection`, and `vikunja`).
A Codex model running inside omp uses omp's tools and session format, not native Codex CLI's.
Native Codex CLI gets only `codex/`:
skills for its role as a second opinion — code analysis, review, architecture — plus peer-chat.
skills.sh reads `marketplace.json` and would expose plugin skills, so native Codex installs use:
`npx skills add semsemyonoff/agent-skills/codex -a codex -g`.

## Writing skills

Draft and tune Claude skills with the official `skill-creator` (installed from `claude-plugins-official`):
it runs evals and optimizes the description for triggering — do that step for every skill, bilingual
triggers are the fragile part. Keep eval cases in `plugins/<plugin>/evals/` so `claude plugin eval`
can run them. For `codex/` skills follow Codex's built-in `skill-creator` (incl. `agents/openai.yaml`).

- Write skills in English. Users prompt in Russian and English: descriptions carry trigger phrases in
  both languages, and the skill answers in the user's language.
- `name` equals the directory name, lowercase kebab-case, no prefix — the plugin namespaces it.
- `description` says when to trigger and, when useful, when not to.
- Keep `SKILL.md` short (aim for ≤200 lines). Move scenarios to `sections/` and point to them from an
  index ("read `sections/backlog.md` when creating a task").
- Paths inside a skill are relative to its directory. Never reference `~/.claude/skills`,
  `~/.claude/plugins` or a home directory: plugins run from a cache dir, Codex from `~/.agents/skills`.
  Resolve bundled scripts and references from the directory of the loaded `SKILL.md`.
  Claude-only adapters may use `"${CLAUDE_SKILL_DIR}/scripts/<script>"` (Claude Code substitutes it);
  shared instructions and omp adapters must not require that variable. Keep model routing in each
  harness's native configuration, not in a shared skill-specific settings file.
- A skill is self-contained: no dependency on another skill's files. Duplicate a small piece rather
  than couple two skills.
- Keep portable planning rules outside skills: first nonempty project `.agents/<name>-rules.md`,
  then `.claude/<name>-rules.md`, then XDG `agent-skills/<name>-rules.md`; never merge or embed
  personal rules. Include upstream MIT copyright/license in each separately distributed adapted
  skill directory. Native agent resources are optional files, not automatic installations.
- Anything deterministic (resolving ids, building markup, parsing transcripts) goes to `scripts/`;
  the model interprets results. Scripts use only the standard library of Python 3 or POSIX shell.
- Writes to external systems (trackers, forges) happen only after explicit user confirmation unless
  the user asked for that exact action.

## Versioning

Bump `version` in the plugin's `plugin.json` on every user-visible change and add a line to its
`CHANGELOG.md`. Versions are per plugin, not per repo.

## Checks

```sh
python3 scripts/check.py          # manifests, frontmatter, paths, links
claude plugin validate .          # marketplace + plugin schema (needs Claude Code)
shellcheck $(git ls-files '*.sh')
# script tests: python3 -m unittest in every dir with test_*.py
```

CI (`.github/workflows/check.yml`) runs the same on Forgejo Actions and on the GitHub mirror.

Before merging a skill, test it by hand in each supported harness: explicit invocation
(`/<plugin>:<skill>` in Claude, `/skill:<skill>` in omp) and a natural prompt in Russian and in
English that should trigger it. Exercise capability-unavailable paths without pretending they ran.
`claude plugin details <plugin>@semsemyonoff` shows the always-on token cost — keep it small.

## Commits

Short imperative messages in English stating the essence, scoped to one plugin or one repo-level
change. No file lists.
