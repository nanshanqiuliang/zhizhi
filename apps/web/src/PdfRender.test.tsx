import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { AnchorRef, PersistApi, ResourceInfo } from "./api";
import { App } from "./App";

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
      expect(screen.getByText(/2\\.1 The Derivative of a Function/)).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText(/2\\.1 The Derivative of a Function/));

    await waitFor(() => {
      expect(screen.getByLabelText("锚点高亮区域")).toBeInTheDocument();
    });
  });
});
