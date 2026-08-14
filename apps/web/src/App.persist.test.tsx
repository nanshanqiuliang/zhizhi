import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { PersistApi, WorkspaceSnapshot } from "./api";
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
});
