# WORK-2026-004 recovery checkpoint

Updated: 2026-08-13 (Asia/Shanghai)

## Original objective

Continue the repository's current active development work after reading the governing documents and engineering logs. The recovered active scope is `WORK-2026-004_calculus-gold-dataset`: deliver the smallest deterministic, role-separated AI review v2 prototype and its contracts/evidence without enabling a real provider or live test.

## Recovered completion state

- Branch: `feature/WORK-2026-004-calculus-gold`.
- Committed implementation chain:
  - `73a74da` — deterministic AI review v2 prototype.
  - `3f9b637` — replay evidence, claim/position binding, adjudication evidence, and assurance hardening.
  - `db0831b` — subject-evidence assurance and adjudication-position bypass closure.
- The deterministic harness, review policy v2, machine-review/review-policy schemas, repository validator integration, and contract tests are present.
- The independent subject reviewer accepted `db0831b` after three attempts.
- Four uncommitted immutable-handoff summaries exist under `evidence/TR-20260813-005/` (three subject attempts and one QA attempt).
- The independent QA attempt reran the repository gates successfully but returned FAIL because of three P1 and three P2 semantic bypasses.
- Eight regression tests for those findings were added to `tests/contract/test_ai_review_harness.py`; the recovered red baseline was 8 failed, 31 passed.
- All six findings are now closed in commit `ae834d9051553aa02a079e72ce2bf6bd8955c081`; the targeted harness suite passes 39/39.

## Key decisions

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

- No implementation, verification, QA, evidence, or documentation work remains in WORK-2026-004 scope.
- The closure changes are ready for their final Conventional Commit; after that, only confirm HEAD and a clean worktree.

## Current risks or blockers

- No blocker remains for WORK-2026-004 closure.
- Real-provider execution and owner authentication are explicitly out of scope and must remain disabled.
- Subject and QA attestations may be correlated because the available agents can share a model/provider family; the evidence must disclose that correlation and cannot impersonate a human signature.

## Verification after recovery

- Targeted contract suite: 39/39 passed.
- Full local gates at `ae834d9`: repository validator passed; Ruff format/lint passed; mypy passed; pytest 84/84 passed; pnpm frozen install/peer check/web check/web build passed.
- No live provider, network search, secret, database, or owner-authentication path was enabled.
- Role-separated QA attempt 002 passed immutable commit `ae834d9`, superseded the preserved FAIL attempt 001, and found no new P0/P1/P2; correlation remains conservatively classified as `correlated_review`.
- Final post-documentation gates also passed: repository validator, Ruff format/lint, mypy, pytest 84/84, pnpm frozen install/peers/check, Web 1/1, and production build.

## Exact next action

On recovery, first verify the closure commit exists and `git status --short` is empty. Do not start a new main stage automatically: follow `docs/ENGINEERING_PLAN.md`, where the next dependency is workspace-owner review of WORK-2026-001/002 decisions; keep real Provider/Web and owner acceptance disabled meanwhile.
