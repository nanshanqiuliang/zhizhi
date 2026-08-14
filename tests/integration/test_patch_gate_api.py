"""Red-light integration tests for the patch-gate API endpoints (WORK-2026-019).

Targets the `POST .../graph/patches`, `POST .../graph/undo`, `POST .../graph/redo`
and `GET .../history` endpoints which do not exist yet, so they are expected to
fail (404/ImportError) until implemented.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from tests.contract.test_graph_contracts import (
    CONCEPT_B_ID,
    WORKSPACE_ID,
    valid_graph,
    valid_patch,
)

JsonObject = dict[str, Any]
ALLOWED_ORIGIN = "http://localhost:5173"


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    app = create_app(data_root=tmp_path, allowed_origins=[ALLOWED_ORIGIN])
    return TestClient(app)


def _seed_graph(client: TestClient) -> None:
    response = client.put(f"/api/workspaces/{WORKSPACE_ID}/graph", json=valid_graph())
    assert response.status_code == 200


def _confirmed_patch() -> JsonObject:
    patch = valid_patch()
    patch["confirmed"] = True
    return patch


def _set_lock_patch(*, base_revision: int) -> JsonObject:
    patch = _confirmed_patch()
    patch["patch_id"] = f"00000000-0000-7000-9100-0000000000{base_revision:02d}"
    patch["base_revision_no"] = base_revision
    patch["operations"] = [
        {
            "op_id": f"00000000-0000-7000-9100-0000000001{base_revision:02d}",
            "op": "set_lock",
            "target": {"type": "concept", "id": CONCEPT_B_ID},
            "expected_updated_revision_no": base_revision,
            "dimension": "content",
            "value": True,
        }
    ]
    return patch


def _update_label_patch(*, base_revision: int) -> JsonObject:
    patch = _confirmed_patch()
    patch["patch_id"] = f"00000000-0000-7000-9100-0000000002{base_revision:02d}"
    patch["base_revision_no"] = base_revision
    patch["operations"] = [
        {
            "op_id": f"00000000-0000-7000-9100-0000000003{base_revision:02d}",
            "op": "update_concept",
            "target": {"type": "concept", "id": CONCEPT_B_ID},
            "expected_updated_revision_no": base_revision,
            "evidence_ids": [],
            "changes": {"label": "被覆盖"},
        }
    ]
    return patch


# TC-GATE-006: patches / undo / redo / history endpoints
def test_patch_endpoint_applies_and_lists_history(client: TestClient) -> None:
    _seed_graph(client)

    applied = client.post(f"/api/workspaces/{WORKSPACE_ID}/graph/patches", json=_confirmed_patch())
    assert applied.status_code == 200
    assert applied.json()["status"] == "applied"
    assert applied.json()["revision_no"] == 1

    history = client.get(f"/api/workspaces/{WORKSPACE_ID}/history")
    assert history.status_code == 200
    assert len(history.json()["records"]) == 1


def test_undo_redo_endpoints(client: TestClient) -> None:
    _seed_graph(client)
    patch = _confirmed_patch()
    assert (
        client.post(f"/api/workspaces/{WORKSPACE_ID}/graph/patches", json=patch).status_code == 200
    )

    undone = client.post(f"/api/workspaces/{WORKSPACE_ID}/graph/undo")
    assert undone.status_code == 200
    assert undone.json()["revision_no"] == 2

    redone = client.post(f"/api/workspaces/{WORKSPACE_ID}/graph/redo")
    assert redone.status_code == 200
    assert redone.json()["revision_no"] == 3


def test_undo_empty_history_conflict(client: TestClient) -> None:
    _seed_graph(client)
    response = client.post(f"/api/workspaces/{WORKSPACE_ID}/graph/undo")
    assert response.status_code == 409
    assert response.json()["code"] == "history_empty"


def test_patch_missing_workspace_404(client: TestClient) -> None:
    response = client.post(f"/api/workspaces/{WORKSPACE_ID}/graph/patches", json=_confirmed_patch())
    assert response.status_code == 404


def test_patch_target_locked_conflict(client: TestClient) -> None:
    _seed_graph(client)
    assert (
        client.post(
            f"/api/workspaces/{WORKSPACE_ID}/graph/patches",
            json=_set_lock_patch(base_revision=0),
        ).status_code
        == 200
    )

    response = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/graph/patches",
        json=_update_label_patch(base_revision=1),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "target_locked"

    loaded = client.get(f"/api/workspaces/{WORKSPACE_ID}/graph")
    concept_b = next(c for c in loaded.json()["concepts"] if c["id"] == CONCEPT_B_ID)
    assert concept_b["label"] == "连续"
