"""Red-light tests for AI edit history (WORK-2026-032, Step 9 final).

`GraphChangeRecord.source`, `apply_graph_patch(source=...)`, `/history` source
and `POST /interpret/accept` do not exist yet, so these tests are expected to
fail (AttributeError/TypeError/404) until implemented.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from knowledge_tree_infrastructure.workspace import (
    accept_ai_draft,
    apply_graph_patch,
    create_workspace,
    import_resource,
    migrate,
    record_from_json,
    record_to_json,
    save_course_graph,
)

from apps.api.main import create_app
from tests.contract.test_graph_contracts import COURSE_ID, WORKSPACE_ID

JsonObject = dict[str, Any]
ALLOWED_ORIGIN = "http://localhost:5173"
EVIDENCE = "00000000-0000-7000-9000-000000000001"
CONCEPT_A = "00000000-0000-7000-8000-000000000101"


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


def _confirmed_patch() -> JsonObject:
    return {
        "schema_version": 1,
        "patch_id": "00000000-0000-7000-8000-000000000201",
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "base_revision_no": 0,
        "actor": {"type": "user", "id": "local-user"},
        "reason": "AI 草案",
        "requires_confirmation": True,
        "confirmed": True,
        "operations": [
            {
                "op_id": "00000000-0000-7000-8000-000000000202",
                "op": "create_concept",
                "concept": {
                    "id": CONCEPT_A,
                    "course_id": COURSE_ID,
                    "label": "极限",
                    "origin": "user",
                    "review_state": "accepted",
                    "confidence": None,
                    "evidence_ids": [EVIDENCE],
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


def _seed(layout: Any) -> None:
    save_course_graph(layout, _empty_graph())


def test_apply_graph_patch_marks_source_and_round_trips(tmp_path: Path) -> None:
    layout = create_workspace(tmp_path / "ws")
    migrate(layout.db_path)
    _seed(layout)
    record = apply_graph_patch(
        layout,
        _confirmed_patch(),
        trusted_actor={"type": "user", "id": "local-user"},
        source="ai_draft",
    )
    assert record.source == "ai_draft"
    parsed = record_from_json(record_to_json(record))
    assert parsed.source == "ai_draft"


def test_accept_ai_draft_marks_ai_draft(tmp_path: Path) -> None:
    layout = create_workspace(tmp_path / "ws")
    migrate(layout.db_path)
    _seed(layout)
    info = import_resource(layout, display_name="notes.md", content=b"# limit")
    record = accept_ai_draft(
        layout,
        _confirmed_patch(),
        trusted_actor={"type": "user", "id": "local-user"},
        anchors=[{"id": EVIDENCE, "resource_id": info.id, "page": 0, "label": "AI 草案来源"}],
    )
    assert record.source == "ai_draft"


def test_history_endpoint_returns_source(tmp_path: Path) -> None:
    app = create_app(data_root=tmp_path, allowed_origins=[ALLOWED_ORIGIN])
    with TestClient(app) as client:
        client.put(f"/api/workspaces/{WORKSPACE_ID}/graph", json=_empty_graph())
        patch = _confirmed_patch()
        client.post(f"/api/workspaces/{WORKSPACE_ID}/graph/patches", json=patch)
        response = client.get(f"/api/workspaces/{WORKSPACE_ID}/history")
        assert response.status_code == 200
        assert response.json()["records"][0]["source"] == "manual"


def test_interpret_accept_marks_ai_command(tmp_path: Path) -> None:
    app = create_app(data_root=tmp_path, allowed_origins=[ALLOWED_ORIGIN])
    with TestClient(app) as client:
        client.put(f"/api/workspaces/{WORKSPACE_ID}/graph", json=_empty_graph())
        response = client.post(
            f"/api/workspaces/{WORKSPACE_ID}/interpret/accept",
            json={"patch": _confirmed_patch()},
        )
        assert response.status_code == 200
        history = client.get(f"/api/workspaces/{WORKSPACE_ID}/history").json()
        assert history["records"][0]["source"] == "ai_command"
