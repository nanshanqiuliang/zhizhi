// Minimal, XSS-safe Markdown renderer for the local note viewer.
//
// It first HTML-escapes the raw text (so user-imported content can never inject
// markup), then applies a small, explicit set of Markdown constructs on top of
// the escaped text. The produced HTML only contains tags this module emits.

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderInline(text: string): string {
  let value = escapeHtml(text);
  value = value.replace(/`([^`]+)`/g, "<code>$1</code>");
  value = value.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  value = value.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  return value;
}

export function renderMarkdown(text: string): string {
  const lines = text.split("\n");
  const output: string[] = [];
  let inCodeBlock = false;
  let inList = false;
  const codeLines: string[] = [];

  const closeList = () => {
    if (inList) {
      output.push("</ul>");
      inList = false;
    }
  };

  for (const line of lines) {
    if (line.trimStart().startsWith("```")) {
      closeList();
      if (inCodeBlock) {
        output.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
        codeLines.length = 0;
        inCodeBlock = false;
      } else {
        inCodeBlock = true;
      }
      continue;
    }
    if (inCodeBlock) {
      codeLines.push(line);
      continue;
    }
    const heading = line.match(/^(#{1,3})\s+(.*)$/);
    if (heading) {
      closeList();
      const level = heading[1].length;
      output.push(`<h${level}>${renderInline(heading[2])}</h${level}>`);
      continue;
    }
    if (line.trimStart().startsWith("- ")) {
      if (!inList) {
        output.push("<ul>");
        inList = true;
      }
      output.push(`<li>${renderInline(line.trimStart().slice(2))}</li>`);
      continue;
    }
    closeList();
    if (line.trim() === "") {
      continue;
    }
    output.push(`<p>${renderInline(line)}</p>`);
  }
  closeList();
  if (inCodeBlock) {
    output.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
  }
  return output.join("\n");
}
