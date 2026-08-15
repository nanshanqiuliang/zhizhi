"""Red-light tests for AI draft source-anchor persistence (WORK-2026-027 slice 4).

`accept_ai_draft` does not exist and the `POST .../ai-draft/accept` endpoint is
absent, so these tests are expected to fail (ImportError/404) until implemented.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from knowledge_tree_domain.ai_draft import deterministic_uuidv7
from knowledge_tree_infrastructure.workspace import (
    WorkspaceError,
    accept_ai_draft,
    create_workspace,
    import_resource,
    list_anchors,
    load_course_graph,
    migrate,
    save_course_graph,
)
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


def _confirmed_patch(resource_id: str) -> JsonObject:
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


def _md_workspace(tmp_path: Path) -> tuple[Any, str]:
    layout = create_workspace(tmp_path / WORKSPACE_ID)
    migrate(layout.db_path)
    info = import_resource(layout, display_name="notes.md", content=b"# limit\n\nlim")
    save_course_graph(layout, _empty_graph())
    return layout, info.id


def test_deterministic_uuidv7_is_stable_and_valid() -> None:
    first = deterministic_uuidv7("00000000-0000-7000-8000-000000000003")
    second = deterministic_uuidv7("00000000-0000-7000-8000-000000000003")
    assert first == second
    assert UUID(first).version == 7


def test_accept_ai_draft_persists_anchors_and_graph(tmp_path: Path) -> None:
    layout, resource_id = _md_workspace(tmp_path)
    anchors = [
        {"id": EVIDENCE, "resource_id": resource_id, "page": 0, "label": "AI 草案来源"}
    ]
    accept_ai_draft(
        layout,
        _confirmed_patch(resource_id),
        trusted_actor={"type": "user", "id": "local-user"},
        anchors=anchors,
    )
    graph = load_course_graph(layout)
    assert graph["concepts"][0]["evidence_ids"] == [EVIDENCE]
    stored = list_anchors(layout, resource_id)
    assert [anchor.id for anchor in stored] == [EVIDENCE]
    assert stored[0].payload["source"] == "ai_draft"


def test_accept_ai_draft_anchor_failure_rolls_back_graph(tmp_path: Path) -> None:
    layout, resource_id = _md_workspace(tmp_path)
    anchors = [
        {"id": EVIDENCE, "resource_id": resource_id, "page": 0, "label": "a"},
        {"id": "00000000-0000-7000-9000-000000000002", "resource_id": resource_id, "page": 0, "label": "b"},
    ]
    with pytest.raises(WorkspaceError):
        accept_ai_draft(
            layout,
            _confirmed_patch(resource_id),
            trusted_actor={"type": "user", "id": "local-user"},
            anchors=anchors,
        )
    # The graph must be unchanged because the whole transaction rolled back.
    assert load_course_graph(layout)["concepts"] == []


def test_ai_draft_accept_endpoint(tmp_path: Path) -> None:
    resource_id = _md_workspace(tmp_path)[1]
    app = create_app(data_root=tmp_path, allowed_origins=[ALLOWED_ORIGIN])
    with TestClient(app) as client:
        response = client.post(
            f"/api/workspaces/{WORKSPACE_ID}/ai-draft/accept",
            json={
                "patch": _confirmed_patch(resource_id),
                "evidence": [
                    {"anchor_id": EVIDENCE, "resource_id": resource_id, "label": "AI 草案来源"}
                ],
            },
        )
        assert response.status_code == 200


def test_ai_draft_accept_endpoint_rejects_unconfirmed_patch(tmp_path: Path) -> None:
    resource_id = _md_workspace(tmp_path)[1]
    app = create_app(data_root=tmp_path, allowed_origins=[ALLOWED_ORIGIN])
    with TestClient(app) as client:
        patch = _confirmed_patch(resource_id)
        patch["confirmed"] = False
        response = client.post(
            f"/api/workspaces/{WORKSPACE_ID}/ai-draft/accept",
            json={"patch": patch, "evidence": []},
        )
        assert response.status_code in (409, 422, 500)
