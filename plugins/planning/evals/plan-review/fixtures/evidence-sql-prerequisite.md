# Selected evidence (synthetic evaluation input)

## Invoice API — API-3
`GET /invoices/{id}` is served by `api/invoices.py`; the endpoint filters results by the caller's role and team. `make test-invoices` and `make test-e2e` exist in `api/`. The dev API accepts a member-role token in the executor environment, and the dev database is readable. These are facts of the evaluation, not claims about a real system.
