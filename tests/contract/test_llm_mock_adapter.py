"""Mock LLM provider adapter and resilience contract tests (WORK-2026-007).

Covers TC-LLM-002..009 in offline/mock mode per LLM-COMPAT-BASELINE-001:
streaming events, tool calls, thinking reasoning-state replay, error
mapping, retry/backoff/budget/circuit, idempotency, redaction and
capability/config validation. No real Provider, network, key or budget is
ever touched.
"""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from knowledge_tree_contracts import validate_llm_contract
from knowledge_tree_contracts.llm_v1 import CAPABILITY_NAMES
from knowledge_tree_infrastructure.llm.canonical import (
    Budget,
    CanonicalMessage,
    CanonicalToolCall,
    ContentPart,
    GenerationRequest,
    TraceContext,
    request_from_dict,
    request_to_dict,
    result_from_dict,
    result_to_dict,
    validate_typed_output,
)
from knowledge_tree_infrastructure.llm.capabilities import (
    capability_fingerprint,
    check_required_capabilities,
)
from knowledge_tree_infrastructure.llm.errors import LLMProviderError
from knowledge_tree_infrastructure.llm.mock import (
    MockContinuationStore,
    MockLlmAdapter,
    MockScript,
)
from knowledge_tree_infrastructure.llm.resilience import (
    AttemptBudget,
    CircuitBreaker,
    backoff_sequence,
)
from knowledge_tree_infrastructure.llm.router import (
    resolve_deployment,
    select_deployment,
)

MODEL_RUN_ID = "00000000-0000-7000-8000-000000000001"
CORRELATION_ID = "00000000-0000-7000-8000-000000000002"
OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["concepts"],
    "properties": {"concepts": {"type": "array"}},
    "additionalProperties": False,
}


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
        output_schema=OUTPUT_SCHEMA,
    )
    return replace(request, **overrides)


def make_adapter(**overrides: Any) -> MockLlmAdapter:
    capabilities = {name: False for name in CAPABILITY_NAMES}
    capabilities.update({"text_input": True, "text_output": True, "json_object": True})
    return MockLlmAdapter(capabilities=capabilities, **overrides)


# ---------------------------------------------------------------------------
# TC-LLM-001: canonical message/role/content mapping (offline part)
# ---------------------------------------------------------------------------


def test_request_dict_round_trip() -> None:
    request = make_request()
    payload = request_to_dict(request)

    validate_llm_contract("generation_request", payload)
    assert request_from_dict(payload) == request


def test_result_dict_round_trip() -> None:
    result = make_adapter().generate(make_request(), MockScript(text="极限是……"))
    payload = result_to_dict(result)

    validate_llm_contract("generation_result", payload)
    assert result_from_dict(payload) == result


def test_invalid_role_rejected_at_dto_boundary() -> None:
    with pytest.raises(LLMProviderError) as raised:
        request_from_dict(
            {
                "schema_version": 1,
                "model_run_id": MODEL_RUN_ID,
                "task": "concept_extract",
                "messages": [{"role": "admin", "parts": []}],
                "output_schema": None,
                "tools": [],
                "model_policy": "concept_extract",
                "idempotency_key": "idem-001",
                "budget": {"max_attempts": 2, "max_output_tokens": 4096},
                "trace_context": {"correlation_id": CORRELATION_ID},
            }
        )
    assert raised.value.code == "provider_invalid_request"


def test_mock_generate_returns_contract_valid_result() -> None:
    result = make_adapter().generate(make_request(), MockScript(text="极限是……"))

    validate_llm_contract("generation_result", result_to_dict(result))
    assert result.text == "极限是……"
    assert result.provider == "mock"
    assert result.protocol == "mock"
    assert result.finish_reason == "stop"


# ---------------------------------------------------------------------------
# TC-LLM-002: JSON object + local schema success/failure/truncation/blank
# ---------------------------------------------------------------------------


def test_typed_output_validates_against_local_schema() -> None:
    result = make_adapter().generate(
        make_request(), MockScript(typed_output={"concepts": ["极限", "连续"]})
    )

    validate_typed_output(result.typed_output, OUTPUT_SCHEMA)


def test_truncated_json_text_fails_schema_as_provider_schema_failed() -> None:
    adapter = make_adapter()
    result = adapter.generate(
        make_request(), MockScript(text='{"concepts": [', finish_reason="length")
    )

    with pytest.raises(LLMProviderError) as raised:
        validate_typed_output(result.text, OUTPUT_SCHEMA)
    assert raised.value.code == "provider_schema_failed"


def test_blank_json_output_fails_schema_as_provider_schema_failed() -> None:
    result = make_adapter().generate(make_request(), MockScript(text="   "))

    with pytest.raises(LLMProviderError) as raised:
        validate_typed_output(result.text, OUTPUT_SCHEMA)
    assert raised.value.code == "provider_schema_failed"


# ---------------------------------------------------------------------------
# TC-LLM-003: streaming event sequence / heartbeat / break / cancel
# ---------------------------------------------------------------------------


def test_stream_event_sequence() -> None:
    events = list(
        make_adapter().stream(make_request(), MockScript(stream_deltas=("极", "限", "是")))
    )

    assert [event.type for event in events] == [
        "response.started",
        "text.delta",
        "text.delta",
        "text.delta",
        "usage.updated",
        "response.completed",
    ]
    assert [event.text for event in events if event.type == "text.delta"] == ["极", "限", "是"]
    assert events[-1].finish_reason == "stop"


def test_stream_heartbeat_is_tolerated() -> None:
    events = list(
        make_adapter().stream(
            make_request(),
            MockScript(stream_deltas=("A",), stream_extra_events=("heartbeat",)),
        )
    )

    assert any(event.type == "heartbeat" for event in events)
    assert events[-1].type == "response.completed"


def test_stream_break_reports_stream_incomplete() -> None:
    events = list(
        make_adapter().stream(
            make_request(),
            MockScript(stream_deltas=("A",), stream_extra_events=("break",)),
        )
    )

    assert events[-1].type == "response.failed"
    assert events[-1].error_code == "provider_stream_incomplete"


def test_stream_cancel_raises_model_run_cancelled() -> None:
    adapter = make_adapter()

    with pytest.raises(LLMProviderError) as raised:
        list(
            adapter.stream(
                make_request(),
                MockScript(stream_deltas=("A",), stream_extra_events=("cancel",)),
            )
        )
    assert raised.value.code == "model_run_cancelled"


# ---------------------------------------------------------------------------
# TC-LLM-004: tool calls, results and duplicate-call protection
# ---------------------------------------------------------------------------


def test_tool_call_event_order() -> None:
    tool_call = CanonicalToolCall(id="call-1", name="search_notes", arguments={"q": "极限"})
    events = list(
        make_adapter().stream(
            make_request(), MockScript(tool_calls=(tool_call,), stream_deltas=("A",))
        )
    )

    kinds = [event.type for event in events]
    assert kinds.index("tool_call.started") < kinds.index("tool_call.arguments.delta")
    assert kinds.index("tool_call.arguments.delta") < kinds.index("tool_call.completed")
    assert kinds.index("tool_call.completed") < kinds.index("usage.updated")
    completed = next(event for event in events if event.type == "tool_call.completed")
    assert completed.tool_call == tool_call


def test_duplicate_tool_call_id_is_rejected() -> None:
    adapter = make_adapter()
    tool_calls = (
        CanonicalToolCall(id="call-1", name="search_notes", arguments={"q": "极限"}),
        CanonicalToolCall(id="call-1", name="read_page", arguments={"page": 1}),
    )

    with pytest.raises(LLMProviderError) as raised:
        adapter.generate(make_request(), MockScript(tool_calls=tool_calls))
    assert raised.value.code == "provider_protocol_mismatch"


# ---------------------------------------------------------------------------
# TC-LLM-005: thinking + tool reasoning-state replay
# ---------------------------------------------------------------------------


def test_thinking_round_preserves_continuation_state() -> None:
    store = MockContinuationStore()
    adapter = MockLlmAdapter(continuation_store=store)

    first = adapter.generate(make_request(), MockScript(text="思考中", thinking=True))
    assert store.contains(first.model_run_id)

    second = adapter.generate(
        make_request(idempotency_key="idem-002"),
        MockScript(text="tool 轮", thinking=True, requires_continuation=True),
    )
    assert second.text == "tool 轮"


def test_continuation_lost_when_reasoning_state_missing() -> None:
    adapter = make_adapter()  # fresh empty store

    with pytest.raises(LLMProviderError) as raised:
        adapter.generate(
            make_request(idempotency_key="idem-002"),
            MockScript(thinking=True, requires_continuation=True),
        )
    assert raised.value.code == "provider_continuation_lost"


def test_reasoning_content_never_appears_in_result() -> None:
    result = make_adapter().generate(make_request(), MockScript(text="答案", thinking=True))

    payload = result_to_dict(result)
    assert "reasoning" not in payload
    assert "reasoning_content" not in str(payload)


# ---------------------------------------------------------------------------
# TC-LLM-006: stable error mapping for injected failures
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "failure_code",
    [
        "provider_invalid_request",
        "provider_continuation_lost",
        "provider_auth_failed",
        "provider_balance_exhausted",
        "provider_rate_limited",
        "provider_unavailable",
        "provider_connection_failed",
        "provider_timeout",
        "provider_schema_failed",
        "provider_protocol_mismatch",
    ],
)
def test_injected_failures_map_to_stable_error_codes(failure_code: str) -> None:
    adapter = make_adapter()

    with pytest.raises(LLMProviderError) as raised:
        adapter.generate(make_request(), MockScript(failure=failure_code))
    assert raised.value.code == failure_code


# ---------------------------------------------------------------------------
# TC-LLM-007: retry/backoff/circuit/budget/idempotency
# ---------------------------------------------------------------------------


def test_backoff_sequence_is_deterministic_and_capped() -> None:
    first = backoff_sequence(max_attempts=3, base_ms=500, cap_ms=2000)
    second = backoff_sequence(max_attempts=3, base_ms=500, cap_ms=2000)

    assert first == second
    assert len(first) == 3
    assert all(0 <= value <= 2000 for value in first)


def test_attempt_budget_exhaustion_raises_budget_exceeded() -> None:
    budget = AttemptBudget(max_attempts=2, max_latency_ms=None)
    budget.record_attempt()
    budget.record_attempt()

    with pytest.raises(LLMProviderError) as raised:
        budget.record_attempt()
    assert raised.value.code == "budget_exceeded"


def test_circuit_breaker_state_machine() -> None:
    breaker = CircuitBreaker(failure_threshold=2, open_seconds=10.0)
    assert breaker.allow_request()

    breaker.record_failure()
    breaker.record_failure()
    assert not breaker.allow_request()  # open

    breaker.advance_clock(11.0)
    assert breaker.allow_request()  # half-open probe

    breaker.record_success()
    assert breaker.allow_request()  # closed again


def test_auth_failure_opens_circuit_immediately() -> None:
    breaker = CircuitBreaker(failure_threshold=5, open_seconds=10.0)

    breaker.open_immediately()

    assert not breaker.allow_request()


def test_generate_is_idempotent_for_same_script_and_key() -> None:
    adapter = make_adapter()

    first = adapter.generate(make_request(), MockScript(typed_output={"concepts": ["极限"]}))
    second = adapter.generate(make_request(), MockScript(typed_output={"concepts": ["极限"]}))

    assert first == second


def test_capability_missing_is_rejected_before_request() -> None:
    capabilities = {name: False for name in CAPABILITY_NAMES}
    capabilities.update({"text_input": True})

    with pytest.raises(LLMProviderError) as raised:
        check_required_capabilities(["text_output", "thinking"], capabilities)
    assert raised.value.code == "provider_capability_missing"
    assert set(raised.value.details["missing"]) == {"text_output", "thinking"}


# ---------------------------------------------------------------------------
# TC-LLM-008: redaction of logs/traces/diagnostics
# ---------------------------------------------------------------------------


def test_error_details_never_contain_prompt_or_content() -> None:
    adapter = make_adapter()
    request = make_request()

    with pytest.raises(LLMProviderError) as raised:
        adapter.generate(request, MockScript(failure="provider_auth_failed"))
    rendered = str(raised.value) + str(raised.value.details)
    assert "极限" not in rendered
    assert "idem-001" not in rendered
    assert "sk-" not in rendered


def test_mock_fixtures_do_not_contain_secret_patterns() -> None:
    source = Path(__file__).read_text(encoding="utf-8")
    assert re.search(r"sk-[A-Za-z0-9]{16,}", source) is None
    assert re.search(r"sk_[A-Za-z0-9]{16,}", source) is None


# ---------------------------------------------------------------------------
# TC-LLM-009: capability/config schema and fingerprint
# ---------------------------------------------------------------------------


def test_capability_fingerprint_is_stable_and_sensitive_to_change() -> None:
    capabilities = {name: False for name in CAPABILITY_NAMES}
    capabilities.update({"text_input": True, "text_output": True})

    same = capability_fingerprint(capabilities)
    assert same == capability_fingerprint(capabilities)
    changed = dict(capabilities, thinking=True)
    assert capability_fingerprint(changed) != same
    assert same.startswith("sha256:")


def test_deployment_resolution_uses_vendor_model_ids() -> None:
    providers = {
        "providers": {
            "deepseek": {
                "models": {"fast": {"model_id": "deepseek-v4-flash"}},
                "enabled": False,
            },
            "mock": {"models": {"deterministic": {"model_id": "mock-deterministic-v1"}}},
        }
    }

    assert resolve_deployment("deepseek/fast", providers) == ("deepseek", "deepseek-v4-flash")
    assert resolve_deployment("mock/deterministic", providers) == (
        "mock",
        "mock-deterministic-v1",
    )

    with pytest.raises(LLMProviderError) as raised:
        resolve_deployment("missing/model", providers)
    assert raised.value.code == "provider_invalid_request"


def test_select_deployment_prefers_enabled_mock() -> None:
    providers = {
        "providers": {
            "deepseek": {"enabled": False, "models": {}},
            "mock": {"enabled": True, "models": {"deterministic": {}}},
        }
    }
    policies = {
        "task_profiles": {
            "concept_extract": {"production_preference": ["deepseek/fast", "mock/deterministic"]}
        }
    }

    assert select_deployment("concept_extract", policies, providers) == "mock/deterministic"
    assert select_deployment("unknown_task", policies, providers) is None
