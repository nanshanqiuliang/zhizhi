"""Build the frozen Windows desktop bundle (WORK-2026-033 slice 1).

Usage (from the repository root):

    uv sync --group dev --group build
    uv run python scripts/build_desktop.py

This builds the Web UI with a same-origin API base (`VITE_LOCAL_API=""`), then
freezes the sidecar with PyInstaller. Produces `dist/zhizhi/` (onedir) containing
`zhizhi.exe` plus the bundled Web UI and LLM config. Requires `pyinstaller` from
the `build` group.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import PyInstaller.__main__  # type: ignore[import-untyped]

_ROOT = Path(__file__).resolve().parents[1]
_WEB_DIST = _ROOT / "apps" / "web" / "dist"


def _build_web() -> None:
    # A same-origin (relative) API base makes the desktop UI work on any loopback
    # port the launcher picks, instead of hard-coding http://127.0.0.1:8000.
    # `pnpm` is a .cmd shim on Windows, so resolve it through the shell.
    env = {**os.environ, "VITE_LOCAL_API": ""}
    subprocess.run(
        "pnpm --filter @knowledge-tree/web build",
        cwd=_ROOT,
        env=env,
        check=True,
        shell=True,
    )


def main() -> None:
    _build_web()
    if not (_WEB_DIST / "index.html").is_file():
        raise SystemExit("web build produced no apps/web/dist/index.html")
    try:
        PyInstaller.__main__.run(
            [str(_ROOT / "apps" / "desktop" / "build.spec"), "--noconfirm", "--clean"]
        )
    except SystemExit as error:
        if error.code not in (None, 0):
            raise


if __name__ == "__main__":
    main()
