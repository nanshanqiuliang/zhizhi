"""Red-light tests for the Inno Setup installer (WORK-2026-035 slice 3b).

`apps/desktop/installer.iss` and `scripts.build_installer` do not exist yet, so
this file is expected to fail until the installer slice is implemented.
"""

from __future__ import annotations

from pathlib import Path


def test_installer_script_exists() -> None:
    iss = Path("apps/desktop/installer.iss")
    assert iss.is_file(), f"missing {iss}"


def test_installer_script_has_required_sections() -> None:
    iss = Path("apps/desktop/installer.iss")
    content = iss.read_text(encoding="utf-8")
    for token in ("[Setup]", "AppId=", "PrivilegesRequired", "[Icons]", "[Run]"):
        assert token in content, f"installer.iss missing {token!r}"


def test_build_installer_module_exists() -> None:
    import scripts.build_installer

    assert callable(scripts.build_installer.main)
