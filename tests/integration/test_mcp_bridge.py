"""MCP bridge tests (WORK-2026-048, Step 11 slice 1).

The built-in MCP server exposes read + AI-propose tools ONLY; this slice has
no write tools: external AI can read the tree and propose drafts, while
confirmation and writing stay inside the app (harness hard rule).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

from knowledge_tree_infrastructure.workspace import (
    create_workspace,
    import_resource,
    migrate,
    save_course_graph,
)

from apps.api.mcp_server import build_mcp_server

JsonObject = dict[str, Any]

WORKSPACE_ID = "00000000-0000-7000-8000-000000000001"
COURSE_ID = "00000000-0000-7000-8000-000000000002"


def _empty_graph() -> JsonObject:
    return {
        "schema_version": 1,
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "revision_no": 0,
        "concepts": [],
        "edges": [],
        "layout_items": [],
    }


def _seed_workspace(root: Path, with_resource: bool = True) -> str:
    layout = create_workspace(root / WORKSPACE_ID)
    migrate(layout.db_path)
    save_course_graph(layout, _empty_graph())
    if with_resource:
        import_resource(
            layout,
            display_name="notes.md",
            content=b"# limit\n\ncontinuity",
        )
    return WORKSPACE_ID


def _fake_workspace_draft(texts: list[tuple[str, str]], graph: JsonObject) -> JsonObject:
    """Deterministic offline generator: one AI chain draft (no network)."""
    base = int(graph["revision_no"])
    course_id = str(graph["course_id"])
    workspace_id = str(graph["workspace_id"])
    evidence = "00000000-0000-7000-9000-000000000001"
    concept_a = "00000000-0000-7000-8000-000000000101"
    concept_b = "00000000-0000-7000-8000-000000000102"

    def concept(concept_id: str, label: str) -> JsonObject:
        return {
            "id": concept_id,
            "course_id": course_id,
            "label": label,
            "origin": "user",
            "review_state": "accepted",
            "confidence": None,
            "evidence_ids": [evidence],
            "locks": {
                "content": False,
                "relations": False,
                "position": False,
                "annotations": False,
            },
            "annotations": [],
            "revision_no": 0,
        }

    patch = {
        "schema_version": 1,
        "patch_id": f"00000000-0000-7000-8000-{base + 1:012d}",
        "workspace_id": workspace_id,
        "course_id": course_id,
        "base_revision_no": base,
        "actor": {"type": "user", "id": "local-user"},
        "reason": "AI 草案：全库思维导图",
        "requires_confirmation": True,
        "confirmed": False,
        "operations": [
            {
                "op_id": f"00000000-0000-7000-8000-{base + 2:012d}",
                "op": "create_concept",
                "concept": concept(concept_a, "极限"),
            },
            {
                "op_id": f"00000000-0000-7000-8000-{base + 3:012d}",
                "op": "create_concept",
                "concept": concept(concept_b, "连续"),
            },
            {
                "op_id": f"00000000-0000-7000-8000-{base + 4:012d}",
                "op": "create_edge",
                "expected_source_revision_no": 0,
                "expected_target_revision_no": 0,
                "edge": {
                    "id": f"00000000-0000-7000-8000-{base + 5:012d}",
                    "course_id": course_id,
                    "source_concept_id": concept_a,
                    "target_concept_id": concept_b,
                    "edge_type": "prerequisite_of",
                    "origin": "user",
                    "review_state": "accepted",
                    "confidence": None,
                    "evidence_ids": [evidence],
                    "locked": False,
                    "revision_no": 0,
                },
            },
            {
                "op_id": f"00000000-0000-7000-8000-{base + 6:012d}",
                "op": "set_layout_item",
                "target": {"type": "concept", "id": concept_a},
                "expected_updated_revision_no": 0,
                "layout_item": {
                    "view_id": workspace_id,
                    "concept_id": concept_a,
                    "x": 0.0,
                    "y": 0.0,
                    "pinned": False,
                    "revision_no": 0,
                },
            },
            {
                "op_id": f"00000000-0000-7000-8000-{base + 7:012d}",
                "op": "set_layout_item",
                "target": {"type": "concept", "id": concept_b},
                "expected_updated_revision_no": 0,
                "layout_item": {
                    "view_id": workspace_id,
                    "concept_id": concept_b,
                    "x": 220.0,
                    "y": 0.0,
                    "pinned": False,
                    "revision_no": 0,
                },
            },
        ],
    }
    return {
        "draft": {
            "concepts": [
                {"label": "极限", "aliases": [], "confidence": 0.9, "evidence_ids": [evidence]},
                {"label": "连续", "aliases": [], "confidence": 0.85, "evidence_ids": [evidence]},
            ],
            "relations": [
                {
                    "source_label": "极限",
                    "target_label": "连续",
                    "edge_type": "prerequisite_of",
                    "confidence": 0.7,
                    "evidence_ids": [evidence],
                }
            ],
        },
        "patch": patch,
    }


def _server(root: Path) -> Any:
    return build_mcp_server(
        root,
        workspace_draft_generator=_fake_workspace_draft,
        draft_generator=lambda text, resource_id, graph: _fake_workspace_draft(
            [(resource_id, text)], graph
        ),
    )


def _call_tool(server: Any, tool: str, **kwargs: Any) -> JsonObject:
    """Invoke a tool's underlying function through the FastMCP tool registry."""
    manager = server._tool_manager  # noqa: SLF001 - test-only introspection
    fn = manager.get_tool(tool).fn
    result = fn(**kwargs)
    return result if isinstance(result, dict) else {"ok": True, "result": result}


def test_mcp_toolset_is_read_only(tmp_path: Path) -> None:
    server = _server(tmp_path)

    tools = {item.name for item in server._tool_manager.list_tools()}  # noqa: SLF001
    # WORK-2026-050: propose_patch queues a PENDING proposal file (never the
    # graph); proposal_status is read-only observation. No tool may write the
    # graph itself (harness hard rule).
    assert tools == {
        "list_workspaces",
        "read_workspace",
        "preview_draft",
        "validate_patch",
        "propose_patch",
        "proposal_status",
    }
    # No graph-write-capable tool verb may appear in any tool name.
    for forbidden in ("write", "apply", "submit", "commit", "save", "delete", "accept"):
        assert not any(forbidden in tool for tool in tools)


def test_list_and_read_workspace(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)
    server = _server(tmp_path)

    listed = _call_tool(server, "list_workspaces")
    assert listed["ok"] is True
    assert WORKSPACE_ID in [item["id"] for item in listed["workspaces"]]

    graph = _call_tool(server, "read_workspace", workspace_id=WORKSPACE_ID)
    assert graph["ok"] is True
    assert graph["graph"]["workspace_id"] == WORKSPACE_ID


def test_preview_draft_returns_unconfirmed_proposal_without_writing(
    tmp_path: Path,
) -> None:
    workspace_id = _seed_workspace(tmp_path)
    server = _server(tmp_path)

    result = _call_tool(server, "preview_draft", workspace_id=workspace_id)
    assert result["ok"] is True
    patch = result["patch"]
    assert patch["requires_confirmation"] is True
    assert patch["confirmed"] is False
    # Nothing was written: the graph is still the empty baseline.
    graph = _call_tool(server, "read_workspace", workspace_id=workspace_id)
    assert graph["graph"]["revision_no"] == 0
    assert graph["graph"]["concepts"] == []


def test_preview_draft_without_key_fails_closed(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)
    server = build_mcp_server(tmp_path)  # no injected generator, no key

    result = _call_tool(server, "preview_draft", workspace_id=WORKSPACE_ID)
    assert result["ok"] is False
    assert result["code"] == "ai_not_available"


def test_validate_patch_previews_without_writing(tmp_path: Path) -> None:
    workspace_id = _seed_workspace(tmp_path)
    server = _server(tmp_path)

    draft = _call_tool(server, "preview_draft", workspace_id=workspace_id)
    patch = draft["patch"]

    preview = _call_tool(server, "validate_patch", workspace_id=workspace_id, patch=patch)
    assert preview["ok"] is True
    assert preview["status"] == "requires_confirmation"
    # Still nothing written.
    graph = _call_tool(server, "read_workspace", workspace_id=workspace_id)
    assert graph["graph"]["revision_no"] == 0


def test_validate_patch_rejects_conflict_without_writing(tmp_path: Path) -> None:
    workspace_id = _seed_workspace(tmp_path)
    server = _server(tmp_path)

    draft = _call_tool(server, "preview_draft", workspace_id=workspace_id)
    patch = draft["patch"]
    patch["base_revision_no"] = 99  # conflict with graph revision 0

    result = _call_tool(server, "validate_patch", workspace_id=workspace_id, patch=patch)
    assert result["ok"] is False
    assert result["code"] == "patch_invalid"
    assert result["rule"] == "base_revision_mismatch"


def _stdio_smoke(root: Path) -> None:
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "apps.api.mcp_server", "--data-root", str(root)],
    )

    async def run() -> None:
        async with (
            stdio_client(params) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            assert names == {
                "list_workspaces",
                "read_workspace",
                "preview_draft",
                "validate_patch",
                "propose_patch",
                "proposal_status",
            }
            result = await session.call_tool("list_workspaces", {})
            text = result.content[0].text
            assert '"ok": true' in text

    asyncio.run(run())


def test_stdio_protocol_smoke(tmp_path: Path) -> None:
    _stdio_smoke(tmp_path)


# -- WORK-2026-050: propose_patch queues a pending proposal, never writes -----


def test_propose_patch_queues_pending_without_writing(tmp_path: Path) -> None:
    workspace_id = _seed_workspace(tmp_path)
    server = _server(tmp_path)

    draft = _call_tool(server, "preview_draft", workspace_id=workspace_id)
    result = _call_tool(
        server,
        "propose_patch",
        workspace_id=workspace_id,
        patch=draft["patch"],
        note="from cursor",
    )
    assert result["ok"] is True
    assert result["proposal_id"]
    assert result["status"] == "pending"
    assert result["requires_confirmation"] is True
    assert result["confirmed"] is False

    # The graph itself is untouched: still the empty baseline.
    graph = _call_tool(server, "read_workspace", workspace_id=workspace_id)
    assert graph["graph"]["revision_no"] == 0
    assert graph["graph"]["concepts"] == []

    # The proposal is observable through the read-only status tool.
    status = _call_tool(
        server, "proposal_status", workspace_id=workspace_id, proposal_id=result["proposal_id"]
    )
    assert status["ok"] is True
    assert status["status"] == "pending"
    assert status["change_id"] is None


def test_propose_patch_invalid_patch_fails_closed_without_file(tmp_path: Path) -> None:
    workspace_id = _seed_workspace(tmp_path)
    server = _server(tmp_path)

    result = _call_tool(
        server,
        "propose_patch",
        workspace_id=workspace_id,
        patch={"schema_version": 1, "operations": []},
    )
    assert result["ok"] is False
    assert result["code"] == "patch_invalid"

    # Fail-closed: nothing was queued on disk.
    proposals_dir = tmp_path / WORKSPACE_ID / "proposals"
    assert not proposals_dir.exists() or list(proposals_dir.iterdir()) == []


def test_proposal_status_reflects_settled_outcome(tmp_path: Path) -> None:
    from knowledge_tree_infrastructure.proposals import settle_proposal
    from knowledge_tree_infrastructure.workspace import resolve_workspace

    workspace_id = _seed_workspace(tmp_path)
    server = _server(tmp_path)

    draft = _call_tool(server, "preview_draft", workspace_id=workspace_id)
    proposed = _call_tool(server, "propose_patch", workspace_id=workspace_id, patch=draft["patch"])
    proposal_id = proposed["proposal_id"]

    # The in-app human decision (mimicked by settling the store directly).
    settle_proposal(
        resolve_workspace(tmp_path / workspace_id),
        proposal_id,
        "accepted",
        change_id="00000000-0000-7000-8000-0000000000ff",
    )

    status = _call_tool(
        server, "proposal_status", workspace_id=workspace_id, proposal_id=proposal_id
    )
    assert status["ok"] is True
    assert status["status"] == "accepted"
    assert status["change_id"] == "00000000-0000-7000-8000-0000000000ff"


def test_proposal_status_unknown_id_fails_closed(tmp_path: Path) -> None:
    workspace_id = _seed_workspace(tmp_path)
    server = _server(tmp_path)

    status = _call_tool(
        server,
        "proposal_status",
        workspace_id=workspace_id,
        proposal_id="00000000-0000-7000-8000-0000000000ee",
    )
    assert status["ok"] is False
    assert status["code"] == "proposal_missing"
