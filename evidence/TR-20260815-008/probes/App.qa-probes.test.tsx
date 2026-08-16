import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { PersistApi, WorkspaceSnapshot } from "./api";
import { App } from "./App";
import { canvasSurfaceSize } from "./canvas";

// QA adversarial probes for WORK-2026-045 (TR-20260815-008).
// Every assertion is checked against real rendered DOM / real pure-function output.

function nodeButton(name: string): HTMLElement {
  return screen.getByRole("button", { name: new RegExp(`^概念：${name}$`) });
}

function dragNode(node: HTMLElement, from: { x: number; y: number }, to: { x: number; y: number }) {
  fireEvent.pointerDown(node, { pointerId: 1, clientX: from.x, clientY: from.y, buttons: 1 });
  fireEvent.pointerMove(node, { pointerId: 1, clientX: to.x, clientY: to.y, buttons: 1 });
  fireEvent.pointerUp(node, { pointerId: 1, clientX: to.x, clientY: to.y, buttons: 1 });
}

function wheel(viewport: Element, deltaY: number, times = 1) {
  for (let i = 0; i < times; i++) {
    fireEvent.wheel(viewport, { deltaY });
  }
}

function zoomOf(surface: HTMLElement): number {
  const m = surface.style.transform.match(/scale\(([\d.]+)\)/);
  return m ? parseFloat(m[1]) : 1;
}

function mockApi(overrides: Partial<PersistApi> = {}): PersistApi {
  return {
    loadGraph: vi.fn(async () => null),
    saveGraph: vi.fn(async () => undefined),
    searchGraph: vi.fn(async () => []),
    importResource: vi.fn(async () => ({
      id: "00000000-0000-7000-8100-000000000001",
      display_name: "n.md",
      mime: "text/markdown",
      byte_size: 1,
      content_hash: "sha256:abc",
      created_at: "2026-08-14T00:00:00Z",
    })),
    listResources: vi.fn(async () => []),
    parsePdf: vi.fn(async () => ({ page_count: 1 })),
    getPageText: vi.fn(async () => ({
      resource_version_id: "v",
      page: 1,
      text: "t",
      text_hash: "sha256:x",
    })),
    listAnchors: vi.fn(async () => []),
    getFileUrl: vi.fn(() => "http://127.0.0.1:8000/f.pdf"),
    getResourceText: vi.fn(async () => "text"),
    generateDraft: vi.fn(async () => ({ draft: { concepts: [], relations: [] }, patch: {} })),
    acceptDraft: vi.fn(async () => ({ status: "applied", change_id: "c", revision_no: 1 })),
    askQuestion: vi.fn(async () => ({ answer: "", sources: [] })),
    interpretCommand: vi.fn(async () => ({ summary: "", patch: {} })),
    acceptCommand: vi.fn(async () => ({ status: "applied", change_id: "c", revision_no: 1 })),
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
}

function surfaceBox(container: HTMLElement) {
  const surface = container.querySelector(".canvas-surface") as HTMLElement;
  const edge = container.querySelector(".edge-layer") as SVGSVGElement;
  return {
    surface,
    edge,
    width: parseFloat(surface.style.width),
    height: parseFloat(surface.style.height),
    viewBox: edge.getAttribute("viewBox") ?? "",
  };
}

describe("QA adversarial probes WORK-2026-045 (TR-20260815-008)", () => {
  it("P-001 drags far beyond the old 835/555 clamp to the exact target", () => {
    const { container } = render(<App />);
    const node = nodeButton("极限");
    // start (115,205); drag pointer from (100,100) to (5000,4000) at zoom 1.
    dragNode(node, { x: 100, y: 100 }, { x: 5000, y: 4000 });
    expect(parseFloat(node.style.left)).toBe(115 + 4900);
    expect(parseFloat(node.style.top)).toBe(205 + 3900);
    expect(parseFloat(node.style.left)).toBeGreaterThan(835);
    expect(parseFloat(node.style.top)).toBeGreaterThan(555);
    // surface grows with content: max x = 5015, max y = 4105
    const box = surfaceBox(container);
    expect(box.width).toBe(5015 + 150 + 48);
    expect(box.height).toBe(4105 + 68 + 48);
    expect(box.viewBox).toBe(`0 0 ${box.width} ${box.height}`);
  });

  it("P-002 negative drags stay floored at the >=8 lower bound", () => {
    const { container } = render(<App />);
    const node = nodeButton("极限");
    // delta (-2100, -2100) -> 115-2100=-1985 -> floor 8
    dragNode(node, { x: 100, y: 100 }, { x: -2000, y: -2000 });
    expect(parseFloat(node.style.left)).toBe(8);
    expect(parseFloat(node.style.top)).toBe(8);
    const box = surfaceBox(container);
    expect(box.width).toBe(1000);
    expect(box.height).toBe(650);
    expect(box.viewBox).toBe("0 0 1000 650");
  });

  it("P-003 drag deltas are divided by zoom (zoom=2) with exact coordinates", () => {
    const { container } = render(<App />);
    const viewport = container.querySelector(".canvas-viewport") as HTMLElement;
    wheel(viewport, -100, 10); // zoom 1 -> 2.0 (float drift: 2.000000000000001)
    const surface = container.querySelector(".canvas-surface") as HTMLElement;
    const zoom = zoomOf(surface);
    expect(zoom).toBeCloseTo(2, 5);

    const node = nodeButton("极限");
    // client delta (400,200) / zoom = (400/zoom, 200/zoom)
    dragNode(node, { x: 100, y: 100 }, { x: 500, y: 300 });
    expect(parseFloat(node.style.left)).toBeCloseTo(115 + 400 / zoom, 5);
    expect(parseFloat(node.style.top)).toBeCloseTo(205 + 200 / zoom, 5);
    expect(parseFloat(node.style.left)).toBeGreaterThan(115 + 199);
    expect(parseFloat(node.style.top)).toBeGreaterThan(205 + 99);
  });

  it("P-004 drag deltas are divided by zoom (zoom=0.5) with exact coordinates", () => {
    const { container } = render(<App />);
    const viewport = container.querySelector(".canvas-viewport") as HTMLElement;
    wheel(viewport, 100, 5); // zoom 1 -> 0.5 (float drift)
    const surface = container.querySelector(".canvas-surface") as HTMLElement;
    const zoom = zoomOf(surface);
    expect(zoom).toBeCloseTo(0.5, 5);

    const node = nodeButton("极限");
    // client delta (200,100) / 0.5 = (400,200) in world units
    dragNode(node, { x: 100, y: 100 }, { x: 300, y: 200 });
    expect(parseFloat(node.style.left)).toBeCloseTo(115 + 200 / zoom, 5);
    expect(parseFloat(node.style.top)).toBeCloseTo(205 + 100 / zoom, 5);
    expect(parseFloat(node.style.left)).toBeGreaterThan(115 + 399);
    expect(parseFloat(node.style.top)).toBeGreaterThan(205 + 199);
  });

  it("P-005 canvasSurfaceSize pure function: floor, far coords, negatives, max-only", () => {
    expect(canvasSurfaceSize([])).toEqual({ width: 1000, height: 650 });
    expect(canvasSurfaceSize([{ x: 100, y: 100 }])).toEqual({ width: 1000, height: 650 });
    expect(canvasSurfaceSize([{ x: 5000, y: 3000 }])).toEqual({ width: 5198, height: 3116 });
    expect(canvasSurfaceSize([{ x: -100, y: -50 }])).toEqual({ width: 1000, height: 650 });
    // intermediate nodes must not affect the result; only max x / max y count
    expect(
      canvasSurfaceSize([
        { x: 5000, y: 0 },
        { x: 100, y: 100 },
        { x: 0, y: 3000 },
      ]),
    ).toEqual({ width: 5198, height: 3116 });
    // boundary exactly at the floor stays at the floor
    expect(canvasSurfaceSize([{ x: 802, y: 534 }])).toEqual({ width: 1000, height: 650 });
    expect(canvasSurfaceSize([{ x: 803, y: 535 }])).toEqual({ width: 1001, height: 651 });
  });

  it("P-006 surface inline size == edge-layer viewBox == canvasSurfaceSize(nodes)", () => {
    const { container } = render(<App />);
    const box = surfaceBox(container);
    // sample workspace max x=665 (->863), max y=405 (->521): both below floor
    expect(box.width).toBe(1000);
    expect(box.height).toBe(650);
    expect(box.viewBox).toBe("0 0 1000 650");
    expect(parseFloat(box.edge.style.width)).toBe(box.width);
    expect(parseFloat(box.edge.style.height)).toBe(box.height);

    const node = nodeButton("极限");
    dragNode(node, { x: 100, y: 100 }, { x: 1400, y: 1300 });
    const after = surfaceBox(container);
    const expected = canvasSurfaceSize([{ x: 1415, y: 1405 }]);
    expect(after.width).toBe(expected.width);
    expect(after.height).toBe(expected.height);
    expect(after.viewBox).toBe(`0 0 ${expected.width} ${expected.height}`);
    expect(parseFloat(after.edge.style.width)).toBe(expected.width);
  });

  it("P-007 legend is a direct child of the viewport, outside the transformed surface", () => {
    const { container } = render(<App />);
    const viewport = container.querySelector(".canvas-viewport") as HTMLElement;
    const surface = container.querySelector(".canvas-surface") as HTMLElement;
    const legend = container.querySelector(".canvas-legend") as HTMLElement;
    expect(legend).not.toBeNull();
    expect(legend.parentElement).toBe(viewport);
    expect(surface.contains(legend)).toBe(false);
    // legend must not inherit the surface transform (no translate/scale)
    expect(legend.style.transform).toBe("");
    expect(surface.style.transform).toContain("translate(");
  });

  it("P-008 empty workspace renders without error and keeps the 1000x650 floor", async () => {
    const api = mockApi({
      loadGraph: vi.fn(async () => ({ nodes: [], edges: [], revisionNo: 1 })),
    });
    const { container } = render(<App api={api} />);
    await waitFor(() => expect(api.loadGraph).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(container.querySelector(".canvas-surface")).not.toBeNull());
    const box = surfaceBox(container);
    expect(box.width).toBe(1000);
    expect(box.height).toBe(650);
    expect(box.viewBox).toBe("0 0 1000 650");
  });

  it("P-009 position-locked nodes still refuse drags (no lock bypass)", () => {
    const { container } = render(<App />);
    const node = nodeButton("极限");
    fireEvent.click(node);
    fireEvent.click(screen.getByRole("button", { name: "锁定位置" }));
    const before = { left: node.style.left, top: node.style.top };
    dragNode(node, { x: 100, y: 100 }, { x: 5000, y: 4000 });
    expect(node.style.left).toBe(before.left);
    expect(node.style.top).toBe(before.top);
    expect(screen.getByRole("status")).toHaveTextContent("位置已锁定，无法移动");
    const box = surfaceBox(container);
    expect(box.width).toBe(1000);
    expect(box.height).toBe(650);
  });

  it("P-010 auto-layout resets surface to the laid-out bounding box; locked nodes keep positions", () => {
    const { container } = render(<App />);
    const node = nodeButton("极限");
    // grow the surface first
    dragNode(node, { x: 100, y: 100 }, { x: 5000, y: 4000 });
    expect(surfaceBox(container).width).toBeGreaterThan(1000);

    fireEvent.click(screen.getByRole("button", { name: "自动排布" }));
    const box = surfaceBox(container);
    // laid-out sample max x=665 -> 863 < floor; max y=405 -> 521 < floor
    expect(box.width).toBe(1000);
    expect(box.height).toBe(650);
    expect(box.viewBox).toBe("0 0 1000 650");
  });

  it("P-010b auto-layout preserves a locked far node and keeps the grown surface", () => {
    const { container } = render(<App />);
    const node = nodeButton("极限");
    // grow + move the node first, then lock it, then re-layout
    dragNode(node, { x: 100, y: 100 }, { x: 5000, y: 4000 });
    expect(parseFloat(node.style.left)).toBe(5015);
    fireEvent.click(node);
    fireEvent.click(screen.getByRole("button", { name: "锁定位置" }));

    fireEvent.click(screen.getByRole("button", { name: "自动排布" }));
    expect(parseFloat(node.style.left)).toBe(5015);
    expect(parseFloat(node.style.top)).toBe(4105);
    const box = surfaceBox(container);
    expect(box.width).toBe(5015 + 150 + 48);
    expect(box.height).toBe(4105 + 68 + 48);
  });

  it("P-011 api graph with far coordinates grows the surface and renders the node", async () => {
    const far: WorkspaceSnapshot = {
      nodes: [
        {
          id: "far",
          title: "远端",
          note: "",
          x: 5000,
          y: 3000,
          positionLocked: false,
          tone: "leaf",
        },
      ],
      edges: [],
      revisionNo: 1,
    };
    const api = mockApi({ loadGraph: vi.fn(async () => far) });
    const { container } = render(<App api={api} />);
    const node = await screen.findByRole("button", { name: /概念：远端/ });
    expect(node.style.left).toBe("5000px");
    expect(node.style.top).toBe("3000px");
    const box = surfaceBox(container);
    expect(box.width).toBe(5000 + 150 + 48);
    expect(box.height).toBe(3000 + 68 + 48);
    expect(box.viewBox).toBe(`0 0 ${box.width} ${box.height}`);
  });

  it("P-012 edge-layer paths follow nodes beyond the old bounds", () => {
    const { container } = render(<App />);
    const node = nodeButton("极限");
    dragNode(node, { x: 100, y: 100 }, { x: 5000, y: 4000 });
    const paths = Array.from(container.querySelectorAll(".edge-layer path"));
    expect(paths.length).toBeGreaterThan(0);
    // course->limit edge: x2 = 5015+75 = 5090, y2 = 4105
    const d = paths.map((p) => p.getAttribute("d") ?? "").join("\n");
    expect(d).toContain("5090");
    expect(d).toContain("4105");
  });

  it("P-013 wheel zoom stays clamped to [0.5, 2.5]", () => {
    const { container } = render(<App />);
    const viewport = container.querySelector(".canvas-viewport") as HTMLElement;
    const surface = container.querySelector(".canvas-surface") as HTMLElement;
    wheel(viewport, -100, 30);
    expect(surface.style.transform).toContain("scale(2.5)");
    expect(surface.style.transform).not.toContain("scale(2.6)");
    wheel(viewport, 100, 60);
    expect(surface.style.transform).toContain("scale(0.5)");
    expect(surface.style.transform).not.toContain("scale(0.4)");
  });

  it("P-014 drag far keeps the camera/background transform stable (node drag != pan)", () => {
    const { container } = render(<App />);
    const surface = container.querySelector(".canvas-surface") as HTMLElement;
    const beforeTransform = surface.style.transform;
    const node = nodeButton("极限");
    dragNode(node, { x: 100, y: 100 }, { x: 5000, y: 4000 });
    // the surface legitimately grows, but the camera transform must not move
    expect(surface.style.transform).toBe(beforeTransform);
    expect(surface.style.transform).toContain("translate(0px, 0px)");
    // and panning the background still moves the camera
    fireEvent.pointerDown(surface, { pointerId: 2, clientX: 300, clientY: 300, buttons: 1 });
    fireEvent.pointerMove(surface, { pointerId: 2, clientX: 350, clientY: 340, buttons: 1 });
    fireEvent.pointerUp(surface, { pointerId: 2, clientX: 350, clientY: 340, buttons: 1 });
    expect(surface.style.transform).toContain("translate(50px, 40px)");
  });
});
