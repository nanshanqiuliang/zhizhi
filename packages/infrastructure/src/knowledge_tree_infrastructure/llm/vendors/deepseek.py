"""DeepSeek vendor profile and concrete adapter (WORK-2026-008).

Wraps the OpenAI Chat Completions protocol adapter with DeepSeek-specific
policy: stable endpoint, explicit `thinking.type`, reasoning_content replay
for tool rounds, HTTP error mapping, and bounded retry/backoff/circuit-breaker
wiring. API keys are only accepted via the constructor (composition root).
"""

from __future__ import annotations

import time
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any
from urllib import error as urlerror

from ..canonical import GenerationRequest, GenerationResult
from ..capabilities import capability_fingerprint
from ..errors import LLMProviderError
from ..http_client import HttpJsonClient, HttpTransportError
from ..mock import LlmStreamEvent
from ..protocols.openai_chat import build_chat_request, parse_chat_response, sse_stream_events
from ..resilience import CircuitBreaker, CostBudget, Pricing

JsonObject = dict[str, Any]

_RETRYABLE_CODES = {
    "provider_rate_limited",
    "provider_unavailable",
    "provider_connection_failed",
    "provider_timeout",
}
_IMMEDIATE_OPEN_CODES = {"provider_auth_failed", "provider_balance_exhausted"}


def map_deepseek_http_error(error: HttpTransportError) -> LLMProviderError:
    """Map a DeepSeek HTTP status to the canonical stable error code (baseline 4.6)."""

    status = error.status
    if status in (401, 403):
        return LLMProviderError(
            "provider_auth_failed", details={"rule": "http_status", "status": status}
        )
    if status == 402:
        return LLMProviderError(
            "provider_balance_exhausted", details={"rule": "http_status", "status": status}
        )
    if status == 429:
        return LLMProviderError(
            "provider_rate_limited", details={"rule": "http_status", "status": status}
        )
    if status in (500, 503):
        return LLMProviderError(
            "provider_unavailable", details={"rule": "http_status", "status": status}
        )
    if status in (400, 422):
        return LLMProviderError(
            "provider_invalid_request", details={"rule": "http_status", "status": status}
        )
    return LLMProviderError(
        "provider_unknown_error", details={"rule": "http_status", "status": status}
    )


@dataclass(frozen=True, slots=True)
class DeepSeekConfig:
    """Non-sensitive deployment snapshot; secrets never live here."""

    base_url: str = "https://api.deepseek.com"
    chat_path: str = "/chat/completions"
    model_id: str = "deepseek-v4-flash"
    connect_timeout_s: float = 10.0
    read_timeout_s: float = 120.0
    max_network_attempts: int = 3
    retry_backoff_ms: tuple[int, ...] = (500, 1000, 2000)
    pricing: Pricing | None = None


def _extract_reasoning_content(payload: Mapping[str, Any]) -> str | None:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    message = first.get("message") if isinstance(first, dict) else None
    if not isinstance(message, dict):
        return None
    content = message.get("reasoning_content")
    return str(content) if isinstance(content, str) and content else None


class DeepSeekLlmAdapter:
    """Concrete DeepSeek adapter over the OpenAI Chat Completions protocol."""

    provider_id = "deepseek"
    protocol = "openai_chat_completions"

    def __init__(
        self,
        *,
        api_key: str,
        config: DeepSeekConfig | None = None,
        http: HttpJsonClient | None = None,
        capabilities: Mapping[str, bool] | None = None,
        breaker: CircuitBreaker | None = None,
    ) -> None:
        self._config = config or DeepSeekConfig()
        self._http = http or HttpJsonClient(
            base_url=self._config.base_url,
            api_key=api_key,
            read_timeout_s=self._config.read_timeout_s,
        )
        self._capabilities = dict(capabilities or {})
        self._breaker = (
            breaker
            if breaker is not None
            else CircuitBreaker(failure_threshold=3, open_seconds=30.0)
        )
        self._reasoning: dict[str, str] = {}

    def _snapshot(self) -> str:
        return capability_fingerprint(self._capabilities)

    def _attempt(
        self, request: GenerationRequest, *, thinking: str | None, max_tokens: int
    ) -> GenerationResult:
        payload = build_chat_request(
            model_id=self._config.model_id,
            request=request,
            max_tokens=max_tokens,
            thinking=thinking,
            reasoning_continuation=self._reasoning.get(request.model_run_id),
        )
        raw = self._http.post_json(self._config.chat_path, payload)
        reasoning = _extract_reasoning_content(raw)
        if reasoning is not None:
            self._reasoning[request.model_run_id] = reasoning
        return parse_chat_response(
            raw,
            model_run_id=request.model_run_id,
            provider_id=self.provider_id,
            protocol=self.protocol,
            model_id=self._config.model_id,
            capability_snapshot=self._snapshot(),
        )

    def generate(
        self,
        request: GenerationRequest,
        *,
        thinking: str | None = "disabled",
        max_tokens: int | None = None,
    ) -> GenerationResult:
        """Non-streaming generation with bounded retry and circuit breaking."""

        if max_tokens is None:
            max_tokens = request.budget.max_output_tokens
        cost_budget = (
            CostBudget(max_cost_usd=request.budget.max_cost_usd, pricing=self._config.pricing)
            if self._config.pricing is not None and request.budget.max_cost_usd is not None
            else None
        )
        max_attempts = self._config.max_network_attempts
        backoffs = self._config.retry_backoff_ms
        last_error: LLMProviderError | None = None

        for attempt in range(max_attempts):
            if not self._breaker.allow_request():
                raise LLMProviderError("provider_unavailable", details={"rule": "circuit_open"})
            try:
                result = self._attempt(request, thinking=thinking, max_tokens=max_tokens)
                if cost_budget is not None:
                    cost_budget.record_usage(result.usage.input_tokens, result.usage.output_tokens)
                return result
            except HttpTransportError as http_error:
                error = map_deepseek_http_error(http_error)
                if error.code in _IMMEDIATE_OPEN_CODES:
                    self._breaker.open_immediately()
                    raise error from http_error
                if error.code not in _RETRYABLE_CODES:
                    raise error from http_error
                last_error = error
            except urlerror.URLError as url_error:
                reason = url_error.reason
                if isinstance(reason, TimeoutError):
                    last_error = LLMProviderError("provider_timeout", details={"rule": "timeout"})
                else:
                    last_error = LLMProviderError(
                        "provider_connection_failed", details={"rule": "connection"}
                    )
            self._breaker.record_failure()
            if attempt < max_attempts - 1 and backoffs:
                delay = backoffs[min(attempt, len(backoffs) - 1)]
                if delay:
                    time.sleep(delay / 1000.0)

        if last_error is not None:
            raise last_error
        raise LLMProviderError("provider_unknown_error", details={"rule": "no_attempts"})

    def stream(
        self,
        request: GenerationRequest,
        *,
        thinking: str | None = "disabled",
        max_tokens: int | None = None,
    ) -> Iterator[LlmStreamEvent]:
        """Streaming generation; a broken stream is never resumed mid-delta."""

        if max_tokens is None:
            max_tokens = request.budget.max_output_tokens
        payload = build_chat_request(
            model_id=self._config.model_id,
            request=request,
            max_tokens=max_tokens,
            thinking=thinking,
            stream=True,
            reasoning_continuation=self._reasoning.get(request.model_run_id),
        )
        try:
            lines = self._http.post_stream_lines(self._config.chat_path, payload)
        except HttpTransportError as http_error:
            raise map_deepseek_http_error(http_error) from http_error
        yield from sse_stream_events(lines)
