"""Integration tests for diff-based ordinary-edit save and cross-session undo."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from knowledge_tree_infrastructure.workspace import (
    WorkspaceError,
    create_workspace,
    load_course_graph,
    migrate,
    save_course_graph,
    undo_graph,
)

from tests.contract.test_graph_contracts import (
    CONCEPT_A_ID,
    CONCEPT_B_ID,
    COURSE_ID,
    WORKSPACE_ID,
    concept,
    valid_graph,
)

JsonObject = dict[str, Any]


def _setup(tmp_path: Path):
    layout = create_workspace(tmp_path / "ws")
    migrate(layout.db_path)
    return layout


def test_ordinary_edits_are_cross_session_undoable(tmp_path: Path) -> None:
    layout = _setup(tmp_path)
    save_course_graph(layout, valid_graph())  # revision 0: A + B

    # Edit A's label -> update_concept via diff -> revision 1.
    edited = deepcopy(valid_graph())
    for c in edited["concepts"]:
        if c["id"] == CONCEPT_A_ID:
            c["label"] = "极限新"
    save_course_graph(layout, edited)
    assert load_course_graph(layout)["revision_no"] == 1

    # Add concept C -> create_concept via diff -> revision 2.
    with_c = deepcopy(edited)
    with_c["concepts"].append(concept("00000000-0000-7000-8020-000000000001", "函数"))
    save_course_graph(layout, with_c)
    assert load_course_graph(layout)["revision_no"] == 2

    # Delete B -> delete_concept via diff -> revision 3.
    without_b = deepcopy(with_c)
    without_b["concepts"] = [c for c in without_b["concepts"] if c["id"] != CONCEPT_B_ID]
    without_b["edges"] = [
        e
        for e in without_b["edges"]
        if e["source_concept_id"] != CONCEPT_B_ID and e["target_concept_id"] != CONCEPT_B_ID
    ]
    save_course_graph(layout, without_b)
    current = load_course_graph(layout)
    assert current["revision_no"] == 3
    assert all(c["id"] != CONCEPT_B_ID for c in current["concepts"])

    # Undo the delete -> B returns -> revision 4.
    undone = undo_graph(layout)
    assert undone["revision_no"] == 4
    assert any(c["id"] == CONCEPT_B_ID for c in undone["concepts"])

    # Undo the add -> C gone -> revision 5.
    undone2 = undo_graph(layout)
    assert undone2["revision_no"] == 5
    assert all(c["id"] != "00000000-0000-7000-8020-000000000001" for c in undone2["concepts"])


def test_noop_save_preserves_revision_and_history(tmp_path: Path) -> None:
    layout = _setup(tmp_path)
    save_course_graph(layout, valid_graph())

    # A semantic no-op save must not advance revision or append history.
    save_course_graph(layout, deepcopy(valid_graph()))
    assert load_course_graph(layout)["revision_no"] == 0


def test_delete_concept_rejects_surviving_relations_lock(tmp_path: Path) -> None:
    layout = _setup(tmp_path)
    base = deepcopy(valid_graph())
    base["edges"].append(
        {
            "id": "00000000-0000-7000-8000-000000000009",
            "course_id": COURSE_ID,
            "source_concept_id": CONCEPT_A_ID,
            "target_concept_id": CONCEPT_B_ID,
            "edge_type": "prerequisite_of",
            "origin": "user",
            "review_state": "accepted",
            "confidence": None,
            "evidence_ids": [],
            "locked": False,
            "revision_no": 0,
        }
    )
    save_course_graph(layout, base)

    locked = deepcopy(base)
    for c in locked["concepts"]:
        if c["id"] == CONCEPT_B_ID:
            c["locks"]["relations"] = True
    save_course_graph(layout, locked)

    # Deleting A cascades the A->B edge, which touches B's locked relations.
    deleted = deepcopy(locked)
    deleted["concepts"] = [c for c in deleted["concepts"] if c["id"] != CONCEPT_A_ID]
    deleted["edges"] = [e for e in deleted["edges"] if e["source_concept_id"] != CONCEPT_A_ID]
    with pytest.raises(WorkspaceError) as excinfo:
        save_course_graph(layout, deleted)
    assert excinfo.value.code == "target_locked"


def test_new_concept_layout_is_preserved(tmp_path: Path) -> None:
    layout = _setup(tmp_path)
    save_course_graph(layout, valid_graph())

    with_c = deepcopy(valid_graph())
    with_c["concepts"].append(concept("00000000-0000-7000-8021-000000000001", "函数"))
    with_c["layout_items"].append(
        {
            "view_id": WORKSPACE_ID,
            "concept_id": "00000000-0000-7000-8021-000000000001",
            "x": 120,
            "y": 240,
            "pinned": False,
            "revision_no": 0,
        }
    )
    save_course_graph(layout, with_c)

    current = load_course_graph(layout)
    assert any(
        li["concept_id"] == "00000000-0000-7000-8021-000000000001" and li["x"] == 120
        for li in current["layout_items"]
    )
