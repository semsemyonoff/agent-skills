# Intake: understand a task and propose a plan

Use when the user points at a task ("посмотри задачу N викунджа, проанализируй, опиши план, что
делегируешь и на кого, начинай после подтверждения", "look at task N and tell me how you'd do it").
This scenario is read-only until the user confirms.

## Steps

1. **Load the task.** `task_get` (parameter `id`), then `comments_list` for `taskId`. Comments often
   carry the latest decision, so read them to the end.
2. **Follow the links.** For every `#N` in the description or comments, and for related tasks in the
   `task_get` output, `task_get` them (one level deep is usually enough). Note which are done and
   what they decided. Also look at the parent or slice siblings when the task is "Срез N из #M".
3. **Look at the code or docs** the task names, only as far as needed to make the plan realistic.
   Do not start implementing.
4. **Analyse.** State what is asked, what is already done or blocked, hidden dependencies, risks,
   and anything the task leaves undecided.
5. **Write the plan** to the user, in their language:
   - ordered steps, each small enough to verify;
   - for each step who does it: the main session, or a delegated subagent, and on which model
     (a cheaper model for mechanical search or edits, the strongest for design and review). If the
     user named the split, follow it;
   - what will be checked at the end (tests, lint, manual check);
   - open questions that need an answer before starting.
6. **Wait.** Do nothing in the tracker or the repo until the user confirms, unless they said
   "начинай после подтверждения", which means the confirmation is the go signal, not a
   reason to ask twice. Once confirmed, do the work, then use `sections/report.md` to write it up.

## Pitfalls

- Analysing only the description and missing the comment that changed the scope.
- A plan without an owner per step: the user asked "who does what", answer it.
- Editing the task, changing status or creating subtasks before the user agreed.
