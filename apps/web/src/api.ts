// Local persistence API client (WORK-2026-014).
//
// The React workspace speaks `WorkspaceSnapshot`; this module converts between
// that UI shape and the canonical CourseGraph v1 contract that the local
// FastAPI sidecar stores via `knowledge_tree_infrastructure.workspace`.

export type ConceptLocks = {
  content: boolean;
  relations: boolean;
  position: boolean;
  annotations: boolean;
};

export type ConceptNode = {
  id: string;
  title: string;
  note: string;
  x: number;
  y: number;
  positionLocked: boolean;
  tone: "root" | "branch" | "leaf";
  locks?: ConceptLocks;
  revisionNo?: number;
  links?: string[];
  evidenceIds?: string[];
};

export type EdgeKind = "prerequisite_of" | "related_to" | "part_of" | "example_of";

export const EDGE_KINDS: readonly EdgeKind[] = [
  "prerequisite_of",
  "related_to",
  "part_of",
  "example_of",
];

export type ConceptEdge = {
  from: string;
  to: string;
  edge_type?: EdgeKind;
};

export type WorkspaceSnapshot = {
  nodes: ConceptNode[];
  edges: ConceptEdge[];
  revisionNo?: number;
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

export type PageText = {
  resource_version_id: string;
  page: number;
  text: string;
  text_hash: string;
};

export type AnchorRef = {
  id: string;
  page: number;
  label: string;
  bboxNorm?: [number, number, number, number];
};

export type HistoryRecord = {
  change_id: string;
  before_revision_no: number;
  after_revision_no: number;
  source: string;
};

export type DraftConcept = {
  label: string;
  aliases: string[];
  confidence: number;
  evidence_ids: string[];
};

export type DraftRelation = {
  source_label: string;
  target_label: string;
  edge_type: string;
  confidence: number;
  evidence_ids: string[];
};

export type DraftEvidence = {
  anchor_id: string;
  resource_id: string;
  label: string;
};

export type AiDraftResult = {
  draft: {
    concepts: DraftConcept[];
    relations: DraftRelation[];
  };
  patch: Record<string, unknown>;
  evidence?: DraftEvidence[];
};

export type AnswerSource = {
  id: string;
  label: string;
  kind: string;
};

export type AnswerResult = {
  answer: string;
  sources: AnswerSource[];
  note?: string;
};

export type CommandResult = {
  summary: string;
  patch: Record<string, unknown>;
};

export type ExternalProposal = {
  proposal_id: string;
  created_at: string;
  origin: string;
  note: string;
  status: string;
  operations_count: number;
};

export type WebSearchSettings = {
  provider: string;
  configured: boolean;
  enabled: boolean;
};

export type WebSearchSource = {
  title: string;
  url: string;
};

export type ConceptAnchor = {
  anchor_id: string;
  resource_id: string;
  page: number;
  label: string;
  resource_name: string;
  mime: string;
};

export interface PersistApi {
  loadGraph(): Promise<WorkspaceSnapshot | null>;
  saveGraph(graph: WorkspaceSnapshot): Promise<void>;
  searchGraph(query: string): Promise<SearchResultItem[]>;
  importResource(file: File): Promise<ResourceInfo>;
  listResources(): Promise<ResourceInfo[]>;
  parsePdf(resourceId: string): Promise<{ page_count: number }>;
  getPageText(resourceId: string, page: number): Promise<PageText>;
  listAnchors(resourceId: string): Promise<AnchorRef[]>;
  getFileUrl(resourceId: string): string;
  getResourceText(resourceId: string): Promise<string>;
  openResourcesDir?(): Promise<{ status: string; path: string }>;
  revealResource?(resourceId: string): Promise<{ status: string; path: string }>;
  getAiSettings?(): Promise<{ configured: boolean; enabled: boolean }>;
  setAiKey?(apiKey: string): Promise<{ status: string; configured: boolean }>;
  clearAiKey?(): Promise<{ status: string; configured: boolean }>;
  listWorkspaces?(): Promise<
    Array<{ id: string; name: string; concept_count: number; updated_at: number | string }>
  >;
  createWorkspace?(name: string): Promise<{ id: string; name: string }>;
  generateDraft(resourceId?: string): Promise<AiDraftResult>;
  acceptDraft(
    patch: Record<string, unknown>,
    evidence: DraftEvidence[],
  ): Promise<{ status: string; change_id: string; revision_no: number }>;
  askQuestion(question: string): Promise<AnswerResult>;
  interpretCommand(command: string): Promise<CommandResult>;
  acceptCommand(patch: Record<string, unknown>): Promise<{
    status: string;
    change_id: string;
    revision_no: number;
  }>;
  applyPatch(patch: Record<string, unknown>): Promise<{
    status: string;
    change_id: string;
    revision_no: number;
  }>;
  undoGraph(): Promise<{ status: string; revision_no: number }>;
  redoGraph(): Promise<{ status: string; revision_no: number }>;
  backupGraph(): Promise<{ status: string; backup_path: string }>;
  listBackups(): Promise<string[]>;
  restoreBackup(filename: string): Promise<{ status: string }>;
  listHistory(): Promise<HistoryRecord[]>;
  listProposals?(): Promise<ExternalProposal[]>;
  acceptProposal?(
    proposalId: string,
  ): Promise<{ status: string; change_id: string; revision_no: number }>;
  rejectProposal?(proposalId: string): Promise<{ status: string }>;
  getGraphImageDownloadUrl?(): string;
  getWebSearchSettings?(): Promise<WebSearchSettings>;
  setWebSearchKey?(
    provider: string,
    apiKey: string,
  ): Promise<{ status: string; configured: boolean; provider: string }>;
  clearWebSearchKey?(): Promise<{ status: string; configured: boolean }>;
  generateSearchDraft?(query: string): Promise<AiDraftResult & { sources: WebSearchSource[] }>;
  listConceptAnchors?(conceptId: string): Promise<ConceptAnchor[]>;
}

const WORKSPACE_ID = "00000000-0000-7000-8000-000000000001";
const COURSE_ID = "00000000-0000-7000-8000-000000000002";

// The first/sample course workspace; `httpPersistApi` targets it by default and
// the UI rebuilds its api for other workspaces.
export const DEFAULT_WORKSPACE_ID = WORKSPACE_ID;

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
    evidence_ids: node.evidenceIds ?? [],
    locks: {
      content: node.locks?.content ?? false,
      relations: node.locks?.relations ?? false,
      position: node.locks?.position ?? node.positionLocked,
      annotations: node.locks?.annotations ?? false,
    },
    annotations: [
      ...(node.note ? [{ kind: "note", value: node.note }] : []),
      ...(node.links ?? []).map((url, index) => ({
        kind: `link_${index + 1}`,
        value: url,
      })),
    ],
    revision_no: node.revisionNo ?? 0,
  }));
  const edges = snapshot.edges.map((edge) => ({
    id: edgeId(edge.from, edge.to),
    course_id: COURSE_ID,
    source_concept_id: toCanonicalId(edge.from),
    target_concept_id: toCanonicalId(edge.to),
    edge_type: edge.edge_type ?? "related_to",
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
    revision_no: node.revisionNo ?? 0,
  }));
  return {
    schema_version: 1,
    workspace_id: WORKSPACE_ID,
    course_id: COURSE_ID,
    revision_no: snapshot.revisionNo ?? 0,
    concepts,
    edges,
    layout_items,
  };
}

type CanonicalGraph = {
  revision_no?: unknown;
  concepts?: Array<Record<string, unknown>>;
  edges?: Array<Record<string, unknown>>;
  layout_items?: Array<Record<string, unknown>>;
};

function readLocks(concept: Record<string, unknown>): ConceptLocks {
  const raw = concept.locks;
  const locks =
    raw && typeof raw === "object"
      ? (raw as Record<string, unknown>)
      : {};
  return {
    content: locks.content === true,
    relations: locks.relations === true,
    position: locks.position === true,
    annotations: locks.annotations === true,
  };
}

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
    const linkAnnotations = annotations
      .filter((annotation) => /^link_\d+$/.test(String(annotation?.kind ?? "")))
      .sort(
        (a, b) =>
          Number(String(a?.kind).slice(5)) - Number(String(b?.kind).slice(5)),
      );
    const item = layout.get(id);
    const hasParent = (parentsOf.get(id) ?? 0) > 0;
    const hasChildren = (childrenOf.get(id) ?? 0) > 0;
    const tone: ConceptNode["tone"] = !hasParent ? "root" : hasChildren ? "branch" : "leaf";
    const locks = readLocks(concept);
    const evidenceIds = Array.isArray(concept.evidence_ids)
      ? concept.evidence_ids.map(String)
      : [];
    return {
      id,
      title: String(concept.label ?? "未命名"),
      note: noteAnnotation?.value != null ? String(noteAnnotation.value) : "",
      x: typeof item?.x === "number" ? item.x : 0,
      y: typeof item?.y === "number" ? item.y : 0,
      positionLocked: locks.position || item?.pinned === true,
      tone,
      locks,
      revisionNo: typeof concept.revision_no === "number" ? concept.revision_no : 0,
      links: linkAnnotations
        .map((annotation) => String(annotation?.value ?? ""))
        .filter(Boolean),
      evidenceIds,
    };
  });
  return {
    nodes,
    edges: edges.map((edge) => ({
      from: String(edge.source_concept_id),
      to: String(edge.target_concept_id),
      edge_type: EDGE_KINDS.includes(edge.edge_type as EdgeKind)
        ? (edge.edge_type as EdgeKind)
        : undefined,
    })),
    revisionNo: typeof graph.revision_no === "number" ? graph.revision_no : 0,
  };
}

export function httpPersistApi(
  baseUrl: string,
  workspaceId: string = WORKSPACE_ID,
): PersistApi {
  const workspaceBase = `${baseUrl.replace(/\/$/, "")}/api/workspaces/${workspaceId}`;
  const endpoint = `${workspaceBase}/graph`;
  return {
    async loadGraph(): Promise<WorkspaceSnapshot | null> {
      const response = await fetch(endpoint);
      if (response.status === 404) return null;
      if (!response.ok) {
        const body = await readError(response);
        throw new Error(formatCode(body) || `load failed: ${response.status}`);
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
        const body = await readError(response);
        throw new Error(formatCode(body) || `save failed: ${response.status}`);
      }
    },
    async applyPatch(patch: Record<string, unknown>): Promise<{
      status: string;
      change_id: string;
      revision_no: number;
    }> {
      const response = await fetch(`${endpoint}/patches`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      if (!response.ok) {
        const body = await readError(response);
        throw new Error(formatCode(body) || `patch failed: ${response.status}`);
      }
      return (await response.json()) as {
        status: string;
        change_id: string;
        revision_no: number;
      };
    },
    async undoGraph(): Promise<{ status: string; revision_no: number }> {
      const response = await fetch(`${endpoint}/undo`, { method: "POST" });
      if (!response.ok) {
        const body = await readError(response);
        throw new Error(formatCode(body) || `undo failed: ${response.status}`);
      }
      return (await response.json()) as { status: string; revision_no: number };
    },
    async redoGraph(): Promise<{ status: string; revision_no: number }> {
      const response = await fetch(`${endpoint}/redo`, { method: "POST" });
      if (!response.ok) {
        const body = await readError(response);
        throw new Error(formatCode(body) || `redo failed: ${response.status}`);
      }
      return (await response.json()) as { status: string; revision_no: number };
    },
    async backupGraph(): Promise<{ status: string; backup_path: string }> {
      const response = await fetch(`${workspaceBase}/backup`, { method: "POST" });
      if (!response.ok) {
        const body = await readError(response);
        throw new Error(formatCode(body) || `backup failed: ${response.status}`);
      }
      return (await response.json()) as { status: string; backup_path: string };
    },
    async listBackups(): Promise<string[]> {
      const response = await fetch(`${workspaceBase}/backups`);
      if (!response.ok) {
        throw new Error(`list backups failed: ${response.status}`);
      }
      const body = (await response.json()) as { backups: string[] };
      return body.backups;
    },
    async restoreBackup(filename: string): Promise<{ status: string }> {
      const response = await fetch(`${workspaceBase}/restore`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename }),
      });
      if (!response.ok) {
        const body = await readError(response);
        throw new Error(formatCode(body) || `restore failed: ${response.status}`);
      }
      return (await response.json()) as { status: string };
    },
    async listHistory(): Promise<HistoryRecord[]> {
      const response = await fetch(`${workspaceBase}/history`);
      if (!response.ok) {
        throw new Error(`history failed: ${response.status}`);
      }
      const body = (await response.json()) as { records: HistoryRecord[] };
      return body.records;
    },
    async listProposals(): Promise<ExternalProposal[]> {
      const response = await fetch(`${workspaceBase}/proposals`);
      if (!response.ok) {
        throw new Error(`proposals failed: ${response.status}`);
      }
      const body = (await response.json()) as { proposals: ExternalProposal[] };
      return body.proposals;
    },
    async acceptProposal(
      proposalId: string,
    ): Promise<{ status: string; change_id: string; revision_no: number }> {
      const response = await fetch(`${workspaceBase}/proposals/${proposalId}/accept`, {
        method: "POST",
      });
      if (!response.ok) {
        const body = await readError(response);
        throw new Error(formatCode(body) || `accept proposal failed: ${response.status}`);
      }
      return (await response.json()) as {
        status: string;
        change_id: string;
        revision_no: number;
      };
    },
    async rejectProposal(proposalId: string): Promise<{ status: string }> {
      const response = await fetch(`${workspaceBase}/proposals/${proposalId}/reject`, {
        method: "POST",
      });
      if (!response.ok) {
        const body = await readError(response);
        throw new Error(formatCode(body) || `reject proposal failed: ${response.status}`);
      }
      return (await response.json()) as { status: string };
    },
    getGraphImageDownloadUrl(): string {
      return `${workspaceBase}/graph/image`;
    },
    async getWebSearchSettings(): Promise<WebSearchSettings> {
      const response = await fetch(`${baseUrl.replace(/\/$/, "")}/api/settings/web-search`);
      if (!response.ok) {
        throw new Error(`web search settings failed: ${response.status}`);
      }
      return (await response.json()) as WebSearchSettings;
    },
    async setWebSearchKey(
      provider: string,
      apiKey: string,
    ): Promise<{ status: string; configured: boolean; provider: string }> {
      const response = await fetch(`${baseUrl.replace(/\/$/, "")}/api/settings/web-search`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, api_key: apiKey }),
      });
      if (!response.ok) {
        const body = await readError(response);
        throw new Error(formatCode(body) || `save web search failed: ${response.status}`);
      }
      return (await response.json()) as {
        status: string;
        configured: boolean;
        provider: string;
      };
    },
    async clearWebSearchKey(): Promise<{ status: string; configured: boolean }> {
      const response = await fetch(`${baseUrl.replace(/\/$/, "")}/api/settings/web-search`, { method: "DELETE" });
      if (!response.ok) {
        throw new Error(`clear web search failed: ${response.status}`);
      }
      return (await response.json()) as { status: string; configured: boolean };
    },
    async generateSearchDraft(query: string): Promise<AiDraftResult & { sources: WebSearchSource[] }> {
      const response = await fetch(`${workspaceBase}/web-search-draft`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      if (!response.ok) {
        const body = await readError(response);
        throw new Error(formatCode(body) || `web search draft failed: ${response.status}`);
      }
      return (await response.json()) as AiDraftResult & { sources: WebSearchSource[] };
    },
    async listConceptAnchors(conceptId: string): Promise<ConceptAnchor[]> {
      const response = await fetch(
        `${workspaceBase}/concepts/${conceptId}/anchors`,
      );
      if (!response.ok) {
        throw new Error(`concept anchors failed: ${response.status}`);
      }
      const body = (await response.json()) as { anchors: ConceptAnchor[] };
      return body.anchors;
    },
    async searchGraph(query: string): Promise<SearchResultItem[]> {
      const searchEndpoint = `${workspaceBase}/search?q=${encodeURIComponent(query)}`;
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
        `${baseUrl.replace(/\/$/, "")}/api/workspaces/${workspaceId}/resources`,
        { method: "POST", body: form },
      );
      if (!response.ok) {
        throw new Error(`import failed: ${response.status}`);
      }
      return (await response.json()) as ResourceInfo;
    },
    async listResources(): Promise<ResourceInfo[]> {
      const response = await fetch(
        `${baseUrl.replace(/\/$/, "")}/api/workspaces/${workspaceId}/resources`,
      );
      if (!response.ok) {
        throw new Error(`list failed: ${response.status}`);
      }
      const body = (await response.json()) as { resources: ResourceInfo[] };
      return body.resources;
    },
    async parsePdf(resourceId: string): Promise<{ page_count: number }> {
      const response = await fetch(
        `${baseUrl.replace(/\/$/, "")}/api/workspaces/${workspaceId}/resources/${resourceId}/parse`,
        { method: "POST" },
      );
      if (!response.ok) {
        throw new Error(`parse failed: ${response.status}`);
      }
      return (await response.json()) as { page_count: number };
    },
    async getPageText(resourceId: string, page: number): Promise<PageText> {
      const response = await fetch(
        `${baseUrl.replace(/\/$/, "")}/api/workspaces/${workspaceId}/resources/${resourceId}/pages/${page}`,
      );
      if (!response.ok) {
        throw new Error(`page failed: ${response.status}`);
      }
      return (await response.json()) as PageText;
    },
    async listAnchors(resourceId: string): Promise<AnchorRef[]> {
      const response = await fetch(
        `${baseUrl.replace(/\/$/, "")}/api/workspaces/${workspaceId}/resources/${resourceId}/anchors`,
      );
      if (!response.ok) {
        throw new Error(`anchors failed: ${response.status}`);
      }
      const body = (await response.json()) as {
        anchors: Array<{
          id: string;
          page: number;
          payload: { topic_zh?: string; bbox_norm?: number[] };
        }>;
      };
      return body.anchors.map((anchor) => {
        const raw = anchor.payload.bbox_norm;
        const bboxNorm =
          Array.isArray(raw) &&
          raw.length === 4 &&
          raw.every((item) => typeof item === "number")
            ? ([raw[0], raw[1], raw[2], raw[3]] as [number, number, number, number])
            : undefined;
        return {
          id: anchor.id,
          page: anchor.page,
          label: anchor.payload.topic_zh ?? `第 ${anchor.page} 页`,
          bboxNorm,
        };
      });
    },
    getFileUrl(resourceId: string): string {
      return `${baseUrl.replace(/\/$/, "")}/api/workspaces/${workspaceId}/resources/${resourceId}/file`;
    },
    async getResourceText(resourceId: string): Promise<string> {
      const response = await fetch(
        `${baseUrl.replace(/\/$/, "")}/api/workspaces/${workspaceId}/resources/${resourceId}/file`,
      );
      if (!response.ok) {
        throw new Error(`resource text failed: ${response.status}`);
      }
      return await response.text();
    },
    async openResourcesDir(): Promise<{ status: string; path: string }> {
      const response = await fetch(`${workspaceBase}/resources/open-dir`, { method: "POST" });
      if (!response.ok) {
        throw new Error(`open dir failed: ${response.status}`);
      }
      return (await response.json()) as { status: string; path: string };
    },
    async revealResource(resourceId: string): Promise<{ status: string; path: string }> {
      const response = await fetch(`${workspaceBase}/resources/${resourceId}/reveal`, {
        method: "POST",
      });
      if (!response.ok) {
        throw new Error(`reveal failed: ${response.status}`);
      }
      return (await response.json()) as { status: string; path: string };
    },
    async getAiSettings(): Promise<{ configured: boolean; enabled: boolean }> {
      const response = await fetch(`${baseUrl.replace(/\/$/, "")}/api/settings/ai`);
      if (!response.ok) {
        throw new Error(`ai settings failed: ${response.status}`);
      }
      return (await response.json()) as { configured: boolean; enabled: boolean };
    },
    async setAiKey(apiKey: string): Promise<{ status: string; configured: boolean }> {
      const response = await fetch(`${baseUrl.replace(/\/$/, "")}/api/settings/ai`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: apiKey }),
      });
      if (!response.ok) {
        const body = await readError(response);
        throw new Error(formatCode(body) || `ai settings save failed: ${response.status}`);
      }
      return (await response.json()) as { status: string; configured: boolean };
    },
    async clearAiKey(): Promise<{ status: string; configured: boolean }> {
      const response = await fetch(`${baseUrl.replace(/\/$/, "")}/api/settings/ai`, {
        method: "DELETE",
      });
      if (!response.ok) {
        throw new Error(`ai settings clear failed: ${response.status}`);
      }
      return (await response.json()) as { status: string; configured: boolean };
    },
    async listWorkspaces(): Promise<
      Array<{ id: string; name: string; concept_count: number; updated_at: number | string }>
    > {
      const response = await fetch(`${baseUrl.replace(/\/$/, "")}/api/workspaces`);
      if (!response.ok) {
        throw new Error(`list workspaces failed: ${response.status}`);
      }
      const body = (await response.json()) as {
        workspaces: Array<{
          id: string;
          name: string;
          concept_count: number;
          updated_at: number | string;
        }>;
      };
      return body.workspaces;
    },
    async createWorkspace(name: string): Promise<{ id: string; name: string }> {
      const response = await fetch(`${baseUrl.replace(/\/$/, "")}/api/workspaces`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (!response.ok) {
        const body = await readError(response);
        throw new Error(formatCode(body) || `create workspace failed: ${response.status}`);
      }
      return (await response.json()) as { id: string; name: string };
    },
    async generateDraft(resourceId?: string): Promise<AiDraftResult> {
      const body: Record<string, unknown> = {};
      if (resourceId) body.resource_id = resourceId;
      const response = await fetch(`${workspaceBase}/ai-draft`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        const body = await readError(response);
        throw new Error(formatCode(body) || `draft failed: ${response.status}`);
      }
      return (await response.json()) as AiDraftResult;
    },
    async acceptDraft(
      patch: Record<string, unknown>,
      evidence: DraftEvidence[],
    ): Promise<{ status: string; change_id: string; revision_no: number }> {
      const response = await fetch(`${workspaceBase}/ai-draft/accept`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          patch,
          evidence: evidence.map((item) => ({
            anchor_id: item.anchor_id,
            resource_id: item.resource_id,
            label: item.label,
          })),
        }),
      });
      if (!response.ok) {
        const body = await readError(response);
        throw new Error(formatCode(body) || `draft accept failed: ${response.status}`);
      }
      return (await response.json()) as {
        status: string;
        change_id: string;
        revision_no: number;
      };
    },
    async askQuestion(question: string): Promise<AnswerResult> {
      const response = await fetch(`${workspaceBase}/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (!response.ok) {
        const body = await readError(response);
        throw new Error(formatCode(body) || `answer failed: ${response.status}`);
      }
      return (await response.json()) as AnswerResult;
    },
    async interpretCommand(command: string): Promise<CommandResult> {
      const response = await fetch(`${workspaceBase}/interpret`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command }),
      });
      if (!response.ok) {
        const body = await readError(response);
        throw new Error(formatCode(body) || `interpret failed: ${response.status}`);
      }
      return (await response.json()) as CommandResult;
    },
    async acceptCommand(patch: Record<string, unknown>): Promise<{
      status: string;
      change_id: string;
      revision_no: number;
    }> {
      const response = await fetch(`${workspaceBase}/interpret/accept`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ patch }),
      });
      if (!response.ok) {
        const body = await readError(response);
        throw new Error(formatCode(body) || `interpret accept failed: ${response.status}`);
      }
      return (await response.json()) as {
        status: string;
        change_id: string;
        revision_no: number;
      };
    },
  };
}

async function readError(response: Response): Promise<{ code?: string; rule?: unknown }> {
  try {
    return (await response.json()) as { code?: string; rule?: unknown };
  } catch {
    return {};
  }
}

// Compose `code/rule` so the UI can show the precise failure (e.g.
// draft_invalid/no_new_concepts) instead of an opaque top-level code.
function formatCode(body: { code?: string; rule?: unknown }): string {
  if (!body.code) return "";
  const hasRule = body.rule !== undefined && body.rule !== null && body.rule !== "";
  return hasRule ? `${body.code}/${String(body.rule)}` : body.code;
}

// Build a confirmed user set_lock GraphPatch for a single lock dimension.
export function buildSetLockPatch(
  snapshot: WorkspaceSnapshot,
  node: ConceptNode,
  dimension: keyof ConceptLocks,
  value: boolean,
): Record<string, unknown> {
  return {
    schema_version: 1,
    patch_id: uuidv7(),
    workspace_id: WORKSPACE_ID,
    course_id: COURSE_ID,
    base_revision_no: snapshot.revisionNo ?? 0,
    actor: { type: "user", id: "local-user" },
    reason: value ? "锁定" : "解锁",
    requires_confirmation: true,
    confirmed: true,
    operations: [
      {
        op_id: uuidv7(),
        op: "set_lock",
        target: { type: "concept", id: toCanonicalId(node.id) },
        expected_updated_revision_no: node.revisionNo ?? 0,
        dimension,
        value,
      },
    ],
  };
}

export function nextLinkIndex(node: ConceptNode): number {
  return (node.links?.length ?? 0) + 1;
}

export function buildUpsertLinkPatch(
  snapshot: WorkspaceSnapshot,
  node: ConceptNode,
  url: string,
): Record<string, unknown> {
  return {
    schema_version: 1,
    patch_id: uuidv7(),
    workspace_id: WORKSPACE_ID,
    course_id: COURSE_ID,
    base_revision_no: snapshot.revisionNo ?? 0,
    actor: { type: "user", id: "local-user" },
    reason: "添加链接",
    requires_confirmation: true,
    confirmed: true,
    operations: [
      {
        op_id: uuidv7(),
        op: "upsert_annotation",
        target: { type: "concept", id: toCanonicalId(node.id) },
        expected_updated_revision_no: node.revisionNo ?? 0,
        annotation: { kind: `link_${nextLinkIndex(node)}`, value: url },
      },
    ],
  };
}
