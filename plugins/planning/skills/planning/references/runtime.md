# Native planning adapter

Identify Claude Code or omp from actual tools, not a provider/model. Resolve bundled resources from
the loaded SKILL.md directory. Ordinary planning does not mutate configuration or launch an executor.

## Questions

Use the exposed native ask schema. omp `ask` uses question `id`, options, optional `multi` and
`recommended`; Claude `AskUserQuestion` uses `header` and `multiSelect`. If unavailable, ask one
necessary question in text and wait. Timeouts/defaults/cancellation/redirects are not approval.
No mandatory EnterPlanMode, Skill tool, or shell slash-command API.

## Translate the selected route

- `/planning:make` in historical rules means plan creation. In omp, the discovered `planning` skill
  serves it (`/skill:planning` for manual invocation). Claude may retain its actual upstream command.
- Plan review means one separately delegated read-only review, not the author's consistency check.
  Load the discovered `plan-review` skill with the complete plan/request/rules packet. In omp, a reader
  that supports `skill://` can load `skill://plan-review`; this URI is confined to the omp adapter.
  In Claude, use the real exposed Skill/command mechanism, never an assumed identity.
- `/flow:orchestrate` means the discovered orchestrate workflow (`/skill:orchestrate` manually in omp).
  Pass the full validated design/plan, decisions, files, dependencies, acceptance, rule provenance,
  protected actions and exact permissions. The destination retains its execution approval contract.
- Ralphex is an external execution owner, not a skill implemented here. Present the completed file;
  only provide invocation syntax after reading actual CLI help/schema. Do not run or install it.

A missing chosen skill/agent/tool is an explicit handoff blocker. Preserve the artifact and report the
missing prerequisite; do not install a replacement, fabricate a worker or silently choose a different
route. A loaded rule can constrain which routes are appropriate; changing it needs an explicit user
choice rather than a default button. Creating the plan or selecting review never starts implementation.
