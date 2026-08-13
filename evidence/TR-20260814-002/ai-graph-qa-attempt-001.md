# AI QA attempt 001 — Anchor / GraphPatch v1

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: graph_qa_fresh
decision: fail
reviewed_commit: a25470c1a25bedaf57ff4beba9204bd255d75a2a
red_baseline_commit: 44b623305eb5f01de85f15f1089dbc71ad1f73b7
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Findings

- P0: none.
- P1: `preview_graph_patch()` cold-start validation indirectly calls
  `Path.read_text()` through the contracts package. The domain service therefore
  depends on repository file I/O and may fail once installed away from the
  repository layout.
- P2: the frozen documentation called the three-file target suite `53/53`, while
  those three files contain 49 tests. The additional four graph-related tests
  are repository integration tests and must be reported separately.

## Independent checks

- Git binding: `a25470c` had a clean worktree and exactly one parent,
  `44b6233`. The parent contains the tests importing absent APIs, so the
  red-to-green order is credible.
- Target suite: 49 passed.
- Repository validator: passed.
- Strict package mypy: four files passed.
- TypeScript generation drift and `tsc --noEmit`: passed.
- Mutations rejected actor spoofing; apply-ready non-user drafts; four lock
  dimensions; base/target revision drift; self/long cycles and duplicate edges;
  missing AI evidence; and origin forgery. Determinism and input immutability
  tests passed.
- Direct dependency scan found no FastAPI, SQLAlchemy, parser, graph, LLM,
  storage, or network-library import in the domain module. The indirect schema
  file read remains the P1 failure.

## Limitations

The reviewer did not rerun full pytest, locked installs, Web build, real
Provider, or network checks. It inspected the existing evidence for those
gates. This failed machine review is not a human signature, release approval,
or workspace-owner risk acceptance and must remain preserved after a
superseding review.
