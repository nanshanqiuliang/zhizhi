"""Red-light integration tests for the local persistence API (WORK-2026-014).

Targets `apps.api.main.create_app` which does not exist yet, so collection is
expected to fail with ImportError until the FastAPI composition root is
implemented.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from tests.contract.test_graph_contracts import WORKSPACE_ID, valid_graph

ALLOWED_ORIGIN = "http://localhost:5173"
FORBIDDEN_ORIGIN = "http://evil.example"


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    app = create_app(data_root=tmp_path, allowed_origins=[ALLOWED_ORIGIN])
    return TestClient(app)


# TC-API-001: health / loopback / CORS
def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_allows_configured_origin(client: TestClient) -> None:
    response = client.get(
        "/api/health",
        headers={"Origin": ALLOWED_ORIGIN},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN


def test_cors_rejects_forbidden_origin(client: TestClient) -> None:
    response = client.get(
        "/api/health",
        headers={"Origin": FORBIDDEN_ORIGIN},
    )
    assert response.status_code == 200  # preflight/option allowed at transport
    assert "access-control-allow-origin" not in response.headers


# TC-API-002: PUT valid graph then GET equal
def test_put_then_get_round_trip(client: TestClient, tmp_path: Path) -> None:
    graph = valid_graph()
    response = client.put(f"/api/workspaces/{WORKSPACE_ID}/graph", json=graph)
    assert response.status_code == 200

    loaded = client.get(f"/api/workspaces/{WORKSPACE_ID}/graph")
    assert loaded.status_code == 200
    assert loaded.json()["workspace_id"] == WORKSPACE_ID
    assert loaded.json()["course_id"] == graph["course_id"]
    assert loaded.json()["revision_no"] == graph["revision_no"]
    assert loaded.json()["concepts"] == graph["concepts"]


def test_get_missing_workspace_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/workspaces/{WORKSPACE_ID}/graph")
    assert response.status_code == 404
    assert response.json()["code"] == "workspace_missing"


# TC-API-003: invalid graph rejected without overwrite
def test_put_invalid_graph_rejected(client: TestClient, tmp_path: Path) -> None:
    graph = valid_graph()
    assert client.put(f"/api/workspaces/{WORKSPACE_ID}/graph", json=graph).status_code == 200

    invalid = dict(graph)
    invalid["concepts"] = [{"id": "not-valid"}]
    response = client.put(f"/api/workspaces/{WORKSPACE_ID}/graph", json=invalid)
    assert response.status_code == 422
    assert response.json()["code"] == "graph_invalid"

    loaded = client.get(f"/api/workspaces/{WORKSPACE_ID}/graph")
    assert loaded.json()["revision_no"] == graph["revision_no"]


# TC-API-004: backup endpoint
def test_backup_creates_checksummed_backup(client: TestClient, tmp_path: Path) -> None:
    graph = valid_graph()
    assert client.put(f"/api/workspaces/{WORKSPACE_ID}/graph", json=graph).status_code == 200

    response = client.post(f"/api/workspaces/{WORKSPACE_ID}/backup")
    assert response.status_code == 200
    backup_path = Path(response.json()["backup_path"])
    assert backup_path.exists()
    assert backup_path.with_suffix(backup_path.suffix + ".sha256").exists()


def test_backup_missing_workspace_returns_404(client: TestClient) -> None:
    # A backup must not silently create an empty workspace; it must behave like
    # GET and return workspace_missing when nothing was saved yet.
    response = client.post(f"/api/workspaces/{WORKSPACE_ID}/backup")
    assert response.status_code == 404
    assert response.json()["code"] == "workspace_missing"
