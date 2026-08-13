# Knowledge Tree App development checkpoint

Updated: 2026-08-14 (Asia/Shanghai)

## Original objective

Continue the repository's current active development work after reading the governing documents and engineering logs. The product objective is a Windows, local-first personal note App in which the user can write/import notes, manually edit a tree-shaped knowledge graph, and let AI generate source-linked graph drafts without bypassing preview, confirmation, locks, history, or validation.

The user has now defined a persistent communication convention: future requests such as “继续推进” must use `docs/USER_FACING_DEVELOPMENT_ROADMAP.md`, state the current natural-language step and progress at the beginning/end, then continue actual implementation rather than returning only a plan.

The current user request is “继续开发”. Work has resumed at natural-language Step 1 (MVP scope decisions), with intent to enter Step 2 (Anchor/GraphPatch contracts) once those decisions are frozen and verified.

## Recovered completion state

- WORK-2026-004 is closed by commits `90e13d0` and `ae834d9`; its final evidence is `TR-20260813-005`.
- The user-facing roadmap was committed at `5b0bc1c`.
- Current branch: `feature/WORK-2026-002-mvp-decisions`.
- Current natural-language step: Step 1, QA correction, approximately 85%; overall personal MVP approximately 15%.
- Commit `8ff376d0aa339143332a47500646b455148b1169` records the WORK-2026-002 / PRD v0.3 / ADR-0016 safe-default baseline. The ten architecture section 21 questions are mapped 10/10 and all repository gates passed at that commit.
- Role-separated QA attempt 001 returned FAIL with 1 P1 and 2 P2 evidence/governance findings: unverified exact owner approval, stale frozen status records, and correlated-review wording inconsistent with the current fail-closed validator. It did not reject the substantive MVP scope.
- The superseding correction candidate and preserved FAIL attestation under `evidence/TR-20260814-001/` are contained in the current commit once this checkpoint is recorded; WORK-2026-005 exists only as a `proposed` draft and no Step 2 implementation has begun.
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

- The superseding WORK-2026-002 status and attempt-001 evidence are synchronized and all repository gates pass; its complete commit SHA must be bound by QA attempt 002.
- Obtain role-separated QA against the complete correction SHA; preserve attempt 002 and issue a repeatable test report.
- If QA passes, close the Step 1 development-default gate without impersonating owner approval, make WORK-2026-005 Ready, switch to `feature/WORK-2026-005-anchor-graphpatch-v1`, and begin Step 2 with failing Anchor/GraphPatch contract tests.

## Current risks or blockers

- No substantive blocker remains for the local, offline contract path; the current gate is evidence correction plus QA re-review.
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

## Exact next action

Send the current immutable HEAD SHA to `ai_qa_auditor`. If it passes, freeze the QA evidence, mark WORK-2026-005 Ready, switch to its feature branch, and create the first deliberately failing contract tests. Keep real Provider/Web, user data, database writes, and owner acceptance disabled.
