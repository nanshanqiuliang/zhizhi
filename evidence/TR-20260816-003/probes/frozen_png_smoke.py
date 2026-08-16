"""Frozen-exe MCP smoke probe for WORK-2026-051 (TR-20260816-003).

Boots the FROZEN zhizhi.exe in --mcp-stdio mode over a seeded temp workspace
and checks the export_png path: 7-tool set, export writes a valid PNG into
exports/, the graph stays untouched. Exit code 0 = all checks pass.
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
    load_course_graph,
    migrate,
    save_course_graph,
)

EXE = REPO / "dist" / "zhizhi" / "zhizhi.exe"
WORKSPACE_ID = "00000000-0000-7000-8000-000000000001"
COURSE_ID = "00000000-0000-7000-8000-000000000002"

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{name} {'PASS' if ok else 'FAIL'} {detail}")
    if not ok:
        FAILURES.append(name)


def _graph() -> dict:
    return {
        "schema_version": 1,
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "revision_no": 0,
        "concepts": [
            {
                "id": "00000000-0000-7000-a000-000000000001",
                "course_id": COURSE_ID,
                "label": "微积分",
                "origin": "user",
                "review_state": "accepted",
                "confidence": None,
                "evidence_ids": [],
                "locks": {
                    "content": False,
                    "relations": False,
                    "position": False,
                    "annotations": False,
                },
                "annotations": [],
                "revision_no": 0,
            },
            {
                "id": "00000000-0000-7000-a000-000000000002",
                "course_id": COURSE_ID,
                "label": "极限",
                "origin": "user",
                "review_state": "accepted",
                "confidence": None,
                "evidence_ids": [],
                "locks": {
                    "content": False,
                    "relations": False,
                    "position": False,
                    "annotations": False,
                },
                "annotations": [],
                "revision_no": 0,
            },
        ],
        "edges": [
            {
                "id": "00000000-0000-7000-b000-000000000001",
                "course_id": COURSE_ID,
                "source_concept_id": "00000000-0000-7000-a000-000000000001",
                "target_concept_id": "00000000-0000-7000-a000-000000000002",
                "edge_type": "prerequisite_of",
                "origin": "user",
                "review_state": "accepted",
                "confidence": None,
                "evidence_ids": [],
                "locked": False,
                "revision_no": 0,
            }
        ],
        "layout_items": [],
    }


async def run(data_root: Path) -> None:
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    params = StdioServerParameters(
        command=str(EXE),
        args=["--mcp-stdio", "--data-root", str(data_root)],
    )
    async with (
        stdio_client(params) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        tools = await session.list_tools()
        names = {tool.name for tool in tools.tools}
        check(
            "E1-tools",
            "export_png" in names and len(names) == 7,
            str(sorted(names)),
        )

        result = await session.call_tool("export_png", {"workspace_id": WORKSPACE_ID})
        payload = json.loads(result.content[0].text)
        check("E2-export-ok", payload.get("ok") is True, str(payload)[:200])
        exported = Path(payload["path"])
        check(
            "E3-png-valid",
            exported.is_file() and exported.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n",
        )
        check(
            "E4-in-exports",
            exported.parent == data_root / WORKSPACE_ID / "exports",
            str(exported.parent),
        )


def main() -> int:
    if not EXE.is_file():
        print(f"FATAL: frozen exe missing: {EXE}")
        return 2
    os.environ.pop("DEEPSEEK_API_KEY", None)
    with tempfile.TemporaryDirectory(prefix="zhizhi-png-smoke-") as tmp:
        data_root = Path(tmp)
        layout = create_workspace(data_root / WORKSPACE_ID)
        migrate(layout.db_path)
        save_course_graph(layout, _graph())
        asyncio.run(run(data_root))
        graph = load_course_graph(layout)
        check(
            "E5-graph-untouched",
            graph["revision_no"] == 0 and len(graph["concepts"]) == 2,
        )
    print("RESULT:", "PASS" if not FAILURES else f"FAIL {FAILURES}")
    return 0 if not FAILURES else 1


if __name__ == "__main__":
    raise SystemExit(main())
