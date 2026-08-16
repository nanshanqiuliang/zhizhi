import { fireEvent, render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";
import { canvasSurfaceSize } from "./canvas";

function nodeButton(title: string): HTMLElement {
  const node = document.querySelector(`[aria-label="概念：${title}"]`) as HTMLElement | null;
  if (!node) throw new Error(`node not found: ${title}`);
  return node;
}

describe("unbounded canvas (WORK-2026-045)", () => {
  it("drags a node beyond the old 835/555 clamp bounds", () => {
    render(<App />);

    // 极限 starts at (115, 205); move the pointer far beyond the old bounds.
    const node = nodeButton("极限");
    fireEvent.pointerDown(node, { pointerId: 1, clientX: 100, clientY: 100, buttons: 1 });
    fireEvent.pointerMove(node, { pointerId: 1, clientX: 1400, clientY: 1300, buttons: 1 });
    fireEvent.pointerUp(node, { pointerId: 1, clientX: 1400, clientY: 1300, buttons: 1 });

    const left = parseFloat(node.style.left);
    const top = parseFloat(node.style.top);
    expect(left).toBeGreaterThan(835);
    expect(top).toBeGreaterThan(555);
    // delta = 1300/1200 at zoom 1 → exact target, not the clamped boundary.
    expect(left).toBe(115 + 1300);
    expect(top).toBe(205 + 1200);
  });

  it("grows the canvas surface and edge layer with content", () => {
    const { container } = render(<App />);
    const surface = container.querySelector(".canvas-surface") as HTMLElement;
    const edgeLayer = container.querySelector(".edge-layer") as SVGSVGElement;

    const node = nodeButton("极限");
    fireEvent.pointerDown(node, { pointerId: 1, clientX: 100, clientY: 100, buttons: 1 });
    fireEvent.pointerMove(node, { pointerId: 1, clientX: 1400, clientY: 1300, buttons: 1 });
    fireEvent.pointerUp(node, { pointerId: 1, clientX: 1400, clientY: 1300, buttons: 1 });

    const width = parseFloat(surface.style.width);
    const height = parseFloat(surface.style.height);
    expect(width).toBeGreaterThan(1000);
    expect(height).toBeGreaterThan(650);
    // Content bounds: max x = 1415 (+150 node +48 margin), max y = 1405 (+68 +48).
    expect(width).toBe(1415 + 150 + 48);
    expect(height).toBe(1405 + 68 + 48);
    expect(edgeLayer.getAttribute("viewBox")).toBe(`0 0 ${width} ${height}`);
    expect(parseFloat(edgeLayer.style.width)).toBe(width);
    expect(parseFloat(edgeLayer.style.height)).toBe(height);
  });

  it("keeps a 1000x650 floor and handles empty content in the size helper", () => {
    expect(canvasSurfaceSize([])).toEqual({ width: 1000, height: 650 });
    expect(canvasSurfaceSize([{ x: 100, y: 100 }])).toEqual({ width: 1000, height: 650 });
    expect(canvasSurfaceSize([{ x: 5000, y: 3000 }])).toEqual({
      width: 5000 + 150 + 48,
      height: 3000 + 68 + 48,
    });
    // Negative coordinates are outside the current scope: floor applies.
    expect(canvasSurfaceSize([{ x: -100, y: -50 }])).toEqual({ width: 1000, height: 650 });
  });
});
