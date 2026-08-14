"""Red-light integration tests for safe file import (WORK-2026-016).

Targets `knowledge_tree_infrastructure.workspace` resource helpers and the
`apps.api` import/list endpoints, which do not exist yet, so collection is
expected to fail with ImportError.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from knowledge_tree_infrastructure.workspace import (
    ResourceInfo,
    create_workspace,
    import_resource,
    list_resources,
    migrate,
)

from apps.api.main import create_app
from tests.contract.test_graph_contracts import WORKSPACE_ID

ALLOWED_ORIGIN = "http://localhost:5173"
MD_CONTENT = "# 极限\n\n趋近与连续性的定义。\n".encode()
TXT_CONTENT = "导数\n瞬时变化率。\n".encode()
PDF_HEADER = b"%PDF-1.7\n% fake but header-valid\n"


@pytest.fixture()
def layout(tmp_path: Path):
    workspace = create_workspace(tmp_path / "ws")
    migrate(workspace.db_path)
    return workspace


# TC-IMPORT-001: migration v1 -> v2
def test_migrate_creates_resource_tables(tmp_path: Path) -> None:
    import sqlite3

    workspace = create_workspace(tmp_path / "ws")
    migrate(workspace.db_path)
    with sqlite3.connect(workspace.db_path) as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
    assert version == 3
    assert "resource" in tables
    assert "resource_version" in tables


def test_migrate_rejects_unknown_version(tmp_path: Path) -> None:
    import sqlite3

    workspace = create_workspace(tmp_path / "ws")
    migrate(workspace.db_path)
    with sqlite3.connect(workspace.db_path) as conn:
        conn.execute("PRAGMA user_version = 99")
    with pytest.raises(Exception) as excinfo:
        migrate(workspace.db_path)
    assert "migration_conflict" in str(excinfo.value)


# TC-IMPORT-002: import MD/TXT/PDF
def test_import_markdown(layout) -> None:
    info = import_resource(layout, display_name="notes.md", content=MD_CONTENT)
    assert isinstance(info, ResourceInfo)
    assert info.display_name == "notes.md"
    assert info.mime == "text/markdown"
    assert info.byte_size == len(MD_CONTENT)
    assert info.content_hash.startswith("sha256:")


def test_import_txt(layout) -> None:
    info = import_resource(layout, display_name="notes.txt", content=TXT_CONTENT)
    assert info.mime == "text/plain"


def test_import_pdf(layout) -> None:
    info = import_resource(layout, display_name="book.pdf", content=PDF_HEADER)
    assert info.mime == "application/pdf"


def test_import_duplicate_is_idempotent(layout) -> None:
    first = import_resource(layout, display_name="a.md", content=MD_CONTENT)
    second = import_resource(layout, display_name="b.md", content=MD_CONTENT)
    assert first.content_hash == second.content_hash
    assert len(list_resources(layout)) == 1  # same hash -> one resource


def test_list_resources_metadata_only(layout) -> None:
    import_resource(layout, display_name="a.md", content=MD_CONTENT)
    import_resource(layout, display_name="b.txt", content=TXT_CONTENT)
    resources = list_resources(layout)
    assert len(resources) == 2
    for info in resources:
        assert isinstance(info, ResourceInfo)
        assert info.content_hash.startswith("sha256:")


# TC-IMPORT-003: rejection without writes
def test_import_rejects_out_of_whitelist(layout) -> None:
    with pytest.raises(Exception) as excinfo:
        import_resource(layout, display_name="evil.exe", content=b"MZ\x90\x00")
    assert "import_type_rejected" in str(excinfo.value)
    assert list_resources(layout) == []


def test_import_rejects_forged_extension(layout) -> None:
    with pytest.raises(Exception) as excinfo:
        import_resource(layout, display_name="fake.pdf", content=b"not a pdf at all")
    assert "import_type_rejected" in str(excinfo.value)


def test_import_rejects_too_large(layout) -> None:
    oversized = b"x" * (25 * 1024 * 1024 + 1)
    with pytest.raises(Exception) as excinfo:
        import_resource(layout, display_name="big.txt", content=oversized)
    assert "import_too_large" in str(excinfo.value)


def test_import_rejects_traversal_name(layout) -> None:
    with pytest.raises(Exception) as excinfo:
        import_resource(layout, display_name="../../evil.md", content=MD_CONTENT)
    assert "import_type_rejected" in str(excinfo.value) or "invalid_name" in str(excinfo.value)


def test_import_write_failure_leaves_no_orphan(tmp_path: Path) -> None:
    workspace = create_workspace(tmp_path / "ws")
    migrate(workspace.db_path)
    # Make the resources directory unwritable by placing a file where the
    # directory would be created.
    (workspace.root / "resources").write_text("blocked", encoding="utf-8")
    with pytest.raises(Exception) as excinfo:
        import_resource(workspace, display_name="notes.md", content=MD_CONTENT)
    assert "import_failed" in str(excinfo.value)
    assert list_resources(workspace) == []


# TC-IMPORT-004: API endpoints
@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    app = create_app(data_root=tmp_path, allowed_origins=[ALLOWED_ORIGIN])
    return TestClient(app)


def test_api_import_and_list(client: TestClient) -> None:
    response = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/resources",
        files={"file": ("notes.md", MD_CONTENT, "text/markdown")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] == "notes.md"
    assert body["content_hash"].startswith("sha256:")

    listed = client.get(f"/api/workspaces/{WORKSPACE_ID}/resources")
    assert listed.status_code == 200
    assert len(listed.json()["resources"]) == 1
    assert "content" not in listed.json()["resources"][0]


def test_api_import_rejects_bad_type(client: TestClient) -> None:
    response = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/resources",
        files={"file": ("evil.exe", b"MZ\x90\x00", "application/octet-stream")},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "import_type_rejected"


def test_api_resources_missing_workspace_404(client: TestClient) -> None:
    response = client.get(f"/api/workspaces/{WORKSPACE_ID}/resources")
    assert response.status_code == 404
    assert response.json()["code"] == "workspace_missing"
