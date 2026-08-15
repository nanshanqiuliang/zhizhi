"""Red-light tests for Step 10 slice 1 desktop packaging (WORK-2026-033).

`create_app` does not yet accept `web_dist` and `apps.desktop.launcher` does not
exist, so this file is expected to fail until the static-hosting and launcher
slices are implemented.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app


@pytest.fixture()
def web_dist(tmp_path: Path) -> Path:
    dist = tmp_path / "web"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(
        '<!doctype html><html><body><div id="root"></div></body></html>',
        encoding="utf-8",
    )
    (dist / "assets" / "app.js").write_text("console.log('app')", encoding="utf-8")
    return dist


def test_web_dist_serves_index_and_assets(tmp_path: Path, web_dist: Path) -> None:
    app = create_app(data_root=tmp_path, allowed_origins=[], web_dist=web_dist)
    client = TestClient(app)

    index = client.get("/")
    assert index.status_code == 200
    assert 'id="root"' in index.text

    asset = client.get("/assets/app.js")
    assert asset.status_code == 200
    assert asset.text == "console.log('app')"

    health = client.get("/api/health")
    assert health.status_code == 200


def test_desktop_launcher_module_exists() -> None:
    import apps.desktop.launcher

    assert callable(apps.desktop.launcher.main)
