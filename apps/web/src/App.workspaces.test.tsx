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
    listWorkspaces: vi.fn(async () => [
      {
        id: "00000000-0000-7000-8000-000000000001",
        name: "微积分",
        concept_count: 8,
        updated_at: 0,
      },
    ]),
    createWorkspace: vi.fn(async () => ({ id: "new-ws-0001", name: "线性代数" })),
    ...overrides,
  };
  return api;
}

describe("multi-course workspaces", () => {
  it("lists courses and creates a new one via the factory", async () => {
    const apis = new Map<string, PersistApi>();
    const listWorkspaces = vi.fn(async () => [
      {
        id: "00000000-0000-7000-8000-000000000001",
        name: "微积分",
        concept_count: 8,
        updated_at: 0,
      },
      { id: "new-ws-0001", name: "线性代数", concept_count: 1, updated_at: 0 },
    ]);
    const createWorkspace = vi.fn(async () => ({ id: "new-ws-0001", name: "线性代数" }));
    const factory = (workspaceId: string): PersistApi => {
      if (!apis.has(workspaceId)) {
        apis.set(workspaceId, mockApi({ listWorkspaces, createWorkspace }));
      }
      return apis.get(workspaceId)!;
    };

    render(<App apiFactory={factory} />);

    await waitFor(() => expect(screen.getByText("微积分")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "添加课程" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "添加课程" }));
    await waitFor(() => expect(createWorkspace).toHaveBeenCalledWith("新课程"));
    await waitFor(() => expect(screen.getByText("线性代数")).toBeInTheDocument());
  });

  it("switches courses when a course card is clicked", async () => {
    const apis = new Map<string, PersistApi>();
    const listWorkspaces = vi.fn(async () => [
      { id: "ws-a", name: "课程甲", concept_count: 2, updated_at: 0 },
      { id: "ws-b", name: "课程乙", concept_count: 3, updated_at: 0 },
    ]);
    const factory = (workspaceId: string): PersistApi => {
      if (!apis.has(workspaceId)) {
        apis.set(workspaceId, mockApi({ listWorkspaces }));
      }
      return apis.get(workspaceId)!;
    };

    render(<App apiFactory={factory} />);

    await waitFor(() => expect(screen.getByText("课程甲")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /课程乙/ }));
    await waitFor(() => expect(apis.get("ws-b")).toBeDefined());
  });
});
