"""Canonical LLM contract v1 tests (WORK-2026-007, offline part of roadmap Step 7).

Covers TC-LLM-001/002/009 plus schema/artifact invariants from
LLM-COMPAT-BASELINE-001. Everything here runs offline against the mock
provider; no real Provider, network, key or budget is involved.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from knowledge_tree_contracts import (
    ContractValidationError,
    llm_contract_document,
    llm_contract_schema,
    validate_llm_contract,
)
from knowledge_tree_contracts.llm_v1 import (
    CAPABILITY_NAMES,
    FINISH_REASONS,
    LLM_ERROR_CODES,
    LLM_SCHEMA_VERSION,
    PROTOCOL_IDS,
    PROVIDER_IDS,
)

JsonObject = dict[str, Any]

ROOT = Path(__file__).resolve().parents[2]
MODEL_RUN_ID = "00000000-0000-7000-8000-000000000001"
CORRELATION_ID = "00000000-0000-7000-8000-000000000002"

# Stable error codes mandated by the multi-LLM baseline section 4.6.
_BASELINE_ERROR_CODES = {
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
}
_BASELINE_CAPABILITIES = {
    "text_input",
    "text_output",
    "image_input",
    "streaming",
    "tool_calls",
    "parallel_tool_calls",
    "json_object",
    "json_schema",
    "strict_tool_schema",
    "thinking",
    "reasoning_effort",
    "reasoning_replay",
    "system_message",
    "developer_message",
    "usage_tokens",
    "prompt_cache_usage",
    "provider_request_id",
    "web_search",
    "file_search",
    "embeddings",
}


def valid_request(**overrides: Any) -> JsonObject:
    request: JsonObject = {
        "schema_version": 1,
        "model_run_id": MODEL_RUN_ID,
        "task": "concept_extract",
        "messages": [{"role": "user", "parts": [{"kind": "text", "value": "解释极限的定义"}]}],
        "output_schema": None,
        "tools": [],
        "model_policy": "concept_extract",
        "idempotency_key": "idem-001",
        "budget": {"max_attempts": 2, "max_output_tokens": 4096},
        "trace_context": {"correlation_id": CORRELATION_ID},
    }
    request.update(overrides)
    return request


def valid_result(**overrides: Any) -> JsonObject:
    result: JsonObject = {
        "schema_version": 1,
        "model_run_id": MODEL_RUN_ID,
        "text": "极限是……",
        "typed_output": None,
        "tool_calls": [],
        "usage": {"input_tokens": 128, "output_tokens": 64},
        "finish_reason": "stop",
        "provider_response_id": None,
        "provider": "mock",
        "protocol": "mock",
        "model_id": "mock-deterministic-v1",
        "model_revision": "1",
        "capability_snapshot": None,
    }
    result.update(overrides)
    return result


def capability_set(**overrides: Any) -> JsonObject:
    capabilities = {name: False for name in CAPABILITY_NAMES}
    capabilities.update({"text_input": True, "text_output": True})
    capabilities.update(overrides)
    return capabilities


def test_canonical_llm_schema_is_self_valid() -> None:
    document = llm_contract_document()

    Draft202012Validator.check_schema(document)


def test_schema_version_is_one() -> None:
    assert LLM_SCHEMA_VERSION == 1
    assert llm_contract_document()["$defs"]["GenerationRequest"]["properties"][
        "schema_version"
    ] == {"const": 1}


def test_provider_and_protocol_ids_match_baseline() -> None:
    assert set(PROVIDER_IDS) == {"mock", "deepseek", "openai", "kimi", "anthropic"}
    assert set(PROTOCOL_IDS) == {
        "mock",
        "openai_chat_completions",
        "openai_responses",
        "anthropic_messages",
    }


def test_error_codes_cover_baseline_section_4_6() -> None:
    assert _BASELINE_ERROR_CODES.issubset(set(LLM_ERROR_CODES))
    # Transient errors that may retry are explicitly enumerated for tests.
    assert {"provider_rate_limited", "provider_unavailable", "provider_connection_failed"}.issubset(
        set(LLM_ERROR_CODES)
    )


def test_error_codes_include_config_and_secret_reference() -> None:
    # RB-PROV-001 and ERROR_CODE_CATALOG reference these preflight/secret codes;
    # the canonical enum must be their single source, never a second hand-kept list.
    assert {"provider_config_invalid", "provider_secret_missing"}.issubset(set(LLM_ERROR_CODES))


def test_capability_names_cover_baseline_section_3_2() -> None:
    assert set(CAPABILITY_NAMES) == _BASELINE_CAPABILITIES


def test_finish_reasons_cover_baseline_stream_contract() -> None:
    assert set(FINISH_REASONS) == {"stop", "length", "tool_calls", "content_filter", "abort"}


def test_generated_artifact_matches_repository_schema() -> None:
    source = json.loads((ROOT / "docs/contracts/llm.v1.schema.json").read_text(encoding="utf-8"))

    assert llm_contract_document() == source


def test_valid_request_passes() -> None:
    validate_llm_contract("generation_request", valid_request())


def test_valid_result_passes() -> None:
    validate_llm_contract("generation_result", valid_result())


def test_unknown_field_is_rejected() -> None:
    with pytest.raises(ContractValidationError):
        validate_llm_contract("generation_request", valid_request(extra="boom"))


def test_invalid_message_role_is_rejected() -> None:
    request = valid_request(messages=[{"role": "admin", "parts": []}])

    with pytest.raises(ContractValidationError):
        validate_llm_contract("generation_request", request)


def test_invalid_content_part_kind_is_rejected() -> None:
    request = valid_request(messages=[{"role": "user", "parts": [{"kind": "audio", "value": "x"}]}])

    with pytest.raises(ContractValidationError):
        validate_llm_contract("generation_request", request)


def test_non_uuidv7_model_run_id_is_rejected() -> None:
    with pytest.raises(ContractValidationError):
        validate_llm_contract("generation_request", valid_request(model_run_id="not-a-uuid"))


def test_non_uuidv7_correlation_id_is_rejected() -> None:
    with pytest.raises(ContractValidationError):
        validate_llm_contract(
            "generation_request",
            valid_request(trace_context={"correlation_id": "not-a-uuid"}),
        )


def test_negative_tokens_are_rejected() -> None:
    result = valid_result(usage={"input_tokens": -1, "output_tokens": 10})

    with pytest.raises(ContractValidationError):
        validate_llm_contract("generation_result", result)


def test_unknown_finish_reason_is_rejected() -> None:
    result = valid_result(finish_reason="bogus")

    with pytest.raises(ContractValidationError):
        validate_llm_contract("generation_result", result)


def test_capability_set_requires_every_declared_capability() -> None:
    validate_llm_contract("capability_set", capability_set())

    missing = capability_set()
    del missing["thinking"]
    with pytest.raises(ContractValidationError):
        validate_llm_contract("capability_set", missing)

    extra = capability_set(embeddings_nope=True)
    with pytest.raises(ContractValidationError):
        validate_llm_contract("capability_set", extra)


def test_schema_view_is_isolated_copy() -> None:
    document = llm_contract_document()
    view = llm_contract_schema("generation_request")

    document["$defs"]["ProviderId"] = {"enum": ["tampered"]}
    assert llm_contract_document()["$defs"]["ProviderId"]["enum"] != ["tampered"]
    assert view["$defs"]["ProviderId"]["enum"] == [
        "mock",
        "deepseek",
        "openai",
        "kimi",
        "anthropic",
    ]


def test_input_is_not_mutated() -> None:
    request = valid_request()
    snapshot = deepcopy(request)

    validate_llm_contract("generation_request", request)

    assert request == snapshot
