# Selected evidence (synthetic evaluation input)

## Tooling — TOOL-1
`tools/` has `make test-slug`, `make test` and `make lint`; `tools/slug.py` already exists with a `slugify` stub that the export code already calls, so no call site changes; titles are ASCII-only; `docs/export.md` exists. No external service or stored data is involved. These are facts of the evaluation, not claims about a real system.
