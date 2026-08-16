import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";

function nodeButton(title: string): HTMLElement {
  const node = document.querySelector(`[aria-label="概念：${title}"]`) as HTMLElement | null;
  if (!node) throw new Error(`node not found: ${title}`);
  return node;
}

describe("editing toolbox (WORK-2026-047)", () => {
  it("does not recenter the canvas after a node drag + browser click", () => {
    const { container } = render(<App />);
    const surface = container.querySelector(".canvas-surface") as HTMLElement;
    const before = surface.style.transform;

    const node = nodeButton("极限");
    fireEvent.pointerDown(node, { pointerId: 1, clientX: 100, clientY: 100, buttons: 1 });
    fireEvent.pointerMove(node, { pointerId: 1, clientX: 300, clientY: 200, buttons: 1 });
    fireEvent.pointerUp(node, { pointerId: 1, clientX: 300, clientY: 200, buttons: 1 });
    // Real browsers synthesize a click after pointerup; it must not recenter.
    fireEvent.click(node);

    expect(surface.style.transform).toBe(before);
  });

  it("still recenters the canvas on a plain node click", () => {
    const { container } = render(<App />);
    const surface = container.querySelector(".canvas-surface") as HTMLElement;
    const before = surface.style.transform;

    fireEvent.click(nodeButton("极限"));

    expect(surface.style.transform).not.toBe(before);
  });

  it("adds a free concept block without a parent edge", () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "添加概念" }));

    const block = nodeButton("新概念");
    expect(block).toBeInTheDocument();
    expect(block.querySelector(".node-type")?.textContent).toBe("概念");
    const edgeLabels = Array.from(document.querySelectorAll('[aria-label^="连线："]')).map(
      (element) => element.getAttribute("aria-label") ?? "",
    );
    expect(edgeLabels.some((label) => label.includes("新概念"))).toBe(false);
  });

  it("adds a root outline block", () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "添加总纲" }));

    const block = nodeButton("新总纲");
    expect(block).toBeInTheDocument();
    expect(block.querySelector(".node-type")?.textContent).toBe("主题");
  });

  it("connects two blocks with the selected edge type", () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "连线" }));
    fireEvent.change(screen.getByRole("combobox", { name: "连线类型" }), {
      target: { value: "prerequisite_of" },
    });
    fireEvent.click(nodeButton("函数"));
    fireEvent.click(nodeButton("ε-δ 语言"));

    expect(
      document.querySelector('[aria-label="连线：函数 → ε-δ 语言（先修）"]'),
    ).not.toBeNull();
  });

  it("disconnects an edge from the detail panel", () => {
    render(<App />);

    fireEvent.click(nodeButton("极限"));
    fireEvent.click(screen.getByRole("button", { name: "删除连线 指向 函数" }));

    expect(
      document.querySelector('[aria-label="连线：极限 → 函数（相关）"]'),
    ).toBeNull();
  });
});
