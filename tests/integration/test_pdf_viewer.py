"""Red-light integration tests for PDF parsing and anchor jump (WORK-2026-017).

Targets `knowledge_tree_infrastructure.workspace` parser/anchor helpers and the
`apps.api` page/anchor endpoints, which do not exist yet, so collection is
expected to fail with ImportError.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from knowledge_tree_infrastructure.workspace import (
    PageSegment,
    create_workspace,
    get_page_text,
    import_resource,
    list_anchors,
    migrate,
    parse_pdf_resource,
    register_anchor,
)

from apps.api.main import create_app
from tests.contract.test_graph_contracts import WORKSPACE_ID

ALLOWED_ORIGIN = "http://localhost:5173"
GOLD_PDF = (
    Path(__file__).resolve().parents[2]
    / "evals"
    / "calculus-v1"
    / "source"
    / "mit-ocw-res-18-001-chapter-02-derivatives.pdf"
)
GOLD_JSON = Path(__file__).resolve().parents[2] / "evals" / "calculus-v1" / "gold.json"


@pytest.fixture(scope="module")
def layout(tmp_path_factory) -> object:
    root = tmp_path_factory.mktemp("ws")
    workspace = create_workspace(root / "ws")
    migrate(workspace.db_path)
    return workspace


@pytest.fixture(scope="module")
def pdf_resource(layout) -> str:
    content = GOLD_PDF.read_bytes()
    info = import_resource(layout, display_name="chapter-02.pdf", content=content)
    return info.id


# TC-VIEW-001: PDF parse -> segments
def test_parse_pdf_creates_segments(layout, pdf_resource) -> None:
    page_count = parse_pdf_resource(layout, pdf_resource)
    assert page_count == 52
    segment = get_page_text(layout, pdf_resource, 1)
    assert isinstance(segment, PageSegment)
    assert segment.page == 1
    assert "Derivative" in segment.text
    assert segment.text_hash.startswith("sha256:")


def test_parse_pdf_is_idempotent(layout, pdf_resource) -> None:
    first = parse_pdf_resource(layout, pdf_resource)
    second = parse_pdf_resource(layout, pdf_resource)
    assert first == second


# TC-VIEW-002: page text endpoint
def test_page_text_out_of_range(layout, pdf_resource) -> None:
    with pytest.raises(Exception) as excinfo:
        get_page_text(layout, pdf_resource, 99)
    assert "page_out_of_range" in str(excinfo.value)


def test_page_text_unparsed_resource(tmp_path: Path) -> None:
    workspace = create_workspace(tmp_path / "ws")
    migrate(workspace.db_path)
    info = import_resource(workspace, display_name="x.pdf", content=b"%PDF-1.7\n")
    with pytest.raises(Exception) as excinfo:
        get_page_text(workspace, info.id, 1)
    assert "parse_pending" in str(excinfo.value)


# TC-VIEW-003: anchors
def test_register_and_list_anchors(layout, pdf_resource) -> None:
    gold = json.loads(GOLD_JSON.read_text(encoding="utf-8"))
    for anchor in gold["anchors"]:
        register_anchor(
            layout,
            resource_id=pdf_resource,
            page=int(anchor["selector"]["page"]),
            payload={"topic_zh": anchor["topic_zh"], "concept_ids": anchor["concept_ids"]},
        )
    anchors = list_anchors(layout, pdf_resource)
    assert len(anchors) == 50
    pages = sorted(anchor.page for anchor in anchors)
    assert pages == list(range(1, 51))


def test_register_anchor_returns_stored_id_on_upsert(layout, pdf_resource) -> None:
    register_anchor(layout, resource_id=pdf_resource, page=1, payload={"v": 1})
    second = register_anchor(layout, resource_id=pdf_resource, page=1, payload={"v": 2})
    stored = list_anchors(layout, pdf_resource)
    page_one = [anchor for anchor in stored if anchor.page == 1]
    # The upsert must not create a duplicate row for the same page, and the
    # returned id must match the row actually stored.
    assert len(page_one) == 1
    assert second.id == page_one[0].id


def test_list_anchors_missing_resource_rejected(tmp_path: Path) -> None:
    workspace = create_workspace(tmp_path / "ws")
    migrate(workspace.db_path)
    missing = "00000000-0000-7000-8100-000000000099"
    with pytest.raises(Exception) as excinfo:
        list_anchors(workspace, missing)
    assert "workspace_missing" in str(excinfo.value)


# TC-VIEW-004: drift / missing locate fails closed
def test_page_text_drift_detected(tmp_path: Path) -> None:
    workspace = create_workspace(tmp_path / "ws")
    migrate(workspace.db_path)
    info = import_resource(workspace, display_name="c.pdf", content=GOLD_PDF.read_bytes())
    parse_pdf_resource(workspace, info.id)
    # Simulate content drift: change the stored content_hash.
    with sqlite3.connect(workspace.db_path) as conn:
        conn.execute(
            "UPDATE resource_version SET content_hash=? WHERE resource_id=?",
            ("sha256:" + "0" * 64, info.id),
        )
    with pytest.raises(Exception) as excinfo:
        get_page_text(workspace, info.id, 1)
    assert "source_changed" in str(excinfo.value)


# TC-VIEW-005: API endpoints
@pytest.fixture(scope="module")
def client(tmp_path_factory) -> TestClient:
    root = tmp_path_factory.mktemp("api")
    app = create_app(data_root=root, allowed_origins=[ALLOWED_ORIGIN])
    return TestClient(app)


def test_api_page_text(client: TestClient) -> None:
    with open(GOLD_PDF, "rb") as handle:
        response = client.post(
            f"/api/workspaces/{WORKSPACE_ID}/resources",
            files={"file": ("chapter-02.pdf", handle, "application/pdf")},
        )
    resource_id = response.json()["id"]

    parsed = client.post(f"/api/workspaces/{WORKSPACE_ID}/resources/{resource_id}/parse")
    assert parsed.status_code == 200
    assert parsed.json()["page_count"] == 52

    page = client.get(f"/api/workspaces/{WORKSPACE_ID}/resources/{resource_id}/pages/1")
    assert page.status_code == 200
    assert page.json()["page"] == 1
    assert "Derivative" in page.json()["text"]


def test_api_page_text_missing_resource_404(client: TestClient) -> None:
    missing = "00000000-0000-7000-8100-000000000099"
    response = client.get(f"/api/workspaces/{WORKSPACE_ID}/resources/{missing}/pages/1")
    assert response.status_code == 404
    assert response.json()["code"] == "workspace_missing"
