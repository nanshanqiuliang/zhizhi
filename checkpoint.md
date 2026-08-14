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

## Step 3A red-test checkpoint — 2026-08-14 02:04 +08:00

- Replaced the engineering-status assertion with five product-workspace tests:
  sample tree/non-capability labels; select/edit/save/undo/redo; add child and
  leaf-only deletion; pointer movement/position lock/auto-layout/reset; and
  toolbar/detail/navigation accessibility.
- Existing App still renders the engineering preview, so these tests are
  expected to fail. Exact next action: run and commit this red baseline before
  replacing the UI.

## Step 3A recovery checkpoint — 2026-08-14 02:13 +08:00

- Original product objective remains a Windows local-first personal note App:
  notes and imported material can be organized as a manually editable tree;
  later AI may propose source-linked tree changes, but may not bypass preview,
  confirmation, locks, validation, history, or the user.
- User-facing reporting convention remains active: each “继续推进/继续开发”
  response names the plain-language roadmap step, its progress, overall MVP
  progress, completed work, verification result, and exact next action.
- Workspace evidence matches the prior checkpoint. The active clean branch is
  `feature/WORK-2026-012-knowledge-tree-web-demo`; HEAD `4caa76a` is the committed
  five-test red baseline and its parent `87fb402` is the Ready work-item boundary.
- Completed and verified: Step 2 pure-domain GraphPatch validation plus
  deterministic replay/undo/redo, with 154/154 Python tests, Web 1/1, production
  build, mandatory repository gates, and role-separated QA PASS recorded under
  `TR-20260814-002` and `TR-20260814-003`.
- Completed and verified as intentionally failing: Step 3A scope/non-scope,
  acceptance/risks/rollback/evidence are explicit; all five workspace component
  tests fail against the old engineering status page, proving the product UI is
  absent before implementation.
- Partially complete: natural-language Step 3 “做出真正可操作的知识树网页” is
  approximately 15%; overall personal MVP is approximately 25%.
- Not started in Step 3A: the three-pane workspace implementation, component
  green run, browser desktop/mobile verification, final repository gates,
  role-separated UI QA, evidence/log/roadmap closure.
- Intentionally not started: persistence/API/database, refresh survival, file
  import/source viewer, AI/provider/network, real user data, and Tauri packaging.
- Current risks: session-only state must be labelled honestly; pointer movement
  and responsive layout need real-browser verification; this Web demo must not
  be reported as persistence or AI completion. No current blocker exists.
- Exact next action: replace `apps/web/src/App.tsx` and its styles with the
  smallest in-memory sample workspace that satisfies the five committed tests,
  then run the focused test suite and address only evidenced failures.

## Step 3A component-green checkpoint — 2026-08-14 02:54 +08:00

- Replaced the engineering status page with an in-memory, three-pane “知枝”
  calculus workspace: course/note navigation, eight-node tree canvas, node
  detail editor, add child, leaf-only deletion, pointer movement, auto-layout,
  position locking, reset, and session undo/redo.
- Capability boundaries are visible in the product: the header says “示例数据”
  and “AI 未连接”; the sidebar says changes are retained only in the current
  session; the source panel and footer state that imports/database are absent.
- The first implementation run showed four failures caused by test DOM leaking
  across cases and a non-anchored node-name regex matching the root. Standard
  `afterEach(cleanup)` and exact accessible-name matching corrected the harness;
  no acceptance behavior was removed or weakened.
- Focused component result: `pnpm --filter @knowledge-tree/web test` passes
  5/5 tests. Natural-language Step 3 is approximately 55%; overall personal MVP
  is approximately 30%.
- Current risk: compilation/lint/production build and real-browser desktop/mobile
  layout have not yet been verified. In-memory undo does not yet use the Python
  domain history across an API boundary and is not crash/refresh persistent.
- Exact next action: run Web check and production build, fix only evidenced
  issues, then launch the local preview and verify desktop plus mobile in the
  in-app browser, including horizontal page overflow and core interactions.

## Step 3A browser-verification checkpoint — 2026-08-14 02:58 +08:00

- Web static gates pass: TypeScript project build, ESLint with zero warnings,
  component tests 5/5, and Vite production build (16 modules) are green.
- Desktop browser at 1440×900: exactly eight nodes render; the page itself has
  zero horizontal/vertical overflow; the canvas owns its intended horizontal
  scroll. Browser interaction verified edit/save, undo, redo, pointer drag,
  position lock surviving auto-layout, add/delete child, and sample reset.
- Browser interaction values: drag changed the selected node from
  `left: 115px; top: 205px` to `left: 210px; top: 255px`; auto-layout preserved
  that exact locked style; reset returned status `示例已重新载入`.
- Mobile browser at 390×844: the document has zero horizontal page overflow;
  canvas scrolling remains contained; the detail form follows below the canvas.
  A follow-up fix centers the selected root on first mobile load and prevents a
  zero-distance click from creating a false history item. Reverification shows
  the root fully visible, page overflow 0, and Undo disabled before and after a
  selection-only click.
- Browser console verification found zero warning/error entries. Product title
  is now `知枝 · 知识树笔记`.
- Natural-language Step 3 is approximately 70%; overall personal MVP is
  approximately 32%. The implementation remains sample/session-only and does
  not claim persistence, imports, AI, or desktop packaging.
- Exact next action: commit the green Web implementation with its repeatable
  tests, hand the immutable SHA to role-separated QA, preserve the review
  evidence, then run the complete repository gate suite before closure.

## Step 3A QA failure checkpoint — 2026-08-14 03:08 +08:00

- Frozen implementation `5aab0e3` passed local Web/full-repository/browser
  verification, but role-separated QA attempt 001 returned FAIL with one P1.
- Finding: at `max-width: 820px`, CSS hides the header mode badges, the sidebar
  session-only notice, and the footer database boundary simultaneously. Mobile
  users can still see “保存修改” without any visible statement that data is
  sample/session-only and AI/database/import are absent.
- No P0/P2 or additional finding was reported. QA independently confirmed the
  direct Ready/red/green chain, 8-node fixture, no network/storage APIs, Web
  check/build, history branch/reset mutations, deletion and lock semantics.
- Failure evidence is preserved as
  `evidence/TR-20260814-004/ai-web-qa-attempt-001.md`; it is correlated machine
  review, not a human signature or owner acceptance.
- A new component regression requires one compact-layout boundary element to
  contain `示例数据`, `仅本次会话`, `AI 未连接`, and `未连接数据库`. Against
  `5aab0e3` this test must fail before the UI fix.
- Natural-language Step 3 returns to approximately 75%; personal MVP remains
  approximately 32%. The full QA gate is not passed despite local green checks.
- Exact next action: run and commit the expected failing regression, add an
  always-visible mobile capability-boundary strip, verify its computed mobile
  display in the browser, rerun gates, and submit a superseding frozen SHA.

## Step 3A mobile-boundary fix checkpoint — 2026-08-14 03:11 +08:00

- Red regression commit: `c8c6bf9`; Web result was the expected 1 failure and
  5 passes because no `演示能力边界` element existed.
- Fix: a compact sticky disclosure is rendered at the mobile breakpoint and
  states `示例数据 · 仅本次会话 · AI 未连接 · 无资料导入 · 未连接数据库`.
  Desktop retains its existing header/sidebar/footer disclosures.
- Focused green results: TypeScript, ESLint, component tests 6/6, production
  build, and diff hygiene pass.
- Real-browser 390×844 verification: computed display is `flex`, visibility is
  `visible`, the complete disclosure rectangle is inside the viewport at
  top 68/bottom 106, the save control remains present, document overflow is 0,
  and browser warning/error count is 0. The mobile screenshot was superseded.
- Exact next action: freeze the minimal fix commit, rerun full repository gates,
  then request role-separated QA attempt 002 against that exact SHA with the P1
  as the primary regression target.

## Step 3A closure checkpoint — 2026-08-14 03:12 +08:00

- Frozen final implementation: `fff1ce697cf3524fb7622f36cedfc63136e990f2`;
  QA regression red: `c8c6bf99d8cb008c111ed4918320c58b2f8074fe`;
  original implementation: `5aab0e3`; original product red: `4caa76a`;
  Ready boundary: `87fb402`.
- Role-separated QA attempt 002 returned PASS with no P0/P1/P2 or new finding.
  It independently verified the direct red/fix chain, compact boundary contents
  and mobile CSS override, Web 6/6, production build, eight DOM mutations, the
  8-node fixture, history/lock/delete/reset behavior, and absence of network or
  browser-storage APIs.
- Final full gates pass: repository validator, Ruff, scripts mypy, Python
  154/154, peer check, generated contract drift/tsc, Web 6/6, and production
  build. Locked uv/pnpm installs were also current and passed in this run.
- Browser evidence: desktop 1440×900 and mobile 390×844 have zero document
  horizontal overflow and zero console warnings/errors. The mobile disclosure
  is visible in the first viewport while the save control remains available.
- Evidence/report: `evidence/TR-20260814-004/` and
  `docs/test-reports/TR-20260814-004_knowledge-tree-web-demo.md`. Attempt 001
  remains preserved and superseded, never rewritten.
- Natural-language Step 3 is complete (100%) as a verified developer demo;
  overall personal MVP is approximately 35%. This does not claim persistence,
  imports, source navigation, AI, Tauri, installation, or release.
- Exact next action on the next “继续推进”: enter natural-language Step 4 by
  creating a separate Ready local-workspace/SQLite persistence item with data
  directory, schema/migration, restart survival, backup/export/delete, rollback,
  and failure evidence; start from failing persistence/restart tests.
- Current blocker: none for offline Step 4 preparation. Real Provider/Web and
  owner acceptance remain separately gated and disabled.

## Step 4A Ready checkpoint — 2026-08-14 07:24 +08:00

- Active branch: `feature/WORK-2026-013-local-sqlite-workspace`.
- Ready work item: `docs/work-items/WORK-2026-013_local-sqlite-workspace.md`.
- Scope: pure Python + stdlib `sqlite3` local workspace persistence prototype —
  data directory layout/validation, versioned SQLite schema v1 + migration
  framework, CourseGraph save/load (reusing canonical graph contract and
  `validate_course_graph`), restart survival, backup (checksummed), export
  (validated JSON), delete via purge-manifest semantics, migration rollback,
  and fault-injection evidence (truncated/garbage db, interrupted write,
  duplicate replay).
- Explicit non-capabilities: no Web API/UI hookup, no auto-save UI, no FTS5
  search, no file import/PDF viewer, no AI/Provider, no multi-process, no
  cloud, no encryption. The in-memory Demo must not be presented as saved.
- Acceptance: TC-PERS-001..006 — directory lifecycle; save→close→reopen
  semantic equivalence with revision preserved; migration v1 ordered/duplicate/
  rollback; backup/export/delete consistency; fault injection fails closed;
  history record JSON round-trip consistent with WORK-2026-011.
- Exact next action: commit this Ready boundary, then add failing
  persistence/restart tests (expected ImportError/collection failure) before
  any SQLite implementation.

## Step 4A closure checkpoint — 2026-08-14 07:45 +08:00

- Active branch: `feature/WORK-2026-013-local-sqlite-workspace`.
- Frozen implementation: `8e34a40f02de8d94ad6db3927cf8b189e9caee03`;
  red baseline: `1420b68fd8eb4f4bea82e217140af2efcd820447`;
  Ready boundary: `ec8005e1527b223fee043f2c1bffe718e1bede5b`.
- Role-separated QA (`graph_qa_fresh`) returned PASS with 0 P0/P1/P2 and no
  new finding. Its environment had no shell executor, so mutations were traced
  statically; this session then live re-ran all eight mutation classes (digest
  tamper, truncated/garbage db, migration conflict, duplicate replay, checksum
  tamper, invalid graph overwrite, purge) and all failed closed.
- Full gates pass at `8e34a40`: repository validator, Ruff, scripts + strict
  package mypy (contracts-py/domain/infrastructure), pytest 175/175 (target
  21/21), locked pnpm install/peers, Web 6/6, TypeScript check, and production
  build.
- Evidence/report: `evidence/TR-20260814-005/` and
  `docs/test-reports/TR-20260814-005_local-sqlite-workspace.md`.
- Natural-language Step 4 progress: persistence kernel prototype done
  (approximately 45% of Step 4); overall personal MVP approximately 40%.
  This does not claim browser auto-save, API/UI hookup, FTS5 search, imports,
  encryption, multi-process, or cloud.
- Exact next action on the next "继续推进": create a separate Ready work item
  for browser/API persistence hookup (auto-save, workspace selection UI,
  save-status), starting from failing persistence-API red tests.
- Current blocker: none for offline Step 4 preparation. Real Provider/Web and
  owner acceptance remain separately gated and disabled.

## Step 4B Ready checkpoint — 2026-08-14 07:55 +08:00

- Active branch: `feature/WORK-2026-014-local-persist-api`.
- Ready work item: `docs/work-items/WORK-2026-014_local-persist-api.md`.
- Scope: local FastAPI sidecar under `apps/api` (loopback only, CORS Origin
  allowlist, `/api/health`, CourseGraph GET/PUT, backup endpoint) plus Web
  hookup (load saved graph, debounced auto-save, visible save status, offline
  degradation when the API is unreachable). New deps: fastapi, uvicorn,
  httpx2 (test) are already resolved and locked.
- Reuses WORK-2026-013 workspace adapter and canonical graph validation; no
  new canonical contract, no migration, no prompt changes.
- Explicit non-capabilities: no Tauri packaging, no auth/token (deferred to
  ADR-0011/SPK-009), no FTS5, no import/PDF, no AI/Provider, no cloud,
  no encryption, no browser-direct SQLite.
- Acceptance: TC-API-001..005 — health/loopback/CORS; PUT valid graph then GET
  equal (revision preserved); invalid graph rejected without overwrite;
  Web load/auto-save/status transitions; API-unreachable degradation keeps
  drafts.
- Exact next action: commit this Ready boundary, then add failing API
  integration tests and Web component tests (mock fetch) before any sidecar or
  frontend implementation.

## Step 4B closure checkpoint — 2026-08-14 08:05 +08:00

- Active branch: `feature/WORK-2026-014-local-persist-api`.
- Frozen implementation: `e0a4c7212aa8be2aae1b2319968b3f75159bfba1`
  (initial `6c0c33c` + P2-1 fix); red baseline:
  `4fe918bffde539c10ea69529df45ba854bbe1bb9`; Ready boundary:
  `31ce81486a643304e2d1acd0ef3442a20d3f9440`.
- Role-separated QA attempt 001 reviewed `6c0c33c` and returned PASS (0 P0/P1,
  3 non-blocking P2). P2-1 (backup silently created an empty workspace) was
  closed by `e0a4c72` with a new regression test; attempt 002 reviewed the fix
  and returned PASS with no new findings. P2-2 (mount-load race) and P2-3
  (600ms debounce not flushed on unload) are recorded prototype boundaries.
- Both QA runs were static-tracing (read-only subagents cannot execute tests);
  this session live-ran the full gates (pytest 183/183 incl. API 8/8, Web
  10/10, ruff, strict mypy incl. apps/api, repository validator, frozen
  installs/peers/check/build) and a real uvicorn e2e smoke (PUT→GET round
  trip, invalid 422, backup checksum, CORS forbidden-origin rejection).
- Evidence/report: `evidence/TR-20260814-006/` and
  `docs/test-reports/TR-20260814-006_local-persist-api.md`.
- Natural-language Step 4 progress: persistence kernel + browser/API auto-save
  loop done (approximately 85% of Step 4); overall personal MVP approximately
  50%. Remaining Step 4 items (FTS5 search, file import) are separate work
  items. No Tauri packaging, auth/token, encryption, multi-process, or cloud.
- Exact next action on the next "继续推进": decide whether to continue Step 4
  (FTS5 search or file import) or enter Step 5 (import material and jump to
  sources), each as a separate Ready work item starting from failing tests.
- Current blocker: none for offline Step 4/5 preparation. Real Provider/Web and
  owner acceptance remain separately gated and disabled.

## Step 4C Ready checkpoint — 2026-08-14 08:15 +08:00

- Active branch: `feature/WORK-2026-015-fts5-search`.
- Ready work item: `docs/work-items/WORK-2026-015_fts5-search.md`.
- Scope: FTS5 full-text search over saved CourseGraph concept labels and note
  annotations — FTS5 index in the workspace adapter (rebuilt on save), a
  read-only `GET /api/workspaces/{id}/search?q=...` endpoint with query length/
  syntax guards, and a Web search box listing matches with click-to-locate.
- Explicit non-capabilities: Chinese word segmentation (FTS5 unicode61 space/
  punctuation tokenization; whole-phrase Chinese matching limited — recorded
  boundary), fuzzy/corrected search, file-content search (Step 5), multi-
  workspace search, vector search.
- Acceptance: TC-SEARCH-001..003 — FTS5 index hits label and note; search
  endpoint positive/negative paths (matches, empty/overlong/invalid 422,
  missing workspace 404); Web search box interaction with click-to-locate.
- Exact next action: commit this Ready boundary, then add failing FTS5/API/Web
  tests before any implementation. Completing this work item makes natural-
  language Step 4 100%.

## Step 4C closure checkpoint — 2026-08-14 08:40 +08:00

- Active branch: `feature/WORK-2026-015-fts5-search`.
- Frozen implementation: `d6c8e015f3e3ad77a2649a838e03b7b5db9c8789`
  (initial `eeba073` + P2-2 fix); Ready boundary:
  `e451057b17eedeec5180d1ac5a41490021ea6236`.
- Process deviation (disclosed): the red-light tests and implementation were
  merged into a single commit `eeba073` instead of separate commits. Red-light
  truth was re-confirmed twice: a git worktree at the parent commit reproduces
  `ImportError: cannot import name 'SearchResult'`, and QA verified at the
  direct parent `e451057` that no SearchResult/endpoint/test file exists.
- Role-separated QA reviewed `eeba073` and returned PASS (0 P0/P1, 3 P2).
  P2-2 (search input maxLength + explicit failure hint) closed by `d6c8e01`;
  P2-1 (no debounce/race) and P2-3 (hand-tampered non-FTS5 table error
  classification) recorded as prototype boundaries.
- Full gates pass at `d6c8e01`: repository validator, Ruff, scripts + strict
  package mypy (incl. apps/api), pytest 193/193 (search 10/10), locked pnpm
  install/peers, Web 12/12, TypeScript check, and production build. Live e2e
  smoke via real uvicorn confirmed CJK label/note substring hits and empty-
  query 422.
- Evidence/report: `evidence/TR-20260814-007/` and
  `docs/test-reports/TR-20260814-007_fts5-search.md`.
- **Natural-language Step 4 is COMPLETE (100%)**: SQLite persistence kernel
  (TR-005), FastAPI sidecar + Web auto-save (TR-006), and FTS5 search
  (TR-007) are all verified. Overall personal MVP is approximately 55%.
- Exact next action on the next "继续推进": enter natural-language Step 5
  (import material and jump from nodes back to sources) with a separate Ready
  work item (WORK-2026-016), starting from failing import/source red tests.
- Current blocker: none for offline Step 5 preparation. Real Provider/Web and
  owner acceptance remain separately gated and disabled.

## Step 5A Ready checkpoint — 2026-08-14 08:55 +08:00

- Active branch: `feature/WORK-2026-016-safe-import`.
- Ready work item: `docs/work-items/WORK-2026-016_safe-import.md`.
- Scope: safe local import of Markdown/TXT/PDF into the workspace — SQLite
  schema v2 migration (new `resource`/`resource_version` tables), controlled
  storage directory (UUIDv7 filenames, no path traversal), SHA-256 content
  hash + idempotent de-dup, content-based type/size guards (≤25 MiB, magic
  bytes + extension), `POST`/`GET /api/workspaces/{id}/resources` endpoints,
  and a Web import control + resource list.
- Reuses the v1 workspace adapter; migration v1→v2 is forward-compatible.
  No new canonical contract, no prompt changes.
- Explicit non-capabilities: PDF text parsing/viewer, Markdown rendering,
  Anchor generation and source jump (WORK-2026-005 Anchor contract stays
  frozen; landing later), url/note resources, cloud, encryption.
- Acceptance: TC-IMPORT-001..005 — migration v1→v2; MD/TXT/PDF import with
  correct metadata and idempotent de-dup; rejection of out-of-whitelist/
  forged/oversized/traversal payloads without writes; resources list metadata
  only; Web import control and list.
- Exact next action: commit this Ready boundary, then add failing import tests
  (expected ImportError/collection failure) before any implementation.

## Step 5A closure checkpoint — 2026-08-14 09:15 +08:00

- Active branch: `feature/WORK-2026-016-safe-import`.
- Frozen implementation: `eee15d0e5127bd91d7e21124282107a4e02c1f25`
  (initial `10e104f` + P2-1/P2-3 fix); red baseline:
  `50b324528ec594876f2949b0de9d76fc7a6fce61`; Ready boundary:
  `293c0ef6eec2250ef8780f4089d2384fb9597762`.
- Role-separated QA reviewed `10e104f` and returned PASS (0 P0/P1, 5 P2).
  P2-1 (DB-commit vs disk-write non-atomicity, orphan records) and P2-3 (dead
  `mime` param) were closed by `eee15d0` (write-then-commit + orphan cleanup
  regression test); P2-2 (idempotency not concurrency-safe), P2-4 (POST
  implicitly creates workspace, consistent with PUT /graph) and P2-5 (coarse
  front-end error mapping) are recorded prototype boundaries.
- Full gates pass at `eee15d0`: repository validator, Ruff, scripts + strict
  package mypy (incl. apps/api), pytest 208/208 (import 15/15), locked pnpm
  install/peers, Web 15/15, TypeScript check, and production build. Live e2e
  smoke via real uvicorn confirmed MD/PDF import, same-hash idempotency, exe
  rejection, and metadata-only listing.
- Evidence/report: `evidence/TR-20260814-008/` and
  `docs/test-reports/TR-20260814-008_safe-import.md`.
- Natural-language Step 5 progress: first work item (safe file import) done
  (approximately 25% of Step 5); overall personal MVP approximately 60%.
- Exact next action on the next "继续推进": create a separate Ready work item
  for PDF text parsing/viewer and Anchor-based source jump (WORK-2026-017),
  starting from failing viewer/anchor red tests. The calculus gold PDF and
  page-level samples are ready for acceptance.
- Current blocker: none for offline Step 5 preparation. Real Provider/Web and
  owner acceptance remain separately gated and disabled.

## Step 5B Ready checkpoint — 2026-08-14 09:30 +08:00

- Active branch: `feature/WORK-2026-017-pdf-viewer-anchor`.
- Ready work item: `docs/work-items/WORK-2026-017_pdf-viewer-anchor.md`.
- Scope: PDF text parsing + Anchor-based source jump — schema v3
  (`resource_segment` table), pypdf page-text extraction (idempotent, bound
  to resource_version + content_hash), `GET .../pages/{n}` and
  `GET .../anchors` endpoints, anchor-aware locate (no fuzzy matching;
  drift → `source_changed`, missing → `anchor_not_found`), and a Web page-text
  viewer with a "jump to source" entry. Calculus gold 50 page anchors are the
  acceptance fixture.
- Reuses frozen Anchor v1 contract (WORK-2026-005) and safe-import resources
  (WORK-2026-016). No new canonical contract, no prompt changes.
- Explicit non-capabilities: PDF.js visual rendering, bbox highlighting,
  Markdown/TXT viewer, OCR, Chinese segmentation, cloud, encryption.
- Acceptance: TC-VIEW-001..005 — PDF parse → segments (idempotent); page-text
  endpoint positive/negative; anchors endpoint lists gold 50; drift/missing
  locate fails closed; Web viewer + jump + drift notice.
- Exact next action: commit this Ready boundary, then add failing viewer/anchor
  tests (expected ImportError/collection failure) before any implementation.

## Step 5B closure checkpoint — 2026-08-14 09:45 +08:00

- Active branch: `feature/WORK-2026-017-pdf-viewer-anchor`.
- Frozen implementation: `267fb7e3e15670fed11a8727960eec738662cbaf`
  (initial `8c3c620` + P2-1/3/4/6 fix); red baseline:
  `53eb2cd0effde49bf00b5347e03cf287131ceffa`; Ready boundary:
  `2829ff22dc5d312df7bb6aeac4c74db53cb9e7f8`.
- Role-separated QA reviewed `8c3c620` and returned PASS (0 P0/P1, 6 P2).
  P2-1 (anchor upsert returned a dangling id), P2-3 (anchor endpoints did not
  404 on missing resources), P2-4 (storage_key not guarded to workspace),
  and P2-6 (stale migrate docstring) were closed by `267fb7e` with regression
  tests. P2-2 (read-time drift check, not concurrent-atomic) and P2-5
  (front-end maps out-of-range to drift) are recorded prototype boundaries.
- Full gates pass at `267fb7e`: repository validator, Ruff, scripts + strict
  package mypy (incl. apps/api), pytest 218/218 (viewer 10/10), locked pnpm
  install/peers, Web 18/18, TypeScript check, and production build. Live e2e
  smoke via real uvicorn on the gold PDF confirmed 52-page parse, correct
  page-1 text, and out-of-range 422.
- Evidence/report: `evidence/TR-20260814-009/` and
  `docs/test-reports/TR-20260814-009_pdf-viewer-anchor.md`.
- Natural-language Step 5 progress: safe import (TR-008) + PDF page-text
  viewer/anchor jump (TR-009) done (approximately 50% of Step 5); overall
  personal MVP approximately 65%.
- Exact next action on the next "继续推进": create a separate Ready work item
  for PDF.js visual rendering and bbox highlighting (WORK-2026-018), starting
  from failing render red tests, or continue with Step 6 (undo/lock safety).
- Current blocker: none for offline Step 5/6 preparation. Real Provider/Web
  and owner acceptance remain separately gated and disabled.

## Step 5C Ready checkpoint — 2026-08-14 10:00 +08:00

- Active branch: `feature/WORK-2026-018-pdfjs-render`.
- Ready work item: `docs/work-items/WORK-2026-018_pdfjs-render.md`.
- Scope: PDF.js visual rendering + bbox highlighting — `pdfjs-dist` (6.2.108,
  already locked) renders PDF pages to canvas in the browser (local worker, no
  network), a bbox highlight layer draws `PageBboxSelector.bbox_norm` boxes
  scaled by page size, a new `GET .../resources/{rid}/file` endpoint serves the
  registered resource binary (guarded by `_storage_key_within`, 404 on missing,
  `source_changed` on drift), and the viewer switches between page-text and
  rendered views with anchor-click highlighting. Gold 50 page anchors +
  synthetic bbox anchors are the acceptance fixtures.
- Reuses schema v3 (resource_version.storage_key, anchor table) from
  WORK-2026-016/017. No new canonical contract, no migration, no prompt.
- Explicit non-capabilities: text-layer/page-text highlight linkage,
  multi-page continuous scrolling, Markdown/TXT visual rendering, OCR, cloud,
  encryption.
- Acceptance: TC-RENDER-001..004 — file endpoint positive/negative; PDF.js
  page render + flip/jump; bbox highlight position and no-box case; drift/
  missing/escape fail closed.
- Exact next action: commit this Ready boundary, then add failing render/file
  tests before any implementation. Completing this work item marks natural-
  language Step 5 100%.

## Step 5 closure checkpoint — 2026-08-14 11:40 +08:00

- Active branch: `feature/WORK-2026-018-pdfjs-render`.
- Frozen implementation: `d56e7ef07e463b114b55f749f621f11f93d80ebf`
  (initial `2601215` + P1/P2-1/P2-4 fix); red baseline:
  `275d7c6429aa870eda86184a4023f0cf8cf7d1f2`; Ready boundary:
  `54a108be875b4fb76e3331c6babc89f30e6e3c90`.
- Role-separated QA reviewed `2601215` and returned FAIL (1 P1: bbox
  highlight vertically misaligned on narrow viewports because .pdf-page had a
  fixed inline height while the canvas shrank with max-width). P1 fixed by
  `d56e7ef` (container height driven by the canvas), verified in a real
  800px headless viewport: pageH == canvasH and bbox top 20% / left 10% /
  height 15% / width 50%, aligned true. P2-1 (missing file → 404
  file_not_found) and P2-4 (drift clears activeAnchor) also closed; remaining
  P2s recorded as boundaries.
- Full gates pass at `d56e7ef`: repository validator, Ruff, scripts + strict
  package mypy (incl. apps/api), pytest 224/224 (pdf viewer 12/12, file 4/4),
  locked pnpm install/peers, Web 20/20 (incl. bbox position assertions),
  TypeScript check, and production build (dist includes pdf.worker.min.mjs).
- Real-browser auto-check (CDP headless Chrome): viewer open, text view,
  render view, canvas 979×1267, page flip, anchor jump, bbox highlight all
  pass; narrow 800px viewport bbox aligned.
- Evidence/report: `evidence/TR-20260814-010/` and
  `docs/test-reports/TR-20260814-010_pdfjs-render.md`.
- **Natural-language Step 5 is COMPLETE (100%)**: safe import (TR-008),
  PDF page-text viewer/anchor jump (TR-009), and PDF.js render/bbox highlight
  (TR-010) are all verified. Overall personal MVP is approximately 70%.
- Exact next action on the next "继续推进": enter natural-language Step 6
  (editing safety: undo/lock/crash recovery) with a separate Ready work item
  (WORK-2026-019), starting from failing undo/lock red tests.
- Current blocker: none for offline Step 6 preparation. Real Provider/Web and
  owner acceptance remain separately gated and disabled.

## Manual-verification launcher checkpoint — 2026-08-14 11:55 +08:00

- Added `uv run python -m apps.api --data-root <dir> [--port N] [--origin URL]`
  (commit `ff02c3e`) so a human can start the loopback API without a custom
  launcher; added `apps/__init__.py` + `apps/api/__init__.py` so mypy treats
  `apps.api.main` as one module. Verified: health 200, allowed origin 200,
  evil origin no ACAO header, pytest 224/224, mypy 11 source files.
- Rewrote `docs/USER_MANUAL.md` (commit `356a75e`) to match verified
  capabilities (persistence/save status, FTS5 search, safe import, PDF page
  text + PDF.js render, anchor jump + bbox highlight, drift protection) with a
  step-by-step manual acceptance checklist the workspace owner can follow.
- The workspace owner is performing manual acceptance now; any discrepancy
  should be reported and handled as red→fix→re-review.

## Delivery-check closure checkpoint — 2026-08-14 12:20 +08:00

- Two delivery-check passes closed all identified DoD gaps: local-gate
  commands synced (ruff covers packages/apps; mypy covers packages +
  apps/api; pytest via `python -m pytest`), README/AGENTS current-status
  updated, ERROR_CODE_CATALOG gained a verified-codes table (14 codes) and
  DoD checklist (telemetry metric only open), RISK-2026-013/014 registered,
  test-reports index now lists TR-004..010, ENVIRONMENT_INVENTORY local-dev
  updated, CI pytest command unified, and the Windows `uv run pytest`
  venv-repointing gap documented in OPS_LOG.
- All 13 TR evidence checksums byte-match their manifests (no drift; earlier
  mismatch reports were a check-script path/format issue).
- Commits: `bf35b18` (round 1), `f56c99e` (round 2); logs updated in
  DEVELOPMENT_LOG (3 entries) and OPS_LOG (delivery-check entry).
- Manual acceptance is handed to the workspace owner via
  `docs/USER_MANUAL.md`; next engineering step is WORK-2026-019 (Step 6).

## Delivery-check finding: main lags 64 commits; CI never executed

- Verified during delivery check on 2026-08-14: `main` still sits at
  `9e15cb4` (skeleton baseline from WORK-2026-006); the current branch
  `feature/WORK-2026-018-pdfjs-render` leads `main` by 64 commits containing
  WORK-2026-002/004/005/011..018. The feature branches form a linear
  inheritance chain but were never merged to `main`.
- The CI workflow triggers only on push to `main` or pull requests, so it has
  never actually run for any delivered work (consistent with
  ENVIRONMENT_INVENTORY `ci: declared_not_executed`).
- This is a repository-governance gap owned by WORK-2026-003 (repository,
  license, branch protection — not started), not a code defect. `main` must
  NOT be treated as the authority for current state; use
  `feature/WORK-2026-018-pdfjs-render` and checkpoint.md instead.
- Recorded in OPS_LOG (2026-08-14 12:30) and ENVIRONMENT_INVENTORY (ci row).
- Manual acceptance of delivered capabilities proceeds via
  `docs/USER_MANUAL.md` regardless of branch state.

## Step 6 startup checkpoint — 2026-08-14 16:50 +08:00

- Active branch: `feature/WORK-2026-019-patch-gate`.
- Ready work item: `docs/work-items/WORK-2026-019_patch-gate-undo-redo.md`
  (Ready boundary `4f5fbd3`, red baseline `db3cb26`).
- Scope: persistent protected GraphPatch commit gate + cross-session LIFO
  undo/redo + idempotency + atomicity. `apply_graph_patch`/`undo_graph`/
  `redo_graph` rebuild history from the persisted initial graph
  (`meta.course_graph_initial`) plus the record log, apply the change through
  `GraphHistory.apply_patch` (confirmation gate, four-dimension locks, revision
  conflict, duplicate change_id), and commit graph/record/initial/applied-count
  (`meta.course_graph_applied`) in one transaction. `save_course_graph` now uses
  whole-graph-replacement semantics (overwrites initial, clears history).
- API: `POST .../graph/patches|undo|redo`, `GET .../history`; server pins the
  trusted actor to `{"type":"user","id":"local-user"}`. New stable errors:
  `patch_invalid`(422), `patch_revision_conflict`/`target_locked`/
  `permission_denied`/`history_empty`/`history_conflict`/`record_tampered`/
  `record_invalid`(409).
- Verification: targeted gate 13/13 (apply→replay, cross-session undo/redo with
  monotonic revision 2→3→4, locked-dimension rejection, unconfirmed/stale-base
  rejection, duplicate change_id, tampered record). Full gates at `49e78eb`:
  repository validator, Ruff, mypy (scripts 9 + strict packages/api 11), pytest
  237/237, locked pnpm install/peers/check (Web 20/20)/build all pass.
- Natural-language Step 6 progress: backend commit gate + undo/redo verified in
  isolation (approximately 30% of Step 6); front-end patch save + lock/undo UI
  remain. Overall personal MVP approximately 70%.
- Exact next action: send the frozen implementation SHA to role-separated QA,
  add regression tests for any finding, then preserve evidence and move to the
  front-end patch-save / lock UI work item (WORK-2026-020). Keep real
  Provider/Web, user data, and owner acceptance disabled.
