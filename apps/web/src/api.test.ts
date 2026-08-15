import { afterEach, describe, expect, it, vi } from "vitest";

import { httpPersistApi } from "./api";

const WORKSPACE_ID = "00000000-0000-7000-8000-000000000001";
const BASE = "http://127.0.0.1:8000";

describe("persist api URL contract", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("routes backup/restore/history on the workspace base, not /graph", async () => {
    const fetchMock = vi.fn<
      (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
    >(async () => new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const api = httpPersistApi(BASE);

    await api.backupGraph();
    await api.listBackups();
    await api.restoreBackup("backup-1.sqlite3");
    await api.listHistory();

    const urls = fetchMock.mock.calls.map((call) => String(call[0]));
    expect(urls).toEqual([
      `${BASE}/api/workspaces/${WORKSPACE_ID}/backup`,
      `${BASE}/api/workspaces/${WORKSPACE_ID}/backups`,
      `${BASE}/api/workspaces/${WORKSPACE_ID}/restore`,
      `${BASE}/api/workspaces/${WORKSPACE_ID}/history`,
    ]);
  });

  it("uses a relative API base for same-origin desktop serving", async () => {
    const fetchMock = vi.fn<
      (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
    >(async () => new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const api = httpPersistApi("");

    await api.loadGraph();
    await api.backupGraph();

    const urls = fetchMock.mock.calls.map((call) => String(call[0]));
    expect(urls).toEqual([
      `/api/workspaces/${WORKSPACE_ID}/graph`,
      `/api/workspaces/${WORKSPACE_ID}/backup`,
    ]);
  });

  it("surfaces the rule in draft generation errors", async () => {
    const fetchMock = vi.fn<
      (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
    >(
      async () =>
        new Response(
          JSON.stringify({ code: "draft_invalid", rule: "no_new_concepts" }),
          { status: 422 },
        ),
    );
    vi.stubGlobal("fetch", fetchMock);
    const api = httpPersistApi(BASE);

    await expect(api.generateDraft()).rejects.toThrow(/draft_invalid\/no_new_concepts/);
  });
});
