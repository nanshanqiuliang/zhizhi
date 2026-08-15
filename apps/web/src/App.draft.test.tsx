import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { AiDraftResult, PersistApi, ResourceInfo, WorkspaceSnapshot } from "./api";
import { App } from "./App";

const RESOURCE: ResourceInfo = {
  id: "00000000-0000-7000-8100-000000000001",
  display_name: "notes.md",
  mime: "text/markdown",
  byte_size: 12,
  content_hash: "sha256:abc",
  created_at: "2026-08-15T00:00:00Z",
};

const DRAFT: AiDraftResult = {
  draft: {
    concepts: [
      { label: "极限", aliases: [], confidence: 0.9, evidence_ids: ["e1"] },
      { label: "连续", aliases: [], confidence: 0.85, evidence_ids: ["e1"] },
    ],
    relations: [
      {
        source_label: "极限",
        target_label: "连续",
        edge_type: "prerequisite_of",
        confidence: 0.7,
        evidence_ids: ["e1"],
      },
    ],
  },
  patch: {
    schema_version: 1,
    patch_id: "00000000-0000-7000-8100-000000000010",
    workspace_id: "00000000-0000-7000-8000-000000000001",
    course_id: "00000000-0000-7000-8000-000000000002",
    base_revision_no: 0,
    actor: { type: "user", id: "local-user" },
    reason: "AI 草案",
    requires_confirmation: true,
    confirmed: false,
    operations: [],
  },
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
    generateDraft: vi.fn(async () => DRAFT),
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
    expect(screen.getByRole("button", { name: /生成草案/ })).toBeInTheDocument();
  });

  it("generates, previews, accepts and rejects a draft", async () => {
    const api = mockApi({
      listResources: vi.fn(async () => [RESOURCE]),
      loadGraph: vi.fn(async () => null),
    });
    render(<App api={api} />);

    await waitFor(() => {
      expect(screen.getByText("notes.md")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /生成草案/ }));
    await waitFor(() => {
      expect(screen.getByRole("region", { name: /AI 草案预览/ })).toBeInTheDocument();
    });
    const panel = screen.getByRole("region", { name: /AI 草案预览/ });
    expect(within(panel).getByText("极限")).toBeInTheDocument();
    expect(within(panel).getByText(/极限 → 连续/)).toBeInTheDocument();

    // Reject first: the draft panel disappears and no patch is applied.
    fireEvent.click(screen.getByRole("button", { name: "拒绝" }));
    await waitFor(() => {
      expect(screen.queryByRole("region", { name: /AI 草案预览/ })).not.toBeInTheDocument();
    });
    expect(api.applyPatch).not.toHaveBeenCalled();

    // Generate again and accept: applyPatch is called with confirmed=true.
    fireEvent.click(screen.getByRole("button", { name: /生成草案/ }));
    await waitFor(() => {
      expect(screen.getByRole("region", { name: /AI 草案预览/ })).toBeInTheDocument();
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
    expect(applied.actor).toEqual({ type: "user", id: "local-user" });
  });

  it("shows AI not connected when generateDraft fails closed", async () => {
    const api = mockApi({
      listResources: vi.fn(async () => [RESOURCE]),
      generateDraft: vi.fn(async () => {
        throw new Error("ai_not_available");
      }),
    });
    render(<App api={api} />);

    await waitFor(() => {
      expect(screen.getByText("notes.md")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /生成草案/ }));
    await waitFor(() => {
      expect(screen.getByText("AI 未连接", { selector: "p.import-note" })).toBeInTheDocument();
    });
  });

  it("offers jump-to-source for each draft concept", async () => {
    const api = mockApi({ listResources: vi.fn(async () => [RESOURCE]) });
    render(<App api={api} />);

    await waitFor(() => {
      expect(screen.getByText("notes.md")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /生成草案/ }));
    await waitFor(() => {
      expect(screen.getByRole("region", { name: /AI 草案预览/ })).toBeInTheDocument();
    });
    const panel = screen.getByRole("region", { name: /AI 草案预览/ });
    expect(within(panel).getAllByRole("button", { name: /跳回原文/ }).length).toBeGreaterThan(0);
  });
});
