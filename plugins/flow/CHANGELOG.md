# Changelog

## 2.1.0 (Unreleased)

- Separate capability from slice complexity, uncertainty, coupling and failure cost; derive minimum sufficient permitted native model/reasoning profiles and distinguish configured/requested from exposed actual routing.
- Add optional native omp full-editing and independent-review profile resources for light/standard/strong work, with role aliases and precise thinking levels; no live deployment, shared routing config or blanket default-task bypass.
- Preserve already permitted LSP capability across every editing profile; independent review profiles allow only available read-only navigation/diagnostics and prohibit mutating LSP actions, without changing global config or installing servers.
- Preserve supported Claude native selection, public task/eval boundaries, relative-hint versus fixed-reasoning semantics, sharper-brief/authorized escalation and bounded review overhead without paid fallback or quota-savings claims.
- Extend the existing trace checker only for exact discovered profile allowlists, justified default matches and public argument boundaries; align scenario expectations and add deterministic boundary coverage, without a new evaluator or model runs.

## 2.0.1

- Carry validated design/plan decisions, rules, acceptance and execution boundaries into recon without repeating design or treating an artifact as execution approval; preserve an existing execution owner unless the user explicitly selects orchestration.

## 2.0.0

- Replace Claude-specific shared model routing with one recon → plan → approval → autonomous execution → independent verification → report process for Claude Code and omp. Execution pauses per phase only on request; external actions and routing deviations need explicit permission.
- Add small runtime adapters, supported Claude native agent definitions, and cited native setup/override guidance. omp uses its configured scout/sonic/default task/reviewer routes without a task-wire model parameter or embedded private profile.
- Require an actual independent reviewer; missing capabilities cannot become self-verification. Sharpen failing briefs before using only configured or user-approved native escalation routes.
- Keep optional read-only Codex CLI second opinions opt-in and separate from native review; preserve user execpolicy rules and report rejected model/effort choices without a fallback retry.
- Add bilingual trigger evals and portable action-trace behavioral scenarios for both adapters, approval/capability boundaries, independent review, external permissions, and unapproved model switches.
- Discover Claude delegation as exposed `Agent` or `Task`; validate flat and batch omp routes consistently without treating JSON Schema fields as dispatch model overrides.

## 1.1.0

- Optional Codex review of the whole change set, offered at plan confirmation when the Codex CLI is installed. `scripts/codex_review.py` checks availability (CODEX_REVIEW=off disables, CODEX_REVIEW_GUARD gates) and runs `codex exec` read-only on commits since the start plus staged, unstaged and untracked changes, with a process-group timeout and captured artifacts; model/effort come from Codex config or CODEX_MODEL / CODEX_REASONING_EFFORT. Reviewed twice by Codex.

## 1.0.3

- Brainstorm offer and plan confirmation use AskUserQuestion buttons instead of a text question.

## 1.0.2

- Trigger when "Orchestrate" is chosen as the next step of a brainstorm; take the brainstorm design as input.

## 1.0.1

- Plan only after the solution is settled; otherwise propose a brainstorm after recon.

## 1.0.0

- Added the orchestrate skill: recon, plan with per-step model routing (haiku/sonnet/opus), confirmation, delegated execution with the model always set, verification by the orchestrator, short report. References for routing, worker briefs and report templates.
