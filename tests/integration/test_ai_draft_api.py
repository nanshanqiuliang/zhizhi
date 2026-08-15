"""Integration tests for the AI draft endpoint (WORK-2026-026 slice 3).

A deterministic fake generator (no network) proves the generate → preview →
accept flow, the endpoint's fail-closed behavior, and the commit-gate
acceptance of a user-confirmed draft patch.
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

    def concept(concept_id: str, label: str) -> JsonObject:
        # Mirrors the production generator's acceptance re-authoring: the
        # persistent gate only accepts user-authored entities; provenance is
        # carried by evidence_ids + the draft payload (confidence shown there).
        return {
            "id": concept_id,
            "course_id": course_id,
            "label": label,
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
                "concept": concept(CONCEPT_A, "极限"),
            },
            {
                "op_id": f"00000000-0000-7000-8000-{base + 3:012d}",
                "op": "create_concept",
                "concept": concept(CONCEPT_B, "连续"),
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
                    "origin": "user",
                    "review_state": "accepted",
                    "confidence": None,
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
    assert concepts["极限"]["origin"] == "user"
    assert concepts["极限"]["review_state"] == "accepted"
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


def test_ai_draft_workspace_mode_without_generator_returns_503(client: TestClient) -> None:
    # `{}` now means "whole-workspace mode"; the fixture has no workspace generator.
    _seed_md_resource(client)
    response = client.post(f"/api/workspaces/{WORKSPACE_ID}/ai-draft", json={})
    assert response.status_code == 503
    assert response.json()["code"] == "ai_not_available"


def test_ai_draft_workspace_mode_returns_draft(tmp_path: Path) -> None:
    def fake_workspace(texts: list[tuple[str, str]], graph: JsonObject) -> JsonObject:
        assert texts
        return _fake_generator("\n\n".join(text for _rid, text in texts), texts[0][0], graph)

    app = create_app(
        data_root=tmp_path,
        allowed_origins=[ALLOWED_ORIGIN],
        workspace_draft_generator=fake_workspace,
    )
    with TestClient(app) as ws_client:
        ws_client.put(f"/api/workspaces/{WORKSPACE_ID}/graph", json=_empty_graph())
        ws_client.post(
            f"/api/workspaces/{WORKSPACE_ID}/resources",
            files={"file": ("notes.md", b"# limit\n\ncontinuity", "text/markdown")},
        )
        response = ws_client.post(f"/api/workspaces/{WORKSPACE_ID}/ai-draft", json={})
        assert response.status_code == 200
        body = response.json()
        assert body["draft"]["concepts"]
        assert body["patch"]["operations"]


def test_ai_draft_workspace_mode_no_resources_returns_422(tmp_path: Path) -> None:
    app = create_app(
        data_root=tmp_path,
        allowed_origins=[ALLOWED_ORIGIN],
        workspace_draft_generator=lambda texts, graph: {"draft": {}, "patch": {}},
    )
    with TestClient(app) as ws_client:
        ws_client.put(f"/api/workspaces/{WORKSPACE_ID}/graph", json=_empty_graph())
        response = ws_client.post(f"/api/workspaces/{WORKSPACE_ID}/ai-draft", json={})
        assert response.status_code == 422
        assert response.json()["code"] == "draft_invalid"


def test_ai_draft_invalid_resource_id_type_422(client: TestClient) -> None:
    _seed_md_resource(client)
    response = client.post(f"/api/workspaces/{WORKSPACE_ID}/ai-draft", json={"resource_id": 123})
    assert response.status_code == 422
    assert response.json()["code"] == "draft_invalid"


def test_ai_draft_no_new_concepts_returns_422(tmp_path: Path) -> None:
    def empty_generator(texts: list[tuple[str, str]], graph: JsonObject) -> JsonObject:
        return {
            "draft": {"concepts": [], "relations": []},
            "patch": {"operations": []},
            "evidence": [],
        }

    app = create_app(
        data_root=tmp_path,
        allowed_origins=[ALLOWED_ORIGIN],
        workspace_draft_generator=empty_generator,
    )
    with TestClient(app) as ws_client:
        ws_client.put(f"/api/workspaces/{WORKSPACE_ID}/graph", json=_empty_graph())
        ws_client.post(
            f"/api/workspaces/{WORKSPACE_ID}/resources",
            files={"file": ("notes.md", b"# limit\n", "text/markdown")},
        )
        response = ws_client.post(f"/api/workspaces/{WORKSPACE_ID}/ai-draft", json={})
        assert response.status_code == 422
        assert response.json()["code"] == "draft_invalid"
        assert response.json()["rule"] == "no_new_concepts"


def test_ai_draft_missing_resource_returns_404(client: TestClient) -> None:
    _seed_md_resource(client)
    response = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/ai-draft",
        json={"resource_id": "00000000-0000-7000-8000-000000000999"},
    )
    assert response.status_code == 404


def test_ai_draft_large_workspace_patch_exceeds_old_cap(tmp_path: Path) -> None:
    """WORK-2026-046: a whole-corpus mind map exceeds the old 100-op cap.

    Regression for the user's `maxitems` failure on paper.pdf: 120 concepts
    produce 240 operations (create_concept + set_layout_item each), which the
    GraphPatch v1 contract rejected before the cap was raised to 5000.
    """

    def large_workspace(texts: list[tuple[str, str]], graph: JsonObject) -> JsonObject:
        assert texts
        course_id = str(graph["course_id"])
        workspace_id = str(graph["workspace_id"])
        concepts: list[JsonObject] = []
        operations: list[JsonObject] = []
        for index in range(120):
            concept_id = f"00000000-0000-7000-8000-{5000 + index:012d}"
            concepts.append(
                {
                    "label": f"概念{index:03d}",
                    "aliases": [],
                    "confidence": None,
                    "evidence_ids": [EVIDENCE],
                }
            )
            operations.append(
                {
                    "op_id": f"00000000-0000-7000-8000-{6000 + index * 2:012d}",
                    "op": "create_concept",
                    "concept": {
                        "id": concept_id,
                        "course_id": course_id,
                        "label": f"概念{index:03d}",
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
            )
            operations.append(
                {
                    "op_id": f"00000000-0000-7000-8000-{6001 + index * 2:012d}",
                    "op": "set_layout_item",
                    "target": {"type": "concept", "id": concept_id},
                    "expected_updated_revision_no": 0,
                    "layout_item": {
                        "view_id": workspace_id,
                        "concept_id": concept_id,
                        "x": float(index % 20) * 120.0,
                        "y": float(index // 20) * 120.0,
                        "pinned": False,
                        "revision_no": 0,
                    },
                }
            )
        patch = {
            "schema_version": 1,
            "patch_id": "00000000-0000-7000-8000-000000004000",
            "workspace_id": workspace_id,
            "course_id": course_id,
            "base_revision_no": int(graph["revision_no"]),
            "actor": {"type": "user", "id": "local-user"},
            "reason": "AI 草案：全库思维导图（120 概念，240 操作）",
            "requires_confirmation": True,
            "confirmed": False,
            "operations": operations,
        }
        return {"draft": {"concepts": concepts, "relations": []}, "patch": patch}

    app = create_app(
        data_root=tmp_path,
        allowed_origins=[ALLOWED_ORIGIN],
        workspace_draft_generator=large_workspace,
    )
    with TestClient(app) as ws_client:
        ws_client.put(f"/api/workspaces/{WORKSPACE_ID}/graph", json=_empty_graph())
        ws_client.post(
            f"/api/workspaces/{WORKSPACE_ID}/resources",
            files={"file": ("notes.md", b"# limit\n\ncontinuity", "text/markdown")},
        )
        response = ws_client.post(f"/api/workspaces/{WORKSPACE_ID}/ai-draft", json={})
        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body["patch"]["operations"]) == 240
        assert body["patch"]["requires_confirmation"] is True
        assert body["patch"]["confirmed"] is False
