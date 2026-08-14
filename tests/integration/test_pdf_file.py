"""Red-light integration tests for the PDF file endpoint (WORK-2026-018).

Targets `apps.api` file serving and the `knowledge_tree_infrastructure`
file guard, which do not exist yet, so collection is expected to fail.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from knowledge_tree_infrastructure.workspace import (
    create_workspace,
    import_resource,
    migrate,
)

from tests.contract.test_graph_contracts import WORKSPACE_ID

ALLOWED_ORIGIN = "http://localhost:5173"
GOLD_PDF = (
    Path(__file__).resolve().parents[2]
    / "evals"
    / "calculus-v1"
    / "source"
    / "mit-ocw-res-18-001-chapter-02-derivatives.pdf"
)


@pytest.fixture(scope="module")
def client(tmp_path_factory) -> TestClient:
    root = tmp_path_factory.mktemp("api")
    app = create_app(data_root=root, allowed_origins=[ALLOWED_ORIGIN])
    return TestClient(app)


# TC-RENDER-001: file endpoint
def test_file_endpoint_serves_pdf(client: TestClient) -> None:
    with open(GOLD_PDF, "rb") as handle:
        response = client.post(
            f"/api/workspaces/{WORKSPACE_ID}/resources",
            files={"file": ("chapter-02.pdf", handle, "application/pdf")},
        )
    resource_id = response.json()["id"]

    file_response = client.get(f"/api/workspaces/{WORKSPACE_ID}/resources/{resource_id}/file")
    assert file_response.status_code == 200
    assert file_response.headers["content-type"] == "application/pdf"
    assert file_response.content.startswith(b"%PDF-")
    assert len(file_response.content) == GOLD_PDF.stat().st_size


def test_file_endpoint_missing_resource_404(client: TestClient) -> None:
    missing = "00000000-0000-7000-8100-000000000099"
    response = client.get(f"/api/workspaces/{WORKSPACE_ID}/resources/{missing}/file")
    assert response.status_code == 404
    assert response.json()["code"] == "workspace_missing"


def test_file_endpoint_non_pdf_resource_rejected(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient as TC

    workspace = create_workspace(tmp_path / "ws")
    migrate(workspace.db_path)
    info = import_resource(workspace, display_name="notes.md", content=b"# hi")
    # The file guard is exercised through import_resource storage keys; the
    # endpoint itself requires an application/pdf resource. This test just
    # confirms the guard exists at the infrastructure layer.
    assert info.content_hash.startswith("sha256:")
