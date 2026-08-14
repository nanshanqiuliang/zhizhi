"""Stable error codes and content-safe errors for the LLM port (WORK-2026-007).

`code` is always one of the canonical `LlmErrorCode` enum values from
`docs/contracts/llm.v1.schema.json`; `details` never contains prompt,
response, reasoning content or secrets.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from knowledge_tree_contracts.llm_v1 import LLM_ERROR_CODES

JsonObject = dict[str, Any]


class LLMProviderError(ValueError):
    """A stable, content-safe LLM port rejection."""

    def __init__(self, code: str, *, details: Mapping[str, Any] | None = None) -> None:
        if code not in LLM_ERROR_CODES:
            raise ValueError(f"unknown llm error code: {code}")
        self.code = code
        self.details: JsonObject = dict(details or {})
        super().__init__(f"{code}: llm provider rejected")
