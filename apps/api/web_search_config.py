"""Web-search provider configuration for the local sidecar (WORK-2026-053).

Mirrors `apps.api.ai_config`: the provider + key are saved (via the Web
settings dialog) to `data_root/web-search.json` and read back with priority
over environment variables (`ZHIZHI_WEB_SEARCH_PROVIDER`, then per-provider
`TAVILY_API_KEY` / `BRAVE_API_KEY`), which remain fallbacks for dev/CI. The
key is stored in plain text inside the user's local data directory
(documented boundary); it never leaves the machine and is never returned by
any endpoint.
"""

from __future__ import annotations

import json
import os
from contextlib import suppress
from pathlib import Path

_ENV_PROVIDER = "ZHIZHI_WEB_SEARCH_PROVIDER"
_ENV_KEYS = {"tavily": "TAVILY_API_KEY", "brave": "BRAVE_API_KEY"}
_CONFIG_FILE = "web-search.json"
_PROVIDERS = ("tavily", "brave")


def _config_path(data_root: Path) -> Path:
    return data_root / _CONFIG_FILE


def load_web_search_config(data_root: Path) -> dict[str, str | None]:
    """Return `{"provider", "api_key"}` (config file first, then environment)."""

    provider: str | None = None
    api_key: str | None = None
    try:
        payload = json.loads(_config_path(data_root).read_text(encoding="utf-8"))
        if isinstance(payload.get("provider"), str):
            provider = payload["provider"]
        if isinstance(payload.get("api_key"), str) and payload["api_key"]:
            api_key = payload["api_key"]
    except (OSError, ValueError):
        pass
    if provider not in _PROVIDERS:
        env_provider = os.environ.get(_ENV_PROVIDER)
        provider = env_provider if env_provider in _PROVIDERS else "tavily"
    if api_key is None:
        api_key = os.environ.get(_ENV_KEYS[provider]) or None
    return {"provider": provider, "api_key": api_key}


def save_web_search_config(data_root: Path, provider: str, api_key: str | None) -> None:
    """Persist provider+key, or delete the file when the key is None."""

    if provider not in _PROVIDERS:
        raise ValueError(f"unknown web search provider: {provider}")
    config = _config_path(data_root)
    if api_key is None:
        with suppress(OSError):
            config.unlink()
        return
    data_root.mkdir(parents=True, exist_ok=True)
    config.write_text(json.dumps({"provider": provider, "api_key": api_key}), encoding="utf-8")
