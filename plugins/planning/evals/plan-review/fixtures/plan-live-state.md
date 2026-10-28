# Per-persona report filter

## Goal and scope
The reports API accepts `persona` and returns only that persona's reports. Non-goals: persona management, the reports schema. The run may edit code and tests.

## Acceptance criteria

### Executor acceptance
- `GET /reports?persona=analyst` returns only analyst reports; an unknown persona returns 404.

## Validation Commands
- `make test-reports` in `api/`.

## Implementation Steps

### Task 1: Persona filter
Files: `api/reports.py`, `api/tests/test_reports.py`.
Depends on: none.
- [ ] Add the `persona` filter and the 404 branch.
- [ ] Run `make test-reports`.
Acceptance: unit tests cover filter and 404.

### Task 2: Dev-environment check with the `analyst` and `auditor` personas
Files: `api/tests/e2e/test_reports_live.py`.
Depends on: Task 1.
- [ ] Against the dev API, call `GET /reports?persona=analyst` and `persona=auditor` and assert each returns at least one report of its own persona.
- [ ] Run `make test-e2e` in `api/`.
Acceptance: both personas return their own reports on dev.

### Task 3: Final verification
Files: `docs/reports.md`.
Depends on: Task 2.
- [ ] Verify every Executor acceptance criterion; run `make test` and `make lint` in `api/`.

## Execution boundaries
Allowed: code and test edits in `api/`. Forbidden: deploys.
