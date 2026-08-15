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
    askQuestion: vi.fn(async () => ({ answer: "", sources: [] })),
    interpretCommand: vi.fn(async () => ({ summary: "", patch: {} })),
    acceptCommand: vi.fn(async () => ({ status: "applied", change_id: "c", revision_no: 1 })),
    applyPatch: vi.fn(async () => ({ status: "applied", change_id: "c", revision_no: 1 })),
    undoGraph: vi.fn(async () => ({ status: "undone", revision_no: 0 })),
    redoGraph: vi.fn(async () => ({ status: "redone", revision_no: 1 })),
    backupGraph: vi.fn(async () => ({ status: "backed_up", backup_path: "b.sqlite3" })),
    listBackups: vi.fn(async () => []),
    restoreBackup: vi.fn(async () => ({ status: "restored" })),
    listHistory: vi.fn(async () => []),
    getAiSettings: vi.fn(async () => ({ configured: false, enabled: false })),
    setAiKey: vi.fn(async () => ({ status: "saved", configured: true })),
    clearAiKey: vi.fn(async () => ({ status: "cleared", configured: false })),
    ...overrides,
  };
  return api;
}

describe("AI settings", () => {
  it("shows AI 已连接 when the backend reports enabled", async () => {
    const api = mockApi({
      getAiSettings: vi.fn(async () => ({ configured: true, enabled: true })),
    });
    render(<App api={api} />);

    await waitFor(() => expect(screen.getByText("AI 已连接")).toBeInTheDocument());
  });

  it("opens the settings dialog and saves a key", async () => {
    const api = mockApi();
    render(<App api={api} />);

    const button = await screen.findByRole("button", { name: "AI 设置" });
    fireEvent.click(button);
    expect(screen.getByRole("dialog", { name: "AI 设置" })).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText(/粘贴 sk-/), {
      target: { value: "fake-deepseek-key" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存并启用" }));

    await waitFor(() => expect(api.setAiKey).toHaveBeenCalledWith("fake-deepseek-key"));
    await waitFor(() => expect(screen.getByText("AI 已连接")).toBeInTheDocument());
    expect(screen.queryByRole("dialog", { name: "AI 设置" })).not.toBeInTheDocument();
  });
});
