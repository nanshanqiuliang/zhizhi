import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { PersistApi, ResourceInfo } from "./api";
import { App } from "./App";

function mockApi(overrides: Partial<PersistApi> = {}): PersistApi {
  const api: PersistApi = {
    loadGraph: vi.fn(async () => null),
    saveGraph: vi.fn(async () => undefined),
    searchGraph: vi.fn(async () => []),
    importResource: vi.fn(async () => ({
      id: "00000000-0000-7000-8100-000000000001",
      display_name: "notes.md",
      mime: "text/markdown",
      byte_size: 12,
      content_hash: "sha256:abc",
      created_at: "2026-08-14T00:00:00Z",
    })),
    listResources: vi.fn(async () => []),
    ...overrides,
  };
  return api;
}

describe("resource import", () => {
  it("lists imported resources from the API", async () => {
    const api = mockApi({
      listResources: vi.fn(
        async (): Promise<ResourceInfo[]> => [
          {
            id: "00000000-0000-7000-8100-000000000001",
            display_name: "导数讲义.md",
            mime: "text/markdown",
            byte_size: 120,
            content_hash: "sha256:abc",
            created_at: "2026-08-14T00:00:00Z",
          },
        ],
      ),
    });
    render(<App api={api} />);

    await waitFor(() => {
      expect(screen.getByText("导数讲义.md")).toBeInTheDocument();
    });
  });

  it("imports a file and shows the new resource", async () => {
    const api = mockApi();
    render(<App api={api} />);

    const input = screen.getByLabelText("导入资料（MD / TXT / PDF）");
    const file = new File(["# 极限"], "notes.md", { type: "text/markdown" });
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(api.importResource).toHaveBeenCalledTimes(1);
    });
    expect(screen.getByText("notes.md")).toBeInTheDocument();
  });

  it("shows an import failure message", async () => {
    const api = mockApi({
      importResource: vi.fn(async () => {
        throw new Error("import failed");
      }),
    });
    render(<App api={api} />);

    const input = screen.getByLabelText("导入资料（MD / TXT / PDF）");
    const file = new File(["x"], "evil.exe", { type: "application/octet-stream" });
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getAllByText(/导入失败/).length).toBeGreaterThan(0);
    });
  });
});
