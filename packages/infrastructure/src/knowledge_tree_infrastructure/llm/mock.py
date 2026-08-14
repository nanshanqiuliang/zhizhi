"""Deterministic mock LLM provider adapter (WORK-2026-007).

Implements the canonical LLM port without any network access: scripted
text/JSON/tool/streaming outputs, opaque thinking continuation state, and
injectable stable failures. This is the offline test baseline for
TC-LLM-001..009 until a real protocol adapter exists.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any

from knowledge_tree_contracts import ContractValidationError, validate_llm_contract

from .canonical import (
    CanonicalToolCall,
    CanonicalUsage,
    GenerationRequest,
    GenerationResult,
    request_to_dict,
)
from .capabilities import capability_fingerprint
from .errors import LLMProviderError

JsonObject = dict[str, Any]

_STREAM_EVENT_TYPES = {
    "response.started",
    "text.delta",
    "tool_call.started",
    "tool_call.arguments.delta",
    "tool_call.completed",
    "usage.updated",
    "response.completed",
    "response.failed",
    "heartbeat",
}


@dataclass(frozen=True, slots=True)
class MockScript:
    """Deterministic scripted behaviour for a single mock model run."""

    text: str | None = None
    typed_output: JsonObject | None = None
    finish_reason: str = "stop"
    tool_calls: tuple[CanonicalToolCall, ...] = ()
    thinking: bool = False
    failure: str | None = None
    stream_deltas: tuple[str, ...] = ()
    stream_extra_events: tuple[str, ...] = ()
    output_tokens: int | None = None
    requires_continuation: bool = False


@dataclass(frozen=True, slots=True)
class LlmStreamEvent:
    """One finite canonical stream event; never passes vendor-only fields."""

    type: str
    text: str | None = None
    tool_call_id: str | None = None
    tool_call_name: str | None = None
    arguments_delta: str | None = None
    tool_call: CanonicalToolCall | None = None
    usage: CanonicalUsage | None = None
    finish_reason: str | None = None
    error_code: str | None = None
    heartbeat: bool = False


class MockContinuationStore:
    """Opaque reasoning-state store for the mock (existence/hash only)."""

    def __init__(self) -> None:
        self._states: dict[str, JsonObject] = {}

    def put(self, model_run_id: str, state: JsonObject) -> None:
        self._states[model_run_id] = dict(state)

    def get(self, model_run_id: str) -> JsonObject | None:
        state = self._states.get(model_run_id)
        return dict(state) if state is not None else None

    def contains(self, model_run_id: str) -> bool:
        return model_run_id in self._states


class MockLlmAdapter:
    """Deterministic, offline mock implementation of the canonical LLM port."""

    provider_id = "mock"
    protocol = "mock"

    def __init__(
        self,
        *,
        model_id: str = "mock-deterministic-v1",
        model_revision: str = "1",
        capabilities: Mapping[str, bool] | None = None,
        continuation_store: MockContinuationStore | None = None,
    ) -> None:
        self.model_id = model_id
        self.model_revision = model_revision
        self._capabilities = dict(capabilities or {})
        self._store = (
            continuation_store if continuation_store is not None else MockContinuationStore()
        )

    # -- internal helpers ---------------------------------------------------

    def _validate_request(self, request: GenerationRequest) -> None:
        try:
            validate_llm_contract("generation_request", request_to_dict(request))
        except ContractValidationError as error:
            raise LLMProviderError("provider_invalid_request", details=error.details) from error

    def _usage(self, request: GenerationRequest, script: MockScript, text: str) -> CanonicalUsage:
        input_tokens = max(1, len(json.dumps(request_to_dict(request), ensure_ascii=False)) // 4)
        if script.output_tokens is not None:
            output_tokens = script.output_tokens
        else:
            output_tokens = max(1, len(text) // 2)
        return CanonicalUsage(input_tokens=input_tokens, output_tokens=output_tokens)

    def _check_duplicate_tool_calls(self, tool_calls: tuple[CanonicalToolCall, ...]) -> None:
        seen: set[str] = set()
        for call in tool_calls:
            if call.id in seen:
                raise LLMProviderError(
                    "provider_protocol_mismatch",
                    details={"rule": "duplicate_tool_call_id", "tool_call_id": call.id},
                )
            seen.add(call.id)

    def _reasoning_state(self, script: MockScript, model_run_id: str) -> None:
        """Record opaque reasoning existence; never the content itself."""

        if not script.thinking:
            return
        digest = hashlib.sha256(f"mock-thinking-{model_run_id}".encode()).hexdigest()
        self._store.put(
            model_run_id,
            {"reasoning_present": True, "bytes": 12, "sha256": f"sha256:{digest}"},
        )

    def _check_continuation(self, script: MockScript, model_run_id: str) -> None:
        if script.requires_continuation and self._store.get(model_run_id) is None:
            raise LLMProviderError(
                "provider_continuation_lost",
                details={"rule": "reasoning_state_missing", "model_run_id": model_run_id},
            )

    def _inject_failure(self, script: MockScript) -> None:
        if script.failure is not None:
            raise LLMProviderError(script.failure, details={"rule": "injected_failure"})

    # -- public API ----------------------------------------------------------

    def generate(self, request: GenerationRequest, script: MockScript) -> GenerationResult:
        """Return a deterministic non-streaming result for the given script."""

        self._validate_request(request)
        self._inject_failure(script)
        self._check_duplicate_tool_calls(script.tool_calls)
        self._check_continuation(script, request.model_run_id)
        self._reasoning_state(script, request.model_run_id)

        if script.typed_output is not None:
            text = json.dumps(script.typed_output, ensure_ascii=False)
        else:
            text = script.text or ""
        return GenerationResult(
            model_run_id=request.model_run_id,
            provider=self.provider_id,
            protocol=self.protocol,
            model_id=self.model_id,
            text=text if script.typed_output is None else None,
            typed_output=script.typed_output,
            tool_calls=script.tool_calls,
            usage=self._usage(request, script, text),
            finish_reason=script.finish_reason,
            provider_response_id=f"mock-{request.idempotency_key}",
            model_revision=self.model_revision,
            capability_snapshot=capability_fingerprint(self._capabilities),
        )

    def stream(self, request: GenerationRequest, script: MockScript) -> Iterator[LlmStreamEvent]:
        """Yield the finite canonical stream event sequence for the script."""

        self._validate_request(request)
        self._inject_failure(script)
        self._check_duplicate_tool_calls(script.tool_calls)
        self._check_continuation(script, request.model_run_id)
        self._reasoning_state(script, request.model_run_id)

        yield LlmStreamEvent(type="response.started")
        for delta in script.stream_deltas:
            yield LlmStreamEvent(type="text.delta", text=delta)
        for extra in script.stream_extra_events:
            if extra == "heartbeat":
                yield LlmStreamEvent(type="heartbeat", heartbeat=True)
            elif extra == "break":
                yield LlmStreamEvent(
                    type="response.failed", error_code="provider_stream_incomplete"
                )
                return
            elif extra == "cancel":
                raise LLMProviderError("model_run_cancelled", details={"rule": "client_cancelled"})
            else:
                raise LLMProviderError(
                    "provider_protocol_mismatch",
                    details={"rule": "unknown_stream_event", "event": extra},
                )
        for tool_call in script.tool_calls:
            yield LlmStreamEvent(
                type="tool_call.started",
                tool_call_id=tool_call.id,
                tool_call_name=tool_call.name,
            )
            arguments_json = json.dumps(tool_call.arguments, ensure_ascii=False)
            yield LlmStreamEvent(
                type="tool_call.arguments.delta",
                tool_call_id=tool_call.id,
                arguments_delta=arguments_json,
            )
            yield LlmStreamEvent(
                type="tool_call.completed",
                tool_call_id=tool_call.id,
                tool_call=tool_call,
            )
        if script.typed_output is not None:
            text = json.dumps(script.typed_output, ensure_ascii=False)
        else:
            text = script.text or ""
        yield LlmStreamEvent(type="usage.updated", usage=self._usage(request, script, text))
        yield LlmStreamEvent(type="response.completed", finish_reason=script.finish_reason)
