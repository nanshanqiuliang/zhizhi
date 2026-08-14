import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { AnchorRef, PageText, PersistApi } from "./api";
import { App } from "./App";

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
      page: 1,
      text: "CHAPTER 2\nDerivatives\n",
      text_hash: "sha256:abc",
    })),
    listAnchors: vi.fn(async () => []),
    ...overrides,
  };
  return api;
}

describe("pdf viewer and anchor jump", () => {
  it("opens a resource in the page-text viewer", async () => {
    const api = mockApi({
      listResources: vi.fn(async () => [
        {
          id: "00000000-0000-7000-8100-000000000001",
          display_name: "chapter-02.pdf",
          mime: "application/pdf",
          byte_size: 1000,
          content_hash: "sha256:abc",
          created_at: "2026-08-14T00:00:00Z",
        },
      ]),
    });
    render(<App api={api} />);

    await waitFor(() => {
      expect(screen.getByText("chapter-02.pdf")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("chapter-02.pdf"));

    await waitFor(() => {
      expect(screen.getByText(/Derivatives/)).toBeInTheDocument();
    });
  });

  it("shows a jump-to-source button and jumps to the anchored page", async () => {
    const api = mockApi({
      listAnchors: vi.fn(
        async (): Promise<AnchorRef[]> => [
          {
            id: "00000000-0000-7000-8100-000000000010",
            page: 3,
            label: "2.1 The Derivative of a Function",
          },
        ],
      ),
    });
    render(<App api={api} />);

    await waitFor(() => {
      expect(screen.getByText("2.1 The Derivative of a Function")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("2.1 The Derivative of a Function"));

    await waitFor(() => {
      expect(api.getPageText).toHaveBeenCalledWith(
        "00000000-0000-7000-8100-000000000001",
        3,
      );
    });
  });

  it("shows a drift warning instead of a wrong jump", async () => {
    const api = mockApi({
      getPageText: vi.fn(async () => {
        throw new Error("source changed");
      }),
      listAnchors: vi.fn(
        async (): Promise<AnchorRef[]> => [
          { id: "a1", page: 3, label: "2.1 The Derivative of a Function" },
        ],
      ),
    });
    render(<App api={api} />);

    await waitFor(() => {
      expect(screen.getByText("2.1 The Derivative of a Function")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("2.1 The Derivative of a Function"));

    await waitFor(() => {
      expect(screen.getByText(/资料已变化，无法定位/)).toBeInTheDocument();
    });
  });
});
