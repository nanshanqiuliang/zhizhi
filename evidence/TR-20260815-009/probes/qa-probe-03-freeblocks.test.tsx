import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";

function nodeButton(title: string): HTMLElement {
  const node = document.querySelector(`[aria-label="概念：${title}"]`) as HTMLElement | null;
  if (!node) throw new Error(`node not found: ${title}`);
  return node;
}

function edgeLabels(): string[] {
  return Array.from(document.querySelectorAll('[aria-label^="连线："]')).map((element) =>
    element.getAttribute("aria-label") ?? "",
  );
}

function stubViewport(container: HTMLElement, width: number, height: number) {
  const viewport = container.querySelector(".canvas-viewport") as HTMLElement;
  Object.defineProperty(viewport, "clientWidth", { value: width, configurable: true });
  Object.defineProperty(viewport, "clientHeight", { value: height, configurable: true });
}

describe("QA-03 free blocks (WORK-2026-047)", () => {
  it("P-201 add concept lands at the viewport center with no upper clamp", () => {
    const { container } = render(<App />);
    stubViewport(container, 1200, 800);
    // Pan the camera left by 1600px so the world-space viewport center is at
    // x=2200 (> the old 835 clamp); a clamped implementation would cap there.
    const surface = container.querySelector(".canvas-surface") as HTMLElement;
    fireEvent.pointerDown(surface, { pointerId: 2, clientX: 1600, clientY: 0, buttons: 1 });
    fireEvent.pointerMove(surface, { pointerId: 2, clientX: 0, clientY: 0, buttons: 1 });
    fireEvent.pointerUp(surface, { pointerId: 2, clientX: 0, clientY: 0, buttons: 1 });

    fireEvent.click(screen.getByRole("button", { name: "添加概念" }));
    const block = nodeButton("新概念");
    expect(block).toBeInTheDocument();
    // centerX = (1200/2 - camera.x)/zoom - 75 = (600 + 1600) - 75 = 2125
    expect(block.style.left).toBe("2125px");
    // centerY = (800/2 - camera.y)/zoom - 34 = 400 - 34 = 366
    expect(block.style.top).toBe("366px");
    expect(block.querySelector(".node-type")?.textContent).toBe("概念");
    expect(block.classList.contains("locked")).toBe(false);
    // No parent edge is drawn for the free block.
    expect(edgeLabels().some((label) => label.includes("新概念"))).toBe(false);
  });

  it("P-202 add outline creates a root block with 主题 tone and no parent edge", () => {
    const { container } = render(<App />);
    stubViewport(container, 1200, 800);
    fireEvent.click(screen.getByRole("button", { name: "添加总纲" }));
    const block = nodeButton("新总纲");
    expect(block).toBeInTheDocument();
    expect(block.querySelector(".node-type")?.textContent).toBe("主题");
    expect(block.style.left).toBe("525px");
    expect(block.style.top).toBe("366px");
    expect(edgeLabels().some((label) => label.includes("新总纲"))).toBe(false);
  });

  it("P-203 a new free block can be dragged arbitrarily far (no clamp)", () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "添加概念" }));
    const block = nodeButton("新概念");
    // Drag from origin (8,8) by (+900,+700) -> (908,708), far past 835/555.
    fireEvent.pointerDown(block, { pointerId: 3, clientX: 0, clientY: 0, buttons: 1 });
    fireEvent.pointerMove(block, { pointerId: 3, clientX: 900, clientY: 700, buttons: 1 });
    fireEvent.pointerUp(block, { pointerId: 3, clientX: 900, clientY: 700, buttons: 1 });
    expect(block.style.left).toBe("908px");
    expect(block.style.top).toBe("708px");
  });
});
