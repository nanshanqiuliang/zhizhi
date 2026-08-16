"""Controlled web-search providers for the search agent (WORK-2026-053).

Stdlib-only HTTP clients (mirroring the LLM transport layer): HTTPS-only,
bounded timeouts, injectable opener for offline tests, and stable
`code`/`rule` error mapping. API keys are only ever passed into the call and
never included in error details or logs. Search results are UNTRUSTED external
input; callers must treat them as draft material only.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Never
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

JsonObject = dict[str, Any]

PROVIDERS = frozenset({"tavily", "brave"})
_MAX_QUERY_CHARS = 200
_READ_TIMEOUT_S = 15.0

_TAVILY_URL = "https://api.tavily.com/search"
_BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"

Opener = Callable[..., Any]


class WebSearchError(Exception):
    """Stable-code search failure (never carries the API key)."""

    def __init__(self, code: str, *, details: dict[str, Any] | None = None) -> None:
        self.code = code
        self.details = details or {}
        super().__init__(f"web search error: {code}")


def _reject(code: str, rule: str, **details: Any) -> Never:
    raise WebSearchError(code, details={"rule": rule, **details})


def _validate_query(query: str) -> str:
    if not isinstance(query, str):
        _reject("web_search_invalid_query", "query_not_string")
    stripped = query.strip()
    if not stripped:
        _reject("web_search_invalid_query", "query_empty")
    if len(stripped) > _MAX_QUERY_CHARS:
        _reject("web_search_invalid_query", "query_too_long")
    return stripped


def _read_json(request: urlrequest.Request, opener: Opener) -> JsonObject:
    try:
        with opener(request, timeout=_READ_TIMEOUT_S) as response:
            body = response.read().decode("utf-8", "replace")
    except urlerror.HTTPError as error:
        status = getattr(error, "code", None)
        _reject("web_search_failed", "http_error", status=status)
    except urlerror.URLError as error:
        _reject("web_search_failed", "network_error", detail=str(error.reason)[:200])
    try:
        payload = json.loads(body)
    except ValueError as error:
        _reject("web_search_failed", "response_invalid", detail=str(error)[:120])
    if not isinstance(payload, dict):
        _reject("web_search_failed", "payload_not_object")
    return payload


def _bounded_text(value: Any, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:limit]


def search_tavily(
    api_key: str,
    query: str,
    *,
    max_results: int = 8,
    opener: Opener = urlrequest.urlopen,
) -> list[JsonObject]:
    """Search via api.tavily.com and return normalized `{title,url,snippet}` hits."""

    cleaned = _validate_query(query)
    payload = json.dumps(
        {"query": cleaned, "max_results": max_results, "search_depth": "basic"},
        ensure_ascii=False,
    ).encode("utf-8")
    request = urlrequest.Request(
        _TAVILY_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "knowledge-tree-agent",
        },
        method="POST",
    )
    body = _read_json(request, opener)
    results = body.get("results")
    if not isinstance(results, list):
        _reject("web_search_failed", "results_missing")
    hits: list[JsonObject] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        url = _bounded_text(item.get("url"), 500)
        if not url.startswith("https://"):
            continue
        hits.append(
            {
                "title": _bounded_text(item.get("title"), 200) or "(untitled)",
                "url": url,
                "snippet": _bounded_text(item.get("content"), 1000),
            }
        )
    return hits


def search_brave(
    api_key: str,
    query: str,
    *,
    max_results: int = 8,
    opener: Opener = urlrequest.urlopen,
) -> list[JsonObject]:
    """Search via api.search.brave.com and return normalized hits."""

    cleaned = _validate_query(query)
    url = f"{_BRAVE_URL}?{urlparse.urlencode({'q': cleaned, 'count': max_results})}"
    request = urlrequest.Request(
        url,
        headers={
            "X-Subscription-Token": api_key,
            "Accept": "application/json",
            "User-Agent": "knowledge-tree-agent",
        },
        method="GET",
    )
    body = _read_json(request, opener)
    web = body.get("web")
    results = web.get("results") if isinstance(web, dict) else None
    if not isinstance(results, list):
        _reject("web_search_failed", "results_missing")
    hits: list[JsonObject] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        url = _bounded_text(item.get("url"), 500)
        if not url.startswith("https://"):
            continue
        hits.append(
            {
                "title": _bounded_text(item.get("title"), 200) or "(untitled)",
                "url": url,
                "snippet": _bounded_text(item.get("description"), 1000),
            }
        )
    return hits


def build_searcher(provider: str, api_key: str) -> Callable[[str], list[JsonObject]]:
    """Bind a provider + key into a plain `query -> hits` callable."""

    if provider == "tavily":
        return lambda query: search_tavily(api_key, query)
    if provider == "brave":
        return lambda query: search_brave(api_key, query)
    _reject("web_search_invalid_provider", "provider_unknown", provider=provider)
