# AI QA attempt 001 — graph replay and inverse prototype

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: graph_qa_fresh
decision: pass
reviewed_commit: 4fc8e60a392d1442f7475aa3f8082e31a1469cde
red_baseline_commit: 24257186911bede6f68c16ed18b525211d011c32
ready_commit: 9d9f569d694a969cf6c262430b99fafa0ea8e96a
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

PASS with no P0, P1, P2, or new finding.

## Independent checks

- The Ready, red, and implementation commits form a direct parent chain. The red
  commit had both history test modules but no GraphHistory API and failed with
  the documented two collection ImportErrors.
- History/security/property target suite: 18/18 passed.
- Strict contracts/domain mypy: six files passed.
- Domain import scan found no FastAPI, SQLAlchemy, parser/graph/LLM, database,
  storage, network, or I/O dependency.
- Independent mutations of entity delta, record digest, semantic hash, revision,
  record order, and duplicate change ID all failed closed.
- Two-level LIFO undo/redo, redo invalidation after a new branch, all-six-operation
  roundtrip, monotonic revision sequence, and caller-copy isolation behaved as
  specified.
- With `Path.read_text`, `open`, `socket`, and `subprocess.run` disabled, the
  in-memory path still completed.
- Record fields are limited to change ID, revisions, hashes, deltas, and digest;
  there is no whole snapshot, patch reason, or actor credential.

## Limitations

The reviewer did not repeat full pytest, locked install, Web test, or production
build; it checked their immutable implementation evidence. The initial inline
mutation process lacked `PYTHONPATH`; the reviewer corrected the read-only test
environment and completed the mutations. No network, real Provider, database,
or user data was used. This correlated machine attestation is not a human
signature, release approval, ADR acceptance, or workspace-owner acceptance.
