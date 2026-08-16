import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { PersistApi, WorkspaceSnapshot } from "./api";
import { graphToSnapshot, snapshotToGraph } from "./api";
import { App } from "./App";

function nodeButton(title: string): HTMLElement {
  const node = document.querySelector(`[aria-label="概念：${title}"]`) as HTMLElement | null;
  if (!node) throw new Error(`node not found: ${title}`);
  return node;
}

function mockApi(overrides: Partial<PersistApi> = {}): PersistApi {
  const api: PersistApi = {
    loadGraph: vi.fn(async () => null),
    saveGraph: vi.fn(async () => undefined),
    searchGraph: vi.fn(async () => []),
    importResource: vi.fn(async () => ({
      id: "00000000-0000-7000-8100-000000000001",
      display_name: "notes.md",
      mime: "text/markdown",
      byte_size: 12,
      content_hash: "sha256:abc",
      created_at: "2026-08-14T00:00:00Z",
    })),
    listResources: vi.fn(async () => []),
    parsePdf: vi.fn(async () => ({ page_count: 1 })),
    getPageText: vi.fn(async () => ({ resource_version_id: "v", page: 1, text: "t", text_hash: "sha256:x" })),
    listAnchors: vi.fn(async () => []),
    getFileUrl: vi.fn(() => "http://127.0.0.1:8000/file.pdf"),
    getResourceText: vi.fn(async () => "text content"),
    generateDraft: vi.fn(async () => ({ draft: { concepts: [], relations: [] }, patch: {} })),
    acceptDraft: vi.fn(async () => ({ status: "applied", change_id: "c", revision_no: 1 })),
    askQuestion: vi.fn(async () => ({ answer: "", sources: [] })),
    interpretCommand: vi.fn(async () => ({ summary: "", patch: {} })),
    acceptCommand: vi.fn(async () => ({ status: "applied", change_id: "c", revision_no: 1 })),
    applyPatch: vi.fn(async () => ({ status: "applied", change_id: "00000000-0000-7000-8100-000000000099", revision_no: 1 })),
    undoGraph: vi.fn(async () => ({ status: "undone", revision_no: 0 })),
    redoGraph: vi.fn(async () => ({ status: "redone", revision_no: 1 })),
    backupGraph: vi.fn(async () => ({ status: "backed_up", backup_path: "b.sqlite3" })),
    listBackups: vi.fn(async () => []),
    restoreBackup: vi.fn(async () => ({ status: "restored" })),
    listHistory: vi.fn(async () => []),
    ...overrides,
  };
  return api;
}

const COURSE_ID = "00000000-0000-7000-8000-000000000002";
const CONCEPT_A = "00000000-0000-7000-8000-000000000101";
const CONCEPT_B = "00000000-0000-7000-8000-000000000102";

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

describe("QA-04 disconnect / edge-type roundtrip / empty workspace (WORK-2026-047)", () => {
  it("P-301 typed edge survives snapshotToGraph → graphToSnapshot → snapshotToGraph", () => {
    const snapshot: WorkspaceSnapshot = {
      revisionNo: 0,
      nodes: [
        { id: CONCEPT_A, title: "A", note: "", x: 0, y: 0, positionLocked: false, tone: "branch" as const },
        { id: CONCEPT_B, title: "B", note: "", x: 0, y: 0, positionLocked: false, tone: "leaf" as const },
      ],
      edges: [{ from: CONCEPT_A, to: CONCEPT_B, edge_type: "prerequisite_of" }],
    };
    const graph1 = snapshotToGraph(snapshot) as { edges: Array<Record<string, unknown>> };
    expect(graph1.edges[0].edge_type).toBe("prerequisite_of");

    const snap2 = graphToSnapshot(graph1);
    expect(snap2.edges[0].edge_type).toBe("prerequisite_of");

    const graph2 = snapshotToGraph(snap2) as { edges: Array<Record<string, unknown>> };
    expect(graph2.edges[0].edge_type).toBe("prerequisite_of");
  });

  it("P-302 type-less snapshot edge defaults to related_to (backward compatible)", () => {
    const snapshot: WorkspaceSnapshot = {
      revisionNo: 0,
      nodes: [
        { id: CONCEPT_A, title: "A", note: "", x: 0, y: 0, positionLocked: false, tone: "branch" as const },
        { id: CONCEPT_B, title: "B", note: "", x: 0, y: 0, positionLocked: false, tone: "leaf" as const },
      ],
      edges: [{ from: CONCEPT_A, to: CONCEPT_B }],
    };
    const graph = snapshotToGraph(snapshot) as { edges: Array<Record<string, unknown>> };
    expect(graph.edges[0].edge_type).toBe("related_to");
    // And an unknown backend type is dropped back to undefined on load.
    const loaded = graphToSnapshot({
      revision_no: 0,
      concepts: [canonicalConcept(CONCEPT_A, "A"), canonicalConcept(CONCEPT_B, "B")],
      edges: [
        {
          id: "00000000-0000-7000-8000-000000000103",
          course_id: COURSE_ID,
          source_concept_id: CONCEPT_A,
          target_concept_id: CONCEPT_B,
          edge_type: "weird_unknown",
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
    expect(loaded.edges[0].edge_type).toBeUndefined();
  });

  it("P-303 disconnecting an edge persists across save → reload", async () => {
    let stored: WorkspaceSnapshot | null = null;
    const saves: WorkspaceSnapshot[] = [];
    const api = mockApi({
      loadGraph: vi.fn(async () => stored),
      saveGraph: vi.fn(async (graph: WorkspaceSnapshot) => {
        stored = graph;
        saves.push(graph);
      }),
    });
    const first = render(<App api={api} />);

    fireEvent.click(nodeButton("极限"));
    fireEvent.click(screen.getByRole("button", { name: "删除连线 指向 函数" }));
    expect(document.querySelector('[aria-label="连线：极限 → 函数（相关）"]')).toBeNull();
    // Auto-save (600ms debounce) must persist the state without the edge.
    await waitFor(() => expect(saves.length).toBeGreaterThan(0), { timeout: 4000 });
    expect(stored?.edges.some((edge) => edge.from === "limit" && edge.to === "function")).toBe(false);

    first.unmount();
    const second = render(<App api={api} />);
    await waitFor(() => expect(nodeButton("极限")).toBeInTheDocument());
    expect(document.querySelector('[aria-label="连线：极限 → 函数（相关）"]')).toBeNull();
    second.unmount();
  });

  it("P-304 a disconnected edge is undoable in local history", () => {
    render(<App />);
    fireEvent.click(nodeButton("极限"));
    fireEvent.click(screen.getByRole("button", { name: "删除连线 指向 函数" }));
    expect(document.querySelector('[aria-label="连线：极限 → 函数（相关）"]')).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "撤销" }));
    expect(document.querySelector('[aria-label="连线：极限 → 函数（相关）"]')).not.toBeNull();
  });

  it("P-305 BUG-2026-001 empty-workspace crash still reproduces at HEAD (pre-existing P2)", async () => {
    const api = mockApi({ loadGraph: vi.fn(async () => ({ nodes: [], edges: [] })) });
    const evidence: string[] = [];
    const originalError = console.error;
    const onWindowError = (event: ErrorEvent) => {
      evidence.push(String(event.message));
    };
    console.error = (...args: unknown[]) => {
      evidence.push(String(args[0] ?? ""));
      originalError(...args);
    };
    window.addEventListener("error", onWindowError);
    try {
      render(<App api={api} />);
      await new Promise((resolve) => setTimeout(resolve, 150));
    } catch (error) {
      evidence.push(String(error));
    } finally {
      console.error = originalError;
      window.removeEventListener("error", onWindowError);
    }
    const crashReported = evidence.some(
      (line) => line.includes("tone") || line.includes("reading 'tone'") || line.includes("undefined"),
    );
    // Inverted semantics on purpose: PASS here means the known P2 bug reproduces.
    expect(crashReported).toBe(true);
  });
});
