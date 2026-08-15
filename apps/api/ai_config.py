"""DeepSeek API key configuration for the local sidecar (WORK-2026-038).

The key is saved (via the Web settings dialog) to `data_root/ai.json` and read
back with priority over the `DEEPSEEK_API_KEY` environment variable, which
remains a fallback for dev/CI. The key is stored in plain text inside the user's
local data directory (documented boundary); it never leaves the machine and is
never returned by any endpoint.
"""

from __future__ import annotations

import json
import os
from contextlib import suppress
from pathlib import Path

_ENV_KEY = "DEEPSEEK_API_KEY"
_CONFIG_FILE = "ai.json"


def _config_path(data_root: Path) -> Path:
    return data_root / _CONFIG_FILE


def load_api_key(data_root: Path) -> str | None:
    """Return the saved key (config file first, then environment)."""
    config = _config_path(data_root)
    try:
        payload = json.loads(config.read_text(encoding="utf-8"))
        key = payload.get("api_key")
        if isinstance(key, str) and key:
            return key
    except (OSError, ValueError):
        pass
    return os.environ.get(_ENV_KEY) or None


def save_api_key(data_root: Path, api_key: str | None) -> None:
    """Write the key to `ai.json`, or delete the file when `api_key` is None."""
    config = _config_path(data_root)
    if api_key is None:
        with suppress(OSError):
            config.unlink()
        return
    data_root.mkdir(parents=True, exist_ok=True)
    config.write_text(json.dumps({"api_key": api_key}), encoding="utf-8")
