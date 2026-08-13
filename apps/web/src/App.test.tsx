import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";

function nodeButton(name: string) {
  return screen.getByRole("button", { name: new RegExp(`概念：${name}`) });
}

describe("knowledge tree workspace", () => {
  it("renders the sample workspace and names unavailable capabilities", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "微积分 · 连续性与可导性" })).toBeInTheDocument();
    expect(screen.getByLabelText("知识树画布")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /概念：/ })).toHaveLength(8);
    expect(screen.getByText("示例数据")).toBeInTheDocument();
    expect(screen.getByText(/仅保留在本次会话/)).toBeInTheDocument();
    expect(screen.getByText(/AI 未连接/)).toBeInTheDocument();
  });

  it("selects a node and edits its title and note with undo and redo", () => {
    render(<App />);

    fireEvent.click(nodeButton("极限"));
    const title = screen.getByLabelText("概念标题");
    const note = screen.getByLabelText("概念笔记");
    expect(title).toHaveValue("极限");

    fireEvent.change(title, { target: { value: "函数极限" } });
    fireEvent.change(note, { target: { value: "描述自变量趋近时函数的行为。" } });
    fireEvent.click(screen.getByRole("button", { name: "保存修改" }));
    expect(nodeButton("函数极限")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "撤销" }));
    expect(nodeButton("极限")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "重做" }));
    expect(nodeButton("函数极限")).toBeInTheDocument();
  });

  it("adds a child and deletes only leaf nodes", () => {
    render(<App />);

    fireEvent.click(nodeButton("连续"));
    fireEvent.click(screen.getByRole("button", { name: "添加子概念" }));
    expect(nodeButton("新概念")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "删除当前节点" }));
    expect(screen.queryByRole("button", { name: /概念：新概念/ })).not.toBeInTheDocument();

    fireEvent.click(nodeButton("极限"));
    fireEvent.click(screen.getByRole("button", { name: "删除当前节点" }));
    expect(screen.getByRole("status")).toHaveTextContent("只能删除没有子节点的概念");
    expect(nodeButton("极限")).toBeInTheDocument();
  });

  it("moves a node, preserves a locked position during layout, and can reset demo", () => {
    render(<App />);

    const node = nodeButton("极限");
    const before = node.getAttribute("style");
    fireEvent.pointerDown(node, { pointerId: 1, clientX: 100, clientY: 100 });
    fireEvent.pointerMove(node, { pointerId: 1, clientX: 190, clientY: 150 });
    fireEvent.pointerUp(node, { pointerId: 1, clientX: 190, clientY: 150 });
    expect(node.getAttribute("style")).not.toBe(before);

    fireEvent.click(screen.getByRole("button", { name: "锁定位置" }));
    const lockedPosition = node.getAttribute("style");
    fireEvent.click(screen.getByRole("button", { name: "自动排布" }));
    expect(node.getAttribute("style")).toBe(lockedPosition);

    fireEvent.click(screen.getByRole("button", { name: "重新载入示例" }));
    expect(screen.getAllByRole("button", { name: /概念：/ })).toHaveLength(8);
    expect(screen.getByRole("status")).toHaveTextContent("示例已重新载入");
  });

  it("keeps toolbar and detail controls accessible", () => {
    render(<App />);

    const toolbar = screen.getByRole("toolbar", { name: "知识树工具" });
    expect(within(toolbar).getByRole("button", { name: "撤销" })).toBeDisabled();
    expect(within(toolbar).getByRole("button", { name: "重做" })).toBeDisabled();
    expect(screen.getByRole("region", { name: "节点详情" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "课程与笔记" })).toBeInTheDocument();
  });
});
