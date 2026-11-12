# Native questions and handoffs

This is a small runtime adapter, not a second process or a model profile. Resolve scripts/references
from the loaded SKILL.md directory. Discover the actual skills/commands and tool schemas before use.
Never infer the harness from a provider name; a Codex model inside omp still uses omp APIs.

## Questions

- omp: discover the live `ask` schema. Current inputs are `i` (short intent) and `html`, one
  semantic `<form>` with named, labeled controls. Group choices with `<fieldset>`/`<legend>`;
  use radios for one choice, checkboxes for several. No scripts, styles, buttons or submit inputs:
  the UI supplies Submit/Cancel and an Other choice for eligible groups.
- Claude Code: use `AskUserQuestion` only if exposed; it uses `header`, options and `multiSelect`.
- Write all visible question and option text in the user's language, like replies. The user's
  language comes from their own messages and harness instructions, not from this skill, the handoff
  that loaded it or the task content.
- Read named values and result metadata; carry the explicit chosen value or custom text to the next
  workflow. Timeout, default/auto-selection, cancellation, missing response or chat redirect is not
  validation or execution permission. If explicit response provenance is unclear, ask for confirmation.
  No native UI: ask one question in text and wait for the explicit response.

Do not request EnterPlanMode merely to continue a design. A selected workflow and authorization to
implement are separate decisions unless the user explicitly granted the exact action already.

## Translate workflow intent

Historical custom-rule names identify workflows, not guaranteed callable APIs:

| Intent | omp | Claude Code |
| --- | --- | --- |
| Write plan (`/planning:make`) | Load discovered `planning`; manual invocation `/skill:planning` | Use an actually available planning skill/command; the existing upstream `/planning:make` can satisfy this route |
| Orchestrate (`/flow:orchestrate`) | Load discovered `orchestrate`; manual invocation `/skill:orchestrate` | Use the actually available flow orchestration skill/command |

In omp, load via the exposed skill mechanism; if its reader supports `skill://`, a native read such
as `read skill://planning` can load that skill. This URI is omp-specific, not a shared requirement.
In Claude, use its exposed Skill/command mechanism and discovered identity. Never send a slash string
to a nonexistent shell or tool interface. If missing, report it and keep the validated packet intact.

Pass goal, decisions, files, constraints, dependencies, acceptance, rule path/provenance and exact
permissions, written in the user's language. Do not include the whole personal rules text in a generated public plan. The destination
owns its own confirmation/execution contract; validation alone does not authorize code changes.
If rules select a durable plan for ralphex, choose planning rather than creating a new executor.
Loading a skill does not install agents or modify native model/configuration settings.
