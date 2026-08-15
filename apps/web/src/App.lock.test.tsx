import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { PersistApi, WorkspaceSnapshot } from "./api";
import { App } from "./App";

function nodeButton(name: string) {
  return screen.getByRole("button", { name: new RegExp(`^概念：${name}$`) });
}

function mockApi(overrides: Partial<PersistApi> = {}): PersistApi {
  return {
    loadGraph: vi.fn(async () => null),
    saveGraph: vi.fn(async () => undefined),
    searchGraph: vi.fn(async () => []),
    importResource: vi.fn(async () => {
      throw new Error("not used");
    }),
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
    applyPatch: vi.fn(async () => ({ status: "applied", change_id: "c", revision_no: 1 })),
    undoGraph: vi.fn(async () => ({ status: "undone", revision_no: 0 })),
    redoGraph: vi.fn(async () => ({ status: "redone", revision_no: 1 })),
    backupGraph: vi.fn(async () => ({ status: "backed_up", backup_path: "b.sqlite3" })),
    listBackups: vi.fn(async () => []),
    restoreBackup: vi.fn(async () => ({ status: "restored" })),
    listHistory: vi.fn(async () => []),
    ...overrides,
  };
}

describe("lock and cross-session undo hookup", () => {
  it("locks a concept's content through the patch gate", async () => {
    const patches: Record<string, unknown>[] = [];
    const api = mockApi({
      applyPatch: vi.fn(async (patch: Record<string, unknown>) => {
        patches.push(patch);
        return { status: "applied", change_id: "c", revision_no: 1 };
      }),
      loadGraph: vi
        .fn<() => Promise<WorkspaceSnapshot | null>>()
        .mockResolvedValueOnce(null)
        .mockResolvedValue({
          nodes: [
            {
              id: "00000000-0000-7000-8000-000000000005",
              title: "极限",
              note: "note",
              x: 0,
              y: 0,
              positionLocked: false,
              tone: "branch",
              locks: { content: true, relations: false, position: false, annotations: false },
              revisionNo: 1,
            },
          ],
          edges: [],
          revisionNo: 1,
        }),
    });
    render(<App api={api} />);

    await waitFor(() => expect(nodeButton("极限")).toBeInTheDocument());
    fireEvent.click(nodeButton("极限"));
    fireEvent.click(screen.getByRole("button", { name: "锁定内容" }));

    await waitFor(() => expect(api.applyPatch).toHaveBeenCalledTimes(1));
    const operation = (patches[0].operations as Array<Record<string, unknown>>)[0];
    expect(operation.op).toBe("set_lock");
    expect(operation.dimension).toBe("content");
    expect(operation.value).toBe(true);

    await waitFor(() => {
      expect(screen.getByLabelText("内容已锁定")).toBeInTheDocument();
    });
  });

  it("falls back to the backend undo when the session stack is empty", async () => {
    const api = mockApi({
      undoGraph: vi.fn(async () => ({ status: "undone", revision_no: 0 })),
    });
    render(<App api={api} />);

    const undoButton = screen.getByRole("button", { name: "撤销" });
    expect(undoButton).not.toBeDisabled();
    fireEvent.click(undoButton);

    await waitFor(() => expect(api.undoGraph).toHaveBeenCalledTimes(1));
  });

  it("rejects editing a content-locked concept before saving", async () => {
    const api = mockApi({
      loadGraph: vi
        .fn<() => Promise<WorkspaceSnapshot | null>>()
        .mockResolvedValue({
          nodes: [
            {
              id: "00000000-0000-7000-8000-000000000005",
              title: "极限",
              note: "note",
              x: 0,
              y: 0,
              positionLocked: false,
              tone: "branch",
              locks: { content: true, relations: false, position: false, annotations: false },
              revisionNo: 1,
            },
          ],
          edges: [],
          revisionNo: 1,
        }),
    });
    render(<App api={api} />);

    await waitFor(() => expect(nodeButton("极限")).toBeInTheDocument());
    fireEvent.click(nodeButton("极限"));
    fireEvent.change(screen.getByLabelText("概念标题"), { target: { value: "被覆盖" } });
    fireEvent.click(screen.getByRole("button", { name: "保存修改" }));

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("内容已锁定，无法修改");
    });
    expect(nodeButton("极限")).toBeInTheDocument();
    expect(api.saveGraph).not.toHaveBeenCalled();
  });

  it("shows a specific message when saving hits a lock", async () => {
    const api = mockApi({
      saveGraph: vi.fn(async () => {
        throw new Error("target_locked");
      }),
    });
    render(<App api={api} />);

    await waitFor(() => expect(nodeButton("极限")).toBeInTheDocument());
    fireEvent.click(nodeButton("极限"));
    fireEvent.change(screen.getByLabelText("概念标题"), { target: { value: "函数极限" } });
    fireEvent.click(screen.getByRole("button", { name: "保存修改" }));

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("保存被拒：该内容已锁定");
    });
  });

  it("backs up from the sidebar", async () => {
    const api = mockApi({
      backupGraph: vi.fn(async () => ({ status: "backed_up", backup_path: "b.sqlite3" })),
      listBackups: vi.fn(async () => ["backup-20260814T120000Z.sqlite3"]),
    });
    render(<App api={api} />);

    const backupButton = screen.getByRole("button", { name: "备份数据" });
    fireEvent.click(backupButton);

    await waitFor(() => expect(api.backupGraph).toHaveBeenCalledTimes(1));
  });

  it("shows the version history panel", async () => {
    const api = mockApi({
      listHistory: vi.fn(async () => [
        {
          change_id: "00000000-0000-7000-8000-000000000099",
          before_revision_no: 0,
          after_revision_no: 1,
        },
      ]),
    });
    render(<App api={api} />);

    await waitFor(() => {
      expect(screen.getByLabelText("版本历史")).toBeInTheDocument();
    });
    expect(screen.getByText(/v0 → v1/)).toBeInTheDocument();
  });
});
