import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ConceptNode, PersistApi, WorkspaceSnapshot } from "./api";
import { App } from "./App";

function nodeButton(name: string) {
  return screen.getByRole("button", { name: new RegExp(`^概念：${name}$`) });
}

function positionOf(name: string) {
  const style = nodeButton(name).getAttribute("style") ?? "";
  const left = Number(/left:\s*(-?[\d.]+)px/.exec(style)?.[1] ?? NaN);
  const top = Number(/top:\s*(-?[\d.]+)px/.exec(style)?.[1] ?? NaN);
  return { left, top };
}

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
    ...overrides,
  };
  return api;
}

function node(id: string, title: string, tone: ConceptNode["tone"] = "leaf"): ConceptNode {
  return {
    id,
    title,
    note: "",
    x: 0,
    y: 0,
    positionLocked: false,
    tone,
  };
}

describe("vertical tree auto-layout (WORK-2026-054)", () => {
  it("stacks children below a centered parent with even, non-cramped spacing", async () => {
    const snapshot: WorkspaceSnapshot = {
      nodes: [
        node("p", "总纲", "root"),
        node("c1", "子一"),
        node("c2", "子二"),
        node("c3", "子三"),
      ],
      edges: [
        { from: "p", to: "c1" },
        { from: "p", to: "c2" },
        { from: "p", to: "c3" },
      ],
    };
    const api = mockApi({ loadGraph: vi.fn(async () => snapshot) });
    render(<App api={api} />);
    await waitFor(() => {
      expect(nodeButton("总纲")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "自动排布" }));

    const parent = positionOf("总纲");
    const children = [positionOf("子一"), positionOf("子二"), positionOf("子三")].sort(
      (a, b) => a.left - b.left,
    );
    // Vertical-first: every child sits one level below the parent, evenly.
    for (const child of children) {
      expect(child.top - parent.top).toBeGreaterThanOrEqual(190);
    }
    for (const [left, right] of Array.from({ length: 2 }, (_, i) => [children[i], children[i + 1]])) {
      expect(right.left - left.left).toBeGreaterThanOrEqual(240);
    }
    // The parent is centered over the children block.
    expect(parent.left).toBeCloseTo(
      (children[0].left + children[children.length - 1].left) / 2,
      5,
    );
  });

  it("moves isolated nodes to a bottom row below the tree", async () => {
    const snapshot: WorkspaceSnapshot = {
      nodes: [
        node("a", "链一", "root"),
        node("b", "链二"),
        node("x", "孤块一"),
        node("y", "孤块二"),
      ],
      edges: [{ from: "a", to: "b" }],
    };
    const api = mockApi({ loadGraph: vi.fn(async () => snapshot) });
    render(<App api={api} />);
    await waitFor(() => {
      expect(nodeButton("链一")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "自动排布" }));

    const chainBottom = positionOf("链二").top;
    expect(positionOf("孤块一").top).toBeGreaterThan(chainBottom);
    expect(positionOf("孤块二").top).toBeGreaterThan(chainBottom);
    // Isolated nodes spread horizontally instead of stacking.
    expect(Math.abs(positionOf("孤块二").left - positionOf("孤块一").left)).toBeGreaterThanOrEqual(240);
  });

  it("keeps a position-locked node in place while relayouting the rest", async () => {
    const snapshot: WorkspaceSnapshot = {
      nodes: [
        { ...node("p", "锁定总纲", "root"), positionLocked: true, x: 500, y: 500 },
        node("c1", "自由子一"),
        node("c2", "自由子二"),
      ],
      edges: [
        { from: "p", to: "c1" },
        { from: "p", to: "c2" },
      ],
    };
    const api = mockApi({ loadGraph: vi.fn(async () => snapshot) });
    render(<App api={api} />);
    await waitFor(() => {
      expect(nodeButton("锁定总纲")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "自动排布" }));

    // The locked node did not move...
    expect(positionOf("锁定总纲")).toEqual({ left: 500, top: 500 });
    // ...and its children still formed an evenly spaced row.
    const children = [positionOf("自由子一"), positionOf("自由子二")].sort(
      (a, b) => a.left - b.left,
    );
    expect(children[1].top).toBe(children[0].top);
    expect(children[1].left - children[0].left).toBeGreaterThanOrEqual(240);
  });
});
