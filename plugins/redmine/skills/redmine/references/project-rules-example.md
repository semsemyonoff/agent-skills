# Example `.claude/redmine-rules.md`

A project puts this file in its own repository. Everything here is an example; write what is true for
the project. The skill reads it at the start of intake and reply.

```markdown
## Intake
- The spec and requirements are Google Docs linked in the issue description. If they are not yet in
  `docs/local/<topic>/`, import them with the gdoc-import skill first, then compare the issue with them.
- The contract with the client is `docs/local/contract.md`; flag anything the issue asks that it does not cover.
- The staging site can be inspected read-only over ssh (`ssh stage`), database queries SELECT only.

## Reply
- Drafts live in `docs/local/<topic>/<issue-id>-drafts.md`.
- Estimates always include a separate line for testing on staging.
```
