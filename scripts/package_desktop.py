"""Package the frozen desktop bundle into a portable zip (WORK-2026-033 slice 3a).

Run after `scripts/build_desktop.py`:

    uv run python scripts/package_desktop.py

Produces `dist/zhizhi-<version>-portable.zip` from the `dist/zhizhi/` onedir. The
zip is self-contained: unzip it anywhere and run `zhizhi.exe`; user data lives
in `%LOCALAPPDATA%\\知枝\\data`, so replacing the folder later (upgrade) keeps it.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

# Scripts run by path (`python scripts/package_desktop.py`) do not have the
# repository root on sys.path; add it so `apps` resolves.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from apps.desktop.version import __version__  # noqa: E402

_DIST = _ROOT / "dist"
_BUNDLE = _DIST / "zhizhi"


def main() -> None:
    if not (_BUNDLE / "zhizhi.exe").is_file():
        raise SystemExit(
            "missing dist/zhizhi/zhizhi.exe; run `uv run python scripts/build_desktop.py` first"
        )

    target = _DIST / f"zhizhi-{__version__}-portable.zip"
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(_BUNDLE.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(_DIST))
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
