# Changelog

## 1.1.0

- Optional Codex review of the whole change set, offered at plan confirmation when the Codex CLI is installed; disabled by CODEX_REVIEW=off, gated by CODEX_REVIEW_GUARD; model/effort from Codex config or CODEX_MODEL / CODEX_REASONING_EFFORT.

## 1.0.3

- Brainstorm offer and plan confirmation use AskUserQuestion buttons instead of a text question.

## 1.0.2

- Trigger when "Orchestrate" is chosen as the next step of a brainstorm; take the brainstorm design as input.

## 1.0.1

- Plan only after the solution is settled; otherwise propose a brainstorm after recon.

## 1.0.0

- Added the orchestrate skill: recon, plan with per-step model routing (haiku/sonnet/opus), confirmation, delegated execution with the model always set, verification by the orchestrator, short report. References for routing, worker briefs and report templates.
