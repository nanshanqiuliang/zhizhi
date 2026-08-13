# AI QA Machine Attestation — Attempt 002

```yaml
attestation_type: machine_attestation
schema_version: ai-qa-report.v2
actor_type: ai_agent
role_id: ai_qa_auditor
reviewed_commit: ae834d9051553aa02a079e72ce2bf6bd8955c081
decision: pass
supersedes_qa_artifact: evidence/TR-20260813-005/ai-qa-attempt-001.md
superseded_qa_artifact_sha256: aa7803656c3647e5b1189eb20d281b00838aaedf2cd0127c05d52fee1bc1a371
subject_artifact: evidence/TR-20260813-005/ai-subject-attempt-003.md
subject_artifact_sha256: 9905ca560d6776427db4d890f498fa7f8ab68601f21b187e91590a64ea6ec2b1
network_used: false
workspace_modified: false
human_signature: false
owner_acceptance: false
correlation_classification: correlated_review
```

## Independent run and immutable bindings

This was a new, role-separated, read-only QA run. It did not inherit subject-review search summaries, inspect hidden reasoning, modify repository files, commit, or use the network.

Both prior artifacts were read directly from Git objects at `ae834d9051553aa02a079e72ce2bf6bd8955c081` and hashed as raw bytes:

```yaml
qa_attempt_001:
  sha256: aa7803656c3647e5b1189eb20d281b00838aaedf2cd0127c05d52fee1bc1a371
  reviewed_commit: db0831b0806d82e7bab95e2ad804bfe69e8d81cd
  decision: fail
  subject_binding: 9905ca560d6776427db4d890f498fa7f8ab68601f21b187e91590a64ea6ec2b1
subject_attempt_003:
  sha256: 9905ca560d6776427db4d890f498fa7f8ab68601f21b187e91590a64ea6ec2b1
  reviewed_commit: db0831b0806d82e7bab95e2ad804bfe69e8d81cd
  decision: accept
```

The bindings are internally consistent. No external proof establishes model/provider independence between subject and QA agents, so this attestation conservatively declares `correlated_review`.

## Attempt-001 regression replay

All three P1 and three P2 mutations now fail closed:

| Prior finding | Mutation result |
|---|---|
| P1 mock relabeled `controlled_live` and promoted to `machine_verified` | Rejected: `controlled_live execution is not implemented in this prototype` |
| P1 empty subject/QA trace | Rejected by 120-item trace contract |
| P1 falsified trace query hash, result hash, and `status=denied` | Rejected: `tool audit trace mismatch` |
| P1 spoofed, expired owner acceptance | Rejected: authenticated owner boundary is not implemented |
| P2 finding claim substituted while retaining original item identity | Rejected: `claim_id does not match item identity` |
| P2 attacker-defined self-consistent tool-policy provenance | Rejected: `tool_policy version/hash mismatch` |
| P2 adjudicator sharing subject session | Rejected: adjudication requires a distinct session |

Additional combinations also passed their expected fail-closed behavior:

- Adjudicator sharing the QA session: rejected.
- Adjudicator tool-policy substitution: rejected.
- Duplicate/misaligned evidence claim coverage: rejected.
- Duplicate/swapped trace call identity: rejected.
- Mock review promoted to `machine_reviewed`: rejected.
- Any owner-acceptance object, even future-dated, is rejected while authentication is unavailable.
- Reordering a complete, valid trace remains accepted; ordering is not part of its semantic identity.
- Unmodified deterministic mock baseline remains valid and `inconclusive`.

## Diff review

Reviewed `db0831b0806d82e7bab95e2ad804bfe69e8d81cd..ae834d9051553aa02a079e72ce2bf6bd8955c081`, including implementation, schema, regression tests, and frozen evidence.

The change:

- disables unavailable controlled-live and owner-authentication paths;
- binds provenance to the effective role tool policy and harness version;
- requires exact subject/QA replay-trace coverage;
- binds each trace call ID, query hash, result hash, tool, and status to replay evidence;
- derives finding claim identity from item kind and ID;
- isolates adjudicator run and session from subject and QA;
- adds exact 120-item trace cardinality for subject and QA artifacts.

No new P0, P1, or P2 finding was identified.

## Repository gates

```text
uv sync --locked --group dev
exit 0

uv run python -m scripts.validate_repository
exit 0 — repository validator passed; mock/replay state remained inconclusive

uv run ruff format --check scripts tests
exit 0 — 17 files already formatted

uv run ruff check .
exit 0

uv run mypy scripts
exit 0 — no issues in 9 source files

uv run pytest
exit 0 — 84 passed

pnpm install --frozen-lockfile
exit 0 — already up to date

pnpm peers check
exit 0 — no peer dependency issues

pnpm check
exit 0 — TypeScript, ESLint, and 1 web test passed

pnpm build
exit 0 — production build succeeded
```

`git diff --check db0831b…ae834d9…` also exited successfully.

## Residual risks and limitations

- This validates only the deterministic mock/replay prototype. It does not establish subject-matter correctness or product eligibility.
- Real-provider, controlled-live, and authenticated owner-acceptance paths remain deliberately unavailable and fail closed.
- Same-model/provider correlation remains possible; `pass` means the reviewed deterministic controls close the six frozen QA findings, not that epistemic independence was achieved.
- No new full visual review of all 52 PDF pages was performed because the data/PDF content did not change in this fix.
- During the run, another actor modified `checkpoint.md`. That unrelated concurrent change was preserved and was not used as audit evidence; all reviewed implementation paths remained bound to immutable commit `ae834d9`.
- This is an AI machine attestation, not a human signature, workspace-owner acceptance, release approval, or authorization to enable live providers.
