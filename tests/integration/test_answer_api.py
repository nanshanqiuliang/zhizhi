"""Integration tests for sourced Q&A (WORK-2026-028, Step 9 slice 1).

Covers `build_answer_context` (FTS5 forward match + reverse substring fallback)
and the `POST /answer` endpoint's fail-closed behavior with a deterministic fake
generator (no network).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from knowledge_tree_infrastructure.workspace import (
    build_answer_context,
    create_workspace,
    migrate,
    save_course_graph,
)

from apps.api.main import create_app
from tests.contract.test_graph_contracts import COURSE_ID, WORKSPACE_ID

JsonObject = dict[str, Any]
ALLOWED_ORIGIN = "http://localhost:5173"


def _graph() -> JsonObject:
    def concept(concept_id: str, label: str, note: str) -> JsonObject:
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
            "annotations": [{"kind": "note", "value": note}],
            "revision_no": 0,
        }

    return {
        "schema_version": 1,
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "revision_no": 0,
        "concepts": [
            concept("00000000-0000-7000-8000-000000000101", "极限", "自变量趋近某点时函数值的趋势"),
            concept("00000000-0000-7000-8000-000000000102", "连续", "极限等于函数值"),
        ],
        "edges": [],
        "layout_items": [],
    }


def _seed(layout: Any) -> None:
    save_course_graph(layout, _graph())


def test_build_answer_context_cites_matches(tmp_path: Path) -> None:
    layout = create_workspace(tmp_path / "ws")
    migrate(layout.db_path)
    _seed(layout)
    context = build_answer_context(layout, "极限")
    assert context.sources
    assert context.sources[0].label == "极限"
    assert "[1]" in context.context


def test_build_answer_context_no_matches(tmp_path: Path) -> None:
    layout = create_workspace(tmp_path / "ws")
    migrate(layout.db_path)
    _seed(layout)
    context = build_answer_context(layout, "不存在的话题zzz")
    assert context.context == ""
    assert context.sources == ()


def _fake_generator(question: str, context: str, sources: list[JsonObject]) -> JsonObject:
    return {"answer": f"回答：{question}", "sources": sources}


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    app = create_app(
        data_root=tmp_path,
        allowed_origins=[ALLOWED_ORIGIN],
        answer_generator=_fake_generator,
    )
    with TestClient(app) as test_client:
        test_client.put(f"/api/workspaces/{WORKSPACE_ID}/graph", json=_graph())
        yield test_client


def test_answer_endpoint_returns_answer_and_sources(client: TestClient) -> None:
    response = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/answer", json={"question": "什么是极限"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer"].startswith("回答：")
    assert body["sources"][0]["label"] == "极限"


def test_answer_endpoint_no_matches(client: TestClient) -> None:
    response = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/answer", json={"question": "不存在的话题zzz"}
    )
    assert response.status_code == 200
    assert response.json()["answer"] == ""
    assert response.json()["sources"] == []


def test_answer_endpoint_requires_generator(tmp_path: Path) -> None:
    app = create_app(data_root=tmp_path, allowed_origins=[ALLOWED_ORIGIN])
    with TestClient(app) as no_generator_client:
        response = no_generator_client.post(
            f"/api/workspaces/{WORKSPACE_ID}/answer", json={"question": "什么是极限"}
        )
        assert response.status_code == 503
        assert response.json()["code"] == "ai_not_available"


def test_answer_endpoint_invalid_question(client: TestClient) -> None:
    response = client.post(f"/api/workspaces/{WORKSPACE_ID}/answer", json={"question": ""})
    assert response.status_code == 422


def test_answer_endpoint_question_too_long(client: TestClient) -> None:
    response = client.post(f"/api/workspaces/{WORKSPACE_ID}/answer", json={"question": "极" * 150})
    assert response.status_code == 422
    assert response.json()["rule"] == "question_too_long"
