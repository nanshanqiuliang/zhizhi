from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from knowledge_tree_domain import (
    GraphHistory,
    GraphHistoryError,
    semantic_graph_hash,
)

from tests.contract.test_graph_contracts import (
    CONCEPT_A_ID,
    CONCEPT_B_ID,
    COURSE_ID,
    WORKSPACE_ID,
    concept,
    valid_graph,
    valid_patch,
)

JsonObject = dict[str, Any]
TRUSTED_USER = {"type": "user", "id": "local-user"}


def confirmed_patch() -> JsonObject:
    patch = valid_patch()
    patch["confirmed"] = True
    return patch


def annotation_patch(*, base_revision: int, target_revision: int, value: str) -> JsonObject:
    return {
        "schema_version": 1,
        "patch_id": f"00000000-0000-7000-81{base_revision:02d}-000000000201",
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "base_revision_no": base_revision,
        "actor": dict(TRUSTED_USER),
        "reason": "标记重点",
        "requires_confirmation": True,
        "confirmed": True,
        "operations": [
            {
                "op_id": f"00000000-0000-7000-81{base_revision:02d}-000000000202",
                "op": "upsert_annotation",
                "target": {"type": "concept", "id": CONCEPT_A_ID},
                "expected_updated_revision_no": target_revision,
                "annotation": {"kind": "importance", "value": value},
            }
        ],
    }


def all_operations_patch() -> JsonObject:
    new_concept = concept("00000000-0000-7000-8200-000000000001", "函数")
    return {
        "schema_version": 1,
        "patch_id": "00000000-0000-7000-8200-000000000002",
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "base_revision_no": 0,
        "actor": dict(TRUSTED_USER),
        "reason": "覆盖六类修改",
        "requires_confirmation": True,
        "confirmed": True,
        "operations": [
            {
                "op_id": "00000000-0000-7000-8200-000000000003",
                "op": "create_concept",
                "concept": new_concept,
            },
            {
                "op_id": "00000000-0000-7000-8200-000000000004",
                "op": "update_concept",
                "target": {"type": "concept", "id": CONCEPT_A_ID},
                "expected_updated_revision_no": 0,
                "evidence_ids": [],
                "changes": {"label": "函数极限"},
            },
            {
                "op_id": "00000000-0000-7000-8200-000000000005",
                "op": "create_edge",
                "expected_source_revision_no": 0,
                "expected_target_revision_no": 0,
                "edge": {
                    "id": "00000000-0000-7000-8200-000000000006",
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
                },
            },
            {
                "op_id": "00000000-0000-7000-8200-000000000007",
                "op": "set_lock",
                "target": {"type": "concept", "id": CONCEPT_B_ID},
                "expected_updated_revision_no": 0,
                "dimension": "content",
                "value": True,
            },
            {
                "op_id": "00000000-0000-7000-8200-000000000008",
                "op": "upsert_annotation",
                "target": {"type": "concept", "id": CONCEPT_A_ID},
                "expected_updated_revision_no": 0,
                "annotation": {"kind": "importance", "value": "critical"},
            },
            {
                "op_id": "00000000-0000-7000-8200-000000000009",
                "op": "set_layout_item",
                "target": {"type": "concept", "id": CONCEPT_A_ID},
                "expected_updated_revision_no": 0,
                "layout_item": {
                    "view_id": "00000000-0000-7000-8200-000000000010",
                    "concept_id": CONCEPT_A_ID,
                    "x": 10.0,
                    "y": 20.0,
                    "pinned": True,
                    "revision_no": 0,
                },
            },
        ],
    }


def test_apply_creates_immutable_minimal_change_record_without_mutating_inputs() -> None:
    graph = valid_graph()
    patch = confirmed_patch()
    graph_before = deepcopy(graph)
    patch_before = deepcopy(patch)

    history = GraphHistory.start(graph).apply_patch(patch, trusted_actor=TRUSTED_USER)
    record = history.undo_records[-1]

    assert history.snapshot["revision_no"] == 1
    assert graph == graph_before
    assert patch == patch_before
    assert record.change_id == patch["patch_id"]
    assert record.before_semantic_hash == semantic_graph_hash(graph)
    assert record.after_semantic_hash == semantic_graph_hash(history.snapshot)
    assert record.deltas
    assert not hasattr(record, "snapshot")
    assert not hasattr(record, "reason")
    assert not hasattr(record, "actor")
    with pytest.raises(FrozenInstanceError):
        record.change_id = "forbidden"  # type: ignore[misc]


def test_replay_two_records_reconstructs_applied_business_semantics() -> None:
    initial = valid_graph()
    first = GraphHistory.start(initial).apply_patch(confirmed_patch(), trusted_actor=TRUSTED_USER)
    second_patch = annotation_patch(base_revision=1, target_revision=1, value="important")
    second = first.apply_patch(second_patch, trusted_actor=TRUSTED_USER)

    replayed = GraphHistory.replay(initial, second.undo_records)

    assert replayed.snapshot == second.snapshot
    assert semantic_graph_hash(replayed.snapshot) == semantic_graph_hash(second.snapshot)
    assert len(replayed.undo_records) == 2
    assert replayed.redo_records == ()


def test_snapshot_return_value_cannot_mutate_history_state() -> None:
    history = GraphHistory.start(valid_graph())
    escaped = history.snapshot

    escaped["concepts"][0]["label"] = "外部尝试修改"
    escaped["revision_no"] = 99

    assert history.snapshot == valid_graph()


def test_history_rejects_invalid_initial_graph() -> None:
    graph = valid_graph()
    graph["concepts"].append(deepcopy(graph["concepts"][0]))

    with pytest.raises(GraphHistoryError) as raised:
        GraphHistory.start(graph)

    assert raised.value.code == "validation_failed"


def test_all_six_operations_round_trip_through_undo_and_redo() -> None:
    initial = valid_graph()
    applied = GraphHistory.start(initial).apply_patch(
        all_operations_patch(), trusted_actor=TRUSTED_USER
    )

    undone = applied.undo()
    redone = undone.redo()

    assert semantic_graph_hash(undone.snapshot) == semantic_graph_hash(initial)
    assert semantic_graph_hash(redone.snapshot) == semantic_graph_hash(applied.snapshot)
    assert [
        applied.snapshot["revision_no"],
        undone.snapshot["revision_no"],
        redone.snapshot["revision_no"],
    ] == [1, 2, 3]
    assert len(undone.redo_records) == 1
    assert redone.redo_records == ()


def test_undo_then_new_apply_clears_redo_branch() -> None:
    applied = GraphHistory.start(valid_graph()).apply_patch(
        confirmed_patch(), trusted_actor=TRUSTED_USER
    )
    undone = applied.undo()
    branched = undone.apply_patch(
        annotation_patch(base_revision=2, target_revision=2, value="branch"),
        trusted_actor=TRUSTED_USER,
    )

    assert branched.redo_records == ()
    with pytest.raises(GraphHistoryError) as raised:
        branched.redo()
    assert raised.value.code == "history_empty"


def test_multiple_undo_and_redo_actions_follow_lifo_order() -> None:
    initial = valid_graph()
    first = GraphHistory.start(initial).apply_patch(confirmed_patch(), trusted_actor=TRUSTED_USER)
    second = first.apply_patch(
        annotation_patch(base_revision=1, target_revision=1, value="important"),
        trusted_actor=TRUSTED_USER,
    )

    undo_second = second.undo()
    undo_first = undo_second.undo()
    redo_first = undo_first.redo()
    redo_second = redo_first.redo()

    assert semantic_graph_hash(undo_second.snapshot) == semantic_graph_hash(first.snapshot)
    assert semantic_graph_hash(undo_first.snapshot) == semantic_graph_hash(initial)
    assert semantic_graph_hash(redo_first.snapshot) == semantic_graph_hash(first.snapshot)
    assert semantic_graph_hash(redo_second.snapshot) == semantic_graph_hash(second.snapshot)
    assert [
        second.snapshot["revision_no"],
        undo_second.snapshot["revision_no"],
        undo_first.snapshot["revision_no"],
        redo_first.snapshot["revision_no"],
        redo_second.snapshot["revision_no"],
    ] == [2, 3, 4, 5, 6]


@pytest.mark.parametrize("action", ["undo", "redo"])
def test_empty_history_action_fails_without_changing_snapshot(action: str) -> None:
    history = GraphHistory.start(valid_graph())
    before = history.snapshot

    with pytest.raises(GraphHistoryError) as raised:
        getattr(history, action)()

    assert raised.value.code == "history_empty"
    assert history.snapshot == before


def test_replay_rejects_reordered_and_duplicate_records() -> None:
    initial = valid_graph()
    first = GraphHistory.start(initial).apply_patch(confirmed_patch(), trusted_actor=TRUSTED_USER)
    second = first.apply_patch(
        annotation_patch(base_revision=1, target_revision=1, value="important"),
        trusted_actor=TRUSTED_USER,
    )
    first_record, second_record = second.undo_records

    with pytest.raises(GraphHistoryError) as reordered:
        GraphHistory.replay(initial, (second_record, first_record))
    assert reordered.value.code == "history_conflict"

    with pytest.raises(GraphHistoryError) as duplicate:
        GraphHistory.replay(initial, (first_record, first_record))
    assert duplicate.value.code == "validation_failed"
    assert duplicate.value.details["rule"] == "duplicate_change_id"


def test_replay_rejects_tampered_delta_and_drifted_initial_snapshot() -> None:
    initial = valid_graph()
    applied = GraphHistory.start(initial).apply_patch(confirmed_patch(), trusted_actor=TRUSTED_USER)
    record = applied.undo_records[0]
    tampered_delta = replace(record.deltas[0], after_json=record.deltas[0].before_json)
    tampered_record = replace(record, deltas=(tampered_delta, *record.deltas[1:]))

    with pytest.raises(GraphHistoryError) as tampered:
        GraphHistory.replay(initial, (tampered_record,))
    assert tampered.value.code == "validation_failed"
    assert tampered.value.details["rule"] == "history_record_digest_mismatch"

    drifted = valid_graph()
    drifted["concepts"][0]["label"] = "被外部篡改"
    with pytest.raises(GraphHistoryError) as conflict:
        GraphHistory.replay(drifted, applied.undo_records)
    assert conflict.value.code == "history_conflict"


def test_history_memory_path_works_with_common_io_entry_points_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject_io(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("graph history must not perform I/O")

    monkeypatch.setattr(Path, "read_text", reject_io)
    monkeypatch.setattr("builtins.open", reject_io)
    monkeypatch.setattr("socket.socket", reject_io)
    monkeypatch.setattr("subprocess.run", reject_io)

    applied = GraphHistory.start(valid_graph()).apply_patch(
        confirmed_patch(), trusted_actor=TRUSTED_USER
    )
    assert semantic_graph_hash(applied.undo().snapshot) == semantic_graph_hash(valid_graph())


@given(
    value=st.text(
        alphabet=st.characters(blacklist_categories=("Cs",)),
        min_size=1,
        max_size=64,
    )
)
@settings(max_examples=30, deadline=None)
def test_annotation_apply_undo_redo_property(value: str) -> None:
    initial = valid_graph()
    patch = annotation_patch(base_revision=0, target_revision=0, value=value)

    applied = GraphHistory.start(initial).apply_patch(patch, trusted_actor=TRUSTED_USER)
    undone = applied.undo()
    redone = undone.redo()

    assert semantic_graph_hash(undone.snapshot) == semantic_graph_hash(initial)
    assert semantic_graph_hash(redone.snapshot) == semantic_graph_hash(applied.snapshot)
