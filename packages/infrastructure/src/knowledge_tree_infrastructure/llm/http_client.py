"""Minimal stdlib HTTP/SSE transport for the LLM port (WORK-2026-008).

No third-party SDK or dependency: `urllib.request` only. Non-2xx responses
raise `HttpTransportError`; connection/timeout errors bubble up as
`urllib.error.URLError` so the vendor profile can map them to stable error
codes. API keys are only ever passed into the constructor and never logged.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any, cast
from urllib import error as urlerror
from urllib import request as urlrequest

JsonObject = dict[str, Any]


class HttpTransportError(Exception):
    """A non-2xx HTTP response carrying only the status and bounded body text."""

    def __init__(self, status: int | None, body: str | None = None) -> None:
        self.status = status
        self.body = body
        super().__init__(f"http transport error: status={status}")


class HttpJsonClient:
    """POST JSON to a JSON/SSE endpoint and return parsed data or raw lines."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        read_timeout_s: float = 120.0,
        user_agent: str = "knowledge-tree-agent",
    ) -> None:
        if not base_url.startswith("https://"):
            raise ValueError("base_url must use HTTPS; refusing to send a bearer key in cleartext")
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._read_timeout_s = read_timeout_s
        self._user_agent = user_agent

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": self._user_agent,
        }

    def _request(self, path: str, payload: JsonObject) -> urlrequest.Request:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        return urlrequest.Request(
            f"{self._base_url}{path}",
            data=data,
            headers=self._headers(),
            method="POST",
        )

    def post_json(self, path: str, payload: JsonObject) -> JsonObject:
        """POST and return the parsed JSON response body."""

        request = self._request(path, payload)
        try:
            with urlrequest.urlopen(request, timeout=self._read_timeout_s) as response:
                body = response.read().decode("utf-8")
        except urlerror.HTTPError as error:
            body = error.read().decode("utf-8", "replace") if error.fp else None
            raise HttpTransportError(status=error.code, body=body) from error
        return cast(JsonObject, json.loads(body))

    def post_stream_lines(self, path: str, payload: JsonObject) -> Iterator[str]:
        """POST and yield decoded response lines (for SSE parsing)."""

        request = self._request(path, payload)
        try:
            with urlrequest.urlopen(request, timeout=self._read_timeout_s) as response:
                for raw in response:
                    yield raw.decode("utf-8", "replace")
        except urlerror.HTTPError as error:
            body = error.read().decode("utf-8", "replace") if error.fp else None
            raise HttpTransportError(status=error.code, body=body) from error
