import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { AnchorRef, PersistApi, ResourceInfo } from "./api";
import { App } from "./App";

// PdfRenderer performs real pdfjs loading; in jsdom tests we stub it so the
// App-level behavior (view switching, bbox highlight rendering) is what is
// verified.
vi.mock("./PdfRenderer", () => ({
  PdfRenderer: ({
    page,
    activeAnchor,
  }: {
    page: number;
    activeAnchor: AnchorRef | null;
  }) => (
    <div aria-label="PDF 渲染视图" data-page={page}>
      <canvas aria-label="PDF 页面画布" data-page={page} />
      {activeAnchor?.bboxNorm && (
        <div
          aria-label="锚点高亮区域"
          data-left={Math.round(activeAnchor.bboxNorm[0] * 100)}
          data-top={Math.round(activeAnchor.bboxNorm[1] * 100)}
          data-width={Math.round((activeAnchor.bboxNorm[2] - activeAnchor.bboxNorm[0]) * 100)}
          data-height={Math.round((activeAnchor.bboxNorm[3] - activeAnchor.bboxNorm[1]) * 100)}
        />
      )}
    </div>
  ),
}));

const PDF_RESOURCE: ResourceInfo = {
  id: "00000000-0000-7000-8100-000000000001",
  display_name: "chapter-02.pdf",
  mime: "application/pdf",
  byte_size: 1000,
  content_hash: "sha256:abc",
  created_at: "2026-08-14T00:00:00Z",
};

function mockApi(overrides: Partial<PersistApi> = {}): PersistApi {
  const api: PersistApi = {
    loadGraph: vi.fn(async () => null),
    saveGraph: vi.fn(async () => undefined),
    searchGraph: vi.fn(async () => []),
    importResource: vi.fn(async () => {
      throw new Error("not used");
    }),
    listResources: vi.fn(async () => []),
    parsePdf: vi.fn(async () => ({ page_count: 52 })),
    getPageText: vi.fn(async () => ({
      resource_version_id: "v",
      page: 1,
      text: "CHAPTER 2\nDerivatives\n",
      text_hash: "sha256:abc",
    })),
    listAnchors: vi.fn(async () => []),
    getFileUrl: vi.fn(() => "http://127.0.0.1:8000/file.pdf"),
    getResourceText: vi.fn(async () => "text content"),
    generateDraft: vi.fn(async () => ({ draft: { concepts: [], relations: [] }, patch: {} })),
    acceptDraft: vi.fn(async () => ({ status: "applied", change_id: "c", revision_no: 1 })),
    askQuestion: vi.fn(async () => ({ answer: "", sources: [] })),
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

describe("pdf.js visual render and bbox highlight", () => {
  it("opens a PDF in the rendered view with a canvas", async () => {
    const api = mockApi({ listResources: vi.fn(async () => [PDF_RESOURCE]) });
    render(<App api={api} />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "打开" })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "打开" }));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "渲染" })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "渲染" }));

    await waitFor(() => {
      expect(screen.getByLabelText("PDF 渲染视图")).toBeInTheDocument();
    });
    // The canvas is rendered by the PDF renderer component.
    expect(screen.getByLabelText("PDF 页面画布")).toBeInTheDocument();
  });

  it("highlights a bbox anchor on the rendered page", async () => {
    const api = mockApi({
      listResources: vi.fn(async () => [PDF_RESOURCE]),
      listAnchors: vi.fn(
        async (): Promise<AnchorRef[]> => [
          {
            id: "a1",
            page: 3,
            label: "2.1 The Derivative of a Function",
            bboxNorm: [0.1, 0.2, 0.6, 0.35],
          },
        ],
      ),
    });
    render(<App api={api} />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "打开" })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "打开" }));

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /The Derivative of a Function/ }),
      ).toBeInTheDocument();
    });
    fireEvent.click(
      screen.getByRole("button", { name: /The Derivative of a Function/ }),
    );

    await waitFor(() => {
      expect(screen.getByLabelText("锚点高亮区域")).toBeInTheDocument();
    });
    const highlight = screen.getByLabelText("锚点高亮区域");
    expect(highlight).toHaveAttribute("data-left", "10");
    expect(highlight).toHaveAttribute("data-top", "20");
    expect(highlight).toHaveAttribute("data-width", "50");
    expect(highlight).toHaveAttribute("data-height", "15");
  });
});
