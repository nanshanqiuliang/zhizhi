import { afterEach, describe, expect, it, vi } from "vitest";

import { graphToSnapshot, httpPersistApi, snapshotToGraph } from "./api";

const WORKSPACE_ID = "00000000-0000-7000-8000-000000000001";
const BASE = "http://127.0.0.1:8000";

const CONCEPT_A = "00000000-0000-7000-8000-000000000101";
const CONCEPT_B = "00000000-0000-7000-8000-000000000102";
const COURSE_ID = "00000000-0000-7000-8000-000000000002";

function canonicalConcept(id: string, label: string): Record<string, unknown> {
  return {
    id,
    course_id: COURSE_ID,
    label,
    origin: "user",
    review_state: "accepted",
    confidence: null,
    evidence_ids: [],
    locks: { content: false, relations: false, position: false, annotations: false },
    annotations: [],
    revision_no: 0,
  };
}

describe("edge type roundtrip (WORK-2026-047)", () => {
  it("preserves a typed edge through graphToSnapshot → snapshotToGraph", () => {
    const snapshot = graphToSnapshot({
      revision_no: 0,
      concepts: [canonicalConcept(CONCEPT_A, "A"), canonicalConcept(CONCEPT_B, "B")],
      edges: [
        {
          id: "00000000-0000-7000-8000-000000000103",
          course_id: COURSE_ID,
          source_concept_id: CONCEPT_A,
          target_concept_id: CONCEPT_B,
          edge_type: "prerequisite_of",
          origin: "user",
          review_state: "accepted",
          confidence: null,
          evidence_ids: [],
          locked: false,
          revision_no: 0,
        },
      ],
      layout_items: [],
    });

    expect(snapshot.edges[0].edge_type).toBe("prerequisite_of");

    const graph = snapshotToGraph(snapshot) as { edges: Array<Record<string, unknown>> };
    expect(graph.edges[0].edge_type).toBe("prerequisite_of");
  });

  it("defaults a type-less snapshot edge to related_to", () => {
    const snapshot = graphToSnapshot({
      revision_no: 0,
      concepts: [canonicalConcept(CONCEPT_A, "A"), canonicalConcept(CONCEPT_B, "B")],
      edges: [
        {
          id: "00000000-0000-7000-8000-000000000103",
          course_id: COURSE_ID,
          source_concept_id: CONCEPT_A,
          target_concept_id: CONCEPT_B,
          edge_type: "related_to",
          origin: "user",
          review_state: "accepted",
          confidence: null,
          evidence_ids: [],
          locked: false,
          revision_no: 0,
        },
      ],
      layout_items: [],
    });

    snapshot.edges[0].edge_type = undefined;
    const graph = snapshotToGraph(snapshot) as { edges: Array<Record<string, unknown>> };
    expect(graph.edges[0].edge_type).toBe("related_to");
  });
});

describe("persist api URL contract", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("routes backup/restore/history on the workspace base, not /graph", async () => {
    const fetchMock = vi.fn<
      (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
    >(async () => new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const api = httpPersistApi(BASE);

    await api.backupGraph();
    await api.listBackups();
    await api.restoreBackup("backup-1.sqlite3");
    await api.listHistory();

    const urls = fetchMock.mock.calls.map((call) => String(call[0]));
    expect(urls).toEqual([
      `${BASE}/api/workspaces/${WORKSPACE_ID}/backup`,
      `${BASE}/api/workspaces/${WORKSPACE_ID}/backups`,
      `${BASE}/api/workspaces/${WORKSPACE_ID}/restore`,
      `${BASE}/api/workspaces/${WORKSPACE_ID}/history`,
    ]);
  });

  it("uses a relative API base for same-origin desktop serving", async () => {
    const fetchMock = vi.fn<
      (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
    >(async () => new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const api = httpPersistApi("");

    await api.loadGraph();
    await api.backupGraph();

    const urls = fetchMock.mock.calls.map((call) => String(call[0]));
    expect(urls).toEqual([
      `/api/workspaces/${WORKSPACE_ID}/graph`,
      `/api/workspaces/${WORKSPACE_ID}/backup`,
    ]);
  });

  it("surfaces the rule in draft generation errors", async () => {
    const fetchMock = vi.fn<
      (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
    >(
      async () =>
        new Response(
          JSON.stringify({ code: "draft_invalid", rule: "no_new_concepts" }),
          { status: 422 },
        ),
    );
    vi.stubGlobal("fetch", fetchMock);
    const api = httpPersistApi(BASE);

    await expect(api.generateDraft()).rejects.toThrow(/draft_invalid\/no_new_concepts/);
  });
});
