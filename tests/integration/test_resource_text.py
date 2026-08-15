"""Red-light tests for `read_resource_text` (WORK-2026-026 slice 3).

The function does not exist yet, so this file is expected to fail at
collection until implemented.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from knowledge_tree_infrastructure.workspace import (
    WorkspaceError,
    create_workspace,
    get_resource_mime,
    import_resource,
    migrate,
    parse_pdf_resource,
    read_resource_text,
)

WORKSPACE_ID = "00000000-0000-7000-8000-000000000001"


def _workspace(tmp_path: Path):
    root = tmp_path / WORKSPACE_ID
    layout = create_workspace(root)
    migrate(layout.db_path)
    return layout


def test_read_resource_text_markdown(tmp_path: Path) -> None:
    layout = _workspace(tmp_path)
    info = import_resource(
        layout, display_name="notes.md", content=b"# \xe6\x9e\x81\xe9\x99\x90\n\nlim"
    )
    assert get_resource_mime(layout, info.id) == "text/markdown"
    assert read_resource_text(layout, info.id) == "# 极限\n\nlim"


def test_read_resource_text_pdf_requires_parse(tmp_path: Path) -> None:
    layout = _workspace(tmp_path)
    pdf = (
        Path(__file__).resolve().parents[2]
        / "evals/calculus-v1/source/mit-ocw-res-18-001-chapter-02-derivatives.pdf"
    )
    if not pdf.exists():
        pytest.skip("gold.pdf fixture not present")
    content = pdf.read_bytes()
    info = import_resource(layout, display_name="gold.pdf", content=content)
    with pytest.raises(WorkspaceError) as raised:
        read_resource_text(layout, info.id)
    assert raised.value.code == "parse_pending"
    parse_pdf_resource(layout, info.id)
    text = read_resource_text(layout, info.id)
    assert text


def test_read_resource_text_missing_resource(tmp_path: Path) -> None:
    layout = _workspace(tmp_path)
    with pytest.raises(WorkspaceError) as raised:
        read_resource_text(layout, "00000000-0000-7000-8000-000000000999")
    assert raised.value.code == "workspace_missing"
