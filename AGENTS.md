# Repository Guidelines

Personal skills for Claude Code (plugin marketplace) and Codex (skills.sh). Master is Forgejo
(`git.horn.semsemyonoff.dev/semsemyonoff/agent-skills`), GitHub is a push mirror; installs come from GitHub.

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

Plugins are grouped by theme (`flow`, `vikunja`, `redmine`, `retro`, `gdocs`, `peer`), not by profile.
Which plugin is enabled in which Claude profile (personal `~/.claude`, work `~/.claude-work`) is decided
in chezmoi, not here — moving a skill between profiles must not rename its command.

Claude gets workflows (personal and work). Codex gets only `codex/`: skills for its role as a second
opinion — code analysis, review, architecture — plus the Codex side of peer-chat. skills.sh reads
`marketplace.json` and would expose plugin skills, so Codex installs use the subpath:
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
  In plugin skills call bundled scripts as `"${CLAUDE_SKILL_DIR}/scripts/<script>"` (Claude Code
  substitutes it); `codex/` skills reference files relative to `SKILL.md`.
- A skill is self-contained: no dependency on another skill's files. Duplicate a small piece rather
  than couple two skills.
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
```

CI (`.github/workflows/check.yml`) runs the same on Forgejo Actions and on the GitHub mirror.

Before merging a skill, test it by hand in the target agent: explicit invocation (`/<plugin>:<skill>`
in Claude) and a natural prompt in Russian and in English that should trigger it.
`claude plugin details <plugin>@semsemyonoff` shows the always-on token cost — keep it small.

## Commits

Short imperative messages in English stating the essence, scoped to one plugin or one repo-level
change. No file lists.
