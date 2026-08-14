"""Integration tests for the locked-dimension guard on whole-graph save."""

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
)

from tests.contract.test_graph_contracts import CONCEPT_B_ID, valid_graph

JsonObject = dict[str, Any]


def _setup(tmp_path: Path):
    layout = create_workspace(tmp_path / "ws")
    migrate(layout.db_path)
    return layout


def _set_lock(graph: JsonObject, concept_id: str, dimension: str, value: bool) -> JsonObject:
    changed = deepcopy(graph)
    for concept in changed["concepts"]:
        if concept["id"] == concept_id:
            concept["locks"][dimension] = value
    return changed


def _set_label(graph: JsonObject, concept_id: str, label: str) -> JsonObject:
    changed = deepcopy(graph)
    for concept in changed["concepts"]:
        if concept["id"] == concept_id:
            concept["label"] = label
    return changed


def _drop_concept(graph: JsonObject, concept_id: str) -> JsonObject:
    changed = deepcopy(graph)
    changed["concepts"] = [c for c in changed["concepts"] if c["id"] != concept_id]
    changed["edges"] = [
        e
        for e in changed["edges"]
        if e["source_concept_id"] != concept_id and e["target_concept_id"] != concept_id
    ]
    changed["layout_items"] = [
        item for item in changed["layout_items"] if item["concept_id"] != concept_id
    ]
    return changed


# TC-LOCK-001: locked content cannot be changed (enforced by the patch gate)
def test_locked_content_rejects_label_change(tmp_path: Path) -> None:
    layout = _setup(tmp_path)
    locked = _set_lock(valid_graph(), CONCEPT_B_ID, "content", True)
    save_course_graph(layout, locked)

    changed = _set_label(locked, CONCEPT_B_ID, "被覆盖")
    with pytest.raises(WorkspaceError) as excinfo:
        save_course_graph(layout, changed)
    assert excinfo.value.code == "target_locked"
    assert excinfo.value.details["rule"] == "content_lock"
    assert excinfo.value.details["dimension"] == "content"

    assert load_course_graph(layout)["concepts"][1]["label"] == "连续"


# TC-LOCK-002: unlocking is a legitimate user set_lock (no longer a "downgrade")
def test_unlock_is_allowed_via_set_lock(tmp_path: Path) -> None:
    layout = _setup(tmp_path)
    locked = _set_lock(valid_graph(), CONCEPT_B_ID, "content", True)
    save_course_graph(layout, locked)

    unlocked = _set_lock(locked, CONCEPT_B_ID, "content", False)
    save_course_graph(layout, unlocked)

    assert load_course_graph(layout)["concepts"][1]["locks"]["content"] is False


# TC-LOCK-003: a locked concept cannot be deleted
def test_locked_concept_rejects_delete(tmp_path: Path) -> None:
    layout = _setup(tmp_path)
    locked = _set_lock(valid_graph(), CONCEPT_B_ID, "content", True)
    save_course_graph(layout, locked)

    deleted = _drop_concept(locked, CONCEPT_B_ID)
    with pytest.raises(WorkspaceError) as excinfo:
        save_course_graph(layout, deleted)
    assert excinfo.value.code == "target_locked"
    assert excinfo.value.details["rule"] == "content_lock"


# TC-LOCK-004: unlocked dimensions remain editable
def test_unlocked_dimension_remains_editable(tmp_path: Path) -> None:
    layout = _setup(tmp_path)
    locked = _set_lock(valid_graph(), CONCEPT_B_ID, "content", True)
    save_course_graph(layout, locked)

    changed = _set_label(locked, "00000000-0000-7000-8000-000000000005", "极限新名")
    save_course_graph(layout, changed)

    assert load_course_graph(layout)["concepts"][0]["label"] == "极限新名"


# TC-LOCK-005 (P1-1 regression): content lock protects the whole concept
def test_locked_content_rejects_evidence_change(tmp_path: Path) -> None:
    layout = _setup(tmp_path)
    locked = _set_lock(valid_graph(), CONCEPT_B_ID, "content", True)
    save_course_graph(layout, locked)

    changed = deepcopy(locked)
    for concept in changed["concepts"]:
        if concept["id"] == CONCEPT_B_ID:
            concept["evidence_ids"] = ["00000000-0000-7000-8000-000000000099"]

    with pytest.raises(WorkspaceError) as excinfo:
        save_course_graph(layout, changed)
    assert excinfo.value.code == "target_locked"
    assert excinfo.value.details["dimension"] == "content"


# TC-LOCK-006: revision advances only on business change (not on a bare number)
def test_revision_advances_only_on_business_change(tmp_path: Path) -> None:
    layout = _setup(tmp_path)
    save_course_graph(layout, valid_graph())
    assert load_course_graph(layout)["revision_no"] == 0

    changed = _set_label(valid_graph(), CONCEPT_B_ID, "新名字")
    save_course_graph(layout, changed)
    assert load_course_graph(layout)["revision_no"] == 1

    # A bare revision_no change carries no business delta and is ignored.
    revision_only = deepcopy(changed)
    revision_only["revision_no"] = 99
    save_course_graph(layout, revision_only)
    assert load_course_graph(layout)["revision_no"] == 1
