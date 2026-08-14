"""Frozen canonical DTOs for the LLM port (WORK-2026-007).

These DTOs never import a vendor SDK type; they are the runtime view of
`docs/contracts/llm.v1.schema.json`. Construction from dict validates against
the canonical contract first so malformed payloads fail closed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any, Literal, cast

from jsonschema import Draft202012Validator
from knowledge_tree_contracts import ContractValidationError, validate_llm_contract

from .errors import LLMProviderError

JsonObject = dict[str, Any]

Role = Literal["system", "user", "assistant", "tool"]
PartKind = Literal["text", "image_ref", "tool_call", "tool_result"]
FinishReason = Literal["stop", "length", "tool_calls", "content_filter", "abort"]


@dataclass(frozen=True, slots=True)
class ContentPart:
    kind: str
    value: object
    media_type: str | None = None


@dataclass(frozen=True, slots=True)
class CanonicalMessage:
    role: str
    parts: tuple[ContentPart, ...]
    tool_call_id: str | None = None


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    parameters: JsonObject


@dataclass(frozen=True, slots=True)
class CanonicalToolCall:
    id: str
    name: str
    arguments: JsonObject


@dataclass(frozen=True, slots=True)
class CanonicalUsage:
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class Budget:
    max_attempts: int
    max_output_tokens: int
    max_fallbacks: int = 0
    max_input_tokens: int | None = None
    max_latency_ms: int | None = None
    max_cost_usd: float | None = None


@dataclass(frozen=True, slots=True)
class TraceContext:
    correlation_id: str
    job_id: str | None = None
    stage_run_id: str | None = None


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    model_run_id: str
    task: str
    messages: tuple[CanonicalMessage, ...]
    model_policy: str
    idempotency_key: str
    budget: Budget
    trace_context: TraceContext
    output_schema: JsonObject | None = None
    tools: tuple[ToolDefinition, ...] = ()


@dataclass(frozen=True, slots=True)
class GenerationResult:
    model_run_id: str
    provider: str
    protocol: str
    model_id: str
    usage: CanonicalUsage
    finish_reason: str
    text: str | None = None
    typed_output: JsonObject | None = None
    tool_calls: tuple[CanonicalToolCall, ...] = ()
    provider_response_id: str | None = None
    model_revision: str | None = None
    capability_snapshot: str | None = None


def _validate_or_wrap(contract: str, value: Mapping[str, Any]) -> None:
    try:
        validate_llm_contract(contract, value)
    except ContractValidationError as error:
        raise LLMProviderError("provider_invalid_request", details=error.details) from error


def _jsonable(value: Any) -> Any:
    """Recursively convert dataclass asdict output into JSON-compatible values.

    `dataclasses.asdict` keeps tuple container types, but JSON Schema arrays
    are Python lists, so tuples must be converted before validation.
    """

    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def message_to_dict(message: CanonicalMessage) -> JsonObject:
    payload = cast(JsonObject, _jsonable(asdict(message)))
    _validate_or_wrap("canonical_message", payload)
    return payload


def message_from_dict(data: Mapping[str, Any]) -> CanonicalMessage:
    _validate_or_wrap("canonical_message", data)
    return CanonicalMessage(
        role=data["role"],
        parts=tuple(ContentPart(**part) for part in data["parts"]),
        tool_call_id=data.get("tool_call_id"),
    )


def request_to_dict(request: GenerationRequest) -> JsonObject:
    payload = cast(JsonObject, _jsonable(asdict(request)))
    payload["schema_version"] = 1
    _validate_or_wrap("generation_request", payload)
    return payload


def request_from_dict(data: Mapping[str, Any]) -> GenerationRequest:
    _validate_or_wrap("generation_request", data)
    return GenerationRequest(
        model_run_id=data["model_run_id"],
        task=data["task"],
        messages=tuple(message_from_dict(item) for item in data["messages"]),
        model_policy=data["model_policy"],
        idempotency_key=data["idempotency_key"],
        budget=Budget(**data["budget"]),
        trace_context=TraceContext(
            correlation_id=data["trace_context"]["correlation_id"],
            job_id=data["trace_context"].get("job_id"),
            stage_run_id=data["trace_context"].get("stage_run_id"),
        ),
        output_schema=data.get("output_schema"),
        tools=tuple(
            ToolDefinition(
                name=item["name"], description=item["description"], parameters=item["parameters"]
            )
            for item in data.get("tools", [])
        ),
    )


def result_to_dict(result: GenerationResult) -> JsonObject:
    payload = cast(JsonObject, _jsonable(asdict(result)))
    payload["schema_version"] = 1
    _validate_or_wrap("generation_result", payload)
    return payload


def result_from_dict(data: Mapping[str, Any]) -> GenerationResult:
    _validate_or_wrap("generation_result", data)
    return GenerationResult(
        model_run_id=data["model_run_id"],
        provider=data["provider"],
        protocol=data["protocol"],
        model_id=data["model_id"],
        usage=CanonicalUsage(**data["usage"]),
        finish_reason=data["finish_reason"],
        text=data.get("text"),
        typed_output=data.get("typed_output"),
        tool_calls=tuple(CanonicalToolCall(**call) for call in data.get("tool_calls", [])),
        provider_response_id=data.get("provider_response_id"),
        model_revision=data.get("model_revision"),
        capability_snapshot=data.get("capability_snapshot"),
    )


def validate_typed_output(instance: object, schema: JsonObject | None) -> None:
    """Validate typed output against a local JSON Schema; fail closed.

    A blank, truncated or schema-violating output raises
    `provider_schema_failed` and is never treated as a usable draft.
    """

    if schema is None:
        return
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path))
    if errors:
        raise LLMProviderError(
            "provider_schema_failed",
            details={"rule": "typed_output_validation_failed"},
        )
