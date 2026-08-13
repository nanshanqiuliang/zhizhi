/**
 * Generated from docs/contracts/knowledge-tree-graph.v1.schema.json.
 * Do not hand-edit. Re-run: pnpm --filter @knowledge-tree/contracts-ts generate
 */

export type UuidV7 = string;
export type Sha256 = `sha256:${string}`;
export type Origin = "user" | "ai" | "import" | "system";
export type ReviewState = "unsupported_draft" | "proposed" | "accepted" | "locked" | "rejected";
export type EdgeType = "prerequisite_of" | "related_to" | "part_of" | "example_of";
export type LockDimension = "content" | "relations" | "position" | "annotations";
export type AnchorStatus = "valid" | "recovered" | "ambiguous" | "drifted" | "missing";
export type GraphPatchOperation = "create_concept" | "update_concept" | "create_edge" | "set_lock" | "upsert_annotation" | "set_layout_item";

export const graphContractSchemaVersion = 1 as const;
