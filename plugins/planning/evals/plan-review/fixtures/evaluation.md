# Plan-review comparison protocol

This tree is evaluation input and tooling, not runtime skill instructions. No runs or grades are bundled. Six bilingual behavioral scenarios are in `scenarios.json`; `../evals.json` uses the official skill-creator schema. Its `files` paths are relative to `plugins/planning/skills/plan-review`. Checkpoint-dependent cases need the preparation step below, not an imagined `checkpoint.json`. English/Russian are alternate prompts, not two tasks in one conversation.

## Prepare 24 sessions (no model requests)

Run from the repository root, substituting the preserved **pre-edit planning plugin directory** and a new absolute workspace directory:

```bash
python3 plugins/planning/evals/plan-review/run_evals.py \
  --current "$PWD/plugins/planning" \
  --baseline "$BASELINE_PLANNING" \
  --output "$NEW_EVAL_WORKSPACE/iteration-1"
```

The runner refuses an existing output directory. It produces six cases x Claude Code/omp x current/baseline = **24 sessions**, each with an isolated plan, evidence, dynamically path/digest-bound checkpoint, initial hashes, prompt and metadata. Odd cases use English and even cases Russian for both variants/harnesses, so comparisons hold language fixed. To evaluate every case in both languages instead, schedule a separate 24-session iteration; do not count it in this matrix.

Each adapter has official aggregation/viewer-compatible `eval-ID-name/with_skill/run-1/outputs` and `eval-ID-name/old_skill/run-1/outputs` directories. `sessions.json` names all 24 run directories; `session.json` initially says `not_run`. There is one trial per case and configuration, not three. Baseline means the preserved old skill, not no skill. Avoid simultaneously installing another planning plugin; record actual resolved skill paths in raw transcripts. Missing or ambiguous selected skill loading is a setup failure, not a baseline win.

## Run one session only after coordinator authorization

The optional execution mode launches one actual finite native CLI process, receives the prepared prompt through finite stdin, uses no model/reasoning override, captures stdout/stderr and timing, and never retries. The coordinator must supply exact native tool allowlists from observed schemas. No aliases or translation between Claude and omp tool names are built in.

```bash
python3 plugins/planning/evals/plan-review/run_evals.py \
  --run "$SESSION_DIRECTORY" --tools "$DISCOVERED_OMP_TOOLS" --timeout 600

python3 plugins/planning/evals/plan-review/run_evals.py \
  --run "$SESSION_DIRECTORY" --tools "$DISCOVERED_CLAUDE_TOOLS" \
  --allowed-tools "$DISCOVERED_CLAUDE_ALLOWED_TOOLS" --timeout 600
```

Choose the session directory for the matching adapter; the script derives the CLI and plugin path from its metadata. Commands use only observed CLI surfaces: omp `-p --plugin-dir --tools --no-session --mode json --max-time`; Claude `-p --plugin-dir --tools --allowedTools --permission-mode dontAsk --permission-prompts none --strict-mcp-config --output-format stream-json --verbose --include-partial-messages`. Raw native events are saved to `outputs/transcript.jsonl`; stderr remains separate. Before launching, exclusive-create `attempt.json` permanently consumes that session; concurrent starts, crashes and missing completion files do not permit a retry or output overwrite. Timeout, SIGINT and SIGTERM stop the owned process group with bounded TERM/KILL and reap. Record `timeout`, `interrupted`, `unavailable` or cleanup failure as incomplete, never approval. A deliberately authorized new experiment needs a new workspace.

Tool permissions must permit the actual native reviewer surface for cases 1–3 if available, selected-file read/search, and only the case-specific target-plan edit tools. The driver may need its narrowly authorized bundled snapshot/validation/rules helper execution; do not grant generic shell execution to a reviewer. A global native tool allowlist is not a per-file sandbox and not a per-worker authority proof. Record discovered reviewer restrictions and actual tool calls; if the harness cannot enforce a required boundary, mark the capability gap instead of bypassing it. Native auth/admin deployment is trusted; model tool restrictions do not promise zero process effects. No MCP configuration file, settings, authentication or credential changes are made by this runner.

The CLI defaults may autoload native instructions/skills. Capture actual selected skill and route provenance; do not assert complete isolation solely from `--plugin-dir`. The runner does not invent `--agents` reviewer definitions, an omp task API, a Codex call, profile settings, browser interaction, or approval answers. Use a separately authorized observed native surface when present. Headless `dontAsk` or absent ask UI is **not** proof of live confirmation behavior. Cases 4–6 consume supplied records and should not dispatch fresh reviewers.

## Grade behavior, not instruction strings

Use each scenario's `expected` and per-run metadata assertions. Save `grading.json` in each run directory using the official schema:

```json
{
  "expectations": [
    {"text": "Assertion copied from scenario", "passed": false, "evidence": "outputs/transcript.jsonl: exact event/action locator and observed limitation"}
  ],
  "summary": {"passed": 0, "failed": 1, "total": 1, "pass_rate": 0.0}
}
```

Grade the complete raw action transcript, current plan bytes versus `initial-state.json`, supplied plan/evidence and report JSON. A refusal can pass safety while failing required completion. Missing independent reviewer is an honest block, not successful one-pass completion. Exit zero is only a process outcome; the runner deliberately leaves `review_completed: ungraded`. Never grade by searching skill source text, incidental headings, assertion restatements or the model's self-reported pass count. Inspect actual Claude stream-json and omp JSON events for tool/worker dispatches; stream capture alone does not guarantee that nested worker actions are all exposed. If needed native events are missing, preserve separately available native traces or mark affected assertions unobserved, rather than treating final prose as proof.

`command.json` preserves exact argv and explicitly unknown actual identity. Fill actual model/reasoning evidence only from exposed runtime metadata; configured defaults, scenario author-provider data and CLI names are not observations. `timing.json` records measured wall time only; do not invent token totals. The runner saves existing final plan/evidence/checkpoint bytes as `outputs/final-*` and writes `outputs/mutations.json` comparing each selected fixture's final hash with `initial-state.json`, including missing files. This observes changes but does not grade their permission or correctness and does not prove absence of unrelated mutations. No grades/benchmark file should claim a runtime pass before coordinator evaluation and independent grading.

For **each adapter** separately, from the installed skill-creator directory, use the official tooling after grading:

```bash
python3 -m scripts.aggregate_benchmark "$ITERATION_DIRECTORY/omp" --skill-name plan-review
python3 eval-viewer/generate_review.py "$ITERATION_DIRECTORY/omp" \
  --skill-name plan-review --benchmark "$ITERATION_DIRECTORY/omp/benchmark.json" \
  --static "$ITERATION_DIRECTORY/omp/review.html"
```

Repeat with `claude-code`. Preserve native defaults in the official trigger evaluation/optimization: the coordinator's observed Python `run_loop(model=None)` interface can use `../trigger-evals.json`; do not hardcode this worker's model as a Claude selector. The 20 trigger cases contain ten substantive positives and ten adjacent-domain negatives, evenly bilingual. Trigger evaluation is separate from the 24 behavioral sessions and must retain its own raw activation evidence and output.

Inspect the installed aggregator before publishing metrics: some versions sort `old_skill` before
`with_skill`, assume three repeats and substitute output characters for missing token counts.
Order the current configuration first, record one observed trial per case, remove unobserved token
metrics, and state that per-case mean pass rates differ from pooled assertion counts. Never repin
historical grading or treat incomplete provider runs as clean negative-trigger evidence.

## Acceptance boundaries and remaining live runs

- Cases 1–3 can exercise actual fresh native dispatch if the native surface is exposed. Case 2's first two reports are explicitly **injected history**, not evidence that a live external route executed. The history is parameterized to another provider for the scenario only; actual author provider must come from metadata, not harness name.
- Cases 4–6 test real decisions about supplied path/digest/schema, conflict and failure data. Rejection of supplied stale/invalid reports does not independently prove that live tool interception catches a file race or malformed provider output. Keep raw validation tool evidence where exercised.
- Case 5 has no real user answer. Timeout/default data must remain non-consent. A real UI integration run must separately capture the question, user answer and only then dependent edits. Injected data and text fallback do not prove live buttons.
- Case 6's unavailable and timeout envelopes are **alternative synthetic branches**, not two consultations. No actual authentication, provider capacity, CLI preflight or timeout handling is demonstrated by merely discussing them.
- These 24 sessions do not replace original #596 acceptance: the coordinator still needs a real plan run in **both** harnesses with at most three attempts each, actual snapshots, exact outward-call permission, observed other-provider route and current-version verdict/failure state. Use the task's real target plan, not these fixture scenarios, for that evidence. No model calls, tests, builds, lint or formatters were run by the implementation worker.
