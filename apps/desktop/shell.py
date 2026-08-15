"""Native-window shell for the desktop launcher (WORK-2026-034 slice 2).

Opens a pywebview (WebView2) window at the same-origin sidecar URL and blocks
until the user closes it, so the launcher can then shut the sidecar down.
"""

from __future__ import annotations

import webview

WINDOW_TITLE = "知枝 · 知识树笔记"


def open_window(url: str, *, title: str = WINDOW_TITLE) -> None:
    """Open a native WebView2 window and block until it is closed."""
    webview.create_window(title, url, width=1280, height=800)
    webview.start()
