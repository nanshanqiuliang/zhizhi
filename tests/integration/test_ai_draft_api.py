"""Red-light integration tests for the AI draft endpoint (WORK-2026-026 slice 3).

`create_app` does not yet accept `draft_generator` and the `POST .../ai-draft`
endpoint does not exist, so these tests are expected to fail (TypeError/404)
until implemented. A deterministic fake generator (no network) proves the
generate → preview → accept flow without a real provider.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from tests.contract.test_graph_contracts import (
    COURSE_ID,
    WORKSPACE_ID,
)

JsonObject = dict[str, Any]
ALLOWED_ORIGIN = "http://localhost:5173"

EVIDENCE = "00000000-0000-7000-9000-000000000001"
CONCEPT_A = "00000000-0000-7000-8000-000000000101"
CONCEPT_B = "00000000-0000-7000-8000-000000000102"


def _fake_generator(text: str, resource_id: str, graph: JsonObject) -> JsonObject:
    """Deterministic offline draft generator returning one AI chain draft."""
    base = int(graph["revision_no"])
    course_id = str(graph["course_id"])
    workspace_id = str(graph["workspace_id"])
    assert text and resource_id

    def concept(concept_id: str, label: str, confidence: float) -> JsonObject:
        return {
            "id": concept_id,
            "course_id": course_id,
            "label": label,
            "origin": "ai",
            "review_state": "proposed",
            "confidence": confidence,
            "evidence_ids": [EVIDENCE],
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
        "reason": "AI 草案：微积分概念链",
        "requires_confirmation": True,
        "confirmed": False,
        "operations": [
            {
                "op_id": f"00000000-0000-7000-8000-{base + 2:012d}",
                "op": "create_concept",
                "concept": concept(CONCEPT_A, "极限", 0.9),
            },
            {
                "op_id": f"00000000-0000-7000-8000-{base + 3:012d}",
                "op": "create_concept",
                "concept": concept(CONCEPT_B, "连续", 0.85),
            },
            {
                "op_id": f"00000000-0000-7000-8000-{base + 4:012d}",
                "op": "create_edge",
                "expected_source_revision_no": 0,
                "expected_target_revision_no": 0,
                "edge": {
                    "id": f"00000000-0000-7000-8000-{base + 5:012d}",
                    "course_id": course_id,
                    "source_concept_id": CONCEPT_A,
                    "target_concept_id": CONCEPT_B,
                    "edge_type": "prerequisite_of",
                    "origin": "ai",
                    "review_state": "proposed",
                    "confidence": 0.7,
                    "evidence_ids": [EVIDENCE],
                    "locked": False,
                    "revision_no": 0,
                },
            },
            {
                "op_id": f"00000000-0000-7000-8000-{base + 6:012d}",
                "op": "set_layout_item",
                "target": {"type": "concept", "id": CONCEPT_A},
                "expected_updated_revision_no": 0,
                "layout_item": {
                    "view_id": workspace_id,
                    "concept_id": CONCEPT_A,
                    "x": 0.0,
                    "y": 0.0,
                    "pinned": False,
                    "revision_no": 0,
                },
            },
            {
                "op_id": f"00000000-0000-7000-8000-{base + 7:012d}",
                "op": "set_layout_item",
                "target": {"type": "concept", "id": CONCEPT_B},
                "expected_updated_revision_no": 0,
                "layout_item": {
                    "view_id": workspace_id,
                    "concept_id": CONCEPT_B,
                    "x": 220.0,
                    "y": 0.0,
                    "pinned": False,
                    "revision_no": 0,
                },
            },
        ],
    }
    draft = {
        "concepts": [
            {"label": "极限", "aliases": [], "confidence": 0.9, "evidence_ids": [EVIDENCE]},
            {"label": "连续", "aliases": [], "confidence": 0.85, "evidence_ids": [EVIDENCE]},
        ],
        "relations": [
            {
                "source_label": "极限",
                "target_label": "连续",
                "edge_type": "prerequisite_of",
                "confidence": 0.7,
                "evidence_ids": [EVIDENCE],
            }
        ],
    }
    return {"draft": draft, "patch": patch}


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


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    app = create_app(
        data_root=tmp_path,
        allowed_origins=[ALLOWED_ORIGIN],
        draft_generator=_fake_generator,
    )
    return TestClient(app)


def _seed_md_resource(client: TestClient) -> str:
    client.put(f"/api/workspaces/{WORKSPACE_ID}/graph", json=_empty_graph())
    response = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/resources",
        files={"file": ("notes.md", b"# limit\n\ncontinuity", "text/markdown")},
    )
    assert response.status_code == 200
    return str(response.json()["id"])


def test_ai_draft_endpoint_returns_proposed_patch(client: TestClient) -> None:
    resource_id = _seed_md_resource(client)
    response = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/ai-draft", json={"resource_id": resource_id}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["draft"]["concepts"][0]["label"] == "极限"
    assert body["patch"]["requires_confirmation"] is True
    assert body["patch"]["confirmed"] is False
    assert body["patch"]["actor"] == {"type": "user", "id": "local-user"}


def test_ai_draft_accept_applies_ai_concepts_through_commit_gate(client: TestClient) -> None:
    resource_id = _seed_md_resource(client)
    draft_response = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/ai-draft", json={"resource_id": resource_id}
    ).json()
    patch = draft_response["patch"]
    patch["confirmed"] = True
    response = client.post(f"/api/workspaces/{WORKSPACE_ID}/graph/patches", json=patch)
    assert response.status_code == 200
    graph = client.get(f"/api/workspaces/{WORKSPACE_ID}/graph").json()
    concepts = {concept["label"]: concept for concept in graph["concepts"]}
    assert set(concepts) == {"极限", "连续"}
    assert concepts["极限"]["origin"] == "ai"
    assert concepts["极限"]["review_state"] == "proposed"
    assert concepts["极限"]["evidence_ids"] == [EVIDENCE]
    assert any(edge["edge_type"] == "prerequisite_of" for edge in graph["edges"])


def test_ai_draft_without_generator_returns_503(tmp_path: Path) -> None:
    app = create_app(data_root=tmp_path, allowed_origins=[ALLOWED_ORIGIN])
    with TestClient(app) as no_generator_client:
        response = no_generator_client.post(
            f"/api/workspaces/{WORKSPACE_ID}/ai-draft", json={"resource_id": "x"}
        )
        assert response.status_code == 503
        assert response.json()["code"] == "ai_not_available"


def test_ai_draft_missing_resource_id_returns_422(client: TestClient) -> None:
    _seed_md_resource(client)
    response = client.post(f"/api/workspaces/{WORKSPACE_ID}/ai-draft", json={})
    assert response.status_code == 422


def test_ai_draft_missing_resource_returns_404(client: TestClient) -> None:
    _seed_md_resource(client)
    response = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/ai-draft",
        json={"resource_id": "00000000-0000-7000-8000-000000000999"},
    )
    assert response.status_code == 404
