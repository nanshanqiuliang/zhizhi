import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { PersistApi, WorkspaceSnapshot } from "./api";
import { App } from "./App";

function nodeButton(name: string) {
  return screen.getByRole("button", { name: new RegExp(`^概念：${name}$`) });
}

function emptyGuide() {
  return screen.getByRole("region", { name: "空工作区引导" });
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
    ...overrides,
  };
  return api;
}

const emptyGraph: WorkspaceSnapshot = { nodes: [], edges: [] };

const singleNodeGraph: WorkspaceSnapshot = {
  nodes: [{ id: "solo", title: "唯一节点", note: "孤立的根", x: 10, y: 10, positionLocked: false, tone: "root" as const }],
  edges: [],
};

describe("empty workspace (zero nodes) safety", () => {
  it("renders an empty-state guide instead of crashing when the saved graph has no nodes", async () => {
    const api = mockApi({ loadGraph: vi.fn(async () => emptyGraph) });
    render(<App api={api} />);

    await waitFor(() => {
      expect(emptyGuide()).toBeInTheDocument();
    });
  });

  it("recovers from an empty graph by adding a root concept from the guide", async () => {
    const api = mockApi({ loadGraph: vi.fn(async () => emptyGraph) });
    render(<App api={api} />);

    await waitFor(() => {
      expect(emptyGuide()).toBeInTheDocument();
    });
    fireEvent.click(within(emptyGuide()).getByRole("button", { name: "添加总纲" }));

    await waitFor(() => {
      expect(nodeButton("新总纲")).toBeInTheDocument();
    });
    expect(screen.getByLabelText("概念标题")).toHaveValue("新总纲");
  });

  it("does not crash when deleting the last remaining node", async () => {
    const api = mockApi({ loadGraph: vi.fn(async () => singleNodeGraph) });
    render(<App api={api} />);

    await waitFor(() => {
      expect(nodeButton("唯一节点")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "删除当前节点" }));

    await waitFor(() => {
      expect(emptyGuide()).toBeInTheDocument();
    });
  });

  it("does not crash when undoing an addition back to an empty graph", async () => {
    const api = mockApi({ loadGraph: vi.fn(async () => emptyGraph) });
    render(<App api={api} />);

    await waitFor(() => {
      expect(emptyGuide()).toBeInTheDocument();
    });
    fireEvent.click(within(emptyGuide()).getByRole("button", { name: "添加总纲" }));
    await waitFor(() => {
      expect(nodeButton("新总纲")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "撤销" }));

    await waitFor(() => {
      expect(emptyGuide()).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: "概念：新总纲" })).not.toBeInTheDocument();
  });
});
