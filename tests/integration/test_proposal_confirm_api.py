"""Red-light integration tests for in-app confirmation of external proposals (WORK-2026-050).

The API exposes list/accept/reject over pending proposals queued by the MCP
`propose_patch` tool. Acceptance is the ONLY write path for external proposals
and it goes through the existing commit gate (locks / revision / history).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from knowledge_tree_infrastructure.proposals import (
    read_proposal,
    save_proposal,
)
from knowledge_tree_infrastructure.workspace import (
    create_workspace,
    migrate,
    save_course_graph,
)

from apps.api.main import create_app

WORKSPACE_ID = "00000000-0000-7000-8000-000000000001"
COURSE_ID = "00000000-0000-7000-8000-000000000002"
ALLOWED_ORIGIN = "http://localhost:5173"

_counter = 0


def _next_uuid_tail() -> int:
    global _counter
    _counter += 1
    return _counter


def _empty_graph() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "revision_no": 0,
        "concepts": [],
        "edges": [],
        "layout_items": [],
    }


def _seeded_client(tmp_path: Path) -> TestClient:
    workspace = create_workspace(tmp_path / WORKSPACE_ID)
    migrate(workspace.db_path)
    save_course_graph(workspace, _empty_graph())
    return TestClient(create_app(data_root=tmp_path, allowed_origins=[ALLOWED_ORIGIN]))


def _patch(patch_no: int, concept_no: int) -> dict[str, Any]:
    tail = _next_uuid_tail()
    concept_id = f"00000000-0000-7000-a000-{concept_no:012d}"
    return {
        "schema_version": 1,
        "patch_id": f"00000000-0000-7000-8000-{patch_no:012d}",
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "base_revision_no": 0,
        "actor": {"type": "user", "id": "local-user"},
        "reason": "外部 AI 提议",
        "requires_confirmation": True,
        "confirmed": False,
        "operations": [
            {
                "op_id": f"00000000-0000-7000-9000-{tail:012d}",
                "op": "create_concept",
                "concept": {
                    "id": concept_id,
                    "course_id": COURSE_ID,
                    "label": f"外部概念 {concept_no}",
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


def _queue_proposal(tmp_path: Path, patch_no: int, concept_no: int) -> str:
    """Mimic the MCP side: queue a pending proposal for the seeded workspace."""

    from knowledge_tree_infrastructure.workspace import resolve_workspace

    layout = resolve_workspace(tmp_path / WORKSPACE_ID)
    record = save_proposal(layout, _patch(patch_no, concept_no), origin="mcp", note="e2e")
    return str(record["proposal_id"])


def test_list_proposals_shows_pending_summary(tmp_path: Path) -> None:
    client = _seeded_client(tmp_path)
    _queue_proposal(tmp_path, 1, 1)

    response = client.get(f"/api/workspaces/{WORKSPACE_ID}/proposals")
    assert response.status_code == 200
    proposals = response.json()["proposals"]
    assert len(proposals) == 1
    assert proposals[0]["origin"] == "mcp"
    assert proposals[0]["note"] == "e2e"
    assert proposals[0]["status"] == "pending"
    assert proposals[0]["operations_count"] == 1
    # The listing must stay lean: no full patch payload.
    assert "patch" not in proposals[0]


def test_accept_applies_through_commit_gate_and_marks_accepted(tmp_path: Path) -> None:
    client = _seeded_client(tmp_path)
    proposal_id = _queue_proposal(tmp_path, 2, 2)

    response = client.post(f"/api/workspaces/{WORKSPACE_ID}/proposals/{proposal_id}/accept")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "applied"
    assert body["change_id"]
    assert body["revision_no"] == 1

    # The graph gained the externally proposed concept...
    graph = client.get(f"/api/workspaces/{WORKSPACE_ID}/graph").json()
    assert graph["revision_no"] == 1
    assert [concept["label"] for concept in graph["concepts"]] == ["外部概念 2"]

    # ...with an auditable history source.
    history = client.get(f"/api/workspaces/{WORKSPACE_ID}/history").json()["records"]
    assert history[-1]["source"] == "mcp_proposal"

    # Pending queue drained; the stored record carries the change id.
    assert client.get(f"/api/workspaces/{WORKSPACE_ID}/proposals").json()["proposals"] == []
    from knowledge_tree_infrastructure.workspace import resolve_workspace

    settled = read_proposal(resolve_workspace(tmp_path / WORKSPACE_ID), proposal_id)
    assert settled["status"] == "accepted"
    assert settled["change_id"] == body["change_id"]


def test_accept_twice_returns_state_conflict(tmp_path: Path) -> None:
    client = _seeded_client(tmp_path)
    proposal_id = _queue_proposal(tmp_path, 3, 3)

    first = client.post(f"/api/workspaces/{WORKSPACE_ID}/proposals/{proposal_id}/accept")
    assert first.status_code == 200
    second = client.post(f"/api/workspaces/{WORKSPACE_ID}/proposals/{proposal_id}/accept")
    assert second.status_code == 409
    assert second.json()["code"] == "proposal_state_conflict"


def test_reject_keeps_graph_untouched(tmp_path: Path) -> None:
    client = _seeded_client(tmp_path)
    proposal_id = _queue_proposal(tmp_path, 4, 4)

    response = client.post(f"/api/workspaces/{WORKSPACE_ID}/proposals/{proposal_id}/reject")
    assert response.status_code == 200
    assert response.json() == {"status": "rejected", "proposal_id": proposal_id}

    graph = client.get(f"/api/workspaces/{WORKSPACE_ID}/graph").json()
    assert graph["revision_no"] == 0
    assert graph["concepts"] == []
    assert client.get(f"/api/workspaces/{WORKSPACE_ID}/proposals").json()["proposals"] == []


def test_accept_stale_revision_fails_closed_and_keeps_pending(tmp_path: Path) -> None:
    client = _seeded_client(tmp_path)
    stale_id = _queue_proposal(tmp_path, 5, 5)
    fresh_id = _queue_proposal(tmp_path, 6, 6)

    # Apply one proposal so the graph moves to revision 1...
    accepted = client.post(f"/api/workspaces/{WORKSPACE_ID}/proposals/{fresh_id}/accept")
    assert accepted.status_code == 200

    # ...then the other (base_revision_no=0) must be rejected by the commit gate.
    response = client.post(f"/api/workspaces/{WORKSPACE_ID}/proposals/{stale_id}/accept")
    assert response.status_code == 409
    assert response.json()["code"] == "patch_revision_conflict"

    # Fail-closed: the stale proposal stays pending for the user to reject.
    pending = client.get(f"/api/workspaces/{WORKSPACE_ID}/proposals").json()["proposals"]
    assert [item["proposal_id"] for item in pending] == [stale_id]


def test_accept_missing_proposal_returns_404(tmp_path: Path) -> None:
    client = _seeded_client(tmp_path)
    unknown = "00000000-0000-7000-8000-0000000000ee"

    response = client.post(f"/api/workspaces/{WORKSPACE_ID}/proposals/{unknown}/accept")
    assert response.status_code == 404
    assert response.json()["code"] == "proposal_missing"
