"""Red-light integration tests for per-concept source anchors (WORK-2026-055).

`GET /api/workspaces/{id}/concepts/{concept_id}/anchors` joins a concept's
`evidence_ids` with the anchor table plus resource display names, so the web
detail panel can offer one-click jump-to-source for AI-drafted concepts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from knowledge_tree_infrastructure.workspace import (
    create_workspace,
    import_resource,
    migrate,
    register_anchor,
    save_course_graph,
)

from apps.api.main import create_app

WORKSPACE_ID = "00000000-0000-7000-8000-000000000001"
COURSE_ID = "00000000-0000-7000-8000-000000000002"
ALLOWED_ORIGIN = "http://localhost:5173"

DANGLING = "00000000-0000-7000-9000-0000000000de"
CONCEPT_WITH_EVIDENCE = "00000000-0000-7000-a000-0000000000b1"
CONCEPT_PLAIN = "00000000-0000-7000-a000-0000000000b2"

JsonObject = dict[str, Any]


def _concept(concept_id: str, evidence: list[str]) -> JsonObject:
    return {
        "id": concept_id,
        "course_id": COURSE_ID,
        "label": "来源概念" if evidence else "普通概念",
        "origin": "user",
        "review_state": "accepted",
        "confidence": None,
        "evidence_ids": evidence,
        "locks": {"content": False, "relations": False, "position": False, "annotations": False},
        "annotations": [],
        "revision_no": 0,
    }


@pytest.fixture()
def client(tmp_path: Path) -> tuple[TestClient, list[str]]:
    layout = create_workspace(tmp_path / WORKSPACE_ID)
    migrate(layout.db_path)
    resource = import_resource(layout, display_name="微积分讲义.pdf", content=b"%PDF-1.4 fake")
    anchor_page2 = register_anchor(
        layout,
        resource_id=str(resource.id),
        page=2,
        payload={"label": "第二章 极限"},
    )
    anchor_page5 = register_anchor(
        layout,
        resource_id=str(resource.id),
        page=5,
        payload={"label": "第五章 连续"},
    )
    graph = {
        "schema_version": 1,
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "revision_no": 0,
        "concepts": [
            _concept(CONCEPT_WITH_EVIDENCE, [anchor_page2.id, DANGLING, anchor_page5.id]),
            _concept(CONCEPT_PLAIN, []),
        ],
        "edges": [],
        "layout_items": [],
    }
    save_course_graph(layout, graph)
    client = TestClient(create_app(data_root=tmp_path, allowed_origins=[ALLOWED_ORIGIN]))
    return client, [anchor_page2.id, anchor_page5.id]


def test_lists_concept_anchors_with_resource_names(
    client: tuple[TestClient, list[str]],
) -> None:
    test_client, anchor_ids = client
    response = test_client.get(
        f"/api/workspaces/{WORKSPACE_ID}/concepts/{CONCEPT_WITH_EVIDENCE}/anchors"
    )
    assert response.status_code == 200
    anchors = response.json()["anchors"]
    # The dangling evidence id is skipped; real anchors come back page-ordered.
    assert [item["anchor_id"] for item in anchors] == anchor_ids
    assert all(item["resource_name"] == "微积分讲义.pdf" for item in anchors)
    assert anchors[0]["page"] == 2
    assert anchors[0]["label"] == "第二章 极限"
    assert anchors[0]["mime"] == "application/pdf"
    assert anchors[0]["resource_id"]


def test_concept_without_evidence_returns_empty_list(
    client: tuple[TestClient, list[str]],
) -> None:
    test_client, _ = client
    response = test_client.get(f"/api/workspaces/{WORKSPACE_ID}/concepts/{CONCEPT_PLAIN}/anchors")
    assert response.status_code == 200
    assert response.json() == {"anchors": []}


def test_unknown_concept_returns_404(client: tuple[TestClient, list[str]]) -> None:
    test_client, _ = client
    response = test_client.get(
        f"/api/workspaces/{WORKSPACE_ID}/concepts/00000000-0000-7000-a000-0000000000ff/anchors"
    )
    assert response.status_code == 404
