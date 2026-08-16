"""Live web-search smoke (WORK-2026-053), double-gated like the DeepSeek live tests.

Runs only when RUN_LIVE_WEB_SEARCH_TESTS=1 and a provider key is present in the
environment (TAVILY_API_KEY or BRAVE_API_KEY). Never part of the default suite.
"""

from __future__ import annotations

import os

import pytest
from knowledge_tree_infrastructure.web_search import search_brave, search_tavily

_RUN_LIVE = os.environ.get("RUN_LIVE_WEB_SEARCH_TESTS") == "1"


def _provider_and_key() -> tuple[str, str] | None:
    if os.environ.get("TAVILY_API_KEY"):
        return "tavily", os.environ["TAVILY_API_KEY"]
    if os.environ.get("BRAVE_API_KEY"):
        return "brave", os.environ["BRAVE_API_KEY"]
    return None


pytestmark = pytest.mark.skipif(
    not _RUN_LIVE or _provider_and_key() is None,
    reason=(
        "live web-search smoke requires RUN_LIVE_WEB_SEARCH_TESTS=1 "
        "and TAVILY_API_KEY/BRAVE_API_KEY"
    ),
)


def test_live_search_returns_hits() -> None:
    provider_key = _provider_and_key()
    assert provider_key is not None
    provider, key = provider_key
    searcher = search_tavily if provider == "tavily" else search_brave
    hits = searcher(key, "calculus basics", max_results=3)
    assert hits, "expected at least one search hit"
    assert all(hit["url"].startswith("https://") for hit in hits)
