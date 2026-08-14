"""DeepSeek OpenAI Chat Completions adapter contract tests (WORK-2026-008).

Offline tests: OpenAI wire request/response/SSE serialization against the
canonical LLM contract, error mapping, and a fake-HTTP end-to-end adapter
test. No network, key or real provider is involved here; live smoke lives in
tests/e2e/test_deepseek_live_smoke.py behind RUN_LIVE_LLM_TESTS.
"""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from knowledge_tree_infrastructure.llm.canonical import (
    Budget,
    CanonicalMessage,
    CanonicalToolCall,
    ContentPart,
    GenerationRequest,
    ToolDefinition,
    TraceContext,
)
from knowledge_tree_infrastructure.llm.errors import LLMProviderError
from knowledge_tree_infrastructure.llm.http_client import HttpJsonClient, HttpTransportError
from knowledge_tree_infrastructure.llm.protocols.openai_chat import (
    build_chat_request,
    parse_chat_response,
    sse_stream_events,
)
from knowledge_tree_infrastructure.llm.resilience import CostBudget, Pricing, estimate_cost_usd
from knowledge_tree_infrastructure.llm.runner import ModelRunner
from knowledge_tree_infrastructure.llm.vendors.deepseek import (
    DeepSeekConfig,
    DeepSeekLlmAdapter,
    map_deepseek_http_error,
)

MODEL_RUN_ID = "00000000-0000-7000-8000-000000000001"
CORRELATION_ID = "00000000-0000-7000-8000-000000000002"


def make_request(**overrides: Any) -> GenerationRequest:
    request = GenerationRequest(
        model_run_id=MODEL_RUN_ID,
        task="concept_extract",
        messages=(
            CanonicalMessage(
                role="user",
                parts=(ContentPart(kind="text", value="解释极限的定义"),),
            ),
        ),
        model_policy="concept_extract",
        idempotency_key="idem-001",
        budget=Budget(max_attempts=2, max_output_tokens=4096),
        trace_context=TraceContext(correlation_id=CORRELATION_ID),
    )
    return replace(request, **overrides)


# ---------------------------------------------------------------------------
# TC-DS-001: OpenAI request serialization
# ---------------------------------------------------------------------------


def test_build_chat_request_serializes_messages_and_tools() -> None:
    request = make_request(
        tools=(
            ToolDefinition(
                name="search_notes", description="search", parameters={"type": "object"}
            ),
        )
    )

    payload = build_chat_request(
        model_id="deepseek-v4-flash",
        request=request,
        max_tokens=4096,
        thinking="disabled",
    )

    assert payload["model"] == "deepseek-v4-flash"
    assert payload["max_tokens"] == 4096
    assert payload["stream"] is False
    assert payload["thinking"] == {"type": "disabled"}
    assert payload["messages"] == [{"role": "user", "content": "解释极限的定义"}]
    assert payload["tools"][0]["type"] == "function"
    assert payload["tools"][0]["function"]["name"] == "search_notes"


def test_build_chat_request_json_mode_sets_response_format() -> None:
    request = make_request(output_schema={"type": "object", "required": ["concepts"]})

    payload = build_chat_request(
        model_id="deepseek-v4-flash", request=request, max_tokens=4096, thinking="disabled"
    )

    assert payload["response_format"] == {"type": "json_object"}


def test_build_chat_request_thinking_enabled_rejects_sampling() -> None:
    # The canonical request never carries sampling params; this asserts the
    # protocol adapter refuses a contradictory local override before sending.
    with pytest.raises(LLMProviderError) as raised:
        build_chat_request(
            model_id="deepseek-v4-pro",
            request=make_request(),
            max_tokens=8192,
            thinking="enabled",
            temperature=0.2,
        )
    assert raised.value.code == "provider_invalid_request"


def test_build_chat_request_tool_round_replays_reasoning_continuation() -> None:
    request = make_request(
        messages=(
            CanonicalMessage(
                role="assistant",
                parts=(ContentPart(kind="tool_call", value={"name": "search_notes"}),),
                tool_call_id="call-1",
            ),
            CanonicalMessage(
                role="tool",
                parts=(ContentPart(kind="tool_result", value={"ok": True}),),
                tool_call_id="call-1",
            ),
        )
    )

    payload = build_chat_request(
        model_id="deepseek-v4-pro",
        request=request,
        max_tokens=8192,
        thinking="enabled",
        reasoning_continuation="opaque-reasoning",
    )

    assistant = payload["messages"][0]
    assert assistant["role"] == "assistant"
    assert assistant["reasoning_content"] == "opaque-reasoning"


# ---------------------------------------------------------------------------
# TC-DS-002: OpenAI response mapping
# ---------------------------------------------------------------------------


def test_parse_chat_response_maps_text() -> None:
    result = parse_chat_response(
        {
            "id": "chatcmpl-123",
            "choices": [
                {"message": {"role": "assistant", "content": "极限是……"}, "finish_reason": "stop"}
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            "model": "deepseek-v4-flash",
        },
        model_run_id=MODEL_RUN_ID,
        provider_id="deepseek",
        protocol="openai_chat_completions",
        model_id="deepseek-v4-flash",
        capability_snapshot=None,
    )

    assert result.text == "极限是……"
    assert result.usage.input_tokens == 10
    assert result.usage.output_tokens == 5
    assert result.finish_reason == "stop"
    assert result.provider_response_id == "chatcmpl-123"


def test_parse_chat_response_maps_tool_calls() -> None:
    result = parse_chat_response(
        {
            "id": "chatcmpl-124",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "type": "function",
                                "function": {"name": "search_notes", "arguments": '{"q":"极限"}'},
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            "model": "deepseek-v4-flash",
        },
        model_run_id=MODEL_RUN_ID,
        provider_id="deepseek",
        protocol="openai_chat_completions",
        model_id="deepseek-v4-flash",
        capability_snapshot=None,
    )

    assert result.finish_reason == "tool_calls"
    assert result.tool_calls == (
        CanonicalToolCall(id="call-1", name="search_notes", arguments={"q": "极限"}),
    )


def test_parse_chat_response_maps_finish_reason_length() -> None:
    result = parse_chat_response(
        {
            "id": "chatcmpl-125",
            "choices": [
                {
                    "message": {"role": "assistant", "content": '{"concepts": ['},
                    "finish_reason": "length",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 128},
            "model": "deepseek-v4-flash",
        },
        model_run_id=MODEL_RUN_ID,
        provider_id="deepseek",
        protocol="openai_chat_completions",
        model_id="deepseek-v4-flash",
        capability_snapshot=None,
    )

    assert result.finish_reason == "length"
    assert result.text == '{"concepts": ['


# ---------------------------------------------------------------------------
# TC-DS-003: SSE stream parsing
# ---------------------------------------------------------------------------


def test_sse_stream_parses_deltas_reasoning_and_done() -> None:
    reasoning = (
        'data: {"choices":[{"delta":{"role":"assistant",'
        '"reasoning_content":"想"},"finish_reason":null}]}'
    )
    lines = [
        reasoning,
        "",
        'data: {"choices":[{"delta":{"content":"极"},"finish_reason":null}]}',
        ": keep-alive",
        'data: {"choices":[{"delta":{"content":"限"},"finish_reason":null}]}',
        'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}',
        "data: [DONE]",
    ]

    events = list(sse_stream_events(lines))

    assert [event.type for event in events] == [
        "response.started",
        "text.delta",
        "text.delta",
        "response.completed",
    ]
    assert [event.text for event in events if event.type == "text.delta"] == ["极", "限"]
    assert events[-1].finish_reason == "stop"


def test_sse_stream_break_reports_stream_incomplete() -> None:
    lines = ['data: {"choices":[{"delta":{"content":"{\\"concepts\\": ["},"finish_reason":null}]}']

    with pytest.raises(LLMProviderError) as raised:
        list(sse_stream_events(lines))
    assert raised.value.code == "provider_stream_incomplete"


# ---------------------------------------------------------------------------
# TC-DS-004: HTTP error mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (400, "provider_invalid_request"),
        (401, "provider_auth_failed"),
        (402, "provider_balance_exhausted"),
        (403, "provider_auth_failed"),
        (422, "provider_invalid_request"),
        (429, "provider_rate_limited"),
        (500, "provider_unavailable"),
        (503, "provider_unavailable"),
    ],
)
def test_map_deepseek_http_error(status: int, code: str) -> None:
    error = map_deepseek_http_error(HttpTransportError(status=status, body='{"error":{}}'))

    assert error.code == code


# ---------------------------------------------------------------------------
# TC-DS-005 + adapter end-to-end with a fake HTTP client
# ---------------------------------------------------------------------------


class _FakeHttp:
    """Records requests and returns scripted responses without any network."""

    def __init__(self, responses: list[Any]) -> None:
        self._responses = list(responses)
        self.requests: list[tuple[str, dict[str, Any]]] = []

    def post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.requests.append((path, payload))
        response = self._responses.pop(0)
        if isinstance(response, HttpTransportError):
            raise response
        return response

    def post_stream_lines(self, path: str, payload: dict[str, Any]) -> list[str]:
        self.requests.append((path, payload))
        response = self._responses.pop(0)
        if isinstance(response, HttpTransportError):
            raise response
        return response


def _ok_response() -> dict[str, Any]:
    return {
        "id": "chatcmpl-200",
        "choices": [
            {"message": {"role": "assistant", "content": "极限是……"}, "finish_reason": "stop"}
        ],
        "usage": {"prompt_tokens": 11, "completion_tokens": 6},
        "model": "deepseek-v4-flash",
    }


def test_adapter_generate_end_to_end() -> None:
    fake = _FakeHttp([_ok_response()])
    adapter = DeepSeekLlmAdapter(
        api_key="test-key", http=fake, config=DeepSeekConfig(model_id="deepseek-v4-flash")
    )

    result = adapter.generate(make_request(), thinking="disabled")

    assert result.text == "极限是……"
    assert result.provider == "deepseek"
    assert result.protocol == "openai_chat_completions"
    assert fake.requests[0][0] == "/chat/completions"
    sent = fake.requests[0][1]
    assert sent["model"] == "deepseek-v4-flash"
    assert "Authorization" not in sent  # auth goes in the header, not the body


def test_adapter_retries_then_succeeds_on_429() -> None:
    fake = _FakeHttp([HttpTransportError(status=429, body="{}"), _ok_response()])
    adapter = DeepSeekLlmAdapter(
        api_key="test-key",
        http=fake,
        config=DeepSeekConfig(
            model_id="deepseek-v4-flash",
            max_network_attempts=2,
            retry_backoff_ms=(0, 0),  # no sleep in tests
        ),
    )

    result = adapter.generate(make_request(), thinking="disabled")

    assert result.text == "极限是……"
    assert len(fake.requests) == 2


def test_adapter_does_not_retry_on_401() -> None:
    fake = _FakeHttp([HttpTransportError(status=401, body="{}")])
    adapter = DeepSeekLlmAdapter(
        api_key="test-key",
        http=fake,
        config=DeepSeekConfig(
            model_id="deepseek-v4-flash", max_network_attempts=3, retry_backoff_ms=(0, 0)
        ),
    )

    with pytest.raises(LLMProviderError) as raised:
        adapter.generate(make_request(), thinking="disabled")
    assert raised.value.code == "provider_auth_failed"
    assert len(fake.requests) == 1


def test_fixtures_do_not_contain_secret_patterns() -> None:
    source = Path(__file__).read_text(encoding="utf-8")
    assert re.search(r"sk-[A-Za-z0-9]{16,}", source) is None


# ---------------------------------------------------------------------------
# Monetary budget (max_cost_usd)
# ---------------------------------------------------------------------------


def test_estimate_cost_usd_computes_expected() -> None:
    pricing = Pricing(input_usd_per_mtok=0.28, output_usd_per_mtok=1.14)

    assert estimate_cost_usd(1_000_000, 1_000_000, pricing) == pytest.approx(1.42)
    assert estimate_cost_usd(0, 0, pricing) == 0.0


def test_cost_budget_raises_when_exceeded() -> None:
    budget = CostBudget(
        max_cost_usd=0.01, pricing=Pricing(input_usd_per_mtok=0.28, output_usd_per_mtok=1.14)
    )

    budget.record_usage(1000, 0)  # ~0.00028, under budget
    with pytest.raises(LLMProviderError) as raised:
        budget.record_usage(0, 10000)  # ~0.0114, exceeds 0.01
    assert raised.value.code == "budget_exceeded"


def test_adapter_enforces_cost_budget() -> None:
    fake = _FakeHttp([_ok_response()])
    adapter = DeepSeekLlmAdapter(
        api_key="test-key",
        http=fake,
        config=DeepSeekConfig(
            model_id="deepseek-v4-flash",
            pricing=Pricing(input_usd_per_mtok=0.28, output_usd_per_mtok=1.14),
        ),
    )
    request = make_request(
        budget=Budget(max_attempts=2, max_output_tokens=4096, max_cost_usd=0.000001)
    )

    with pytest.raises(LLMProviderError) as raised:
        adapter.generate(request, thinking="disabled")
    assert raised.value.code == "budget_exceeded"


# ---------------------------------------------------------------------------
# ModelRunner fallback
# ---------------------------------------------------------------------------


def _adapter(responses: list[Any]) -> DeepSeekLlmAdapter:
    return DeepSeekLlmAdapter(
        api_key="test-key",
        http=_FakeHttp(responses),
        config=DeepSeekConfig(model_id="deepseek-v4-flash", max_network_attempts=1),
    )


def test_runner_falls_back_on_rate_limited() -> None:
    primary = _adapter([HttpTransportError(status=429, body="{}")])
    secondary = _adapter([_ok_response()])
    runner = ModelRunner(
        adapters=[primary, secondary],
        allowed_fallback_codes=["provider_rate_limited", "provider_unavailable"],
    )

    result = runner.generate(
        make_request(budget=Budget(max_attempts=2, max_output_tokens=4096, max_fallbacks=1)),
        thinking="disabled",
    )

    assert result.text == "极限是……"


def test_runner_does_not_fall_back_on_auth_failed() -> None:
    primary = _adapter([HttpTransportError(status=401, body="{}")])
    secondary = _adapter([_ok_response()])
    runner = ModelRunner(
        adapters=[primary, secondary],
        allowed_fallback_codes=["provider_rate_limited"],
    )

    with pytest.raises(LLMProviderError) as raised:
        runner.generate(make_request(), thinking="disabled")
    assert raised.value.code == "provider_auth_failed"


def test_runner_raises_when_all_adapters_fail() -> None:
    primary = _adapter([HttpTransportError(status=429, body="{}")])
    secondary = _adapter([HttpTransportError(status=503, body="{}")])
    runner = ModelRunner(
        adapters=[primary, secondary],
        allowed_fallback_codes=["provider_rate_limited", "provider_unavailable"],
    )

    with pytest.raises(LLMProviderError) as raised:
        runner.generate(
            make_request(
                budget=Budget(max_attempts=2, max_output_tokens=4096, max_fallbacks=1)
            ),
            thinking="disabled",
        )
    assert raised.value.code == "provider_unavailable"


# ---------------------------------------------------------------------------
# Review-fix regressions (monetary budget, retry cap, protocol robustness)
# ---------------------------------------------------------------------------


def test_monetary_budget_requires_pricing() -> None:
    adapter = _adapter([_ok_response()])  # config has no pricing
    request = make_request(
        budget=Budget(max_attempts=2, max_output_tokens=4096, max_cost_usd=0.01)
    )

    with pytest.raises(LLMProviderError) as raised:
        adapter.generate(request, thinking="disabled")
    assert raised.value.code == "provider_config_invalid"


def test_adapter_respects_request_max_attempts() -> None:
    fake = _FakeHttp(
        [HttpTransportError(status=429, body="{}"), _ok_response()]
    )
    adapter = DeepSeekLlmAdapter(
        api_key="test-key",
        http=fake,
        config=DeepSeekConfig(model_id="deepseek-v4-flash", retry_backoff_ms=(0, 0)),
    )
    request = make_request(budget=Budget(max_attempts=1, max_output_tokens=4096))

    with pytest.raises(LLMProviderError) as raised:
        adapter.generate(request, thinking="disabled")
    assert raised.value.code == "provider_rate_limited"
    assert len(fake.requests) == 1  # no retry beyond the request budget


def test_runner_respects_max_fallbacks_zero() -> None:
    primary = _adapter([HttpTransportError(status=429, body="{}")])
    secondary = _adapter([_ok_response()])
    runner = ModelRunner(
        adapters=[primary, secondary],
        allowed_fallback_codes=["provider_rate_limited"],
    )

    with pytest.raises(LLMProviderError) as raised:
        runner.generate(make_request(), thinking="disabled")
    assert raised.value.code == "provider_rate_limited"


def test_parse_chat_response_rejects_negative_tokens() -> None:
    with pytest.raises(LLMProviderError) as raised:
        parse_chat_response(
            {
                "id": "chatcmpl-300",
                "choices": [
                    {"message": {"role": "assistant", "content": "x"}, "finish_reason": "stop"}
                ],
                "usage": {"prompt_tokens": -1, "completion_tokens": 5},
                "model": "deepseek-v4-flash",
            },
            model_run_id=MODEL_RUN_ID,
            provider_id="deepseek",
            protocol="openai_chat_completions",
            model_id="deepseek-v4-flash",
            capability_snapshot=None,
        )
    assert raised.value.code == "provider_protocol_mismatch"


def test_parse_chat_response_rejects_missing_finish_reason() -> None:
    with pytest.raises(LLMProviderError) as raised:
        parse_chat_response(
            {
                "id": "chatcmpl-301",
                "choices": [{"message": {"role": "assistant", "content": "x"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                "model": "deepseek-v4-flash",
            },
            model_run_id=MODEL_RUN_ID,
            provider_id="deepseek",
            protocol="openai_chat_completions",
            model_id="deepseek-v4-flash",
            capability_snapshot=None,
        )
    assert raised.value.code == "provider_protocol_mismatch"


def test_http_client_rejects_http_base_url() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        HttpJsonClient(base_url="http://api.deepseek.com", api_key="test-key")
