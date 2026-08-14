"""LLM port implementations for the Knowledge Tree infrastructure.

Contains the canonical DTOs, stable errors, capability validation,
resilience helpers, deployment router and the deterministic mock adapter
(WORK-2026-007). Real protocol adapters and vendor profiles are future work
and must remain disabled until their documented gates pass.
"""

from .canonical import (
    Budget,
    CanonicalMessage,
    CanonicalToolCall,
    CanonicalUsage,
    ContentPart,
    GenerationRequest,
    GenerationResult,
    ToolDefinition,
    TraceContext,
    message_from_dict,
    message_to_dict,
    request_from_dict,
    request_to_dict,
    result_from_dict,
    result_to_dict,
    validate_typed_output,
)
from .capabilities import capability_fingerprint, check_required_capabilities
from .errors import LLMProviderError
from .mock import LlmStreamEvent, MockContinuationStore, MockLlmAdapter, MockScript
from .resilience import AttemptBudget, CircuitBreaker, backoff_sequence
from .router import resolve_deployment, select_deployment

__all__ = [
    "AttemptBudget",
    "Budget",
    "CanonicalMessage",
    "CanonicalToolCall",
    "CanonicalUsage",
    "CircuitBreaker",
    "ContentPart",
    "GenerationRequest",
    "GenerationResult",
    "LLMProviderError",
    "LlmStreamEvent",
    "MockContinuationStore",
    "MockLlmAdapter",
    "MockScript",
    "ToolDefinition",
    "TraceContext",
    "backoff_sequence",
    "capability_fingerprint",
    "check_required_capabilities",
    "message_from_dict",
    "message_to_dict",
    "request_from_dict",
    "request_to_dict",
    "resolve_deployment",
    "result_from_dict",
    "result_to_dict",
    "select_deployment",
    "validate_typed_output",
]
