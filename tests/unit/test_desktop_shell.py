"""Tests for the pywebview native-window shell (WORK-2026-034 slice 2)."""

from __future__ import annotations

from unittest.mock import patch

from apps.desktop.shell import WINDOW_TITLE, open_window


def test_open_window_module_exports_open_window() -> None:
    assert callable(open_window)


def test_open_window_creates_and_starts_window() -> None:
    with patch("apps.desktop.shell.webview") as webview:
        open_window("http://127.0.0.1:8000/")

    webview.create_window.assert_called_once_with(
        WINDOW_TITLE, "http://127.0.0.1:8000/", width=1280, height=800
    )
    webview.start.assert_called_once_with()


def test_open_window_honors_custom_title() -> None:
    with patch("apps.desktop.shell.webview") as webview:
        open_window("http://127.0.0.1:8000/", title="自定义")

    webview.create_window.assert_called_once_with(
        "自定义", "http://127.0.0.1:8000/", width=1280, height=800
    )
