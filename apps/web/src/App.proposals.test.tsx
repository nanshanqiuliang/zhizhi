import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ExternalProposal, PersistApi } from "./api";
import { App } from "./App";

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
    listProposals: vi.fn(async () => []),
    acceptProposal: vi.fn(async () => ({ status: "applied", change_id: "c1", revision_no: 1 })),
    rejectProposal: vi.fn(async () => ({ status: "rejected" })),
    ...overrides,
  };
  return api;
}

const pendingProposal: ExternalProposal = {
  proposal_id: "00000000-0000-7000-8000-0000000000aa",
  created_at: "2026-08-16T10:00:00Z",
  origin: "mcp",
  note: "为第三章添加两个概念",
  status: "pending",
  operations_count: 3,
};

describe("external MCP proposals panel", () => {
  it("lists pending proposals from external AI clients", async () => {
    const api = mockApi({
      listProposals: vi.fn(async () => [pendingProposal]),
    });
    render(<App api={api} />);

    await waitFor(() => {
      expect(screen.getByRole("region", { name: "外部提议" })).toBeInTheDocument();
    });
    expect(screen.getByText("为第三章添加两个概念")).toBeInTheDocument();
    expect(screen.getByText(/3 项操作/)).toBeInTheDocument();
  });

  it("accepts a proposal through the API and refreshes the graph", async () => {
    const api = mockApi({
      listProposals: vi.fn(async () => [pendingProposal]),
    });
    render(<App api={api} />);

    await waitFor(() => {
      expect(screen.getByText("为第三章添加两个概念")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "接受提议" }));

    await waitFor(() => {
      expect(api.acceptProposal).toHaveBeenCalledWith(pendingProposal.proposal_id);
    });
    // Acceptance reloads the graph and the queue.
    await waitFor(() => {
      expect(api.loadGraph).toHaveBeenCalledTimes(2);
    });
    expect(api.listProposals).toHaveBeenCalledTimes(2);
  });

  it("rejects a proposal and keeps the canvas untouched", async () => {
    const api = mockApi({
      listProposals: vi.fn(async () => [pendingProposal]),
    });
    render(<App api={api} />);

    await waitFor(() => {
      expect(screen.getByText("为第三章添加两个概念")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "拒绝提议" }));

    await waitFor(() => {
      expect(api.rejectProposal).toHaveBeenCalledWith(pendingProposal.proposal_id);
    });
    expect(api.acceptProposal).not.toHaveBeenCalled();
  });

  it("stays quiet when there are no pending proposals", async () => {
    const api = mockApi();
    render(<App api={api} />);

    await waitFor(() => {
      expect(api.listProposals).toHaveBeenCalled();
    });
    expect(screen.queryByRole("region", { name: "外部提议" })).not.toBeInTheDocument();
  });
});
