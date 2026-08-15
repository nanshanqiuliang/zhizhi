import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { PersistApi, ResourceInfo, WorkspaceSnapshot } from "./api";
import { App } from "./App";

const RESOURCE: ResourceInfo = {
  id: "00000000-0000-7000-8100-000000000001",
  display_name: "notes.md",
  mime: "text/markdown",
  byte_size: 12,
  content_hash: "sha256:abc",
  created_at: "2026-08-15T00:00:00Z",
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
      text: "text",
      text_hash: "sha256:x",
    })),
    listAnchors: vi.fn(async () => []),
    getFileUrl: vi.fn(() => "http://127.0.0.1:8000/file.pdf"),
    getResourceText: vi.fn(async () => "text content"),
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

describe("sourced Q&A", () => {
  it("shows a question box and renders the answer with clickable sources", async () => {
    const api = mockApi();
    render(<App api={api} />);

    const input = screen.getByRole("textbox", { name: /向本地知识提问/ });
    fireEvent.change(input, { target: { value: "什么是极限" } });
    fireEvent.click(screen.getByRole("button", { name: /提问/ }));

    await waitFor(() => {
      expect(screen.getByRole("region", { name: /回答/ })).toBeInTheDocument();
    });
    const panel = screen.getByRole("region", { name: /回答/ });
    expect(within(panel).getByText(/极限描述自变量趋近/)).toBeInTheDocument();
    expect(within(panel).getByRole("button", { name: /\[1\] 极限/ })).toBeInTheDocument();
    expect(api.askQuestion).toHaveBeenCalledWith("什么是极限");
  });
});
