# AI product-scope QA machine attestation — attempt 001

```yaml
schema_version: 1
attestation_kind: machine_qa
role: ai_qa_auditor
review_subject_commit: 8ff376d0aa339143332a47500646b455148b1169
review_subject: WORK-2026-002 / PRD v0.3 / ADR-0016
decision: fail
correlation: correlated_review
human_signature: false
superseded_by: pending
recorded_at: 2026-08-14
```

## Scope and immutable handoff

The QA role reviewed the committed product-scope decision rather than the author's mutable working tree. It checked the architecture section 21 question mapping, PRD/ADR/work-item consistency, development-gate safety, and repeatable repository gates. This is a machine attestation, not a workspace-owner approval or human signature.

## Recomputed results

- Architecture questions mapped: 10/10.
- The substantive boundaries are coherent with the requested personal, local-first note and editable knowledge-tree app.
- The recorded defaults are sufficient to draft a separate offline Anchor/GraphPatch work item, while real providers, Web access, owner authentication, and user data remain disabled.
- Repository gates passed at the subject commit: 84/84 Python tests and 1/1 Web test, plus repository validation, Ruff, mypy, frozen dependency install, peer check, frontend check, and production build.

## Findings

### P1 — unverified owner approval was asserted

PRD v0.3 was marked `approved`/`approved_by: workspace_owner` and ADR-0016 was marked `accepted` even though no authenticated evidence binds the owner to those exact file contents. The user's recognition of the roadmap and instruction to continue supports reversible offline development defaults, but it must not be represented as exact formal approval or residual-risk acceptance.

Required correction: return the PRD to `in_review`, ADR-0016 to `proposed`, and state the limited authority precisely.

### P2 — frozen status records were stale

The committed work item, checkpoint, plan, traceability rows, and development log still described the baseline as pending commit/test/review. This prevents a reader from reconstructing the actual immutable input and review result.

Required correction: add a superseding status record that binds `8ff376d`, its green gates, this FAIL attempt, and the pending repair/review.

### P2 — correlated-review transition wording conflicted with the implemented policy

PRD v0.3 said correlated review could enter `machine_verified`, while the current validator intentionally returns `inconclusive` for correlated review in this prototype.

Required correction: document current fail-closed behavior; leave any future authenticated owner transition to a separately accepted product policy.

## Decision

FAIL with 1 P1 and 2 P2 findings. No P0 finding and no rejection of the substantive MVP direction. A new immutable commit and independent attempt are required; this attempt must be retained rather than overwritten.
