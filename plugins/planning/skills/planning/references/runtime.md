# Native planning adapter

Identify Claude Code or omp from actual tools, not a provider/model. Resolve bundled resources from
the loaded SKILL.md directory. Ordinary planning does not mutate configuration or launch an executor.

## Questions

Discover the exposed native ask schema before use. In omp, current `ask` takes `i` (short intent)
and `html`: one semantic `<form>` with named, labeled controls; group choices with
`<fieldset>`/`<legend>`, using radios for one choice and checkboxes for several. No scripts, styles,
buttons or submit inputs; the UI supplies Submit/Cancel and an Other choice for eligible groups.
Write visible text in the user's language. Claude `AskUserQuestion`, when exposed, uses its own
actual schema (`header` and `multiSelect`), not omp HTML.

Read the returned named values and result metadata. Pass the explicit chosen value or custom text
to the selected next workflow, with the original decisions and exact permissions. Timeout,
automatic default, cancellation, redirect, silence or missing answer is not approval; if explicit
response provenance is unclear, ask for confirmation. If UI is unavailable, ask the necessary
question in text and wait for a real answer. No mandatory EnterPlanMode, Skill tool, or shell
slash-command API.

## Translate the selected route

- `/planning:make` in historical rules means plan creation. In omp, the discovered `planning` skill
  serves it (`/skill:planning` for manual invocation). Claude may retain its actual upstream command.
- Plan review means one separately delegated read-only native review by default, not author
  consistency checking. Load discovered plan-review with plan/request/decisions/rules/evidence and
  exact permissions, including no-edits/review-only/no-external. Carry explicit chain selection or
  selected-rule opt-in to its sections/chain.md; maximum three attempts, no retries/voting/recursion.
  Each reviewer receives a fresh exact snapshot and returns version-bound canonical JSON. The
  driver alone applies target-plan evidenced unambiguous corrections; architecture/product/conflict/
  scope/route/budget decisions need options and a real answer. Rules do not grant external disclosure;
  ask before required unapproved outward calls. Preserve verdict/version, changes and unresolved
  state; no stale approval or automatic implementation. In omp, an exposed reader may load
  skill://plan-review; Claude uses its real Skill/command mechanism, never an assumed identity.
- `/flow:orchestrate` means the discovered orchestrate workflow (`/skill:orchestrate` manually in omp).
  Pass the full validated design/plan, decisions, files, dependencies, acceptance, rule provenance,
  protected actions and exact permissions. The destination retains its execution approval contract.
- Ralphex is an external execution owner, not a skill implemented here. Present the completed file;
  only provide invocation syntax after reading actual CLI help/schema. Do not run or install it.

A missing chosen skill/agent/tool is an explicit handoff blocker. Preserve the artifact and report the
missing prerequisite; do not install a replacement, fabricate a worker or silently choose a different
route. A loaded rule can constrain which routes are appropriate; changing it needs an explicit user
choice rather than a default button. Creating the plan or selecting review never starts implementation.
