# Slugify helper for export file names

## Goal and scope
Export file names use a `slugify(title)` helper: lowercase ASCII, words joined by `-`, no leading or trailing separator. Non-goals: changing the export format or the storage layout.

## Acceptance criteria
- `slugify("Q3 Report: Final!")` returns `q3-report-final`.
- An empty or all-punctuation title returns `export`.

## Validation Commands
- `make test-slug` in `tools/`.

## Implementation Steps

### Task 1: Slugify helper
Files: modify `tools/slug.py` (existing stub), create `tools/tests/test_slug.py`.
Depends on: none.
- [ ] Implement `slugify` with the fallback for empty results and cover both acceptance examples.
- [ ] Run `make test-slug`.
Acceptance: unit tests pass for normal, punctuation-only and empty titles.

### Task 2: Final verification
Files: modify `docs/export.md`.
Depends on: Task 1.
- [ ] Verify every acceptance criterion; run `make test` and `make lint` in `tools/`.
- [ ] Document the helper in `docs/export.md`.

## Execution boundaries
Allowed: code, test and documentation edits in `tools/` and `docs/`. Forbidden: changes to the export format.
