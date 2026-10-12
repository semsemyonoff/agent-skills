# Consultation modes

All modes are analysis-only: read/search evidence; no tests, arbitrary execution, edits, MCP,
nested agents or permission expansion. Claude has no shell tool. Codex may use its sandboxed
shell only for read/search, as documented by the runtime. Report missing evidence rather than
inventing runtime behavior. These prompt instructions supplement, not replace, tool restrictions.

## Debug (`--mode debug`)

Ask for a focused explanation, not an automatic fix:

```text
Investigate the scoped problem. Return:
1. Root-cause candidates ranked by evidence; distinguish proven facts from inference.
2. The code/evidence supporting each candidate, with actual file:line references where available.
3. Why the relevant previous attempts did not address the cause.
4. The smallest concrete recommendation and what would falsify it.
5. Missing evidence and uncertainties. Suggest checks only; do not run them.
```

Do not manufacture certainty or replace root-cause analysis with warning suppression or a
special case. The driver decides whether a recommendation fits the original authorization.

## Adversarial code review (`--mode code-review`)

Adapted from upstream ask-codex's adversarial review. Include this stance with the scoped diff:

```text
Perform an adversarial code review: find the strongest evidence-based reasons this change
should not ship yet, rather than validating its intent. Inspect the supplied changes and
relevant source through read/search only. Prioritize material, user-visible failures:
- auth, permissions, tenant isolation and trust boundaries;
- data loss, corruption, duplication and irreversible changes;
- rollback safety, partial failure, retries and idempotency;
- races, ordering, stale state and re-entrancy;
- empty states, null/nil, timeouts and degraded dependencies;
- version skew, schema drift, migration and compatibility;
- missing evidence that prevents a grounded decision.
Report no style/naming nitpicks or speculative defects without evidence. Every finding must
explain what can go wrong, why this visible code is vulnerable, the impact and a concrete
risk-reducing change. Prefer one defensible finding to many weak ones. Never invent paths,
line numbers, code paths or executed checks. Label inference and calibrate confidence.
Return ONLY valid JSON using the schema below, without Markdown fences or commentary.
```

The inner result schema (inside the helper envelope's `result` string) is:

```json
{
  "verdict": "needs-attention",
  "summary": "A material failure is supported by the inspected evidence.",
  "findings": [
    {
      "severity": "high",
      "title": "Short actionable title",
      "body": "Evidence, failure mechanism and user-visible impact; identify any inference.",
      "file": "relative/path/to/changed-file",
      "line_start": 42,
      "line_end": 55,
      "confidence": 0.85,
      "recommendation": "Concrete risk-reducing change"
    }
  ],
  "next_steps": ["Suggested check or change, not an instruction to execute it"],
  "uncertainties": []
}
```

Validation and presentation:

- Required fields: `verdict`, `summary`, `findings`, `next_steps`; `uncertainties` is optional.
  Verdict is `approve` or `needs-attention`; severity is `critical`, `high`, `medium` or `low`.
  Summary and finding text fields are nonempty strings. Findings is an array of objects;
  next_steps and uncertainties are arrays of strings. Confidence is a number from 0 to 1.
  Line bounds are positive integers with `line_end >= line_start` and must match actual evidence.
- Require actual source support for file/line findings. Keep unlocated concerns in uncertainties,
  not fabricated finding coordinates. Review completeness and missing scope evidence matter:
  use `needs-attention` if a material risk exists or missing evidence blocks a grounded review.
- Use `approve` only with no supported material finding and no blocking evidence gap. An empty
  findings array is valid only in a complete, valid result; empty output is not an empty review.
  A verdict of `approve` alongside blocking findings is inconsistent, not clean approval.
- Invalid/empty/truncated JSON or unsupported coordinates mean incomplete consultation. Report
  that fact; do not silently repair the verdict, erase findings or launch another model request.
- Preserve the original validated JSON. Present a readable view ordered critical to low, with
  confidence and proven file:line ranges; distinguish the driver's assessment and uncertain claims.
  Do not filter away blocking findings by an arbitrary confidence threshold. A proposed check
  has not passed merely because it appears under next_steps.

## Plan review (`--mode plan-review`)

Supply the selected plan inline or by an authorized readable path, its acceptance criteria,
settled decisions, dependencies and scope. Do not import another planning skill's files.

```text
Review this plan as an independent skeptic. Return:
1. Material blockers and gaps, each tied to an actual plan step or supplied evidence.
2. Contradictions with acceptance, permission boundaries or settled decisions.
3. Missing dependency ordering, migration/rollback steps and unverifiable assumptions.
4. Minimal concrete amendments, without implementing or replacing the plan wholesale.
5. Uncertainties and evidence needed for a decision.
Distinguish blockers from optional improvements. Do not claim the plan is validated by tests.
```

This is one consultation, not an iterative review chain. Return findings and stop when standalone;
any existing authorized driver workflow retains its own decisions and permission boundaries.
