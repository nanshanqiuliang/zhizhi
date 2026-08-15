"""Red-light tests for AI settings endpoints (WORK-2026-038).

`/api/settings/ai` does not exist yet, so these tests are expected to fail with
404 until the endpoints are implemented.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.main import create_app

WORKSPACE_ID = "00000000-0000-7000-8000-000000000001"
FAKE_KEY = "fake-deepseek-key-not-secret"


def test_ai_settings_roundtrip(tmp_path: Path) -> None:
    app = create_app(data_root=tmp_path, allowed_origins=[])
    client = TestClient(app)

    resp = client.get("/api/settings/ai")
    assert resp.status_code == 200
    assert resp.json() == {"configured": False, "enabled": False}

    resp = client.put("/api/settings/ai", json={"api_key": FAKE_KEY})
    assert resp.status_code == 200
    assert resp.json()["configured"] is True

    resp = client.get("/api/settings/ai")
    assert resp.status_code == 200
    assert resp.json() == {"configured": True, "enabled": True}

    resp = client.delete("/api/settings/ai")
    assert resp.status_code == 200
    assert resp.json()["configured"] is False

    resp = client.get("/api/settings/ai")
    assert resp.json() == {"configured": False, "enabled": False}


def test_ai_settings_invalid_key_422(tmp_path: Path) -> None:
    app = create_app(data_root=tmp_path, allowed_origins=[])
    client = TestClient(app)

    resp = client.put("/api/settings/ai", json={"api_key": ""})
    assert resp.status_code == 422
