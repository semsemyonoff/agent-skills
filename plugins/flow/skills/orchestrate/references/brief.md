# Worker brief

The worker does not see the conversation, the plan or other workers' results. Everything it needs is
in the brief; anything missing it will guess. Write the brief in English or in the user's language,
whichever the surrounding code and docs use.

## Template

```
Goal: <one sentence: what must be true when you are done>

Context:
- <repo/dir, relevant files with paths, entry points>
- <decisions already made and constraints: style, libraries, versions, what was ruled out>
- <facts from recon the worker would otherwise re-discover>
- <commands: how to build, test, lint>

Boundaries:
- May touch: <files or dirs>
- Must not: commit, push, write to trackers/forges or any external system, touch files outside the
  list above, touch <files another worker owns>. If the task cannot be done within these limits,
  stop and say why instead of widening the scope.

Done when: <checkable criterion: tests X pass, function Y handles Z, list covers all N items>

Answer format (compact, no retelling of the process):
- What was done, 1-3 lines.
- Changed files (or, for research: findings with path:line references).
- What you are unsure about or did not verify.
```

## Tips

- Give paths and line hints, not pasted file contents; the worker can read files.
- For recon, give the questions as a checklist so the answer maps to it one to one.
- For edits by spec, give one fully worked example of the change; mechanical workers copy the pattern.
- On a retry, add a "Previous attempt" line: what was wrong, and what exactly fixes it.

## Example

```
Goal: Add request-size limiting to the upload handler so bodies over the configured limit get 413.

Context:
- Go service in the current repo. Handler: internal/http/upload.go, func (h *Handler) Upload.
- Config struct: internal/config/config.go; add MaxUploadBytes int64, env UPLOAD_MAX_BYTES,
  default 10 MiB, same pattern as ReadTimeout on line 41.
- Use http.MaxBytesReader; on *http.MaxBytesError respond 413 with the existing writeError helper.
- Tests live in internal/http/upload_test.go (table-driven, httptest). Run: go test ./internal/...

Boundaries:
- May touch: internal/http/upload.go, internal/http/upload_test.go, internal/config/config.go.
- Must not: commit, push, change other handlers, add dependencies.

Done when: a test with a body over the limit gets 413, one under the limit still gets 200, and
go test ./internal/... passes.

Answer format: what was done (1-3 lines), changed files, anything you are unsure about.
```
