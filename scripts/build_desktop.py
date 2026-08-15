"""Build the frozen Windows desktop bundle (WORK-2026-033 slice 1).

Usage (from the repository root):

    pnpm --filter @knowledge-tree/web build
    uv run python scripts/build_desktop.py

Produces `dist/zhizhi/` (PyInstaller onedir) containing `zhizhi.exe` plus the
bundled Web UI and LLM config. Requires `pyinstaller` from the `build` group.
"""

from __future__ import annotations

from pathlib import Path

import PyInstaller.__main__  # type: ignore[import-untyped]

_ROOT = Path(__file__).resolve().parents[1]
_WEB_DIST = _ROOT / "apps" / "web" / "dist"


def main() -> None:
    if not (_WEB_DIST / "index.html").is_file():
        raise SystemExit(
            "apps/web/dist/index.html missing; run `pnpm --filter @knowledge-tree/web build` first."
        )
    try:
        PyInstaller.__main__.run(
            [str(_ROOT / "apps" / "desktop" / "build.spec"), "--noconfirm", "--clean"]
        )
    except SystemExit as error:
        if error.code not in (None, 0):
            raise


if __name__ == "__main__":
    main()
