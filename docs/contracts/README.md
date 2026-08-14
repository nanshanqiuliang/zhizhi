# Contract snapshots

Versioned JSON Schema and OpenAPI snapshots belong here. A contract may be implemented as a reversible stage prototype before its ADR receives exact owner acceptance; its status and authority must be stated in the active work item and test report.

- `knowledge-tree-graph.v1.schema.json` is the canonical WORK-2026-005 source for Anchor v1, CourseGraph snapshot v1, GraphPatch v1, operations, IDs, enums and locks.
- `llm.v1.schema.json` is the canonical WORK-2026-007 source for the LLM port: ProviderId/ProtocolId/MessageRole/ContentPartKind/FinishReason/CapabilityName/LlmErrorCode (15 stable error codes), ContentPart, CanonicalMessage, ToolDefinition, CanonicalToolCall, CanonicalUsage, Budget, TraceContext, GenerationRequest, GenerationResult and CapabilitySet.
- Python validates directly against these documents through `packages/contracts-py` (generated runtime artifacts for both v1 schemas).
- TypeScript public enums are generated into `packages/contracts-ts/src/generated`; `pnpm check` fails on drift. LLM TypeScript enums are intentionally deferred until the Web layer consumes the LLM port (roadmap Step 8).
- Cross-field graph/anchor invariants that JSON Schema cannot express live in the pure domain/contract validators and have tests; they do not create a second enum source.
- `GraphPatch.actor` is an audit declaration, not authentication. The application composition root must pass trusted actor type/ID from outside the untrusted payload; the pure validator rejects any mismatch.

Existing LLM configuration schemas remain under `config/llm/schema` because they validate deploy-time configuration.
