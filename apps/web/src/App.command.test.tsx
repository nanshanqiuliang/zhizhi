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
    askQuestion: vi.fn(async () => ({ answer: "", sources: [] })),
    interpretCommand: vi.fn(async () => ({
      summary: "锁定极限的内容",
      patch: {
        schema_version: 1,
        patch_id: "00000000-0000-7000-8100-000000000020",
        workspace_id: "00000000-0000-7000-8000-000000000001",
        course_id: "00000000-0000-7000-8000-000000000002",
        base_revision_no: 0,
        actor: { type: "user", id: "local-user" },
        reason: "命令",
        requires_confirmation: true,
        confirmed: false,
        operations: [],
      },
    })),
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

describe("natural-language command", () => {
  it("interprets a command and shows a preview with accept/reject", async () => {
    const api = mockApi();
    render(<App api={api} />);

    const input = screen.getByRole("textbox", { name: /向知识树下达指令/ });
    fireEvent.change(input, { target: { value: "锁定极限的内容" } });
    fireEvent.click(screen.getByRole("button", { name: /执行/ }));

    await waitFor(() => {
      expect(screen.getByRole("region", { name: /指令预览/ })).toBeInTheDocument();
    });
    const panel = screen.getByRole("region", { name: /指令预览/ });
    expect(within(panel).getByText(/锁定极限的内容/)).toBeInTheDocument();
  });

  it("accept flips confirmed and reject never applies", async () => {
    const api = mockApi();
    render(<App api={api} />);

    fireEvent.change(screen.getByRole("textbox", { name: /向知识树下达指令/ }), {
      target: { value: "锁定极限的内容" },
    });
    fireEvent.click(screen.getByRole("button", { name: /执行/ }));
    await waitFor(() => {
      expect(screen.getByRole("region", { name: /指令预览/ })).toBeInTheDocument();
    });

    // Reject: no patch is applied.
    fireEvent.click(screen.getByRole("button", { name: "拒绝" }));
    await waitFor(() => {
      expect(screen.queryByRole("region", { name: /指令预览/ })).not.toBeInTheDocument();
    });
    expect(api.applyPatch).not.toHaveBeenCalled();

    // Interpret again and accept: applyPatch is called with confirmed=true.
    fireEvent.change(screen.getByRole("textbox", { name: /向知识树下达指令/ }), {
      target: { value: "锁定极限的内容" },
    });
    fireEvent.click(screen.getByRole("button", { name: /执行/ }));
    await waitFor(() => {
      expect(screen.getByRole("region", { name: /指令预览/ })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /接受并写入/ }));
    await waitFor(() => {
      expect(api.applyPatch).toHaveBeenCalledTimes(1);
    });
    const applied = (api.applyPatch as ReturnType<typeof vi.fn>).mock.calls[0][0] as Record<
      string,
      unknown
    >;
    expect(applied.confirmed).toBe(true);
  });

  it("surfaces AI not connected when interpret fails closed", async () => {
    const api = mockApi({
      interpretCommand: vi.fn(async () => {
        throw new Error("ai_not_available");
      }),
    });
    render(<App api={api} />);

    fireEvent.change(screen.getByRole("textbox", { name: /向知识树下达指令/ }), {
      target: { value: "锁定极限的内容" },
    });
    fireEvent.click(screen.getByRole("button", { name: /执行/ }));
    await waitFor(() => {
      expect(screen.getByRole("status").textContent).toContain("AI 未连接");
    });
  });
});
