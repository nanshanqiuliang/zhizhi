"""Bounded, policy-scoped fallback orchestration for the LLM port (WORK-2026-008).

Baseline section 6.2: only transient errors (rate-limited, unavailable,
connection, timeout) may trigger automatic fallback; auth/balance/params/
schema errors fail closed. Each fallback is a fresh model run and never reuses
another adapter's partial output.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

from .canonical import GenerationRequest, GenerationResult
from .errors import LLMProviderError


class GenerationAdapter(Protocol):
    """The minimal surface ModelRunner needs from a concrete adapter."""

    def generate(self, request: GenerationRequest, **kwargs: Any) -> GenerationResult: ...


class ModelRunner:
    """Runs a generation against an ordered adapter list with scoped fallback."""

    def __init__(
        self,
        *,
        adapters: Sequence[GenerationAdapter],
        allowed_fallback_codes: Sequence[str] = (),
    ) -> None:
        if not adapters:
            raise ValueError("adapters must not be empty")
        self._adapters = list(adapters)
        self._allowed = set(allowed_fallback_codes)

    def generate(self, request: GenerationRequest, **kwargs: Any) -> GenerationResult:
        """Try adapters in order; fall back only on allowed transient errors."""

        last_error: LLMProviderError | None = None
        for adapter in self._adapters:
            try:
                return adapter.generate(request, **kwargs)
            except LLMProviderError as error:
                last_error = error
                if error.code not in self._allowed:
                    raise error
        if last_error is not None:
            raise last_error
        raise LLMProviderError("provider_unknown_error", details={"rule": "no_adapters"})
