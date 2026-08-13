# Contract snapshots

Versioned JSON Schema and OpenAPI snapshots belong here. A contract may be implemented as a reversible stage prototype before its ADR receives exact owner acceptance; its status and authority must be stated in the active work item and test report.

- `knowledge-tree-graph.v1.schema.json` is the canonical WORK-2026-005 source for Anchor v1, CourseGraph snapshot v1, GraphPatch v1, operations, IDs, enums and locks.
- Python validates directly against this document through `packages/contracts-py`.
- TypeScript public enums are generated into `packages/contracts-ts/src/generated`; `pnpm check` fails on drift.
- Cross-field graph/anchor invariants that JSON Schema cannot express live in the pure domain/contract validators and have tests; they do not create a second enum source.
- `GraphPatch.actor` is an audit declaration, not authentication. The application composition root must pass trusted actor type/ID from outside the untrusted payload; the pure validator rejects any mismatch.

Existing LLM configuration schemas remain under `config/llm/schema` because they validate deploy-time configuration.
