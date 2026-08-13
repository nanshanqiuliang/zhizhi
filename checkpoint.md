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
- Eight regression tests for those findings have been added to `tests/contract/test_ai_review_harness.py`; the last recorded targeted run was intentionally red: 8 failed, 31 passed.

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

1. Implement the six QA closures against the eight red regression tests.
2. Rerun targeted tests, then the full mandated repository gates.
3. Commit the fix with the required Conventional Commit body and evidence references.
4. Ask the role-separated QA agent to audit the new immutable commit/artifact, recording model/provider correlation.
5. Save the superseding QA evidence and hashes; update `DEVELOPMENT_LOG`, `OPS_LOG`, `ENGINEERING_PLAN`, `TRACEABILITY_MATRIX`, the active work item, and user-facing documentation as required by the Definition of Done.
6. Run final gates, commit the documentation/evidence closure, and verify a clean worktree.

## Current risks or blockers

- No external blocker is known.
- The current worktree is intentionally red until the QA findings are implemented.
- Real-provider execution and owner authentication are explicitly out of scope and must remain disabled.
- Subject and QA attestations may be correlated because the available agents can share a model/provider family; the evidence must disclose that correlation and cannot impersonate a human signature.

## Exact next action

Patch `scripts/ai_review_harness.py` and `evals/calculus-v1/schema/machine-review.schema.json` so the eight new tests fail closed for live-mode relabeling, incomplete/tampered traces, unauthenticated owner acceptance, claim-ID substitution, policy-provenance substitution, and adjudicator session reuse; then run the targeted contract test file.
