"""Frozen-exe MCP smoke probe for WORK-2026-053 (TR-20260816-004).

Boots the FROZEN zhizhi.exe in --mcp-stdio mode over a seeded temp workspace
and checks the search-draft path with NO key configured (fail-closed): the
8-tool set must enumerate, and search_draft must return a structured
web_search_not_available error without any network egress. Exit 0 = pass.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
for _p in (
    str(REPO),
    str(REPO / "packages" / "contracts-py" / "src"),
    str(REPO / "packages" / "domain" / "src"),
    str(REPO / "packages" / "infrastructure" / "src"),
):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from knowledge_tree_infrastructure.workspace import (  # noqa: E402
    create_workspace,
    migrate,
    save_course_graph,
)

EXE = REPO / "dist" / "zhizhi" / "zhizhi.exe"
WORKSPACE_ID = "00000000-0000-7000-8000-000000000001"
COURSE_ID = "00000000-0000-7000-8000-000000000002"

FAILURES: list[str] = []

EXPECTED_TOOLS = {
    "list_workspaces",
    "read_workspace",
    "preview_draft",
    "validate_patch",
    "propose_patch",
    "proposal_status",
    "export_png",
    "search_draft",
}


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{name} {'PASS' if ok else 'FAIL'} {detail}")
    if not ok:
        FAILURES.append(name)


def _empty_graph() -> dict:
    return {
        "schema_version": 1,
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "revision_no": 0,
        "concepts": [],
        "edges": [],
        "layout_items": [],
    }


async def run(data_root: Path) -> None:
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    params = StdioServerParameters(
        command=str(EXE),
        args=["--mcp-stdio", "--data-root", str(data_root)],
        # Airtight no-key environment for the child process.
        env={k: v for k, v in os.environ.items() if not k.endswith("_API_KEY")},
    )
    async with (
        stdio_client(params) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        tools = await session.list_tools()
        names = {tool.name for tool in tools.tools}
        check("S1-tools", names == EXPECTED_TOOLS, str(sorted(names)))

        result = await session.call_tool(
            "search_draft", {"workspace_id": WORKSPACE_ID, "query": "微积分"}
        )
        payload = json.loads(result.content[0].text)
        check(
            "S2-fail-closed",
            payload.get("ok") is False
            and payload.get("code") == "web_search_not_available",
            str(payload)[:200],
        )


def main() -> int:
    if not EXE.is_file():
        print(f"FATAL: frozen exe missing: {EXE}")
        return 2
    for var in ("TAVILY_API_KEY", "BRAVE_API_KEY", "ZHIZHI_WEB_SEARCH_PROVIDER"):
        os.environ.pop(var, None)
    with tempfile.TemporaryDirectory(prefix="zhizhi-search-smoke-") as tmp:
        data_root = Path(tmp)
        layout = create_workspace(data_root / WORKSPACE_ID)
        migrate(layout.db_path)
        save_course_graph(layout, _empty_graph())
        asyncio.run(run(data_root))
    print("RESULT:", "PASS" if not FAILURES else f"FAIL {FAILURES}")
    return 0 if not FAILURES else 1


if __name__ == "__main__":
    raise SystemExit(main())
