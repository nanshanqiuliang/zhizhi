"""Red-light integration tests for knowledge-tree PNG export (WORK-2026-051).

Targets `knowledge_tree_infrastructure.png_export` (layout + renderer) and the
`GET /graph/image` endpoint, neither of which exists yet.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from knowledge_tree_infrastructure.workspace import (
    create_workspace,
    migrate,
    save_course_graph,
)

from apps.api.main import create_app

WORKSPACE_ID = "00000000-0000-7000-8000-000000000001"
COURSE_ID = "00000000-0000-7000-8000-000000000002"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
ALLOWED_ORIGIN = "http://localhost:5173"


def _concept(concept_id: str, label: str) -> dict[str, Any]:
    return {
        "id": concept_id,
        "course_id": COURSE_ID,
        "label": label,
        "origin": "user",
        "review_state": "accepted",
        "confidence": None,
        "evidence_ids": [],
        "locks": {"content": False, "relations": False, "position": False, "annotations": False},
        "annotations": [],
        "revision_no": 0,
    }


def _graph(concepts: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "revision_no": 0,
        "concepts": concepts,
        "edges": edges,
        "layout_items": [],
    }


def _small_graph() -> dict[str, Any]:
    root = _concept("00000000-0000-7000-a000-000000000001", "微积分")
    child = _concept("00000000-0000-7000-a000-000000000002", "极限")
    edge = {
        "id": "00000000-0000-7000-b000-000000000001",
        "course_id": COURSE_ID,
        "source_concept_id": root["id"],
        "target_concept_id": child["id"],
        "edge_type": "prerequisite_of",
        "origin": "user",
        "review_state": "accepted",
        "confidence": None,
        "evidence_ids": [],
        "locked": False,
        "revision_no": 0,
    }
    return _graph([root, child], [edge])


@pytest.fixture()
def seeded_root(tmp_path: Path) -> Path:
    layout = create_workspace(tmp_path / WORKSPACE_ID)
    migrate(layout.db_path)
    save_course_graph(layout, _small_graph())
    return tmp_path


def test_layout_tree_is_deterministic_and_non_overlapping() -> None:
    from knowledge_tree_infrastructure.png_export import layout_tree

    graph = _small_graph()
    first = layout_tree(graph["concepts"], graph["edges"])
    second = layout_tree(graph["concepts"], graph["edges"])
    assert first == second

    positions = list(first.values())
    assert len(positions) == 2
    # Root above child: strictly smaller depth means strictly smaller y.
    root_id = "00000000-0000-7000-a000-000000000001"
    child_id = "00000000-0000-7000-a000-000000000002"
    assert first[root_id]["y"] < first[child_id]["y"]
    # Same-depth nodes never share an x slot.
    by_depth: dict[int, set[float]] = {}
    for pos in first.values():
        by_depth.setdefault(pos["depth"], set()).add(pos["x"])
    for xs in by_depth.values():
        assert len(xs) == len({x for x in xs})


def test_render_small_graph_writes_valid_png(seeded_root: Path, tmp_path: Path) -> None:
    from knowledge_tree_infrastructure.png_export import render_graph_png
    from knowledge_tree_infrastructure.workspace import load_course_graph, resolve_workspace

    layout = resolve_workspace(seeded_root / WORKSPACE_ID)
    graph = load_course_graph(layout)
    out = tmp_path / "out.png"
    returned = render_graph_png(graph, out)

    assert returned == out
    payload = out.read_bytes()
    assert payload[:8] == PNG_MAGIC
    assert len(payload) > 1000


def test_render_empty_graph_produces_placeholder(tmp_path: Path) -> None:
    from knowledge_tree_infrastructure.png_export import render_graph_png

    out = tmp_path / "empty.png"
    render_graph_png(_graph([], []), out)
    assert out.read_bytes()[:8] == PNG_MAGIC


def test_render_chinese_labels_does_not_crash(tmp_path: Path) -> None:
    from knowledge_tree_infrastructure.png_export import render_graph_png

    out = tmp_path / "zh.png"
    render_graph_png(_small_graph(), out)
    assert out.read_bytes()[:8] == PNG_MAGIC


def test_graph_image_endpoint_serves_png(seeded_root: Path) -> None:
    client = TestClient(create_app(data_root=seeded_root, allowed_origins=[ALLOWED_ORIGIN]))

    response = client.get(f"/api/workspaces/{WORKSPACE_ID}/graph/image")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
    assert response.content[:8] == PNG_MAGIC
    # The exported file lands in the workspace exports dir.
    assert (seeded_root / WORKSPACE_ID / "exports" / "mindmap.png").is_file()


def test_graph_image_endpoint_missing_workspace_404(tmp_path: Path) -> None:
    client = TestClient(create_app(data_root=tmp_path, allowed_origins=[ALLOWED_ORIGIN]))
    response = client.get(f"/api/workspaces/{WORKSPACE_ID}/graph/image")
    assert response.status_code == 404
