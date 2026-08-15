"""Red-light tests for original-filename storage (WORK-2026-041).

Imports currently store files under generated UUID names, so these tests are
expected to fail until the storage naming keeps the original filename/extension.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from knowledge_tree_infrastructure.workspace import (
    create_workspace,
    get_resource_file_path,
    import_resource,
    migrate,
)


@pytest.fixture()
def layout(tmp_path: Path):
    workspace = create_workspace(tmp_path / "ws")
    migrate(workspace.db_path)
    return workspace


def test_import_keeps_original_filename_and_extension(layout) -> None:
    info = import_resource(
        layout,
        display_name="极限讲义.pdf",
        content=b"%PDF-1.7\n% fake but header-valid\n",
    )
    file_path = get_resource_file_path(layout, info.id)
    assert file_path.name == "极限讲义.pdf"
    assert file_path.suffix == ".pdf"


def test_import_name_collision_gets_suffix(layout) -> None:
    first = import_resource(layout, display_name="笔记.md", content=b"# one\n")
    second = import_resource(layout, display_name="笔记.md", content=b"# two\n")
    assert first.id != second.id
    path = get_resource_file_path(layout, second.id)
    assert path.name == "笔记-1.md"


def test_import_sanitizes_unsafe_name(layout) -> None:
    info = import_resource(
        layout,
        display_name="危险<>名称.md",
        content=b"# safe\n",
    )
    file_path = get_resource_file_path(layout, info.id)
    assert ">" not in file_path.name
    assert file_path.suffix == ".md"
