"""Red-light integration tests for FTS5 search (WORK-2026-015).

Targets `knowledge_tree_infrastructure.workspace` search helpers and the
`apps.api` search endpoint, which do not exist yet, so collection is expected
to fail with ImportError.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from knowledge_tree_infrastructure.workspace import (
    SearchResult,
    create_workspace,
    migrate,
    save_course_graph,
    search_course_graph,
)

from apps.api.main import create_app
from tests.contract.test_graph_contracts import WORKSPACE_ID, valid_graph

ALLOWED_ORIGIN = "http://localhost:5173"


def graph_with_notes() -> dict:
    graph = valid_graph()
    for concept in graph["concepts"]:
        concept["annotations"] = [{"kind": "note", "value": f"{concept['label']}的笔记内容"}]
    return graph


@pytest.fixture()
def saved_workspace(tmp_path: Path) -> Path:
    layout = create_workspace(tmp_path / "ws")
    migrate(layout.db_path)
    save_course_graph(layout, graph_with_notes())
    return layout.root


# TC-SEARCH-001: FTS5 index built from saved graph
def test_search_hits_label(saved_workspace: Path) -> None:
    layout = create_workspace(saved_workspace)
    results = search_course_graph(layout, "极限")
    assert any(result.label == "极限" for result in results)


def test_search_hits_note(saved_workspace: Path) -> None:
    layout = create_workspace(saved_workspace)
    results = search_course_graph(layout, "连续")
    assert any(result.label == "连续" for result in results)


def test_search_result_shape(saved_workspace: Path) -> None:
    layout = create_workspace(saved_workspace)
    results = search_course_graph(layout, "极限")
    assert results
    result = results[0]
    assert isinstance(result, SearchResult)
    assert isinstance(result.id, str)
    assert isinstance(result.label, str)
    assert isinstance(result.snippet, str)


def test_search_no_match_returns_empty(saved_workspace: Path) -> None:
    layout = create_workspace(saved_workspace)
    assert search_course_graph(layout, "不存在的关键词") == []


# TC-SEARCH-002: search endpoint positive/negative paths
@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    app = create_app(data_root=tmp_path, allowed_origins=[ALLOWED_ORIGIN])
    return TestClient(app)


def test_search_endpoint_returns_matches(client: TestClient) -> None:
    client.put(f"/api/workspaces/{WORKSPACE_ID}/graph", json=graph_with_notes())
    response = client.get(f"/api/workspaces/{WORKSPACE_ID}/search", params={"q": "极限"})
    assert response.status_code == 200
    labels = [item["label"] for item in response.json()["results"]]
    assert "极限" in labels


def test_search_endpoint_empty_query_rejected(client: TestClient) -> None:
    client.put(f"/api/workspaces/{WORKSPACE_ID}/graph", json=graph_with_notes())
    response = client.get(f"/api/workspaces/{WORKSPACE_ID}/search", params={"q": ""})
    assert response.status_code == 422
    assert response.json()["code"] == "search_invalid_query"


def test_search_endpoint_overlong_query_rejected(client: TestClient) -> None:
    client.put(f"/api/workspaces/{WORKSPACE_ID}/graph", json=graph_with_notes())
    response = client.get(f"/api/workspaces/{WORKSPACE_ID}/search", params={"q": "x" * 101})
    assert response.status_code == 422
    assert response.json()["code"] == "search_invalid_query"


def test_search_endpoint_invalid_syntax_rejected(client: TestClient) -> None:
    client.put(f"/api/workspaces/{WORKSPACE_ID}/graph", json=graph_with_notes())
    response = client.get(f"/api/workspaces/{WORKSPACE_ID}/search", params={"q": "极限 AND ("})
    assert response.status_code == 422
    assert response.json()["code"] == "search_invalid_query"


def test_search_endpoint_no_match_empty_list(client: TestClient) -> None:
    client.put(f"/api/workspaces/{WORKSPACE_ID}/graph", json=graph_with_notes())
    response = client.get(f"/api/workspaces/{WORKSPACE_ID}/search", params={"q": "不存在"})
    assert response.status_code == 200
    assert response.json()["results"] == []


def test_search_endpoint_missing_workspace_404(client: TestClient) -> None:
    response = client.get(f"/api/workspaces/{WORKSPACE_ID}/search", params={"q": "极限"})
    assert response.status_code == 404
    assert response.json()["code"] == "workspace_missing"
