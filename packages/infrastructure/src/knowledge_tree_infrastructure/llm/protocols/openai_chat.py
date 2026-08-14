"""OpenAI Chat Completions protocol adapter (WORK-2026-008).

Maps canonical `GenerationRequest`/`GenerationResult`/stream events to and
from the OpenAI Chat Completions wire format. DeepSeek-specific extensions
(`thinking.type`, `reasoning_content`) ride the OpenAI wire shape and are
handled here; vendor-only policy lives in `vendors/deepseek.py`.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Mapping
from typing import Any, NoReturn

from knowledge_tree_contracts import validate_llm_contract

from ..canonical import (
    CanonicalMessage,
    CanonicalToolCall,
    CanonicalUsage,
    GenerationRequest,
    GenerationResult,
    request_to_dict,
)
from ..errors import LLMProviderError
from ..mock import LlmStreamEvent

JsonObject = dict[str, Any]

_OPENAI_FINISH_REASONS = {"stop", "length", "tool_calls", "content_filter"}


def _reject(code: str, **details: Any) -> NoReturn:
    raise LLMProviderError(code, details=dict(details))


def _map_finish_reason(raw: object) -> str:
    if not isinstance(raw, str) or raw not in _OPENAI_FINISH_REASONS:
        _reject("provider_protocol_mismatch", rule="unknown_finish_reason", finish_reason=raw)
    return raw


def _content_part_to_text(part: Any) -> str:
    kind = part.kind
    if kind == "text":
        return str(part.value)
    if kind == "tool_result":
        return json.dumps(part.value, ensure_ascii=False)
    if kind == "image_ref":
        _reject("provider_capability_missing", rule="image_input_unsupported")
    if kind == "tool_call":
        return ""
    _reject("provider_invalid_request", rule="unknown_content_part_kind", kind=kind)


def _message_to_openai(message: CanonicalMessage) -> JsonObject:
    if message.role == "tool":
        if not message.tool_call_id:
            _reject("provider_invalid_request", rule="tool_message_missing_tool_call_id")
        content = "".join(_content_part_to_text(part) for part in message.parts)
        return {"role": "tool", "tool_call_id": message.tool_call_id, "content": content}

    if message.role == "assistant" and any(part.kind == "tool_call" for part in message.parts):
        tool_calls: list[JsonObject] = []
        for part in message.parts:
            if part.kind != "tool_call":
                continue
            value = part.value
            if not isinstance(value, dict) or "name" not in value:
                _reject("provider_invalid_request", rule="tool_call_content_shape")
            call_id = str(value.get("id") or message.tool_call_id or "")
            tool_calls.append(
                {
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": value["name"],
                        "arguments": json.dumps(value.get("arguments", {}), ensure_ascii=False),
                    },
                }
            )
        return {"role": "assistant", "content": None, "tool_calls": tool_calls}

    content = "".join(_content_part_to_text(part) for part in message.parts)
    return {"role": message.role, "content": content}


def build_chat_request(
    *,
    model_id: str,
    request: GenerationRequest,
    max_tokens: int,
    thinking: str | None = None,
    stream: bool = False,
    reasoning_continuation: str | None = None,
    temperature: float | None = None,
) -> JsonObject:
    """Serialize a canonical request to the OpenAI Chat Completions wire shape.

    `thinking` is the explicit DeepSeek thinking switch ("enabled"/"disabled");
    sending sampling params together with thinking is rejected locally.
    """

    if thinking == "enabled" and temperature is not None:
        _reject("provider_invalid_request", rule="thinking_with_sampling_params")
    validate_llm_contract("generation_request", request_to_dict(request))

    messages = [_message_to_openai(message) for message in request.messages]
    if reasoning_continuation is not None:
        for message in messages:
            if message["role"] == "assistant":
                message["reasoning_content"] = reasoning_continuation
                break

    payload: JsonObject = {
        "model": model_id,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": stream,
    }
    if thinking is not None:
        payload["thinking"] = {"type": thinking}
    if request.output_schema is not None:
        payload["response_format"] = {"type": "json_object"}
    if request.tools:
        payload["tools"] = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in request.tools
        ]
    return payload


def _parse_tool_call_arguments(raw: object) -> JsonObject:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            _reject("provider_schema_failed", rule="tool_arguments_not_json")
        if not isinstance(parsed, dict):
            _reject("provider_schema_failed", rule="tool_arguments_not_object")
        return parsed
    _reject("provider_schema_failed", rule="tool_arguments_not_json")


def parse_chat_response(
    payload: Mapping[str, Any],
    *,
    model_run_id: str,
    provider_id: str,
    protocol: str,
    model_id: str,
    capability_snapshot: str | None,
) -> GenerationResult:
    """Map an OpenAI Chat Completions response to a canonical GenerationResult."""

    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        _reject("provider_protocol_mismatch", rule="missing_choices")
    first = choices[0]
    if not isinstance(first, dict):
        _reject("provider_protocol_mismatch", rule="invalid_choice")
    first_message = first.get("message")
    message = first_message if isinstance(first_message, dict) else {}

    text = message.get("content")
    if text is not None and not isinstance(text, str):
        _reject("provider_protocol_mismatch", rule="non_string_content")

    tool_calls: tuple[CanonicalToolCall, ...] = ()
    raw_calls = message.get("tool_calls")
    if raw_calls:
        if not isinstance(raw_calls, list):
            _reject("provider_protocol_mismatch", rule="invalid_tool_calls")
        parsed_calls: list[CanonicalToolCall] = []
        for call in raw_calls:
            if not isinstance(call, dict):
                _reject("provider_protocol_mismatch", rule="invalid_tool_call")
            function = call.get("function")
            function = function if isinstance(function, dict) else {}
            parsed_calls.append(
                CanonicalToolCall(
                    id=str(call.get("id", "")),
                    name=str(function.get("name", "")),
                    arguments=_parse_tool_call_arguments(function.get("arguments", "{}")),
                )
            )
        tool_calls = tuple(parsed_calls)

    usage = payload.get("usage")
    if not isinstance(usage, dict):
        usage = {}
    canonical_usage = CanonicalUsage(
        input_tokens=int(usage.get("prompt_tokens", 0)),
        output_tokens=int(usage.get("completion_tokens", 0)),
        cache_read_tokens=(
            int(usage["prompt_cache_hit_tokens"])
            if usage.get("prompt_cache_hit_tokens") is not None
            else None
        ),
    )

    return GenerationResult(
        model_run_id=model_run_id,
        provider=provider_id,
        protocol=protocol,
        model_id=model_id,
        text=text,
        typed_output=None,
        tool_calls=tool_calls,
        usage=canonical_usage,
        finish_reason=_map_finish_reason(first.get("finish_reason") or "stop"),
        provider_response_id=payload.get("id") if isinstance(payload.get("id"), str) else None,
        model_revision=None,
        capability_snapshot=capability_snapshot,
    )


def sse_stream_events(lines: Iterable[str]) -> Iterator[LlmStreamEvent]:
    """Parse an SSE `data:` stream into canonical LlmStreamEvent.

    Tolerates blank lines and `: keep-alive` comments, swallows opaque
    `reasoning_content` deltas, and fails closed with `provider_stream_incomplete`
    if the stream ends without `[DONE]` or a finish reason.
    """

    started = False
    finish_reason: str | None = None
    saw_done = False
    for raw_line in lines:
        line = raw_line.rstrip("\r\n")
        if not line.strip():
            continue
        if line.startswith(":"):
            continue
        if not line.startswith("data:"):
            continue
        data = line[len("data:") :].strip()
        if data == "[DONE]":
            saw_done = True
            break
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            _reject("provider_protocol_mismatch", rule="sse_invalid_json")
        if not isinstance(payload, dict):
            _reject("provider_protocol_mismatch", rule="sse_invalid_payload")
        if not started:
            yield LlmStreamEvent(type="response.started")
            started = True
        choices = payload.get("choices") or []
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            delta_raw = choice.get("delta")
            delta = delta_raw if isinstance(delta_raw, dict) else {}
            content = delta.get("content")
            if content:
                yield LlmStreamEvent(type="text.delta", text=str(content))
            reason = delta.get("finish_reason") or choice.get("finish_reason")
            if reason:
                finish_reason = str(reason)
    if not saw_done:
        _reject("provider_stream_incomplete", rule="stream_ended_without_done")
    if finish_reason is None:
        _reject("provider_stream_incomplete", rule="stream_missing_finish_reason")
    yield LlmStreamEvent(type="response.completed", finish_reason=_map_finish_reason(finish_reason))
