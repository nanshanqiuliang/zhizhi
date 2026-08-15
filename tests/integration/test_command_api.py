"""Red-light tests for natural-language -> GraphPatch (WORK-2026-029, Step 9 slice 2).

`build_command_patch` / `CommandError` do not exist and `POST .../interpret` is
absent, so these tests are expected to fail (ImportError/404) until implemented.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from knowledge_tree_infrastructure.command import CommandError, build_command_patch

from apps.api.main import create_app
from tests.contract.test_graph_contracts import COURSE_ID, WORKSPACE_ID

JsonObject = dict[str, Any]
ALLOWED_ORIGIN = "http://localhost:5173"

CONCEPT_A = "00000000-0000-7000-8000-000000000101"
CONCEPT_B = "00000000-0000-7000-8000-000000000102"


def _graph() -> JsonObject:
    def concept(concept_id: str, label: str) -> JsonObject:
        return {
            "id": concept_id,
            "course_id": COURSE_ID,
            "label": label,
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
        }

    return {
        "schema_version": 1,
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "revision_no": 0,
        "concepts": [concept(CONCEPT_A, "极限"), concept(CONCEPT_B, "连续")],
        "edges": [],
        "layout_items": [],
    }


def _ops() -> list[JsonObject]:
    return [
        {"op": "set_lock", "target": "极限", "dimension": "content", "value": True},
        {"op": "create_edge", "source": "极限", "target": "连续", "edge_type": "prerequisite_of"},
    ]


def _counter() -> Any:
    state = {"n": 0}

    def factory() -> str:
        state["n"] += 1
        return f"00000000-0000-7000-9100-{state['n']:012d}"

    return factory


def test_build_command_patch_maps_labels_to_ids() -> None:
    patch = build_command_patch(_graph(), _ops(), id_factory=_counter(), reason="测试命令")
    assert patch["requires_confirmation"] is True
    assert patch["confirmed"] is False
    assert patch["actor"] == {"type": "user", "id": "local-user"}
    operations = patch["operations"]
    set_lock = next(op for op in operations if op["op"] == "set_lock")
    assert set_lock["target"]["id"] == CONCEPT_A
    create_edge = next(op for op in operations if op["op"] == "create_edge")
    assert create_edge["edge"]["source_concept_id"] == CONCEPT_A
    assert create_edge["edge"]["target_concept_id"] == CONCEPT_B


def test_build_command_patch_rejects_unknown_label() -> None:
    ops = [{"op": "set_lock", "target": "不存在的概念", "dimension": "content", "value": True}]
    with pytest.raises(CommandError):
        build_command_patch(_graph(), ops, id_factory=_counter(), reason="x")


def _fake_generator(command: str, concepts: list[JsonObject]) -> JsonObject:
    return {"summary": f"命令：{command}", "operations": _ops()}


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    app = create_app(
        data_root=tmp_path,
        allowed_origins=[ALLOWED_ORIGIN],
        command_generator=_fake_generator,
    )
    with TestClient(app) as test_client:
        test_client.put(f"/api/workspaces/{WORKSPACE_ID}/graph", json=_graph())
        yield test_client


def test_interpret_endpoint_returns_proposed_patch(client: TestClient) -> None:
    response = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/interpret",
        json={"command": "锁定极限并注明连续以极限为前提"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["patch"]["requires_confirmation"] is True
    assert body["patch"]["confirmed"] is False


def test_interpret_accept_applies_through_commit_gate(client: TestClient) -> None:
    draft = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/interpret", json={"command": "锁定极限"}
    ).json()
    patch = draft["patch"]
    patch["confirmed"] = True
    response = client.post(f"/api/workspaces/{WORKSPACE_ID}/graph/patches", json=patch)
    assert response.status_code == 200
    graph = client.get(f"/api/workspaces/{WORKSPACE_ID}/graph").json()
    assert any(edge["edge_type"] == "prerequisite_of" for edge in graph["edges"])


def test_interpret_endpoint_requires_generator(tmp_path: Path) -> None:
    app = create_app(data_root=tmp_path, allowed_origins=[ALLOWED_ORIGIN])
    with TestClient(app) as no_generator_client:
        response = no_generator_client.post(
            f"/api/workspaces/{WORKSPACE_ID}/interpret", json={"command": "锁定极限"}
        )
        assert response.status_code == 503
        assert response.json()["code"] == "ai_not_available"


def test_interpret_endpoint_invalid_command(client: TestClient) -> None:
    response = client.post(f"/api/workspaces/{WORKSPACE_ID}/interpret", json={"command": ""})
    assert response.status_code == 422
