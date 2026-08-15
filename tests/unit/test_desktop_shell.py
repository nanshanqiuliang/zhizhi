"""Red-light tests for the pywebview native-window shell (WORK-2026-034 slice 2).

`apps.desktop.shell` does not exist yet, so importing `open_window` is expected
to fail until the shell module is implemented.
"""

from __future__ import annotations

import pytest


def test_open_window_module_exists() -> None:
    from apps.desktop.shell import open_window

    assert callable(open_window)


@pytest.mark.skip(reason="module absent until slice 2 is implemented")
def test_open_window_creates_and_starts_window() -> None:
    from apps.desktop.shell import open_window

    open_window("http://127.0.0.1:8000/", title="知枝")
