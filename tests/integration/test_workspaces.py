"""Red-light tests for workspace list/create endpoints (WORK-2026-039).

`GET/POST /api/workspaces` do not exist yet, so these tests are expected to
fail with 404 until the endpoints are implemented.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.main import create_app


def test_list_and_create_workspaces(tmp_path: Path) -> None:
    app = create_app(data_root=tmp_path, allowed_origins=[])
    client = TestClient(app)

    resp = client.get("/api/workspaces")
    assert resp.status_code == 200
    assert resp.json() == {"workspaces": []}

    resp = client.post("/api/workspaces", json={"name": "线性代数"})
    assert resp.status_code == 200
    created = resp.json()
    assert created["name"] == "线性代数"
    assert created["id"]

    resp = client.get("/api/workspaces")
    assert resp.status_code == 200
    ids = [ws["id"] for ws in resp.json()["workspaces"]]
    assert created["id"] in ids

    graph = client.get(f"/api/workspaces/{created['id']}/graph")
    assert graph.status_code == 200
    labels = [c["label"] for c in graph.json()["concepts"]]
    assert labels == ["线性代数"]


def test_create_workspace_invalid_name_422(tmp_path: Path) -> None:
    app = create_app(data_root=tmp_path, allowed_origins=[])
    client = TestClient(app)

    resp = client.post("/api/workspaces", json={"name": ""})
    assert resp.status_code == 422

    resp = client.post("/api/workspaces", json={"name": "x" * 51})
    assert resp.status_code == 422
