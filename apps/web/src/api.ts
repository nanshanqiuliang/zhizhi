// Local persistence API client (WORK-2026-014).
//
// The React workspace speaks `WorkspaceSnapshot`; this module converts between
// that UI shape and the canonical CourseGraph v1 contract that the local
// FastAPI sidecar stores via `knowledge_tree_infrastructure.workspace`.

export type ConceptNode = {
  id: string;
  title: string;
  note: string;
  x: number;
  y: number;
  positionLocked: boolean;
  tone: "root" | "branch" | "leaf";
};

export type ConceptEdge = {
  from: string;
  to: string;
};

export type WorkspaceSnapshot = {
  nodes: ConceptNode[];
  edges: ConceptEdge[];
};

export type SearchResultItem = {
  id: string;
  label: string;
  snippet: string;
};

export type ResourceInfo = {
  id: string;
  display_name: string;
  mime: string;
  byte_size: number;
  content_hash: string;
  created_at: string;
};

export interface PersistApi {
  loadGraph(): Promise<WorkspaceSnapshot | null>;
  saveGraph(graph: WorkspaceSnapshot): Promise<void>;
  searchGraph(query: string): Promise<SearchResultItem[]>;
  importResource(file: File): Promise<ResourceInfo>;
  listResources(): Promise<ResourceInfo[]>;
}

const WORKSPACE_ID = "00000000-0000-7000-8000-000000000001";
const COURSE_ID = "00000000-0000-7000-8000-000000000002";

// Deterministic per-session internal id -> canonical UUIDv7 mapping so repeated
// saves of the same node do not drift.
const canonicalIds = new Map<string, string>();

function isUuidV7(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(
    value,
  );
}

export function uuidv7(): string {
  const bytes = new Uint8Array(16);
  const time = BigInt(Date.now());
  bytes[0] = Number((time >> 40n) & 0xffn);
  bytes[1] = Number((time >> 32n) & 0xffn);
  bytes[2] = Number((time >> 24n) & 0xffn);
  bytes[3] = Number((time >> 16n) & 0xffn);
  bytes[4] = Number((time >> 8n) & 0xffn);
  bytes[5] = Number(time & 0xffn);
  const random = crypto.getRandomValues(new Uint8Array(10));
  bytes[6] = 0x70 | (random[0] & 0x0f);
  bytes[7] = random[1];
  bytes[8] = 0x80 | (random[2] & 0x3f);
  bytes.set(random.slice(3), 9);
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

function toCanonicalId(internalId: string): string {
  if (isUuidV7(internalId)) return internalId;
  const existing = canonicalIds.get(internalId);
  if (existing) return existing;
  const generated = uuidv7();
  canonicalIds.set(internalId, generated);
  return generated;
}

function edgeId(from: string, to: string): string {
  const key = `${from}->${to}`;
  return toCanonicalId(key);
}

// Convert the UI snapshot into a canonical CourseGraph v1 payload.
export function snapshotToGraph(snapshot: WorkspaceSnapshot): Record<string, unknown> {
  const concepts = snapshot.nodes.map((node) => ({
    id: toCanonicalId(node.id),
    course_id: COURSE_ID,
    label: node.title,
    origin: "user",
    review_state: "accepted",
    confidence: null,
    evidence_ids: [],
    locks: { content: false, relations: false, position: false, annotations: false },
    annotations: node.note ? [{ kind: "note", value: node.note }] : [],
    revision_no: 0,
  }));
  const edges = snapshot.edges.map((edge) => ({
    id: edgeId(edge.from, edge.to),
    course_id: COURSE_ID,
    source_concept_id: toCanonicalId(edge.from),
    target_concept_id: toCanonicalId(edge.to),
    edge_type: "related_to",
    origin: "user",
    review_state: "accepted",
    confidence: null,
    evidence_ids: [],
    locked: false,
    revision_no: 0,
  }));
  const layout_items = snapshot.nodes.map((node) => ({
    view_id: WORKSPACE_ID,
    concept_id: toCanonicalId(node.id),
    x: node.x,
    y: node.y,
    pinned: node.positionLocked,
    revision_no: 0,
  }));
  return {
    schema_version: 1,
    workspace_id: WORKSPACE_ID,
    course_id: COURSE_ID,
    revision_no: 0,
    concepts,
    edges,
    layout_items,
  };
}

type CanonicalGraph = {
  concepts?: Array<Record<string, unknown>>;
  edges?: Array<Record<string, unknown>>;
  layout_items?: Array<Record<string, unknown>>;
};

// Convert a canonical CourseGraph back into the UI snapshot.
export function graphToSnapshot(graph: CanonicalGraph): WorkspaceSnapshot {
  const concepts = graph.concepts ?? [];
  const layout = new Map(
    (graph.layout_items ?? []).map((item) => [String(item.concept_id), item]),
  );
  const edges = graph.edges ?? [];
  const childrenOf = new Map<string, number>();
  const parentsOf = new Map<string, number>();
  for (const edge of edges) {
    const from = String(edge.source_concept_id);
    const to = String(edge.target_concept_id);
    childrenOf.set(from, (childrenOf.get(from) ?? 0) + 1);
    parentsOf.set(to, (parentsOf.get(to) ?? 0) + 1);
  }
  const nodes = concepts.map((concept) => {
    const id = String(concept.id);
    const annotations = Array.isArray(concept.annotations) ? concept.annotations : [];
    const noteAnnotation = annotations.find(
      (annotation) => annotation?.kind === "note",
    );
    const item = layout.get(id);
    const hasParent = (parentsOf.get(id) ?? 0) > 0;
    const hasChildren = (childrenOf.get(id) ?? 0) > 0;
    const tone: ConceptNode["tone"] = !hasParent ? "root" : hasChildren ? "branch" : "leaf";
    return {
      id,
      title: String(concept.label ?? "未命名"),
      note: noteAnnotation?.value != null ? String(noteAnnotation.value) : "",
      x: typeof item?.x === "number" ? item.x : 0,
      y: typeof item?.y === "number" ? item.y : 0,
      positionLocked: item?.pinned === true,
      tone,
    };
  });
  return {
    nodes,
    edges: edges.map((edge) => ({
      from: String(edge.source_concept_id),
      to: String(edge.target_concept_id),
    })),
  };
}

export function httpPersistApi(baseUrl: string): PersistApi {
  const endpoint = `${baseUrl.replace(/\/$/, "")}/api/workspaces/${WORKSPACE_ID}/graph`;
  return {
    async loadGraph(): Promise<WorkspaceSnapshot | null> {
      const response = await fetch(endpoint);
      if (response.status === 404) return null;
      if (!response.ok) {
        throw new Error(`load failed: ${response.status}`);
      }
      return graphToSnapshot((await response.json()) as CanonicalGraph);
    },
    async saveGraph(graph: WorkspaceSnapshot): Promise<void> {
      const response = await fetch(endpoint, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(snapshotToGraph(graph)),
      });
      if (!response.ok) {
        throw new Error(`save failed: ${response.status}`);
      }
    },
    async searchGraph(query: string): Promise<SearchResultItem[]> {
      const searchEndpoint = `${baseUrl.replace(/\/$/, "")}/api/workspaces/${WORKSPACE_ID}/search?q=${encodeURIComponent(query)}`;
      const response = await fetch(searchEndpoint);
      if (!response.ok) {
        throw new Error(`search failed: ${response.status}`);
      }
      const body = (await response.json()) as { results: SearchResultItem[] };
      return body.results;
    },
    async importResource(file: File): Promise<ResourceInfo> {
      const form = new FormData();
      form.append("file", file);
      const response = await fetch(
        `${baseUrl.replace(/\/$/, "")}/api/workspaces/${WORKSPACE_ID}/resources`,
        { method: "POST", body: form },
      );
      if (!response.ok) {
        throw new Error(`import failed: ${response.status}`);
      }
      return (await response.json()) as ResourceInfo;
    },
    async listResources(): Promise<ResourceInfo[]> {
      const response = await fetch(
        `${baseUrl.replace(/\/$/, "")}/api/workspaces/${WORKSPACE_ID}/resources`,
      );
      if (!response.ok) {
        throw new Error(`list failed: ${response.status}`);
      }
      const body = (await response.json()) as { resources: ResourceInfo[] };
      return body.resources;
    },
  };
}
