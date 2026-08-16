"""Red-light integration tests for the external proposal store (WORK-2026-050).

Targets `knowledge_tree_infrastructure.proposals` which does not exist yet, so
collection is expected to fail with ImportError until the store is implemented.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from knowledge_tree_infrastructure.proposals import (
    list_proposals,
    read_proposal,
    save_proposal,
    settle_proposal,
)
from knowledge_tree_infrastructure.workspace import (
    WorkspaceError,
    create_workspace,
    migrate,
    save_course_graph,
)

WORKSPACE_ID = "00000000-0000-7000-8000-000000000001"
COURSE_ID = "00000000-0000-7000-8000-000000000002"
CHANGE_ID = "00000000-0000-7000-8000-0000000000ff"


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


@pytest.fixture()
def layout(tmp_path: Path) -> Any:
    workspace = create_workspace(tmp_path / WORKSPACE_ID)
    migrate(workspace.db_path)
    save_course_graph(workspace, _empty_graph())
    return workspace


def _patch(patch_no: int) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "patch_id": f"00000000-0000-7000-8000-{patch_no:012d}",
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "base_revision_no": 0,
        "actor": {"type": "user", "id": "local-user"},
        "reason": "外部提议",
        "requires_confirmation": True,
        "confirmed": False,
        "operations": [],
    }


def test_save_then_list_and_read_round_trip(layout: Any) -> None:
    record = save_proposal(layout, _patch(1), origin="mcp", note="from cursor")

    assert record["status"] == "pending"
    assert record["origin"] == "mcp"
    assert record["note"] == "from cursor"
    assert record["schema_version"] == 1
    assert record["created_at"]

    listed = list_proposals(layout)
    assert [item["proposal_id"] for item in listed] == [record["proposal_id"]]

    loaded = read_proposal(layout, record["proposal_id"])
    assert loaded["patch"] == _patch(1)


def test_saved_file_lives_in_proposals_dir_with_atomic_payload(layout: Any, tmp_path: Path) -> None:
    record = save_proposal(layout, _patch(2))

    proposal_file = tmp_path / WORKSPACE_ID / "proposals" / f"{record['proposal_id']}.json"
    assert proposal_file.is_file()
    payload = json.loads(proposal_file.read_text(encoding="utf-8"))
    assert payload["proposal_id"] == record["proposal_id"]
    assert payload["status"] == "pending"


def test_read_proposal_rejects_non_uuid_ids(layout: Any) -> None:
    with pytest.raises(WorkspaceError) as exc_info:
        read_proposal(layout, "../../escape")
    assert exc_info.value.code == "proposal_invalid"


def test_read_proposal_missing_fails_closed(layout: Any) -> None:
    with pytest.raises(WorkspaceError) as exc_info:
        read_proposal(layout, "00000000-0000-7000-8000-0000000000ee")
    assert exc_info.value.code == "proposal_missing"


def test_settle_moves_pending_to_accepted_once(layout: Any) -> None:
    record = save_proposal(layout, _patch(3))

    settled = settle_proposal(layout, record["proposal_id"], "accepted", change_id=CHANGE_ID)
    assert settled["status"] == "accepted"
    assert settled["change_id"] == CHANGE_ID
    assert settled["status_at"]

    # Pending-only listing no longer shows it; the accepted filter does.
    assert list_proposals(layout) == []
    assert [item["proposal_id"] for item in list_proposals(layout, status="accepted")] == [
        record["proposal_id"]
    ]

    with pytest.raises(WorkspaceError) as exc_info:
        settle_proposal(layout, record["proposal_id"], "accepted", change_id=CHANGE_ID)
    assert exc_info.value.code == "proposal_state_conflict"


def test_settle_reject_keeps_graph_untouched(layout: Any) -> None:
    record = save_proposal(layout, _patch(4))

    settled = settle_proposal(layout, record["proposal_id"], "rejected")
    assert settled["status"] == "rejected"
    assert list_proposals(layout) == []
    assert [item["proposal_id"] for item in list_proposals(layout, status="rejected")] == [
        record["proposal_id"]
    ]


def test_list_orders_by_creation(layout: Any) -> None:
    first = save_proposal(layout, _patch(5), note="first")
    second = save_proposal(layout, _patch(6), note="second")

    listed = list_proposals(layout)
    assert [item["proposal_id"] for item in listed] == [first["proposal_id"], second["proposal_id"]]
