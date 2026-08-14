"""Red-light integration tests for the persistent patch gate (WORK-2026-019).

Targets `apply_graph_patch`, `undo_graph` and `redo_graph` on
`knowledge_tree_infrastructure.workspace`, which do not exist yet, so collection
is expected to fail with ImportError until the protected commit gate is
implemented.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from knowledge_tree_domain import GraphHistory, semantic_graph_hash
from knowledge_tree_infrastructure.workspace import (
    WorkspaceError,
    apply_graph_patch,
    create_workspace,
    load_course_graph,
    load_history_records,
    migrate,
    redo_graph,
    save_course_graph,
    undo_graph,
)

from tests.contract.test_graph_contracts import (
    CONCEPT_A_ID,
    CONCEPT_B_ID,
    COURSE_ID,
    WORKSPACE_ID,
    valid_graph,
    valid_patch,
)

JsonObject = dict[str, Any]
TRUSTED_USER = {"type": "user", "id": "local-user"}


def _setup_workspace(tmp_path: Path):
    layout = create_workspace(tmp_path / "ws")
    migrate(layout.db_path)
    save_course_graph(layout, valid_graph())
    return layout


def _confirmed(patches: JsonObject) -> JsonObject:
    patch = deepcopy(patches)
    patch["confirmed"] = True
    return patch


def _edge_patch(*, base_revision: int) -> JsonObject:
    patch = valid_patch()
    patch["base_revision_no"] = base_revision
    patch["patch_id"] = f"00000000-0000-7000-9000-0000000000{base_revision + 1:02d}"
    patch["operations"][0]["op_id"] = f"00000000-0000-7000-9000-0000000001{base_revision:02d}"
    patch["operations"][0]["expected_source_revision_no"] = base_revision
    patch["operations"][0]["expected_target_revision_no"] = base_revision
    return patch


def _annotation_patch(*, base_revision: int, target_revision: int, value: str) -> JsonObject:
    return {
        "schema_version": 1,
        "patch_id": f"00000000-0000-7000-9000-0000000002{base_revision:02d}",
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "base_revision_no": base_revision,
        "actor": dict(TRUSTED_USER),
        "reason": "标记重点",
        "requires_confirmation": True,
        "confirmed": True,
        "operations": [
            {
                "op_id": f"00000000-0000-7000-9000-0000000003{base_revision:02d}",
                "op": "upsert_annotation",
                "target": {"type": "concept", "id": CONCEPT_A_ID},
                "expected_updated_revision_no": target_revision,
                "annotation": {"kind": "importance", "value": value},
            }
        ],
    }


def _set_lock_patch(*, base_revision: int, target_revision: int, dimension: str) -> JsonObject:
    return {
        "schema_version": 1,
        "patch_id": f"00000000-0000-7000-9000-0000000004{base_revision:02d}",
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "base_revision_no": base_revision,
        "actor": dict(TRUSTED_USER),
        "reason": "锁定内容",
        "requires_confirmation": True,
        "confirmed": True,
        "operations": [
            {
                "op_id": f"00000000-0000-7000-9000-0000000005{base_revision:02d}",
                "op": "set_lock",
                "target": {"type": "concept", "id": CONCEPT_B_ID},
                "expected_updated_revision_no": target_revision,
                "dimension": dimension,
                "value": True,
            }
        ],
    }


def _update_label_patch(*, base_revision: int, target_revision: int, label: str) -> JsonObject:
    return {
        "schema_version": 1,
        "patch_id": f"00000000-0000-7000-9000-0000000006{base_revision:02d}",
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "base_revision_no": base_revision,
        "actor": dict(TRUSTED_USER),
        "reason": "改标题",
        "requires_confirmation": True,
        "confirmed": True,
        "operations": [
            {
                "op_id": f"00000000-0000-7000-9000-0000000007{base_revision:02d}",
                "op": "update_concept",
                "target": {"type": "concept", "id": CONCEPT_B_ID},
                "expected_updated_revision_no": target_revision,
                "evidence_ids": [],
                "changes": {"label": label},
            }
        ],
    }


# TC-GATE-001: apply → persist → reopen → replay
def test_apply_patch_persists_and_replays(tmp_path: Path) -> None:
    layout = _setup_workspace(tmp_path)
    initial = load_course_graph(layout)

    first = apply_graph_patch(
        layout, _confirmed(_edge_patch(base_revision=0)), trusted_actor=TRUSTED_USER
    )
    second = apply_graph_patch(
        layout,
        _annotation_patch(base_revision=1, target_revision=1, value="critical"),
        trusted_actor=TRUSTED_USER,
    )

    assert first.after_revision_no == 1
    assert second.after_revision_no == 2

    current = load_course_graph(layout)
    records = load_history_records(layout)
    assert len(records) == 2
    assert current["revision_no"] == 2

    replayed = GraphHistory.replay(initial, records)
    assert semantic_graph_hash(replayed.snapshot) == semantic_graph_hash(current)


# TC-GATE-002: cross-session undo/redo
def test_undo_redo_across_sessions(tmp_path: Path) -> None:
    layout = _setup_workspace(tmp_path)
    apply_graph_patch(layout, _confirmed(_edge_patch(base_revision=0)), trusted_actor=TRUSTED_USER)
    apply_graph_patch(
        layout,
        _annotation_patch(base_revision=1, target_revision=1, value="critical"),
        trusted_actor=TRUSTED_USER,
    )

    undone = undo_graph(layout)
    assert undone["revision_no"] == 3
    assert all(concept["annotations"] == [] for concept in undone["concepts"])

    redone = redo_graph(layout)
    assert redone["revision_no"] == 4
    concept_a = next(c for c in redone["concepts"] if c["id"] == CONCEPT_A_ID)
    assert any(a.get("value") == "critical" for a in concept_a["annotations"])


def test_undo_on_empty_history_fails_closed(tmp_path: Path) -> None:
    layout = _setup_workspace(tmp_path)
    with pytest.raises(WorkspaceError) as excinfo:
        undo_graph(layout)
    assert excinfo.value.code == "history_empty"


# TC-GATE-003: locked dimension must not be overwritten
def test_locked_dimension_rejects_update(tmp_path: Path) -> None:
    layout = _setup_workspace(tmp_path)
    apply_graph_patch(layout, _confirmed(_edge_patch(base_revision=0)), trusted_actor=TRUSTED_USER)
    apply_graph_patch(
        layout,
        _set_lock_patch(base_revision=1, target_revision=1, dimension="content"),
        trusted_actor=TRUSTED_USER,
    )

    with pytest.raises(WorkspaceError) as excinfo:
        apply_graph_patch(
            layout,
            _update_label_patch(base_revision=2, target_revision=2, label="被覆盖"),
            trusted_actor=TRUSTED_USER,
        )
    assert excinfo.value.code == "target_locked"

    current = load_course_graph(layout)
    concept_b = next(c for c in current["concepts"] if c["id"] == CONCEPT_B_ID)
    assert concept_b["label"] == "连续"


def test_unconfirmed_patch_rejected(tmp_path: Path) -> None:
    layout = _setup_workspace(tmp_path)
    patch = _edge_patch(base_revision=0)
    patch["confirmed"] = False
    with pytest.raises(WorkspaceError):
        apply_graph_patch(layout, patch, trusted_actor=TRUSTED_USER)


def test_stale_base_revision_rejected(tmp_path: Path) -> None:
    layout = _setup_workspace(tmp_path)
    apply_graph_patch(layout, _confirmed(_edge_patch(base_revision=0)), trusted_actor=TRUSTED_USER)
    with pytest.raises(WorkspaceError) as excinfo:
        apply_graph_patch(
            layout, _confirmed(_edge_patch(base_revision=0)), trusted_actor=TRUSTED_USER
        )
    assert excinfo.value.code in {"patch_revision_conflict", "patch_invalid"}


# TC-GATE-004: idempotent duplicate change_id across sessions
def test_duplicate_change_id_rejected_across_sessions(tmp_path: Path) -> None:
    layout = _setup_workspace(tmp_path)
    patch = _confirmed(_edge_patch(base_revision=0))
    apply_graph_patch(layout, patch, trusted_actor=TRUSTED_USER)

    # A different operation set reusing the same change_id (replay attack) must
    # be rejected even when the base revision is current.
    duplicate = _annotation_patch(base_revision=1, target_revision=1, value="x")
    duplicate["patch_id"] = patch["patch_id"]
    with pytest.raises(WorkspaceError) as excinfo:
        apply_graph_patch(layout, duplicate, trusted_actor=TRUSTED_USER)
    assert excinfo.value.code == "patch_invalid"
    assert excinfo.value.details.get("rule") == "duplicate_change_id"


# TC-GATE-005: tampered history fails closed
def test_tampered_history_record_fails_closed(tmp_path: Path) -> None:
    layout = _setup_workspace(tmp_path)
    apply_graph_patch(layout, _confirmed(_edge_patch(base_revision=0)), trusted_actor=TRUSTED_USER)

    import sqlite3

    with sqlite3.connect(layout.db_path) as conn:
        conn.execute(
            "UPDATE history_records SET payload = replace(payload, '7000-9000', '7000-9999') "
            "WHERE seq = 1"
        )
        conn.commit()

    with pytest.raises(WorkspaceError) as excinfo:
        apply_graph_patch(
            layout,
            _annotation_patch(base_revision=1, target_revision=1, value="x"),
            trusted_actor=TRUSTED_USER,
        )
    assert excinfo.value.code == "record_tampered"
