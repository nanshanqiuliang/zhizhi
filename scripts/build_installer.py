"""Build the Inno Setup installer for the desktop bundle (WORK-2026-035 slice 3b).

Requires the frozen bundle (`dist/zhizhi/zhizhi.exe`) and Inno Setup 6 (ISCC.exe).
Produces `dist/zhizhi-<version>-setup.exe`.

Run: `uv run python scripts/build_installer.py`
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from apps.desktop.version import __version__  # noqa: E402

_DIST = _ROOT / "dist"
_BUNDLE = _DIST / "zhizhi"
_ISS = _ROOT / "apps" / "desktop" / "installer.iss"

_ISCC_CANDIDATES = [
    Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Inno Setup 6" / "ISCC.exe",
    Path(os.environ.get("PROGRAMFILES", "")) / "Inno Setup 6" / "ISCC.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
]


def _find_iscc() -> Path | None:
    for candidate in _ISCC_CANDIDATES:
        if candidate.is_file():
            return candidate
    return None


def main() -> None:
    if not (_BUNDLE / "zhizhi.exe").is_file():
        raise SystemExit(
            "missing dist/zhizhi/zhizhi.exe; run `uv run python scripts/build_desktop.py` first"
        )
    iscc = _find_iscc()
    if iscc is None:
        raise SystemExit(
            "ISCC.exe not found; install Inno Setup 6 (winget install --id JRSoftware.InnoSetup -e)"
        )
    subprocess.run(
        [str(iscc), str(_ISS), f"/DAppVersion={__version__}"],
        cwd=_ROOT,
        check=True,
    )
    setup = _DIST / f"zhizhi-{__version__}-setup.exe"
    if not setup.is_file():
        raise SystemExit(f"installer build produced no {setup}")
    print(f"wrote {setup}")


if __name__ == "__main__":
    main()
