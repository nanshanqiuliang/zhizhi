import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { PersistApi, SearchResultItem, WorkspaceSnapshot } from "./api";
import { App } from "./App";

function nodeButton(name: string) {
  return screen.getByRole("button", { name: new RegExp(`^概念：${name}$`) });
}

function mockApi(overrides: Partial<PersistApi> = {}): PersistApi & { saved: WorkspaceSnapshot[] } {
  const saved: WorkspaceSnapshot[] = [];
  const api: PersistApi = {
    loadGraph: vi.fn(async () => null),
    saveGraph: vi.fn(async (graph: WorkspaceSnapshot) => {
      saved.push(graph);
    }),
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
    ...overrides,
  };
  return Object.assign(api, { saved });
}

describe("knowledge tree persistence hookup", () => {
  it("loads a saved graph from the API on mount", async () => {
    const api = mockApi({
      loadGraph: vi.fn(async () => ({
        nodes: [{ id: "saved", title: "已保存课程", note: "来自本地库", x: 10, y: 10, positionLocked: false, tone: "root" as const }],
        edges: [],
      })),
    });
    render(<App api={api} />);

    await waitFor(() => {
      expect(nodeButton("已保存课程")).toBeInTheDocument();
    });
    expect(api.loadGraph).toHaveBeenCalledTimes(1);
  });

  it("auto-saves edits and shows save status", async () => {
    const api = mockApi();
    render(<App api={api} />);

    fireEvent.click(nodeButton("极限"));
    fireEvent.change(screen.getByLabelText("概念标题"), { target: { value: "函数极限" } });
    fireEvent.click(screen.getByRole("button", { name: "保存修改" }));

    await waitFor(() => {
      expect(api.saved).toHaveLength(1);
    });
    expect(api.saved[0].nodes.find((node) => node.id === "limit")?.title).toBe("函数极限");
    await waitFor(() => {
      expect(screen.getByText(/已保存/)).toBeInTheDocument();
    });
  });

  it("shows save failure and keeps the draft", async () => {
    const api = mockApi({
      saveGraph: vi.fn(async () => {
        throw new Error("network down");
      }),
    });
    render(<App api={api} />);

    fireEvent.click(nodeButton("极限"));
    fireEvent.change(screen.getByLabelText("概念标题"), { target: { value: "函数极限" } });
    fireEvent.click(screen.getByRole("button", { name: "保存修改" }));

    await waitFor(() => {
      expect(screen.getByText(/保存失败/)).toBeInTheDocument();
    });
    expect(nodeButton("函数极限")).toBeInTheDocument();
  });

  it("degrades gracefully when the API is unreachable on mount", async () => {
    const api = mockApi({
      loadGraph: vi.fn(async () => {
        throw new Error("connection refused");
      }),
    });
    render(<App api={api} />);

    await waitFor(() => {
      expect(screen.getAllByText(/本地服务未连接/).length).toBeGreaterThan(0);
    });
    expect(screen.getAllByRole("button", { name: /概念：/ })).toHaveLength(8);
  });

  it("searches and locates a matching concept", async () => {
    const api = mockApi({
      searchGraph: vi.fn(async () => [
        { id: "limit", label: "极限", snippet: "极限：趋近" },
      ] satisfies SearchResultItem[]),
    });
    render(<App api={api} />);

    const input = screen.getByLabelText("搜索概念或笔记");
    fireEvent.change(input, { target: { value: "趋近" } });

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "定位到概念：极限" })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "定位到概念：极限" }));
    await waitFor(() => {
      expect(nodeButton("极限")).toBeInTheDocument();
    });
  });

  it("shows no-match feedback and a failed-search state", async () => {
    const api = mockApi({
      searchGraph: vi.fn(async () => []),
    });
    render(<App api={api} />);

    const input = screen.getByLabelText("搜索概念或笔记");
    fireEvent.change(input, { target: { value: "不存在" } });

    await waitFor(() => {
      expect(screen.getByText("没有匹配的概念")).toBeInTheDocument();
    });

    api.searchGraph = vi.fn(async () => {
      throw new Error("search down");
    });
    fireEvent.change(input, { target: { value: "又失败" } });
    await waitFor(() => {
      expect(screen.getByText("搜索失败，请检查搜索词")).toBeInTheDocument();
    });
  });
});
