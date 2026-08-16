import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";

function nodeButton(title: string): HTMLElement {
  const node = document.querySelector(`[aria-label="概念：${title}"]`) as HTMLElement | null;
  if (!node) throw new Error(`node not found: ${title}`);
  return node;
}

function surfaceTransform(container: HTMLElement): string {
  const surface = container.querySelector(".canvas-surface") as HTMLElement;
  return surface.style.transform;
}

function dragNode(node: HTMLElement, fromX: number, fromY: number, toX: number, toY: number, pointerId = 1) {
  fireEvent.pointerDown(node, { pointerId, clientX: fromX, clientY: fromY, buttons: 1 });
  fireEvent.pointerMove(node, { pointerId, clientX: toX, clientY: toY, buttons: 1 });
  fireEvent.pointerUp(node, { pointerId, clientX: toX, clientY: toY, buttons: 1 });
}

describe("QA-01 drag-jump regression (WORK-2026-047)", () => {
  it("P-001 camera unchanged across repeated drag+click cycles", () => {
    const { container } = render(<App />);
    const before = surfaceTransform(container);
    const node = nodeButton("极限");
    for (let cycle = 0; cycle < 3; cycle++) {
      const dx = 100 + cycle * 40;
      const dy = 50 + cycle * 30;
      dragNode(node, 100, 100, 100 + dx, 100 + dy, 1 + cycle);
      // Real browsers synthesize a click after pointerup; it must not recenter.
      fireEvent.click(node);
      expect(surfaceTransform(container)).toBe(before);
    }
  });

  it("P-002 plain node click still recenters the canvas", () => {
    const { container } = render(<App />);
    const before = surfaceTransform(container);
    fireEvent.click(nodeButton("极限"));
    expect(surfaceTransform(container)).not.toBe(before);
  });

  it("P-003 zero-displacement down/up still lets the click recenter", () => {
    const { container } = render(<App />);
    const before = surfaceTransform(container);
    const node = nodeButton("极限");
    fireEvent.pointerDown(node, { pointerId: 1, clientX: 100, clientY: 100, buttons: 1 });
    fireEvent.pointerUp(node, { pointerId: 1, clientX: 100, clientY: 100, buttons: 1 });
    fireEvent.click(node);
    expect(surfaceTransform(container)).not.toBe(before);
  });

  it("P-004 connect-mode node click does not recenter or select", () => {
    const { container } = render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "连线" }));
    const before = surfaceTransform(container);
    fireEvent.click(nodeButton("极限"));
    expect(surfaceTransform(container)).toBe(before);
    expect(nodeButton("极限").getAttribute("aria-pressed")).toBe("false");
  });
});
