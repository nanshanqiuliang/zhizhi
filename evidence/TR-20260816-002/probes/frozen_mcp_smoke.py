"""Frozen-exe MCP smoke probe for WORK-2026-050 (TR-20260816-002).

Boots the FROZEN zhizhi.exe in --mcp-stdio mode, seeds a workspace under a
temp data root (via source-side infrastructure), then exercises the full
propose -> observe loop: list_tools must show the 6-tool set, propose_patch
must queue a pending proposal without touching the graph, proposal_status
must observe it. Exit code 0 = all checks pass. Nothing modifies product code.
"""

from __future__ import annotations

import asyncio
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


def _valid_patch() -> dict:
    return {
        "schema_version": 1,
        "patch_id": "00000000-0000-7000-8000-0000000000a1",
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "base_revision_no": 0,
        "actor": {"type": "user", "id": "local-user"},
        "reason": "冻结冒烟提议",
        "requires_confirmation": True,
        "confirmed": False,
        "operations": [
            {
                "op_id": "00000000-0000-7000-8000-0000000000a2",
                "op": "create_concept",
                "concept": {
                    "id": "00000000-0000-7000-a000-0000000000a3",
                    "course_id": COURSE_ID,
                    "label": "冻结冒烟概念",
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
            }
        ],
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
            "P1-tools",
            names
            == {
                "list_workspaces",
                "read_workspace",
                "preview_draft",
                "validate_patch",
                "propose_patch",
                "proposal_status",
            },
            str(sorted(names)),
        )

        result = await session.call_tool(
            "propose_patch",
            {"workspace_id": WORKSPACE_ID, "patch": _valid_patch(), "note": "frozen smoke"},
        )
        payload = __import__("json").loads(result.content[0].text)
        check("P2-propose-ok", payload.get("ok") is True, str(payload)[:200])
        check(
            "P2-unconfirmed",
            payload.get("status") == "pending"
            and payload.get("confirmed") is False,
        )
        proposal_id = payload.get("proposal_id", "")

        status = await session.call_tool(
            "proposal_status",
            {"workspace_id": WORKSPACE_ID, "proposal_id": proposal_id},
        )
        status_payload = __import__("json").loads(status.content[0].text)
        check(
            "P3-status-pending",
            status_payload.get("ok") is True
            and status_payload.get("status") == "pending",
            str(status_payload)[:200],
        )

        missing = await session.call_tool(
            "proposal_status",
            {"workspace_id": WORKSPACE_ID, "proposal_id": "00000000-0000-7000-8000-0000000000ee"},
        )
        missing_payload = __import__("json").loads(missing.content[0].text)
        check(
            "P4-missing-closed",
            missing_payload.get("ok") is False
            and missing_payload.get("code") == "proposal_missing",
            str(missing_payload)[:200],
        )


def main() -> int:
    if not EXE.is_file():
        print(f"FATAL: frozen exe missing: {EXE}")
        return 2
    os.environ.pop("DEEPSEEK_API_KEY", None)
    with tempfile.TemporaryDirectory(prefix="zhizhi-frozen-smoke-") as tmp:
        data_root = Path(tmp)
        layout = create_workspace(data_root / WORKSPACE_ID)
        migrate(layout.db_path)
        save_course_graph(layout, _empty_graph())
        asyncio.run(run(data_root))
        graph = load_course_graph(resolve := layout)
        check(
            "P5-graph-untouched",
            graph["revision_no"] == 0 and graph["concepts"] == [],
        )
        proposals = (data_root / WORKSPACE_ID / "proposals").glob("*.json")
        check("P6-file-queued", any(True for _ in proposals), "proposals dir has a file")
    print("RESULT:", "PASS" if not FAILURES else f"FAIL {FAILURES}")
    return 0 if not FAILURES else 1


if __name__ == "__main__":
    raise SystemExit(main())
