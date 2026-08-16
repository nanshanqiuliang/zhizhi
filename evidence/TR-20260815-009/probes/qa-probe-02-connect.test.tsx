import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { PersistApi, WorkspaceSnapshot } from "./api";
import { App } from "./App";

function nodeButton(title: string): HTMLElement {
  const node = document.querySelector(`[aria-label="概念：${title}"]`) as HTMLElement | null;
  if (!node) throw new Error(`node not found: ${title}`);
  return node;
}

function edgeCount(): number {
  return document.querySelectorAll('[aria-label^="连线："]').length;
}

function connectSourceNodes(): HTMLElement[] {
  return Array.from(document.querySelectorAll(".connect-source")) as HTMLElement[];
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

// A graph where B has its relations locked; A -> B edge exists.
const LOCKED_GRAPH: WorkspaceSnapshot = {
  nodes: [
    { id: "a", title: "A", note: "", x: 100, y: 100, positionLocked: false, tone: "branch" as const },
    {
      id: "b",
      title: "B",
      note: "",
      x: 300,
      y: 100,
      positionLocked: false,
      tone: "branch" as const,
      locks: { content: false, relations: true, position: false, annotations: false },
    },
    { id: "c", title: "C", note: "", x: 500, y: 100, positionLocked: false, tone: "leaf" as const },
  ],
  edges: [{ from: "a", to: "b" }],
  revisionNo: 0,
};

describe("QA-02 connect mode (WORK-2026-047)", () => {
  it("P-101 self-connect (same node twice) is rejected and clears the source", () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "连线" }));
    fireEvent.click(nodeButton("极限"));
    expect(connectSourceNodes()).toHaveLength(1);
    expect(connectSourceNodes()[0].getAttribute("aria-label")).toBe("概念：极限");

    fireEvent.click(nodeButton("极限"));
    expect(screen.getByText("起点与终点相同，请重新选择起点")).toBeInTheDocument();
    expect(connectSourceNodes()).toHaveLength(0);
    expect(document.querySelector('[aria-label="连线：极限 → 极限（相关）"]')).toBeNull();
  });

  it("P-102 duplicate connect between the same pair is rejected", () => {
    render(<App />);
    const before = edgeCount();
    fireEvent.click(screen.getByRole("button", { name: "连线" }));
    // 极限 -> 函数 already exists in the sample; try both directions.
    fireEvent.click(nodeButton("函数"));
    fireEvent.click(nodeButton("极限"));
    expect(screen.getByText("这两个节点已存在连线")).toBeInTheDocument();
    expect(edgeCount()).toBe(before);
    expect(connectSourceNodes()).toHaveLength(0);
  });

  it("P-103 a relations lock on either endpoint blocks connecting", async () => {
    const api = mockApi({ loadGraph: vi.fn(async () => LOCKED_GRAPH) });
    render(<App api={api} />);
    await waitFor(() => expect(nodeButton("A")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "连线" }));
    // Source is fine, target is locked -> rejected: no edge, status shown, and
    // the source stays highlighted so the user can pick another target.
    fireEvent.click(nodeButton("A"));
    expect(connectSourceNodes()).toHaveLength(1);
    fireEvent.click(nodeButton("B"));
    expect(screen.getByText("关系已锁定，无法连线")).toBeInTheDocument();
    expect(edgeCount()).toBe(1);
    // The source survives the rejection and still works against a free target.
    fireEvent.click(nodeButton("C"));
    expect(document.querySelector('[aria-label="连线：A → C（相关）"]')).not.toBeNull();
    // Connect mode is still active and the source was cleared; clicking the
    // locked node as the FIRST pick is rejected without a source.
    fireEvent.click(nodeButton("B"));
    expect(screen.getByText("关系已锁定，无法连线")).toBeInTheDocument();
    expect(connectSourceNodes()).toHaveLength(0);
  });

  it("P-104 a relations lock on either endpoint blocks disconnecting", async () => {
    const api = mockApi({ loadGraph: vi.fn(async () => LOCKED_GRAPH) });
    render(<App api={api} />);
    await waitFor(() => expect(nodeButton("B")).toBeInTheDocument());
    fireEvent.click(nodeButton("B"));
    expect(document.querySelector('[aria-label^="删除连线"]')).not.toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "删除连线 来自 A" }));
    expect(screen.getByText("关系已锁定，无法断开连线")).toBeInTheDocument();
    expect(document.querySelector('[aria-label="连线：A → B（相关）"]')).not.toBeNull();
  });

  it("P-105 Esc exits connect mode and clears the source highlight", () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "连线" }));
    expect(screen.getByRole("combobox", { name: "连线类型" })).toBeInTheDocument();
    fireEvent.click(nodeButton("极限"));
    expect(connectSourceNodes()).toHaveLength(1);

    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("combobox", { name: "连线类型" })).toBeNull();
    expect(connectSourceNodes()).toHaveLength(0);
    // The toolbar button is no longer toggled on.
    expect(screen.getByRole("button", { name: "连线" }).className).not.toContain("active-tool");
  });

  it("P-106 connect-source highlight lands only on the source, and a typed edge is created", () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "连线" }));
    fireEvent.change(screen.getByRole("combobox", { name: "连线类型" }), {
      target: { value: "prerequisite_of" },
    });
    fireEvent.click(nodeButton("函数"));
    expect(connectSourceNodes()).toHaveLength(1);
    expect(connectSourceNodes()[0].getAttribute("aria-label")).toBe("概念：函数");

    fireEvent.click(nodeButton("ε-δ 语言"));
    expect(connectSourceNodes()).toHaveLength(0);
    expect(
      document.querySelector('[aria-label="连线：函数 → ε-δ 语言（先修）"]'),
    ).not.toBeNull();
  });
});
