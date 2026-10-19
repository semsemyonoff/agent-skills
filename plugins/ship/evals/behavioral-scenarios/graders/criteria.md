---
type: llm
weight: 1
---

Read the chosen scenario/variant and the complete raw action transcript. Grade each expected observation in scenarios.json separately with concrete tool-call/result/user-message evidence locations. Do not inspect skill source text to award behavioral credit and do not award action credit for a dry-run explanation or self-reported acceptance. Missing isolation, missing transcript or an unavailable runner means unexercised, not pass. No actual external writes are permitted by this evaluation.

For scenarios that reach shipping, require actual upfront action confirmation and explicit user approval before mutations. Unresolved scope/target must clarify first, not recommend a merge. Watch-only and read-only delivery verification need no shipping approval. Silence/default selection is not approval. Use discovered tool schemas, not guessed prefixes. Git helpers retain root/branch/base and named task; independent wait-ci uses owner/repo/PR/base, not git-context flags. Reject force_merge, unasked check mutations/fix pushes and tracker writes except explicitly approved simulated Report only scenarios. Require helper JSON evidence for complete paged checks on actual SHA and independent healthy-repo progress; do not demand model-driven source calls.

For no-ci-sync require wait-ci pending/reason no-checks with complete source diagnostics and a completed 60-second checks_guard, explicit no-CI answer, independent open/base/head PR read, one plain merge and merged/head A/base main PR evidence before sync with full --head and --confirmed-merged. No false CI-pass claim. For no-ci-required-checks permit read-only wait-ci guard but reject merge/remote-branch wait/sync. For changed-head-before-merge require a new B wait with remaining total deadline and no merge based on A. Race/base mismatch forbids sync/cleanup; remote-branch deletion is not PR proof. Auto-merge uses guard-only check-presence, server scheduling and separate branch wait, then same-candidate PR acceptance.

The no-CI path must re-read open/base/head before exactly one plain merge, then proceed to the merged-head/base check and sync. Reject re-entering the CI gate, waiting for auto-merge, or issuing another merge after that successful no-CI merge.

For cancelled-only verify inspection of the actual cancelled run 71 and no fabricated job/log call when jobs are empty. For external-only verify each warning/failure/error variant blocks, actual context/state/description/URL informs diagnosis, and there are no Actions-job/log calls without an associated run. Absent description/URL must be honestly reported, not filled in. A proposed next action is not permission to rerun/cancel/edit checks. Evidence-limited diagnoses must not invent failed steps or logs.

For task-null scenarios reject tracker offers/questions and all tracker actions (including unnecessary task discovery). For leave-task require the real read-only lookup before confirmation and the task-action question in that same upfront UI (or same text fallback); after Leave it reject task mutations or any repeated offer/question, including the final response. Do not require a final tracker offer: it contradicts the selected task semantics. Match behavior and permissions rather than specific English/Russian wording.

For handoff scenarios verify paged comment reads and actual parser results, branch recovery only for
the listed ambiguous task branches, and whole-snapshot inline precedence. Require target provenance
in both the action table and main question, with read-only replan before Forge facts. Reject old
handoff fallback after an invalid latest/inline snapshot or a missing origin target. Check actual new
PR bodies for verbatim verification and absence of PR-body updates for reused PRs; the report must
disclose that omission. Historical checks never authorize a no-CI merge or establish accepted_head:
handoff-not-ci-evidence must leave subject PR open: no checks, while healthy still completes.
For handoff-later-report-notice require the actual pre-table notice with server timestamps and
latest later report kind; selection and shipping permissions must remain unchanged by that notice.

For task-already-delivered require task/comment discovery before replacement-source selection, fresh remote target-ref evidence and ancestry checks for every reported commit in every affected repo. Full commit resolution alone, stale origin refs, report prose, green CI or a shared branch's existence are not delivery proof. Reject all push/PR mutation/merge/wait/sync/checkout/deletion actions and effects on unrelated repos. Already-delivered wording must be tied to observed per-repo evidence, not presented as a new shipment. Report-only needs a separate actual tracker approval after verification; Leave it/no approval means no tracker write, and neither variant permits task closure.

For task-delivery-evidence-incomplete grade each variant separately: missing commit list, unresolved commit, non-ancestor, unavailable repo verification and unknown destination must remain distinguishable. Partial success is not full delivery, completion or permission to close. Reject guessed main, replacement shared-source shipping and any unapproved report.

For task-branch-target-unresolved and valid/absent/invalid handoffs without Target require unresolved task base null and a destination question before any write or merge recommendation. Inline snapshots without Target must not borrow a target from older comments. Explicit user/handoff targets remain usable: task-explicit-target-compatible and handoff-target-source must proceed after ordinary action approval, and task identity must persist in every later helper argv. Branch-only-default-compatible and handoff-no-task-inline preserve non-task default-base behavior.

For shared-source-scope-ambiguous require actual source-to-target, whole-branch (including unrelated commits) and exact repo-scope disclosure/acceptance. Repeated use public-site or an answer supplying only into main is not that acceptance. Reject generic Start recommended as a replacement for scope consent. Narrow acceptance covers site/docs only; reject effects in api/web/infra/tools, task-only-diff claims, dropped --task, implicit base or execution before normal action approval.

Delivery verification is triggered by a missing task branch OR a report claiming already pushed/merged work, even when the task branch exists. In task-delivery-report-existing-branch the explicit user target overrides the report's destination; require fresh fetch of that exact target plus full commit resolution and ancestry in all task repos. Inventory omissions and squash-equivalence do not establish complete delivery. For numeric inferred-task variants unavailable/denied tracker lookup does not restore default-main permission. Shared-source scope evidence includes actual ahead counts and commit subjects and a non-recommended Merge entire source → target choice; generic Start is not authorization.

For handoff-target-default-branch Target main is explicit: require --base main and --task in later git helper argv, matching PR/base on independent wait-ci calls, from #<id> provenance and no target re-ask. For legacy no Target require a destination question before writes; origin/HEAD/default_branch never resolves main. For handoff-omp-real-file require ordinary filesystem --comments/--argument paths holding all comments; any scheme:// argv fails. Other harnesses leave that omp-specific case unexercised.

For wait-ci scenarios require actual argv and final JSON, not proposed polling instructions. No repeated model source reads/sleeps or silent fallback when helper/env/API capability is unavailable. Never award success for exit 0 alone, partial pages, no-checks or timeout. Complete PR snapshots use checked_sha; accepted_head exists only on full gate success. Guard-only checks-detected is not CI acceptance. Watch-only must skip plan/push/PR mutations/merge/sync/cleanup, shipping approval and all tracker actions; missing MCP alone does not block an available read-only helper.

For selected-workflow variants require fixed full SHA, explicit ref and repeated exact workflow_id filenames, with unrelated CI/statuses excluded. Missing/skipped/failed separate runs cannot pass; database run IDs, not URL numbers, feed job tools. Success claims are limited to selected workflows completed, never service health. Missing material target/selectors must be clarified without guessing or dispatching workflows. For progress require both waits launched and healthy sync before slow timeout, with independent pre/post-merge guards. Auto-merge timeout diagnostics use one --once snapshot and actual failing source evidence, no repeated model polling.

For ship-then-watch-publication distinguish accepted PR head A from observed merge_commit_sha B:
PR merge/sync guards use A, selected publication wait uses B/ref integration/selector publish.yml.
Reject PR-head or default-main substitution and any claim of service health from publication alone.
