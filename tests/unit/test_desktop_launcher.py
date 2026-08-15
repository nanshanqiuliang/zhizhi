"""Unit tests for the desktop launcher helpers (WORK-2026-033 slice 1).

`_read_lock_port` is the crash-recovery safety net for the single-instance guard:
it must tolerate corrupt/partial lock files without treating them as a live
instance, and `_default_data_root` must resolve to a per-user location that
survives app upgrades.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.desktop.launcher import _default_data_root, _read_lock_port


def test_read_lock_port_valid(tmp_path: Path) -> None:
    lock = tmp_path / ".lock"
    lock.write_text(json.dumps({"pid": 123, "port": 8765}), encoding="utf-8")
    assert _read_lock_port(lock) == 8765


def test_read_lock_port_corrupt(tmp_path: Path) -> None:
    lock = tmp_path / ".lock"
    lock.write_text("not-json", encoding="utf-8")
    assert _read_lock_port(lock) is None


def test_read_lock_port_missing_port(tmp_path: Path) -> None:
    lock = tmp_path / ".lock"
    lock.write_text(json.dumps({"pid": 123}), encoding="utf-8")
    assert _read_lock_port(lock) is None


def test_read_lock_port_non_int_port(tmp_path: Path) -> None:
    lock = tmp_path / ".lock"
    lock.write_text(json.dumps({"pid": 123, "port": "abc"}), encoding="utf-8")
    assert _read_lock_port(lock) is None


def test_default_data_root_uses_localappdata(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert _default_data_root() == tmp_path / "知枝" / "data"


def test_default_data_root_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    assert _default_data_root() == Path.home() / "AppData" / "Local" / "知枝" / "data"
