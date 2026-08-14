import { describe, expect, it } from "vitest";

import { renderMarkdown } from "./markdown";

describe("renderMarkdown", () => {
  it("renders headings, lists, bold and inline code", () => {
    const html = renderMarkdown("# 标题\n\n- 项目一\n- 项目二\n\n**加粗** 和 `代码`");

    expect(html).toContain("<h1>标题</h1>");
    expect(html).toContain("<ul>");
    expect(html).toContain("<li>项目一</li>");
    expect(html).toContain("<li>项目二</li>");
    expect(html).toContain("<strong>加粗</strong>");
    expect(html).toContain("<code>代码</code>");
  });

  it("escapes raw HTML to prevent injection", () => {
    const html = renderMarkdown("<script>alert('xss')</script>");

    expect(html).not.toContain("<script>");
    expect(html).toContain("&lt;script&gt;");
  });

  it("renders fenced code blocks", () => {
    const html = renderMarkdown("```\nconst x = 1;\n```");

    expect(html).toContain("<pre><code>const x = 1;</code></pre>");
  });
});
