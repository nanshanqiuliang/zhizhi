"""LLM port implementations for the Knowledge Tree infrastructure.

Contains the canonical DTOs, stable errors, capability validation,
resilience helpers, deployment router, the deterministic mock adapter and the
DeepSeek OpenAI Chat Completions adapter (WORK-2026-007/008). Real provider
deployments stay `enabled: false` until their documented gates pass.
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
from .http_client import HttpJsonClient, HttpTransportError
from .mock import LlmStreamEvent, MockContinuationStore, MockLlmAdapter, MockScript
from .resilience import AttemptBudget, CircuitBreaker, backoff_sequence
from .router import resolve_deployment, select_deployment
from .vendors.deepseek import DeepSeekConfig, DeepSeekLlmAdapter, map_deepseek_http_error

__all__ = [
    "AttemptBudget",
    "Budget",
    "CanonicalMessage",
    "CanonicalToolCall",
    "CanonicalUsage",
    "CircuitBreaker",
    "ContentPart",
    "DeepSeekConfig",
    "DeepSeekLlmAdapter",
    "GenerationRequest",
    "GenerationResult",
    "HttpJsonClient",
    "HttpTransportError",
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
    "map_deepseek_http_error",
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
