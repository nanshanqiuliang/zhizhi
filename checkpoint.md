# Knowledge Tree App development checkpoint

Updated: 2026-08-14 (Asia/Shanghai)

## Original objective

Continue the repository's current active development work after reading the governing documents and engineering logs. The product objective is a Windows, local-first personal note App in which the user can write/import notes, manually edit a tree-shaped knowledge graph, and let AI generate source-linked graph drafts without bypassing preview, confirmation, locks, history, or validation.

The user has now defined a persistent communication convention: future requests such as “继续推进” must use `docs/USER_FACING_DEVELOPMENT_ROADMAP.md`, state the current natural-language step and progress at the beginning/end, then continue actual implementation rather than returning only a plan.

The current user request is “继续开发”. Work has resumed at natural-language Step 1 (MVP scope decisions), with intent to enter Step 2 (Anchor/GraphPatch contracts) once those decisions are frozen and verified.

## Recovered completion state

- WORK-2026-004 is closed by commits `90e13d0` and `ae834d9`; its final evidence is `TR-20260813-005`.
- The user-facing roadmap was committed at `5b0bc1c`.
- Current branch is being handed off from `feature/WORK-2026-002-mvp-decisions` to `feature/WORK-2026-005-anchor-graphpatch-v1`.
- Current natural-language step: Step 2, pre-QA freeze, approximately 70%; overall personal MVP approximately 20%.
- Commit `8ff376d0aa339143332a47500646b455148b1169` records the WORK-2026-002 / PRD v0.3 / ADR-0016 safe-default baseline. The ten architecture section 21 questions are mapped 10/10 and all repository gates passed at that commit.
- Role-separated QA attempt 001 returned FAIL with 1 P1 and 2 P2 evidence/governance findings; commit `10f249b3021da1577aa17eb114d3b44c20a2b0a2` corrected all three. Attempt 002 passed with no P0/P1/P2 or new findings. Both attempts are preserved by `TR-20260814-001`.
- WORK-2026-005 is in progress. Red commit `44b6233` proved the public APIs were missing. The implementation now has a canonical JSON Schema, schema-backed Python API, generated/typechecked TypeScript enums and Python runtime schema artifact, and a pure GraphPatch preview domain service; 50 targeted tests, 4 repository integration tests, and all repository gates pass. QA re-review is pending.
- Real DeepSeek/Web, user data, database writes, owner authentication, and Embedding remain disabled or unresolved.

Historical WORK-2026-004 implementation chain:

- Committed implementation chain:
  - `73a74da` — deterministic AI review v2 prototype.
  - `3f9b637` — replay evidence, claim/position binding, adjudication evidence, and assurance hardening.
  - `db0831b` — subject-evidence assurance and adjudication-position bypass closure.
- The deterministic harness, review policy v2, machine-review/review-policy schemas, repository validator integration, and contract tests are present.
- The independent subject reviewer accepted `db0831b` after three attempts.
- Five committed immutable-handoff summaries exist under `evidence/TR-20260813-005/` (three subject attempts and two QA attempts).
- The first QA attempt returned FAIL because of three P1 and three P2 semantic bypasses; the preserved second attempt passed the frozen fix.
- Eight regression tests for those findings were added to `tests/contract/test_ai_review_harness.py`; the recovered red baseline was 8 failed, 31 passed.
- All six findings are now closed in commit `ae834d9051553aa02a079e72ce2bf6bd8955c081`; the targeted harness suite passes 39/39.

## Key decisions

- Windows 10/11 x64, single-user, local-first; show the shared Web UI before Tauri packaging.
- First import formats are Markdown/TXT/PDF; PPTX/DOCX/OCR and cloud collaboration are deferred.
- Manual editing works without AI. Persistent GraphPatch changes are previewed and explicitly confirmed; content, relations, position, and annotations are independently lockable.
- Safe defaults may drive reversible offline development, but PRD v0.3 remains `in_review` and ADR-0016 remains `proposed` until the workspace owner confirms their exact contents.
- Remain mock/replay-only. `controlled_live` must fail closed until a separate documented live-provider gate and attestation authority exist.
- AI artifacts remain untrusted drafts. Product eligibility requires established subject evidence.
- Owner-risk acceptance must fail closed in this prototype because authenticated owner identity and current-time verification are not implemented; it is not acceptable to trust a self-declared machine payload.
- Tool traces must cover every replayed claim and bind the expected query hash, result hash, tool, call ID, and succeeded status.
- Finding `claim_id` values are deterministically derived from item identity.
- Tool-policy provenance must equal the effective role-policy version/hash.
- Subject, QA, and adjudicator runs must use distinct sessions; same model/provider correlation remains explicitly disclosed.

## Verified results before interruption

- At commit `db0831b`, all mandated repository gates passed, including 77 Python tests and the web checks/build.
- The subject reviewer independently accepted `db0831b` and reported its targeted security/regression checks passing.
- The later QA run independently confirmed the complete gate suite was green and recomputed dataset counts 30/40/50, unique IDs, DAG validity, frozen PDF identity, review-subject hash, and zero schema errors; its overall decision was nevertheless FAIL due to the six semantic issues above.

## Remaining work

- Freeze the implementation commit, then hand its complete SHA to role-separated QA; add regression tests for any finding before fixing it.
- If QA passes, preserve evidence, move WORK-2026-005 to verification, and prepare the next work item without starting DB/API/UI early.

## Current risks or blockers

- No substantive blocker remains for the local, offline contract path; WORK-2026-005 is Ready.
- Real-provider execution and owner authentication are explicitly out of scope and must remain disabled.
- Subject and QA attestations may be correlated because the available agents can share a model/provider family; the evidence must disclose that correlation and cannot impersonate a human signature.
- Repository ownership/public license and monetary LLM budgets remain unresolved; neither is required for the offline Step 2 contract, and both must remain gated rather than guessed.

## Verification after recovery

- Targeted contract suite: 39/39 passed.
- Full local gates at `ae834d9`: repository validator passed; Ruff format/lint passed; mypy passed; pytest 84/84 passed; pnpm frozen install/peer check/web check/web build passed.
- No live provider, network search, secret, database, or owner-authentication path was enabled.
- Role-separated QA attempt 002 passed immutable commit `ae834d9`, superseded the preserved FAIL attempt 001, and found no new P0/P1/P2; correlation remains conservatively classified as `correlated_review`.
- Final post-documentation gates also passed: repository validator, Ruff format/lint, mypy, pytest 84/84, pnpm frozen install/peers/check, Web 1/1, and production build.
- WORK-2026-002 decision baseline `8ff376d`: 10/10 decision mapping and the same full repository gates passed; QA attempt 001 returned FAIL solely for the 1 P1/2 P2 governance findings now being corrected.
- Superseding correction worktree: repository validator, Ruff format/lint, mypy, pytest 84/84, frozen pnpm install, peer check, Web 1/1, and production build all pass.
- `TR-20260814-001`: role-separated QA attempt 002 passed immutable commit `10f249b` with 0 P0/P1/P2 and no new findings; attempt 001 remains preserved; classification is `correlated_review`, not owner acceptance.
- WORK-2026-005 fix at `5ff02a4`: target 50/50 plus repository integration 4/4; full Python 136/136; Web 1/1; graph/LLM repository validator, Ruff, scripts/domain strict mypy, TypeScript/Python generation drift/tsc, locked dependency/peer checks and production build all pass.

## Exact next action

Seal `TR-20260814-002`, move WORK-2026-005 to prototype verification, then create
a Ready Step 2B work item for deterministic operation replay and inverse patch
generation. Start that item from failing pure-domain tests. Keep persistence,
database/API/UI, real Provider/Web, user data, and owner acceptance disabled.

## Recovery checkpoint — 2026-08-14 01:21 +08:00

- Current natural-language position: Step 2A, independent QA and evidence
  closure; Step 2 remains approximately 70% and the personal MVP approximately
  20% until a passing review exists.
- Frozen implementation: `a25470c`; red parent: `44b6233`; worktree was clean at
  handoff.
- QA outcome: FAIL with one P1 (runtime repository-schema file I/O) and one P2
  (49 target tests were reported as 53 without separating four repository
  integration tests). No P0 was found.
- Verified by QA: red/green commit binding, 49 target tests, repository gate,
  strict package mypy, TypeScript generation/typecheck, core security mutations,
  deterministic output, and input immutability.
- Preserved evidence:
  `evidence/TR-20260814-002/ai-graph-qa-attempt-001.md`.
- Current risk: installed contracts must not depend on the repository layout;
  QA remains correlated machine review and cannot accept owner residual risk.
- Next exact action: commit a red zero-runtime-file-I/O regression, then make a
  generated Python schema artifact the runtime source while retaining the JSON
  Schema as the only hand-edited contract source.

## Fix checkpoint — 2026-08-14 01:24 +08:00

- Red regression commit: `1278e79`; the isolated test failed because
  `Path.read_text()` was called during cold-start contract validation.
- Fix: the existing contract generator now derives a Python runtime schema
  artifact from the canonical JSON Schema, and its `--check` mode detects drift
  in both TypeScript and Python outputs. Runtime validation imports the generated
  artifact and performs no repository file read.
- Proportional verification: 50/50 graph contract/domain/security tests, 4/4
  repository integration tests, strict package mypy, Ruff, TypeScript generation
  drift/tsc, and diff hygiene all pass.
- Full mandatory gates passed at `5ff02a4`: repository validator, Ruff, mypy,
  136/136 Python, locked pnpm install/peers, TypeScript generation/typecheck,
  Web 1/1, and production build.
- Next exact action: commit corrected status accounting and send the resulting
  frozen SHA to role-separated QA for a superseding review.

## QA closure checkpoint — 2026-08-14 01:30 +08:00

- Superseding QA attempt 002 reviewed
  `b946855c3f8d70a850f45ce2630303819c54e1dc` and returned PASS with no P0, P1,
  P2, or new finding. The correlated machine review is not owner acceptance.
- QA independently reran the cold-start I/O regression (1/1), graph target suite
  (50/50), repository graph integration (4/4), TypeScript/Python generation
  drift/tsc, and strict package mypy (five files).
- Evidence is sealed under `evidence/TR-20260814-002/`; the report is
  `docs/test-reports/TR-20260814-002_anchor-graphpatch-v1.md`.
- Current natural-language position: Step 2 is approximately 80%; personal MVP
  approximately 22%. Step 2A is prototype-verified; Step 2B replay/inverse/undo
  is the next active work.
- Next exact action: define a Ready work item for pure deterministic replay and
  inverse patch generation, then commit its failing tests before implementation.

## Step 2B Ready checkpoint — 2026-08-14 01:32 +08:00

- Active branch: `feature/WORK-2026-011-graph-replay-inverse`.
- Ready work item: `docs/work-items/WORK-2026-011_graph-replay-inverse.md`;
  proposed decision: `docs/adr/ADR-0005-operation-log-periodic-snapshot.md`.
- Scope: pure in-memory immutable entity deltas, deterministic replay, and LIFO
  undo/redo for confirmed user patches. No persistence, database, API, UI,
  Provider, network, public delete operation, or real user content.
- Key safety decision: public GraphPatch remains the only write request language;
  inverse delete/restore deltas are generated inside the trusted domain and are
  not accepted from AI/import/system payloads.
- Acceptance: two-record replay, six-operation undo/redo, monotonic revisions,
  redo invalidation, tamper/order/empty-stack failure, input immutability, and no
  I/O all need repeatable tests.
- Next exact action: commit this Ready boundary, then add imports/tests for the
  absent history API and preserve the expected failing baseline before any
  implementation.

## Step 2B red-test checkpoint — 2026-08-14 01:36 +08:00

- Added the intended public history API tests for immutable minimal records,
  two-record replay, all six GraphPatch operations, LIFO undo/redo, monotonic
  revisions, redo invalidation, empty/order/duplicate/tamper/drift failures,
  non-user/unconfirmed/spoof rejection, input immutability, and no I/O.
- No history implementation exists yet. The exact next action is to run the
  isolated tests and preserve their expected collection failure, then commit the
  red baseline before adding `graph_history.py` or exports.

## Step 2B implementation checkpoint — 2026-08-14 01:44 +08:00

- Red baseline: `2425718` failed during collection with two expected ImportErrors
  because the GraphHistory API did not exist.
- Implemented a pure immutable `GraphHistory`, `GraphChangeRecord`, `EntityDelta`,
  semantic graph hashing, sequential replay, and LIFO undo/redo. History accepts
  only a confirmed user patch that GraphPatch preview marks `ready_to_apply`.
- Records hold only changed concept/edge/layout before/after canonical JSON,
  indices, revisions, hashes, and a content digest; they do not hold a whole
  graph, patch reason, or actor credential.
- Public GraphPatch schema remains unchanged. Creation reversal is an internal
  trusted delta, not a new AI/import/system delete capability.
- A shared `validate_course_graph()` entry now lets GraphPatch and history enforce
  the same schema plus cross-entity semantics without duplicating business rules.
- Target results: history/security/property 18/18; existing graph contract/domain
  50/50; Ruff, strict contracts/domain mypy, and diff hygiene pass.
- Exact next action: freeze the implementation commit, run all repository gates,
  then update evidence/status and request role-separated QA against the immutable
  SHA.

## Step 2B pre-QA checkpoint — 2026-08-14 01:52 +08:00

- Frozen implementation: `4fc8e60a392d1442f7475aa3f8082e31a1469cde`;
  red baseline: `24257186911bede6f68c16ed18b525211d011c32`;
  Ready boundary: `9d9f569d694a969cf6c262430b99fafa0ea8e96a`.
- Full gates passed: repository validator, Ruff, scripts and strict package mypy,
  154/154 Python tests, locked pnpm install/peers, TypeScript/Python generation
  drift/tsc, Web 1/1, and production build.
- Role-separated QA has received the immutable implementation SHA and is asked
  to mutate record binding/order/revision, LIFO/branch behavior, authorization,
  caller isolation, no-I/O, and minimal-record boundaries.
- Exact next action: do not change frozen implementation while QA runs. Preserve
  its PASS/FAIL evidence; if FAIL, add a red regression before the smallest fix.

## Step 2B QA closure — 2026-08-14 01:55 +08:00

- Role-separated QA reviewed `4fc8e60` and returned PASS with 0 P0/P1/P2 and no
  new finding. It confirmed the direct Ready/red/green chain and independently
  mutated record delta/digest/hash/revision/order/duplicate ID, two-level LIFO,
  redo invalidation, six operations, caller isolation, and no-I/O behavior.
- Evidence: `evidence/TR-20260814-003/`; report:
  `docs/test-reports/TR-20260814-003_graph-replay-inverse.md`.
- Natural-language Step 2 is complete as a pure-domain prototype. This does not
  claim SQLite persistence, crash recovery, API, UI, or product undo is ready.
- Current natural-language position: Step 3, 0%; overall personal MVP roughly
  25%. Next user-visible milestone is a sample-data knowledge-tree Web UI.
- Exact next action: seal WORK-2026-011 evidence, then create a separate Ready
  Web work item with visible acceptance criteria and start from failing component
  tests. Keep persistence and real AI out of that demo scope.

## Step 3A Ready checkpoint — 2026-08-14 02:00 +08:00

- Active branch: `feature/WORK-2026-012-knowledge-tree-web-demo`.
- Ready work item: `docs/work-items/WORK-2026-012_knowledge-tree-web-demo.md`.
- User-visible scope: an in-memory three-pane calculus workspace with selectable
  tree nodes, title/note editing, add-child, leaf deletion, pointer movement,
  auto-layout, position lock, and session undo/redo.
- Explicit non-capabilities: no refresh persistence, API, database, file import,
  source jump, AI generation, Provider, network, Tauri, or real user data.
- Acceptance includes component interaction tests, TypeScript/ESLint/build, and
  1440x900 plus 390x844 browser visual/overflow checks.
- Exact next action: commit the Ready boundary, replace the old status-page test
  with failing product-workspace tests, and preserve the red baseline before UI
  implementation.
