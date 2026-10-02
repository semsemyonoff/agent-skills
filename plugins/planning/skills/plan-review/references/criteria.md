# One-pass review criteria

Read the actual plan, original request/validated design, selected planning rules and relevant source.
A finding needs a specific plan section, evidence, consumer/execution impact and minimal correction.
Unknowns are not findings. Do not edit the plan or run its commands to prove a review point.

1. **Real solution:** the chosen approach solves the requested behavior rather than a nearby symptom.
   Check assumptions, data flow, boundaries and relevant failure cases against repository evidence.
2. **Completeness:** every explicit requirement/acceptance criterion has an achievable plan outcome;
   prerequisite information is not silently dropped, stubbed or hidden as an unspecified follow-up.
3. **Scope and dependencies:** exact files/actions and protected areas are coherent. Tasks consume
   inputs already established by preceding work; no impossible ordering or unapproved outward action.
4. **Proportionate design:** reuse existing conventions. Flag unnecessary abstraction/frameworks or
   speculative compatibility only when evidence shows they are not needed for the actual problem.
5. **Runnable verification:** real named commands and cwd/service context, grounded in repository
   declarations. Test behavioral contracts/boundaries where needed, not every function or wording.
   Distinguish targeted task gates from final acceptance and genuine runtime smoke requirements.
   Missing tool/fixture/service prerequisites are explicit, not pretended passing checks.
6. **Loaded rules:** evaluate the actually selected first-nonempty planning rules, not a remembered
   personal profile. If they designate ralphex, fast targeted Validation Commands must not rerun full
   suites/e2e/coverage after every task; final verification includes applicable full checks and lint.
   Archival is the executor's reviews/finalize responsibility, not a premature move-plan checkbox.
   Long research notes belong in the specified notes subdirectory, not the runnable plans inventory.
7. **Conditional project constraints:** evaluate only restrictions from the loaded rules when their
   own stated conditions are confirmed. Do not infer applicability from the project's name or a
   remembered profile. Report unestablished conditions as unknown, not checked.

No automatic opus/Pro/Astra requirement, exact upstream make.md headings, fixed checkbox count,
universal backwards compatibility, tests for every touched function, or mandatory CLAUDE.md.
Reasonable existing abstractions, necessary test infrastructure and inherent problem complexity
are not overengineering merely because the reviewer prefers a different style.

Report only prioritized proven issues. A clean pass is a concise APPROVE plus checked scope/limits;
a blocked or materially flawed plan is NEEDS REVISION with concrete corrections or prerequisites.
The reviewer does not implement fixes, invoke another reviewer, or start a retry loop. Its verdict
covers only the examined text; later driver corrections and unresolved choices are reported separately,
not promoted to independent approval of the revised plan.
