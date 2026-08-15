import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { App } from "./App";
import type { PersistApi, ResourceInfo, WorkspaceSnapshot } from "./api";

const RESOURCE: ResourceInfo = {
  id: "r1",
  display_name: "a.md",
  mime: "text/markdown",
  byte_size: 10,
  content_hash: "h",
  created_at: "t",
};

function mockApi(overrides: Partial<PersistApi> = {}): PersistApi {
  const api: PersistApi = {
    loadGraph: vi.fn(async () => null as WorkspaceSnapshot | null),
    saveGraph: vi.fn(async () => {}),
    searchGraph: vi.fn(async () => []),
    importResource: vi.fn(async () => RESOURCE),
    listResources: vi.fn(async () => []),
    parsePdf: vi.fn(async () => ({ page_count: 1 })),
    getPageText: vi.fn(async () => ({
      resource_version_id: "v",
      page: 1,
      text: "",
      text_hash: "h",
    })),
    listAnchors: vi.fn(async () => []),
    getFileUrl: vi.fn(() => "http://127.0.0.1:8000/file.pdf"),
    getResourceText: vi.fn(async () => ""),
    generateDraft: vi.fn(async () => ({ draft: { concepts: [], relations: [] }, patch: {} })),
    acceptDraft: vi.fn(async () => ({ status: "applied", change_id: "c", revision_no: 1 })),
    askQuestion: vi.fn(async () => ({
      answer: "极限描述自变量趋近某一点时函数值的趋势。",
      sources: [{ id: "00000000-0000-7000-8000-000000000101", label: "极限", kind: "concept" }],
    })),
    interpretCommand: vi.fn(async () => ({ summary: "", patch: {} })),
    acceptCommand: vi.fn(async () => ({ status: "applied", change_id: "c", revision_no: 1 })),
    applyPatch: vi.fn(async () => ({ status: "applied", change_id: "c", revision_no: 1 })),
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

describe("workspace layout", () => {
  it("shows the AI answer output inside the right column", async () => {
    const api = mockApi();
    const { container } = render(<App api={api} />);

    fireEvent.change(screen.getByRole("textbox", { name: /向本地知识提问/ }), {
      target: { value: "什么是极限" },
    });
    fireEvent.click(screen.getByRole("button", { name: /提问/ }));

    const answerSection = await screen.findByRole("region", { name: "回答" });
    expect(container.querySelector(".right-column")).toContainElement(answerSection);
  });

  it("hides and shows the sidebar", () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "隐藏边栏" }));
    expect(screen.getByRole("navigation", { name: "课程与笔记" })).toHaveClass("hidden");
    expect(screen.getByRole("button", { name: "显示边栏" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "显示边栏" }));
    expect(screen.getByRole("navigation", { name: "课程与笔记" })).not.toHaveClass("hidden");
  });

  it("resizes the sidebar by dragging its right edge", () => {
    const { container } = render(<App />);
    const workspace = container.querySelector(".workspace") as HTMLElement;
    const handle = container.querySelector(".sidebar-resize") as HTMLElement;
    const before = workspace.getAttribute("style");

    fireEvent.pointerDown(handle, { pointerId: 2, clientX: 250, buttons: 1, button: 0 });
    fireEvent.pointerMove(handle, { pointerId: 2, clientX: 330, buttons: 1 });
    fireEvent.pointerUp(handle, { pointerId: 2, clientX: 330, buttons: 1 });

    expect(workspace.getAttribute("style")).not.toBe(before);
    expect(workspace.getAttribute("style")).toContain("330px");
    void waitFor;
  });
});
