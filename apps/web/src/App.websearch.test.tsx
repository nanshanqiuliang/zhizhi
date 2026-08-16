import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { PersistApi } from "./api";
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
    getAiSettings: vi.fn(async () => ({ configured: false, enabled: false })),
    getWebSearchSettings: vi.fn(async () => ({ provider: "tavily", configured: false, enabled: false })),
    setWebSearchKey: vi.fn(async () => ({ status: "saved", configured: true, provider: "tavily" })),
    clearWebSearchKey: vi.fn(async () => ({ status: "cleared", configured: false })),
    generateSearchDraft: vi.fn(async () => ({
      draft: {
        concepts: [{ label: "搜索概念", aliases: [], confidence: 0.9, evidence_ids: [] }],
        relations: [],
      },
      patch: { operations: [{}] },
      sources: [
        { title: "微积分资料", url: "https://example.com/calc" },
        { title: "进阶阅读", url: "https://example.com/adv" },
      ],
    })),
    ...overrides,
  };
  return api;
}

describe("web search agent", () => {
  it("saves a web search provider key from the settings dialog", async () => {
    const api = mockApi();
    render(<App api={api} />);

    fireEvent.click(screen.getByRole("button", { name: "AI 与搜索设置" }));
    const dialog = screen.getByRole("dialog", { name: "AI 设置" });
    fireEvent.change(within(dialog).getByLabelText("搜索 Provider"), {
      target: { value: "brave" },
    });
    fireEvent.change(within(dialog).getByLabelText("Web 搜索 API Key"), {
      target: { value: "brave-key" },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "保存搜索设置" }));

    await waitFor(() => {
      expect(api.setWebSearchKey).toHaveBeenCalledWith("brave", "brave-key");
    });
  });

  it("generates a topic draft from web sources and shows them", async () => {
    const api = mockApi();
    render(<App api={api} />);

    fireEvent.change(screen.getByLabelText("网络主题"), { target: { value: "微积分入门" } });
    fireEvent.click(screen.getByRole("button", { name: "从网络主题生成思维导图" }));

    await waitFor(() => {
      expect(api.generateSearchDraft).toHaveBeenCalledWith("微积分入门");
    });
    await waitFor(() => {
      expect(screen.getByText("搜索概念")).toBeInTheDocument();
    });
    expect(screen.getByRole("link", { name: "微积分资料" })).toHaveAttribute(
      "href",
      "https://example.com/calc",
    );
  });

  it("shows a friendly message when search is not configured", async () => {
    const api = mockApi({
      generateSearchDraft: vi.fn(async () => {
        throw new Error("web_search_not_available");
      }),
    });
    render(<App api={api} />);

    fireEvent.change(screen.getByLabelText("网络主题"), { target: { value: "线性代数" } });
    fireEvent.click(screen.getByRole("button", { name: "从网络主题生成思维导图" }));

    await waitFor(() => {
      expect(screen.getByText(/搜索未配置/)).toBeInTheDocument();
    });
  });
});
