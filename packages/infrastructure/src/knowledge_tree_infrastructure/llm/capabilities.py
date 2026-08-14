"""Capability-set validation and versioned fingerprints for the LLM port.

Capability names come from the canonical `CapabilityName` enum; a task whose
required capabilities are not all declared True must be rejected before any
network request is attempted (`provider_capability_missing`).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from typing import Any

from .errors import LLMProviderError

JsonObject = dict[str, Any]


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def check_required_capabilities(required: Iterable[str], declared: Mapping[str, bool]) -> None:
    """Fail closed before any request if a required capability is not declared True."""

    missing = sorted(name for name in required if declared.get(name) is not True)
    if missing:
        raise LLMProviderError(
            "provider_capability_missing",
            details={"rule": "required_capability_missing", "missing": missing},
        )


def capability_fingerprint(capabilities: Mapping[str, bool]) -> str:
    """Return a versioned, content-addressed snapshot of a capability set."""

    digest = hashlib.sha256(_canonical_json_bytes(dict(capabilities))).hexdigest()
    return f"sha256:{digest}"
