# #596: opt-in bounded plan-review chain

## Goal, placement and execution owner

Implement the approved comment #396 contract as `plan-review/sections/chain.md`, not a new skill,
recursive worker or executable approval loop. The user selected **Orchestrate, then Start** for this
session. The coordinator owns integration, independent review, verification and bounded live runs;
disjoint native implementation workers own core, runtime and eval slices. This explicit approved
one-session route supersedes incompatible ralphex execution for this task. This notes artifact is
the concrete real-plan review target, not an automatic executor launch or archival instruction.
Selected planning-rule provenance is retained in the session; personal rules are not copied here.

## Original acceptance and fixed decisions

- Decide placement/verdict, or reject with reasons. Selected verdict: implement the section placement
  above because it keeps default and worker behavior one-pass while disclosing extra driver policy
  only on opt-in. This is the implementation decision, not independent reviewer approval.
- If implemented, run behavioral evals in **Claude Code and omp**, and one real plan run. Use this
  plan for a real bounded chain in each harness, maximum three reviewer attempts per harness.
- Default exactly one fresh independent native pass. Opt-in: native -> one other-provider request
  -> conditional fresh native if blockers/blocking unknowns or material revisions remain; never
  retry, vote, recursively drive reviews, resume an old context or approve stale text.
- Canonical JSON contains verdict, original absolute plan_path, exact UTF-8 SHA-256 plan_version,
  findings (severity/section/evidence/impact/fix) and unknowns (blocking/detail). APPROVE forbids
  blockers/blocking unknowns; NEEDS REVISION requires one. Invalid/failed/empty/stale reports stop.
- Fresh snapshots accompany full original requirement, settled decisions, rules/evidence and factual
  prior findings/change list. Read-only reviewers never fix, run helpers/tests or spawn others.
- Explicit review-only/no-edits/no-external dominates rules. Only safe evidenced target-plan fixes
  are automatic; product/architecture/conflict/scope/route/budget decisions and unapproved disclosure
  require a real answer. Timeout/default/silence is not consent.
- Preserve native model/effort/auth; unavailable routes stay truthful. External runtime is bundled
  and self-contained, with trusted deployment limits and no direct-CLI/provider/peer fallback.
  Preserve the conditional read-only search/list shell fallback. No ask-other or peer-chat changes.

## Implementation outcomes and dependencies

1. **Core and handoff (ReviewCore).** Update plan-review SKILL.md, references/runtime.md/rules.md/
   criteria.md, agents/omp.md; create sections/chain.md. Update planning SKILL.md/runtime handoff,
   plugin.json and CHANGELOG.md to 1.1.0. Keep user-facing review core under 200 lines. Acceptance:
   default/opt-in/worker authority and reporting are consistent, with no unbounded or stale approval.
2. **Bundled runtime (ReviewRuntime).** Add plan-review/scripts/review_state.py, consult.py and
   behavioral test modules. Reuse only needed established native controls with attribution/license;
   no other-skill runtime reads/imports. Acceptance: snapshot is exact/read-only; validate rejects
   bad schema/path/digest/verdict; consult performs one bounded native request, finite stdin,
   truthful envelope and fail-closed capability/result/cleanup checks. Depends on fixed schema above.
3. **Behavioral evaluation (ReviewEvals).** Add plugins/planning/evals/plan-review/evals.json,
   trigger-evals.json, fixtures and deterministic runner. Six meaningful bilingual behavior cases
   per harness, current versus preserved baseline (24 sessions total); 20 RU/EN trigger cases with
   near negatives. Acceptance: observe permission/pass/version/failure transitions, not instruction
   source-string matching; injected history never claims real external success. Depends on core/runtime.
4. **Stable verification and independent review (coordinator).** After all slices land, reconcile
   CLI/report paths, run deterministic checks once, mandatory separate strong native review and
   evidence-grounded permitted corrections. Run behavioral harness evals, official trigger
   optimization using native defaults, and real chains against this target. Preserve original
   findings, per-pass snapshot/route/status, applied changes and final current-version state.
   The separately authorized single supplemental stable-final opinion does not extend either
   real-plan chain's three-attempt ceiling or count as a fourth plan-review pass.

## Verification commands and live prerequisites

Run only by the coordinator in the stable phase, from repository root with Python 3.11+; workers run none:

```sh
python3 -m unittest discover -s plugins/planning/skills/plan-review/scripts -p 'test_review_state.py'
python3 -m unittest discover -s plugins/planning/skills/plan-review/scripts -p 'test_consult.py'
python3 -m unittest discover -s plugins/planning/evals/plan-review -p 'test_run_evals.py'
python3 scripts/check.py
claude plugin validate .
python3 plugins/planning/skills/plan-review/scripts/review_state.py snapshot docs/plans/notes/596-review-chain.md
python3 plugins/planning/skills/plan-review/scripts/consult.py --target claude --project . --timeout 600 --check
python3 plugins/planning/skills/plan-review/scripts/consult.py --target codex --project . --timeout 600 --check
```

Do not rerun the known out-of-scope #615 resolver failures via a broad `test_*.py` discovery.
The runtime owner supplies the two new modules above before verification; never accept an empty
discovery run as their successful execution. No new full-suite/e2e/coverage requirement is invented.

Prepare the isolated behavior matrix using the preserved pre-edit plugin and a NEW absolute output
directory, then run each prepared session once with its actually discovered native tool allowlists:

```sh
python3 plugins/planning/evals/plan-review/run_evals.py \
  --current "$PWD/plugins/planning" --baseline "$BASELINE_PLANNING" \
  --output "$NEW_EVAL_WORKSPACE/iteration-1"
python3 plugins/planning/evals/plan-review/run_evals.py \
  --run "$OMP_SESSION_DIRECTORY" --tools "$DISCOVERED_OMP_TOOLS" --timeout 600
python3 plugins/planning/evals/plan-review/run_evals.py \
  --run "$CLAUDE_SESSION_DIRECTORY" --tools "$DISCOVERED_CLAUDE_TOOLS" \
  --allowed-tools "$DISCOVERED_CLAUDE_ALLOWED_TOOLS" --timeout 600
```

The coordinator binds these variables to the existing baseline, a fresh workspace, matching session
directories from the generated sessions.json and observed tool names. Session commands illustrate
one run per adapter, not permission to rerun a failed session. Execute the full 24-session matrix,
grade actual actions/bytes with the official schema and generate each harness's official viewer;
follow `plugins/planning/evals/plan-review/fixtures/evaluation.md` for grading/viewer and trigger
optimization using native defaults. Injected checkpoint cases do not replace this real plan's live
chains or demonstrate real external consultation/UI consent.

A completed canonical report is fed on finite stdin to `review_state.py validate` with this original
plan path and the exact expected digest from its supplied snapshot; do not replace the digest after
edits to rescue a stale report. Preflight success is not model/auth/independent-review evidence.
The live coordinator uses discovered native dispatch/CLI schemas, not a fabricated agent/model field.
Claude Code 2.1.296 and Codex 0.162.1 were discovered as installed capability prerequisites by the
coordinator; no observed live model is established by that fact. omp availability does not prove an
independent reviewer route. Capture real identity only when exposed, otherwise unknown.

For live chains, grant only this target's safe plan corrections, approved evidence disclosure and
read-only source inspection; allow the driver solely bundled resolver/snapshot/validate/consult plus
native delegation/UI. Workers get no helper/shell except the existing conditional inspection fallback.
Actual trusted native policy/auth/capacity, complete reviewer result and exact current snapshot remain
prerequisites at run time. A missing capability, refusal, timeout or invalid report terminates that
run unresolved without retry or transport substitution; record it rather than weaken acceptance.

## Approval boundaries and protected scope

No mid-flight tests/builds/lint/smoke/formatters/model calls by implementation workers. No commits,
push, tracker writes, installs, configuration/auth edits, nested implementation agents or external
peer messages. #617 migration and historical #615 resolver failure are out of scope. Existing
ask-other/peer-chat remain unchanged. Additional files or scope, product/architecture decisions,
route/budget changes and ungranted outward actions require real user approval. Final delivery must
separate actual deterministic/live evidence from proposed commands and unresolved acceptance gaps;
a self-check or injected checkpoint is not independent review or a real chain run.
