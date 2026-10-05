# Intake: understand a task, then brainstorm or plan

Use when the user points at a task ("посмотри задачу N викунджа, проанализируй, опиши план, что
делегируешь и на кого, начинай после подтверждения", "look at task N and tell me how you'd do it").
This scenario is read-only until the user confirms.

## Steps

1. **Load the task.** `tasks_read` (parameter `task`), then `task_comments_list` for `task`, both with
   `format: "markdown"`. Comments often carry the latest decision, so read them to the end (all pages).
2. **Follow the links.** For every `#N` in the description or comments, and for tasks under
   `related_tasks`, `tasks_read` them (one level deep is usually enough). Note which are done and
   what they decided. Also look at the parent and sibling tasks when the task is a slice of a bigger one.
3. **Look at the code or docs** the task names, only as far as needed to make the plan realistic.
   Do not start implementing.
4. **Analyse.** State what is asked, what is already done or blocked, hidden dependencies, risks,
   and anything the task leaves undecided.
5. **Decide: brainstorm or plan.** A plan comes only after the solution is settled.
   - **Default — brainstorm.** If the approach is not fully decided in the task (open questions,
     several ways to do it, no concrete design), stop after the analysis: give the summary, list the
     decisions that are open, and ask with the harness's structured-choice tool (Claude Code:
     AskUserQuestion; omp: ask) whether to start a brainstorm — options like
     "Brainstorm (Recommended)" / "Plan anyway" / "Stop here". Use buttons when available, a text
     choice only if the harness has no such tool. On "Brainstorm" invoke the available brainstorm
     workflow with the analysis as context. Do not write a plan.
   - **Plan — only for a ready solution.** Go to step 6 only when the task (description plus the
     latest comments) already spells out the solution: what to change, where, and how to verify it,
     with no open design questions. Say in one line why you consider it settled.
   If the user already said what comes next («потом брейншторм», «потом в оркестраторе»), follow that.
6. **Write the plan** (ready solution only), in the user's language:
   - ordered steps, each small enough to verify;
   - for each step who does it: the main session, or a delegated subagent, and on which model
     (a cheaper model for mechanical search or edits, the strongest for design and review). If the
     user named the split, follow it;
   - what will be checked at the end (tests, lint, manual check);
   - open questions that need an answer before starting.
7. **Wait.** Do nothing in the tracker or the repo until the user confirms, unless they said
   "начинай после подтверждения", which means the confirmation is the go signal, not a
   reason to ask twice. Once confirmed, do the work, then use `sections/report.md` to write it up.

## Pitfalls

- Analysing only the description and missing the comment that changed the scope.
- Writing a plan for a task whose solution is still open: brainstorm first.
- A plan without an owner per step: the user asked "who does what", answer it.
- Editing the task, changing status or creating subtasks before the user agreed.
