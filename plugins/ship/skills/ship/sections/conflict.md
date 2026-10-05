# Conflict

## Upfront "Rebase first"

Chosen in the initial confirmation, so it needs no second question. The option was labeled
"Rebase first (force-with-lease push)" for repos already on the remote, so the user knowingly approved
the force push; plain "Rebase first" for unpushed repos. Before the first push, in the
repos where it was chosen: `git fetch origin` (`plan` does not fetch), then `git rebase origin/<base>` on the branch. No force is needed when the branch
is not on the remote yet; if it already is, push with `--force-with-lease` (covered by the labeled approval). If the rebase stops on conflicts, abort it (`git rebase --abort`), report `conflict` for
that repo with the conflicting files and continue with the others.

## Conflict discovered later

Applies when the PR has `mergeable=false` (status `conflict`) after the initial approval.

1. Explain: which repo/PR, which base, and (read-only `git`) which files conflict.
2. Offer to rebase onto `origin/<base>` and push with `git push --force-with-lease`. This rewrites
   remote history and was NOT part of the initial approval: ask for a separate explicit confirmation
   per repo (structured-choice tool or plain text). No confirmation -> leave the repo as `conflict`.
3. Never resolve conflicts silently. Show how each conflict is resolved and get the user's decision
   when the resolution is not mechanical.
4. After the push the auto-merge stays scheduled: re-check the PR and include the repo in a new
   background `ship.py wait`, then continue the normal flow.
