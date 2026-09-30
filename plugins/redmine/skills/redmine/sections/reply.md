# Reply: draft, check, send

Use when writing anything to an issue: a comment or reply, a description change, a status or
assignee change.

## Steps

1. **Read.** If an intake already ran in this session, reuse its summary. Otherwise `get_redmine_issue`
   with the journal: description, all comments, current status and assignee. Fetch attachments only when
   the question depends on them. Note who asked what and which questions are still unanswered.
2. **Draft into a file.** `<issue-id>-drafts.md` where the project rules say; otherwise follow an existing
   `*-drafts.md` in the project, or ask. Layout: `# <id> — черновики`, then one
   `##` section per comment titled with its status (`черновик, не опубликован` / `опубликован <date>, journal <id>`),
   the Textile body inside a ```textile fence. Edit the current draft in place while iterating; after
   sending, mark the section published and start a new section for the next comment.
   Style and structure: `sections/style.md`.
3. **Lint.** `python3 "${CLAUDE_SKILL_DIR}/scripts/textile_check.py" <file>` and fix every finding. It only
   checks the fenced Textile blocks of a drafts file (or the whole file if it has no fences).
4. **Fact-check.** Always, before showing the draft as final. Follow `sections/factcheck.md`: a separate
   subagent that did not write the draft verifies every factual claim. Fix what it reports, then show the user
   the final draft (the Textile text itself, not a summary).
5. **Wait.** Iterate with the user on wording. Each substantive change to a claim re-triggers the fact-check
   for that claim.
6. **Send** only after explicit approval. Read `sections/send.md` for status/assignee resolution and the
   confirmation format.
