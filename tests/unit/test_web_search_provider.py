"""Red-light unit tests for the web search providers (WORK-2026-053).

Tavily/Brave adapters are stdlib-urllib clients with an injectable opener;
these tests never touch the network.
"""

from __future__ import annotations

import io
import json
from typing import Any
from urllib import error as urlerror

import pytest
from knowledge_tree_infrastructure.web_search import (
    WebSearchError,
    search_brave,
    search_tavily,
)

JsonObject = dict[str, Any]


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._stream = io.BytesIO(payload)

    def read(self) -> bytes:
        return self._stream.read()

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: Any) -> None:
        return None


def _tavily_body() -> bytes:
    return json.dumps(
        {
            "results": [
                {
                    "title": "极限 (数学)",
                    "url": "https://example.com/limit",
                    "content": "极限是微积分的基础概念",
                },
                {
                    "title": "Continuity",
                    "url": "https://example.com/continuity",
                    "content": "A function is continuous when",
                },
            ]
        }
    ).encode("utf-8")


def _brave_body() -> bytes:
    return json.dumps(
        {
            "web": {
                "results": [
                    {
                        "title": "Derivative",
                        "url": "https://example.com/deriv",
                        "description": "Rate of change",
                    },
                    {
                        "title": "Integral",
                        "url": "https://example.com/integral",
                        "description": "Area under curve",
                    },
                    {"title": "NoUrl", "url": "", "description": "dropped"},
                ]
            }
        }
    ).encode("utf-8")


def test_tavily_parses_hits_and_sends_query() -> None:
    captured: dict[str, Any] = {}

    def opener(request: Any, timeout: float) -> _FakeResponse:  # noqa: ARG001
        captured["url"] = request.full_url
        captured["auth"] = request.get_header("Authorization")
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse(_tavily_body())

    hits = search_tavily("tvly-test-key", "微积分 入门", opener=opener)

    assert captured["url"] == "https://api.tavily.com/search"
    assert captured["auth"] == "Bearer tvly-test-key"
    assert captured["body"]["query"] == "微积分 入门"
    assert [hit["url"] for hit in hits] == [
        "https://example.com/limit",
        "https://example.com/continuity",
    ]
    assert hits[0]["title"] == "极限 (数学)"
    assert "极限" in hits[0]["snippet"]


def test_brave_parses_hits_and_skips_empty_urls() -> None:
    captured: dict[str, Any] = {}

    def opener(request: Any, timeout: float) -> _FakeResponse:  # noqa: ARG001
        captured["url"] = request.full_url
        captured["token"] = request.get_header("X-subscription-token")
        return _FakeResponse(_brave_body())

    hits = search_brave("brave-test-key", "calculus", opener=opener)

    assert captured["url"].startswith("https://api.search.brave.com/res/v1/web/search?q=")
    assert captured["token"] == "brave-test-key"
    assert [hit["title"] for hit in hits] == ["Derivative", "Integral"]


def test_http_error_maps_to_stable_code() -> None:
    def opener(request: Any, timeout: float) -> _FakeResponse:  # noqa: ARG001
        raise urlerror.HTTPError(request.full_url, 401, "Unauthorized", None, io.BytesIO(b"{}"))  # type: ignore[arg-type]

    with pytest.raises(WebSearchError) as exc_info:
        search_tavily("bad-key", "query", opener=opener)
    assert exc_info.value.code == "web_search_failed"
    assert exc_info.value.details["rule"] == "http_error"
    assert exc_info.value.details["status"] == 401


def test_network_error_maps_to_stable_code() -> None:
    def opener(request: Any, timeout: float) -> _FakeResponse:  # noqa: ARG001
        raise urlerror.URLError("connection refused")

    with pytest.raises(WebSearchError) as exc_info:
        search_brave("key", "query", opener=opener)
    assert exc_info.value.code == "web_search_failed"
    assert exc_info.value.details["rule"] == "network_error"


def test_invalid_response_maps_to_stable_code() -> None:
    def opener(request: Any, timeout: float) -> _FakeResponse:  # noqa: ARG001
        return _FakeResponse(b"not-json")

    with pytest.raises(WebSearchError) as exc_info:
        search_tavily("key", "query", opener=opener)
    assert exc_info.value.code == "web_search_failed"
    assert exc_info.value.details["rule"] == "response_invalid"


def test_query_validation_rejects_blank_and_overlong() -> None:
    for query in ("", "   ", "x" * 201):
        with pytest.raises(WebSearchError) as exc_info:
            search_tavily("key", query, opener=lambda *a: _FakeResponse(b"{}"))
        assert exc_info.value.code == "web_search_invalid_query"
