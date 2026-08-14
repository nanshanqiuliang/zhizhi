"""Schema-backed canonical LLM port contract v1 (WORK-2026-007).

Loads the generated LLM v1 schema artifact without any repository file I/O at
runtime, exposes the canonical enums (ProviderId, ProtocolId, capabilities,
finish reasons, stable error codes) from that single hand-edited source, and
validates payloads for the named LLM contracts. No vendor SDK type is ever
imported here.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from functools import lru_cache
from typing import Any
from uuid import UUID

from jsonschema import Draft202012Validator, FormatChecker

from ._generated_llm_v1_schema import LLM_V1_SCHEMA_JSON
from .graph_v1 import ContractValidationError

JsonObject = dict[str, Any]

LLM_SCHEMA_VERSION = 1
_CONTRACT_DEFINITIONS = {
    "generation_request": "GenerationRequest",
    "generation_result": "GenerationResult",
    "capability_set": "CapabilitySet",
    "content_part": "ContentPart",
    "canonical_message": "CanonicalMessage",
    "tool_definition": "ToolDefinition",
    "canonical_tool_call": "CanonicalToolCall",
    "canonical_usage": "CanonicalUsage",
    "budget": "Budget",
    "trace_context": "TraceContext",
}


@lru_cache(maxsize=1)
def _load_llm_contract_document() -> JsonObject:
    try:
        value = json.loads(LLM_V1_SCHEMA_JSON)
    except json.JSONDecodeError as error:
        raise RuntimeError("generated llm schema artifact is invalid") from error
    if not isinstance(value, dict):
        raise RuntimeError("canonical llm schema must be an object")
    Draft202012Validator.check_schema(value)
    return value


def llm_contract_document() -> JsonObject:
    """Return an isolated copy of the canonical LLM contract document."""

    return deepcopy(_load_llm_contract_document())


def _enum_values(name: str) -> tuple[str, ...]:
    values = _load_llm_contract_document()["$defs"][name]["enum"]
    return tuple(str(value) for value in values)


# Canonical enum values, all derived from the single JSON Schema source.
PROVIDER_IDS = _enum_values("ProviderId")
PROTOCOL_IDS = _enum_values("ProtocolId")
CAPABILITY_NAMES = _enum_values("CapabilityName")
LLM_ERROR_CODES = _enum_values("LlmErrorCode")
FINISH_REASONS = _enum_values("FinishReason")
MESSAGE_ROLES = _enum_values("MessageRole")
CONTENT_PART_KINDS = _enum_values("ContentPartKind")


def llm_contract_schema(contract: str) -> JsonObject:
    """Build a named validation view while retaining the canonical root definitions."""

    definition = _CONTRACT_DEFINITIONS.get(contract)
    if definition is None:
        raise ValueError(f"unknown llm contract: {contract}")
    root = llm_contract_document()
    return {
        "$schema": root["$schema"],
        "$id": f"{root['$id']}?contract={contract}",
        "$ref": f"#/$defs/{definition}",
        "$defs": deepcopy(root["$defs"]),
    }


def _is_uuidv7(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        identifier = UUID(value)
    except ValueError:
        return False
    return identifier.version == 7 and identifier.variant == "specified in RFC 4122"


def _format_checker() -> FormatChecker:
    checker = FormatChecker()
    checker.checks("uuidv7")(_is_uuidv7)
    return checker


def _path(parts: Any) -> str:
    rendered = ".".join(str(part) for part in parts)
    return rendered or "<root>"


def validate_llm_contract(contract: str, instance: Mapping[str, Any]) -> None:
    """Validate a mapping against a named LLM v1 contract without mutating input."""

    view = llm_contract_schema(contract)
    validator = Draft202012Validator(view, format_checker=_format_checker())
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path))
    if errors:
        first = errors[0]
        raise ContractValidationError(
            contract=contract,
            path=_path(first.absolute_path),
            rule=first.message,
        )
