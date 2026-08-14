"""Integration tests for backup list and restore endpoints (WORK-2026-021)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from tests.contract.test_graph_contracts import WORKSPACE_ID, valid_graph

ALLOWED_ORIGIN = "http://localhost:5173"


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    app = create_app(data_root=tmp_path, allowed_origins=[ALLOWED_ORIGIN])
    return TestClient(app)


def _put_graph(client: TestClient, graph: dict) -> None:
    response = client.put(f"/api/workspaces/{WORKSPACE_ID}/graph", json=graph)
    assert response.status_code == 200


def test_backup_list_and_restore_round_trip(client: TestClient) -> None:
    graph = valid_graph()
    _put_graph(client, graph)

    backed = client.post(f"/api/workspaces/{WORKSPACE_ID}/backup")
    assert backed.status_code == 200

    listed = client.get(f"/api/workspaces/{WORKSPACE_ID}/backups")
    assert listed.status_code == 200
    assert len(listed.json()["backups"]) == 1
    filename = listed.json()["backups"][0]

    # Mutate the graph, then restore the backup and confirm the old value.
    changed = dict(valid_graph())
    changed["revision_no"] = 9
    _put_graph(client, changed)

    restored = client.post(f"/api/workspaces/{WORKSPACE_ID}/restore", json={"filename": filename})
    assert restored.status_code == 200

    loaded = client.get(f"/api/workspaces/{WORKSPACE_ID}/graph")
    assert loaded.status_code == 200
    assert loaded.json()["revision_no"] == graph["revision_no"]


def test_restore_rejects_traversal_filename(client: TestClient) -> None:
    _put_graph(client, valid_graph())
    response = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/restore", json={"filename": "../outside.sqlite3"}
    )
    assert response.status_code == 422
    assert response.json()["code"] == "backup_invalid"


def test_restore_missing_backup_rejected(client: TestClient) -> None:
    _put_graph(client, valid_graph())
    response = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/restore",
        json={"filename": "backup-missing.sqlite3"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "backup_invalid"


def test_restore_rejects_missing_checksum_sidecar(client: TestClient, tmp_path: Path) -> None:
    _put_graph(client, valid_graph())
    backed = client.post(f"/api/workspaces/{WORKSPACE_ID}/backup")
    assert backed.status_code == 200
    filename = Path(backed.json()["backup_path"]).name

    # Remove the checksum sidecar so restore must fail closed.
    sidecar = tmp_path / WORKSPACE_ID / "backups" / f"{filename}.sha256"
    sidecar.unlink()

    response = client.post(f"/api/workspaces/{WORKSPACE_ID}/restore", json={"filename": filename})
    assert response.status_code == 422
    assert response.json()["code"] == "backup_invalid"
    assert response.json()["rule"] == "backup_checksum_missing"


def test_restore_rejects_checksum_mismatch(client: TestClient, tmp_path: Path) -> None:
    _put_graph(client, valid_graph())
    backed = client.post(f"/api/workspaces/{WORKSPACE_ID}/backup")
    assert backed.status_code == 200
    filename = Path(backed.json()["backup_path"]).name

    sidecar = tmp_path / WORKSPACE_ID / "backups" / f"{filename}.sha256"
    sidecar.write_text("0" * 64 + "\n", encoding="utf-8")

    response = client.post(f"/api/workspaces/{WORKSPACE_ID}/restore", json={"filename": filename})
    assert response.status_code == 409
    assert response.json()["code"] == "backup_checksum_mismatch"


def test_restore_recovers_after_database_lost(client: TestClient, tmp_path: Path) -> None:
    graph = valid_graph()
    _put_graph(client, graph)
    backed = client.post(f"/api/workspaces/{WORKSPACE_ID}/backup")
    assert backed.status_code == 200
    filename = Path(backed.json()["backup_path"]).name

    # Simulate a lost database (crash recovery): delete the db file.
    db_path = tmp_path / WORKSPACE_ID / "knowledge-tree.db"
    db_path.unlink()

    # The backup list must still be reachable without a live db.
    listed = client.get(f"/api/workspaces/{WORKSPACE_ID}/backups")
    assert listed.status_code == 200
    assert listed.json()["backups"] == [filename]

    # Restoring must recreate the db from the backup.
    restored = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/restore", json={"filename": filename}
    )
    assert restored.status_code == 200

    loaded = client.get(f"/api/workspaces/{WORKSPACE_ID}/graph")
    assert loaded.status_code == 200
    assert loaded.json()["revision_no"] == graph["revision_no"]
