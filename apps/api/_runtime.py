"""Runtime path bootstrap for the local sidecar (WORK-2026-033).

Shared by the API composition roots and the desktop launcher. In source-tree
runs (`python -m apps.api`) the workspace packages live under `packages/*/src`
and the LLM config under `config/llm`; in a PyInstaller-frozen build they are
bundled under `sys._MEIPASS`. `runtime_root()` returns the base directory that
holds `config/llm` (and `web_dist`) in both cases.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SOURCE_ROOTS = (
    "packages/contracts-py/src",
    "packages/domain/src",
    "packages/infrastructure/src",
)


def is_frozen() -> bool:
    """True when running inside a PyInstaller-frozen executable."""
    return getattr(sys, "frozen", False) or getattr(sys, "_MEIPASS", None) is not None


def runtime_root() -> Path:
    """Base directory holding `config/llm` (and `web_dist`), frozen-aware."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    # Source-tree run: `apps/api/_runtime.py` -> repo root is two parents up.
    return Path(__file__).resolve().parents[2]


def ensure_source_paths() -> None:
    """Add the workspace source trees to `sys.path` (source runs only)."""
    if is_frozen():
        return
    root = runtime_root()
    for src in _SOURCE_ROOTS:
        path = str(root / src)
        if path not in sys.path:
            sys.path.insert(0, path)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
