"""Deployment resolution for the LLM port (pure dict input, no file I/O).

Business code only references deployment aliases like `deepseek/fast`; the
actual provider/model IDs come from the versioned provider configuration.
Unknown aliases fail closed instead of guessing a model.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .errors import LLMProviderError

JsonObject = dict[str, Any]


def resolve_deployment(deployment_alias: str, providers: Mapping[str, Any]) -> tuple[str, str]:
    """Resolve "provider/model" to (provider_id, model_id)."""

    provider_name, separator, model_name = deployment_alias.partition("/")
    if not separator:
        raise LLMProviderError(
            "provider_invalid_request",
            details={"rule": "invalid_deployment_alias", "deployment": deployment_alias},
        )
    provider = providers.get("providers", {}).get(provider_name)
    if not isinstance(provider, dict):
        raise LLMProviderError(
            "provider_invalid_request",
            details={"rule": "unknown_deployment", "deployment": deployment_alias},
        )
    model = provider.get("models", {}).get(model_name)
    if not isinstance(model, dict):
        raise LLMProviderError(
            "provider_invalid_request",
            details={"rule": "unknown_deployment", "deployment": deployment_alias},
        )
    model_id = model.get("model_id")
    if not isinstance(model_id, str) or not model_id:
        raise LLMProviderError(
            "provider_invalid_request",
            details={"rule": "missing_model_id", "deployment": deployment_alias},
        )
    return provider_name, model_id


def select_deployment(
    task_profile: str, policies: Mapping[str, Any], providers: Mapping[str, Any]
) -> str | None:
    """Return the first *enabled* production-preference deployment, or None.

    A deployment is only selectable when its provider is explicitly
    `enabled: true`; anything else (missing key, false) fails closed.
    """

    profile = policies.get("task_profiles", {}).get(task_profile)
    if not isinstance(profile, dict):
        return None
    preference = profile.get("production_preference")
    if not isinstance(preference, list):
        return None
    for deployment_alias in preference:
        if not isinstance(deployment_alias, str):
            continue
        provider_name = deployment_alias.partition("/")[0]
        provider = providers.get("providers", {}).get(provider_name)
        if isinstance(provider, dict) and provider.get("enabled") is True:
            return deployment_alias
    return None
