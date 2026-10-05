# Changelog

## 0.1.0

- Add the ship skill: bring a plan branch to the base branch in every workspace repo on Forgejo (push, PR, server-side auto-merge when CI is green, wait, sync, branch cleanup, per-repo report, offer to report into Vikunja).
- Deterministic helper `scripts/ship.py` for discovery, push, background wait and safe local sync; CI-failure and conflict scenarios in `sections/`.
- Contract hardening before release: forge identity and base checks, CI race guard, explicit terminal statuses, upfront rebase option, AskUserQuestion-sized confirmation.
