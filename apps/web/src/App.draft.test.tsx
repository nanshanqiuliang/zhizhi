import "@testing-library/jest-dom/vitest";
import { render, screen, waitFor } from "@testing-library/react";
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
    applyPatch: vi.fn(async () => ({
      status: "applied",
      change_id: "00000000-0000-7000-8100-000000000099",
      revision_no: 1,
    })),
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

describe("AI draft preview", () => {
  it("shows a generate-draft action for imported text resources", async () => {
    const api = mockApi({ listResources: vi.fn(async () => [RESOURCE]) });
    render(<App api={api} />);

    await waitFor(() => {
      expect(screen.getByText("notes.md")).toBeInTheDocument();
    });
    // The generate-draft control is the entry point for the AI draft flow.
    expect(screen.getByRole("button", { name: /生成草案/ })).toBeInTheDocument();
  });
});
