"""DeepSeek live smoke tests (WORK-2026-008, roadmap Step 7 order 7).

These tests call the real DeepSeek API and therefore run ONLY when both
`RUN_LIVE_LLM_TESTS=1` and `DEEPSEEK_API_KEY` are set in the environment.
They use minimal `max_tokens` so the total spend stays far below the owner's
3 CNY test budget. The API key is never hard-coded, logged, or committed.

DeepSeek V4 thinking mode spends tokens on `reasoning_content` first, so a
small `max_tokens` can legitimately end with `finish_reason=length` and empty
`content`; the thinking smoke therefore only asserts connectivity and usage.
"""

from __future__ import annotations

import os
from typing import Any

import pytest
from knowledge_tree_infrastructure.llm.canonical import (
    Budget,
    CanonicalMessage,
    ContentPart,
    GenerationRequest,
    ToolDefinition,
    TraceContext,
)
from knowledge_tree_infrastructure.llm.vendors.deepseek import DeepSeekConfig, DeepSeekLlmAdapter

_RUN_LIVE = os.environ.get("RUN_LIVE_LLM_TESTS") == "1"

pytestmark = pytest.mark.skipif(
    not _RUN_LIVE,
    reason="live DeepSeek smoke requires RUN_LIVE_LLM_TESTS=1 and DEEPSEEK_API_KEY",
)

_MODEL_RUN_ID = "00000000-0000-7000-8000-000000000011"
_CORRELATION_ID = "00000000-0000-7000-8000-000000000012"


def _api_key() -> str:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        pytest.skip("DEEPSEEK_API_KEY not set")
    return key


def _request(
    model_run_id: str, *, task: str = "concept_extract", **overrides: Any
) -> GenerationRequest:
    request = GenerationRequest(
        model_run_id=model_run_id,
        task=task,
        messages=(
            CanonicalMessage(
                role="user",
                parts=(ContentPart(kind="text", value="用一句话解释微积分中极限的定义。"),),
            ),
        ),
        model_policy=task,
        idempotency_key=f"live-{model_run_id}",
        budget=Budget(max_attempts=1, max_output_tokens=64),
        trace_context=TraceContext(correlation_id=_CORRELATION_ID),
    )
    for key, value in overrides.items():
        object.__setattr__(request, key, value)
    return request


def _report(usage: Any) -> None:
    print(f"    [usage] input={usage.input_tokens} output={usage.output_tokens}")


def test_live_text_generation() -> None:
    adapter = DeepSeekLlmAdapter(
        api_key=_api_key(), config=DeepSeekConfig(model_id="deepseek-v4-flash")
    )

    result = adapter.generate(_request(_MODEL_RUN_ID), thinking="disabled", max_tokens=64)

    assert result.text
    assert result.usage.input_tokens > 0
    assert result.usage.output_tokens > 0
    assert result.finish_reason in {"stop", "length"}
    _report(result.usage)


def test_live_json_object_output() -> None:
    adapter = DeepSeekLlmAdapter(
        api_key=_api_key(), config=DeepSeekConfig(model_id="deepseek-v4-flash")
    )
    request = _request(
        "00000000-0000-7000-8000-000000000013",
        messages=(
            CanonicalMessage(
                role="user",
                parts=(
                    ContentPart(
                        kind="text", value='以 JSON 对象输出：{"concept": "极限", "summary": "..."}'
                    ),
                ),
            ),
        ),
        output_schema={"type": "object", "required": ["concept", "summary"]},
    )

    result = adapter.generate(request, thinking="disabled", max_tokens=128)

    assert result.text
    assert "concept" in result.text
    assert result.finish_reason in {"stop", "length"}
    _report(result.usage)


def test_live_thinking_generation() -> None:
    adapter = DeepSeekLlmAdapter(
        api_key=_api_key(), config=DeepSeekConfig(model_id="deepseek-v4-pro")
    )

    result = adapter.generate(
        _request("00000000-0000-7000-8000-000000000014"), thinking="enabled", max_tokens=256
    )

    # reasoning_content may consume the whole budget; connectivity + usage matter here.
    assert result.usage.output_tokens > 0
    assert result.finish_reason in {"stop", "length"}
    _report(result.usage)


def test_live_tool_call() -> None:
    adapter = DeepSeekLlmAdapter(
        api_key=_api_key(), config=DeepSeekConfig(model_id="deepseek-v4-flash")
    )
    request = _request(
        "00000000-0000-7000-8000-000000000015",
        tools=(
            ToolDefinition(
                name="search_notes",
                description="检索笔记中的概念定义",
                parameters={"type": "object", "properties": {"q": {"type": "string"}}},
            ),
        ),
    )

    result = adapter.generate(request, thinking="disabled", max_tokens=64)

    # The model may answer directly or call the tool; both are valid smoke outcomes.
    assert result.text or result.tool_calls
    assert result.usage.output_tokens > 0
    _report(result.usage)


def test_live_stream_generation() -> None:
    adapter = DeepSeekLlmAdapter(
        api_key=_api_key(), config=DeepSeekConfig(model_id="deepseek-v4-flash")
    )

    events = list(adapter.stream(_request(_MODEL_RUN_ID), thinking="disabled", max_tokens=32))

    assert events[0].type == "response.started"
    assert any(event.type == "text.delta" and event.text for event in events)
    assert events[-1].type == "response.completed"
