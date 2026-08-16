import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ConceptNode, PersistApi, WorkspaceSnapshot } from "./api";
import { graphToSnapshot, snapshotToGraph } from "./api";
import { App } from "./App";

vi.stubGlobal("open", vi.fn(() => null));

function nodeButton(name: string) {
  return screen.getByRole("button", { name: new RegExp(`^概念：${name}$`) });
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
    parsePdf: vi.fn(async () => ({ page_count: 6 })),
    getPageText: vi.fn(async () => ({
      resource_version_id: "v",
      page: 1,
      text: "text",
      text_hash: "sha256:x",
    })),
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
    listConceptAnchors: vi.fn(async () => []),
    ...overrides,
  };
  return api;
}

function node(id: string, title: string, overrides: Partial<ConceptNode> = {}): ConceptNode {
  return {
    id,
    title,
    note: "",
    x: 10,
    y: 10,
    positionLocked: false,
    tone: "leaf",
    ...overrides,
  };
}

describe("snapshot round-trip keeps source data (WORK-2026-055)", () => {
  it("preserves evidence ids and link annotations through snapshot -> graph -> snapshot", () => {
    const graph = {
      schema_version: 1,
      workspace_id: "00000000-0000-7000-8000-000000000001",
      course_id: "00000000-0000-7000-8000-000000000002",
      revision_no: 3,
      concepts: [
        {
          id: "00000000-0000-7000-a000-0000000000c1",
          course_id: "00000000-0000-7000-8000-000000000002",
          label: "带来源的概念",
          origin: "ai",
          review_state: "accepted",
          confidence: 0.9,
          evidence_ids: ["00000000-0000-7000-9000-0000000000a1"],
          locks: { content: false, relations: false, position: false, annotations: false },
          annotations: [
            { kind: "note", value: "笔记" },
            { kind: "link_1", value: "https://example.com/intro" },
            { kind: "link_2", value: "https://example.com/advanced" },
          ],
          revision_no: 1,
        },
      ],
      edges: [],
      layout_items: [],
    };
    const snapshot = graphToSnapshot(graph as never);
    const restored = snapshotToGraph(snapshot) as {
      concepts: Array<{ evidence_ids: string[]; annotations: Array<{ kind: string; value: string }> }>;
    };
    expect(restored.concepts[0].evidence_ids).toEqual([
      "00000000-0000-7000-9000-0000000000a1",
    ]);
    expect(restored.concepts[0].annotations).toEqual(
      expect.arrayContaining([
        { kind: "note", value: "笔记" },
        { kind: "link_1", value: "https://example.com/intro" },
        { kind: "link_2", value: "https://example.com/advanced" },
      ]),
    );
  });
});

describe("node source panel (WORK-2026-055)", () => {
  it("shows web links stored on the node and opens them on click", async () => {
    const api = mockApi({
      loadGraph: vi.fn(async () => ({
        nodes: [
          node("c1", "链接概念", {
            tone: "root" as const,
            links: ["https://example.com/mindmap"],
          }),
        ],
        edges: [],
      })),
    });
    render(<App api={api} />);

    await waitFor(() => {
      expect(nodeButton("链接概念")).toBeInTheDocument();
    });
    fireEvent.click(nodeButton("链接概念"));

    const link = await screen.findByRole("link", { name: /example\.com/ });
    expect(link).toHaveAttribute("href", "https://example.com/mindmap");
    fireEvent.click(link);
    expect(vi.mocked(window.open)).not.toHaveBeenCalled();
    // Real anchor navigation happens on the <a>; the panel also offers the raw URL.
  });

  it("lists document anchors from the concept and jumps into the viewer", async () => {
    const api = mockApi({
      loadGraph: vi.fn(async () => ({
        nodes: [node("c1", "文档概念", { tone: "root" as const, evidenceIds: ["a1"] })],
        edges: [],
      })),
      listConceptAnchors: vi.fn(async () => [
        {
          anchor_id: "a1",
          resource_id: "r1",
          page: 2,
          label: "第二章 极限",
          resource_name: "微积分讲义.pdf",
          mime: "application/pdf",
        },
      ]),
      listResources: vi.fn(async () => [
        {
          id: "r1",
          display_name: "微积分讲义.pdf",
          mime: "application/pdf",
          byte_size: 2048,
          content_hash: "sha256:x",
          created_at: "2026-08-14T00:00:00Z",
        },
      ]),
    });
    render(<App api={api} />);

    await waitFor(() => {
      expect(nodeButton("文档概念")).toBeInTheDocument();
    });
    fireEvent.click(nodeButton("文档概念"));

    const source = await screen.findByRole("button", {
      name: /微积分讲义\.pdf · 第 2 页/,
    });
    fireEvent.click(source);
    await waitFor(() => {
      expect(api.getPageText).toHaveBeenCalledWith("r1", 2);
    });
  });

  it("adds a link through the annotation commit gate", async () => {
    const api = mockApi({
      loadGraph: vi.fn(async () => ({
        nodes: [node("c1", "普通概念", { tone: "root" as const, revisionNo: 2 })],
        edges: [],
      }) as WorkspaceSnapshot),
    });
    render(<App api={api} />);

    await waitFor(() => {
      expect(nodeButton("普通概念")).toBeInTheDocument();
    });
    fireEvent.click(nodeButton("普通概念"));

    fireEvent.change(await screen.findByLabelText("添加链接"), {
      target: { value: "https://example.com/extra" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存链接" }));

    await waitFor(() => {
      expect(api.applyPatch).toHaveBeenCalledTimes(1);
    });
    const patch = vi.mocked(api.applyPatch).mock.calls[0][0] as {
      operations: Array<{ op: string; annotation?: { kind: string; value: string } }>;
    };
    expect(patch.operations[0].op).toBe("upsert_annotation");
    expect(patch.operations[0].annotation).toEqual({
      kind: "link_1",
      value: "https://example.com/extra",
    });
  });

  it("injects web-search source urls when accepting a search draft", async () => {
    const api = mockApi({
      generateSearchDraft: vi.fn(async () => ({
        draft: {
          concepts: [
            { label: "搜索概念", aliases: [], confidence: 0.9, evidence_ids: [] },
          ],
          relations: [],
        },
        patch: {
          schema_version: 1,
          operations: [
            {
              op_id: "00000000-0000-7000-9000-0000000000d1",
              op: "create_concept",
              concept: {
                id: "00000000-0000-7000-a000-0000000000e1",
                label: "搜索概念",
                annotations: [],
              },
            },
          ],
        } as never,
        sources: [
          { title: "资料一", url: "https://example.com/one" },
          { title: "资料二", url: "https://example.com/two" },
        ],
      })),
    });
    render(<App api={api} />);

    fireEvent.change(screen.getByLabelText("网络主题"), { target: { value: "图论" } });
    fireEvent.click(screen.getByRole("button", { name: "从网络主题生成思维导图" }));
    await waitFor(() => {
      expect(screen.getByText("搜索概念")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "接受并写入" }));

    await waitFor(() => {
      expect(api.acceptDraft).toHaveBeenCalledTimes(1);
    });
    const [patch] = vi.mocked(api.acceptDraft).mock.calls[0] as unknown as [
      { operations: Array<{ concept?: { annotations?: Array<{ kind: string }> } }> },
    ];
    const annotations = patch.operations[0].concept?.annotations ?? [];
    expect(annotations).toEqual(
      expect.arrayContaining([
        { kind: "link_1", value: "https://example.com/one" },
        { kind: "link_2", value: "https://example.com/two" },
      ]),
    );
  });
});
