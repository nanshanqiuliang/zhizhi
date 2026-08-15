"""Red-light tests for the reveal (open local directory) endpoints (WORK-2026-037).

`open-dir`/`reveal` endpoints do not exist yet, so these tests are expected to
fail with 404 until the endpoints are implemented.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app

WORKSPACE_ID = "00000000-0000-7000-8000-000000000001"


def _import_md(client: TestClient) -> str:
    files = {"file": ("note.md", b"# hi\n", "text/markdown")}
    resp = client.post(f"/api/workspaces/{WORKSPACE_ID}/resources", files=files)
    assert resp.status_code == 200
    return str(resp.json()["id"])


def test_open_dir_and_reveal_endpoints(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Do not actually launch Explorer during tests.
    monkeypatch.setattr(
        "apps.api.main._reveal_in_explorer", lambda *args, **kwargs: None, raising=False
    )
    app = create_app(data_root=tmp_path, allowed_origins=[])
    client = TestClient(app)
    rid = _import_md(client)

    resp = client.post(f"/api/workspaces/{WORKSPACE_ID}/resources/open-dir")
    assert resp.status_code == 200
    assert "resources" in resp.json()["path"]

    resp = client.post(f"/api/workspaces/{WORKSPACE_ID}/resources/{rid}/reveal")
    assert resp.status_code == 200
    assert str(rid) in resp.json()["path"]


def test_reveal_missing_resource_404(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "apps.api.main._reveal_in_explorer", lambda *args, **kwargs: None, raising=False
    )
    app = create_app(data_root=tmp_path, allowed_origins=[])
    client = TestClient(app)
    _import_md(client)

    missing = "00000000-0000-7000-8000-000000000099"
    resp = client.post(f"/api/workspaces/{WORKSPACE_ID}/resources/{missing}/reveal")
    assert resp.status_code == 404
