# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Knowledge Tree desktop sidecar (WORK-2026-033).

Freezes `apps.desktop.launcher` as a loopback sidecar that also serves the built
Web UI. The Web UI (`apps/web/dist`) and the LLM config (`config/llm`) are
bundled under `_MEIPASS` and resolved at runtime by `apps.api._runtime.runtime_root()`.

Build via `scripts/build_desktop.py` (run `pnpm --filter @knowledge-tree/web build` first).
"""

from pathlib import Path

root = Path(SPECPATH).resolve().parents[1]  # repo root (spec lives in apps/desktop)

source_roots = [
    str(root),
    str(root / "packages" / "contracts-py" / "src"),
    str(root / "packages" / "domain" / "src"),
    str(root / "packages" / "infrastructure" / "src"),
]

# uvicorn loads loop/protocol/lifespan modules via importlib; the launcher pins
# asyncio + h11, but keep the auto fallbacks importable in the frozen bundle.
# pywebview selects its Windows backend dynamically, so list it and the
# pythonnet loader explicitly (hook-webview/hook-clr collect their data/binaries).
hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
    "clr",
    "clr_loader",
    "webview.platforms.winforms",
    "webview.platforms.edgechromium",
]

datas = [
    (str(root / "config" / "llm"), "config/llm"),
    (str(root / "apps" / "web" / "dist"), "web_dist"),
]

a = Analysis(
    [str(root / "apps" / "desktop" / "launcher.py")],
    pathex=source_roots,
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="zhizhi",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="zhizhi",
)
