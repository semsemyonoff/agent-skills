# Invoice visibility for member role

## Goal and scope
`GET /invoices/{id}` returns the invoice to a member of the owning team. Non-goals: invoice creation, role management. The run may edit code and tests and read dev data; it must not write dev data.

## Acceptance criteria

### Executor acceptance
- A member of the owning team gets 200 with the invoice; a member of another team gets 404.

## Run prerequisites
- Invoice `INV-1001` exists on dev. Check: `SELECT id FROM invoices WHERE number = 'INV-1001'` in the dev database returns one row.

## Validation Commands
- `make test-invoices` in `api/`.

## Implementation Steps

### Task 1: Team-scoped invoice lookup
Files: modify `api/invoices.py`, modify `api/tests/test_invoices.py`.
Depends on: none.
- [ ] Restrict the lookup to the caller's teams and cover both acceptance cases.
- [ ] Run `make test-invoices`.
Acceptance: unit tests prove 200 for own team and 404 for another team.

### Task 2: Dev API check
Files: create `api/tests/e2e/test_invoice_member.py`.
Depends on: Task 1.
- [ ] Against the dev API, call `GET /invoices/INV-1001` with the member token and assert 200.
- [ ] Run `make test-e2e` in `api/`.
Acceptance: the member reads `INV-1001` on dev.

### Task 3: Final verification
Files: modify `docs/invoices.md`.
Depends on: Task 2.
- [ ] Verify every Executor acceptance criterion; run `make test` and `make lint` in `api/`.

## Execution boundaries
Allowed: code and test edits in `api/`, read-only access to dev data. Forbidden: writing dev data, deploys.
