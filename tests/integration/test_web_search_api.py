"""Red-light integration tests for web-search settings and draft endpoint (WORK-2026-053).

The sidecar exposes provider/key settings plus a topic -> search -> untrusted
draft flow. Nothing here touches the network: the searcher and the draft
generator are injected fakes, mirroring the /ai-draft test style.
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
ALLOWED_ORIGIN = "http://localhost:5173"

JsonObject = dict[str, Any]


def _empty_graph() -> JsonObject:
    return {
        "schema_version": 1,
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "revision_no": 0,
        "concepts": [],
        "edges": [],
        "layout_items": [],
    }


@pytest.fixture()
def seeded_root(tmp_path: Path) -> Path:
    layout = create_workspace(tmp_path / WORKSPACE_ID)
    migrate(layout.db_path)
    save_course_graph(layout, _empty_graph())
    return tmp_path


def _fake_searcher(query: str) -> list[JsonObject]:
    return [
        {
            "title": f"关于{query}的资料",
            "url": "https://example.com/primary",
            "snippet": f"{query}的核心定义与应用场景。",
        },
        {
            "title": f"{query}进阶",
            "url": "https://example.com/advanced",
            "snippet": f"{query}的进阶主题与延伸阅读。",
        },
    ]


def _fake_workspace_draft(texts: list[tuple[str, str]], graph: JsonObject) -> JsonObject:
    base = int(graph["revision_no"])
    concept_id = "00000000-0000-7000-a000-0000000000b1"
    return {
        "draft": {
            "concepts": [
                {"label": "搜索概念", "aliases": [], "confidence": 0.9, "evidence_ids": []}
            ],
            "relations": [],
        },
        "patch": {
            "schema_version": 1,
            "patch_id": f"00000000-0000-7000-8000-{base + 1:012d}",
            "workspace_id": graph["workspace_id"],
            "course_id": graph["course_id"],
            "base_revision_no": base,
            "actor": {"type": "user", "id": "local-user"},
            "reason": "Web 搜索草案",
            "requires_confirmation": True,
            "confirmed": False,
            "operations": [
                {
                    "op_id": f"00000000-0000-7000-9000-{base + 2:012d}",
                    "op": "create_concept",
                    "concept": {
                        "id": concept_id,
                        "course_id": graph["course_id"],
                        "label": "搜索概念",
                        "origin": "user",
                        "review_state": "accepted",
                        "confidence": None,
                        "evidence_ids": [],
                        "locks": {
                            "content": False,
                            "relations": False,
                            "position": False,
                            "annotations": False,
                        },
                        "annotations": [],
                        "revision_no": 0,
                    },
                }
            ],
        },
    }


def _client(
    root: Path,
    *,
    searcher: Any = None,
    generator: Any = None,
) -> TestClient:
    return TestClient(
        create_app(
            data_root=root,
            allowed_origins=[ALLOWED_ORIGIN],
            web_searcher=searcher,
            workspace_draft_generator=generator,
        )
    )


def test_settings_roundtrip_without_leaking_key(seeded_root: Path) -> None:
    client = _client(seeded_root)

    initial = client.get("/api/settings/web-search")
    assert initial.status_code == 200
    assert initial.json() == {"provider": "tavily", "configured": False, "enabled": False}

    saved = client.put(
        "/api/settings/web-search",
        json={"provider": "brave", "api_key": "brave-secret-key"},
    )
    assert saved.status_code == 200
    assert saved.json() == {"status": "saved", "configured": True, "provider": "brave"}

    loaded = client.get("/api/settings/web-search")
    assert loaded.json() == {"provider": "brave", "configured": True, "enabled": True}
    assert "brave-secret-key" not in loaded.text

    cleared = client.delete("/api/settings/web-search")
    assert cleared.status_code == 200
    assert client.get("/api/settings/web-search").json()["configured"] is False


def test_settings_rejects_unknown_provider(seeded_root: Path) -> None:
    client = _client(seeded_root)

    response = client.put(
        "/api/settings/web-search",
        json={"provider": "google", "api_key": "k"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "web_search_invalid_provider"


def test_web_search_draft_requires_configuration(seeded_root: Path) -> None:
    client = _client(seeded_root)

    response = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/web-search-draft", json={"query": "微积分"}
    )
    assert response.status_code == 503
    assert response.json()["code"] == "web_search_not_available"


def test_web_search_draft_returns_untrusted_draft_with_sources(
    seeded_root: Path,
) -> None:
    client = _client(seeded_root, searcher=_fake_searcher, generator=_fake_workspace_draft)

    response = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/web-search-draft", json={"query": "微积分"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["patch"]["requires_confirmation"] is True
    assert body["patch"]["confirmed"] is False
    assert [source["url"] for source in body["sources"]] == [
        "https://example.com/primary",
        "https://example.com/advanced",
    ]

    # Untrusted: the graph is untouched until the in-app confirmation.
    graph = client.get(f"/api/workspaces/{WORKSPACE_ID}/graph").json()
    assert graph["revision_no"] == 0
    assert graph["concepts"] == []


def test_web_search_draft_validates_query(seeded_root: Path) -> None:
    client = _client(seeded_root, searcher=_fake_searcher, generator=_fake_workspace_draft)

    blank = client.post(f"/api/workspaces/{WORKSPACE_ID}/web-search-draft", json={"query": "  "})
    assert blank.status_code == 422
    assert blank.json()["code"] == "web_search_invalid_query"

    overlong = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/web-search-draft", json={"query": "x" * 201}
    )
    assert overlong.status_code == 422


def test_web_search_draft_empty_results_fail_closed(seeded_root: Path) -> None:
    client = _client(seeded_root, searcher=lambda query: [], generator=_fake_workspace_draft)

    response = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/web-search-draft", json={"query": "冷门主题"}
    )
    assert response.status_code == 422
    assert response.json()["code"] == "web_search_failed"
    assert response.json()["rule"] == "no_results"
