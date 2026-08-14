from __future__ import annotations

from copy import deepcopy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from knowledge_tree_domain import GraphPatchError
from knowledge_tree_domain import preview_graph_patch as _preview_graph_patch

from tests.contract.test_graph_contracts import (
    CONCEPT_A_ID,
    CONCEPT_B_ID,
    COURSE_ID,
    OP_ID,
    valid_graph,
    valid_patch,
)


def preview_graph_patch(graph: dict[str, object], patch: dict[str, object]):  # type: ignore[no-untyped-def]
    return _preview_graph_patch(graph, patch, trusted_actor=patch["actor"])


def test_unconfirmed_user_patch_returns_preview_without_becoming_apply_ready() -> None:
    graph = valid_graph()
    patch = valid_patch()
    graph_before = deepcopy(graph)
    patch_before = deepcopy(patch)

    result = preview_graph_patch(graph, patch)

    assert result.status == "requires_confirmation"
    assert result.snapshot["revision_no"] == 1
    assert len(result.snapshot["edges"]) == 1
    assert graph == graph_before
    assert patch == patch_before


def test_confirmed_user_patch_is_apply_ready_and_deterministic() -> None:
    graph = valid_graph()
    patch = valid_patch()
    patch["confirmed"] = True

    first = preview_graph_patch(graph, patch)
    second = preview_graph_patch(graph, patch)

    assert first.status == "ready_to_apply"
    assert first == second


def test_rejects_stale_graph_revision_without_partial_result() -> None:
    graph = valid_graph()
    patch = valid_patch()
    graph["revision_no"] = 2
    graph_before = deepcopy(graph)

    with pytest.raises(GraphPatchError) as raised:
        preview_graph_patch(graph, patch)

    assert raised.value.code == "revision_conflict"
    assert graph == graph_before


def test_rejects_prerequisite_cycle_with_cycle_path() -> None:
    graph = valid_graph()
    patch = valid_patch()
    graph["edges"] = [
        {
            "id": "00000000-0000-7000-8000-000000000010",
            "course_id": COURSE_ID,
            "source_concept_id": CONCEPT_B_ID,
            "target_concept_id": CONCEPT_A_ID,
            "edge_type": "prerequisite_of",
            "origin": "user",
            "review_state": "accepted",
            "confidence": None,
            "evidence_ids": [],
            "locked": False,
            "revision_no": 0,
        }
    ]

    with pytest.raises(GraphPatchError) as raised:
        preview_graph_patch(graph, patch)

    assert raised.value.code == "graph_cycle_detected"
    assert raised.value.details["operation_id"] == OP_ID
    assert raised.value.details["cycle_path"][0] == raised.value.details["cycle_path"][-1]


def test_rejects_cross_course_edge_endpoint() -> None:
    graph = valid_graph()
    patch = valid_patch()
    graph["concepts"][1]["course_id"] = "00000000-0000-7000-8000-000000000099"

    with pytest.raises(GraphPatchError) as raised:
        preview_graph_patch(graph, patch)

    assert raised.value.code == "validation_failed"


def test_all_six_operations_create_expected_preview() -> None:
    graph = valid_graph()
    patch = valid_patch()
    view_id = "00000000-0000-7000-8000-000000000020"
    new_concept_id = "00000000-0000-7000-8000-000000000021"
    patch["confirmed"] = True
    patch["operations"] = [
        {
            "op_id": "00000000-0000-7000-8000-000000000022",
            "op": "create_concept",
            "concept": {
                **graph["concepts"][0],
                "id": new_concept_id,
                "label": "导数",
            },
        },
        {
            "op_id": "00000000-0000-7000-8000-000000000023",
            "op": "update_concept",
            "target": {"type": "concept", "id": CONCEPT_A_ID},
            "expected_updated_revision_no": 0,
            "evidence_ids": [],
            "changes": {"label": "函数极限"},
        },
        {
            **valid_patch()["operations"][0],
            "op_id": "00000000-0000-7000-8000-000000000024",
        },
        {
            "op_id": "00000000-0000-7000-8000-000000000025",
            "op": "set_lock",
            "target": {"type": "concept", "id": CONCEPT_A_ID},
            "expected_updated_revision_no": 0,
            "dimension": "content",
            "value": True,
        },
        {
            "op_id": "00000000-0000-7000-8000-000000000026",
            "op": "upsert_annotation",
            "target": {"type": "concept", "id": CONCEPT_A_ID},
            "expected_updated_revision_no": 0,
            "annotation": {"kind": "importance", "value": "critical"},
        },
        {
            "op_id": "00000000-0000-7000-8000-000000000027",
            "op": "set_layout_item",
            "target": {"type": "concept", "id": CONCEPT_A_ID},
            "expected_updated_revision_no": 0,
            "layout_item": {
                "view_id": view_id,
                "concept_id": CONCEPT_A_ID,
                "x": 120.5,
                "y": -25.0,
                "pinned": True,
                "revision_no": 0,
            },
        },
    ]

    result = preview_graph_patch(graph, patch)

    concepts = {item["id"]: item for item in result.snapshot["concepts"]}
    assert result.status == "ready_to_apply"
    assert result.findings == ()
    assert result.snapshot["revision_no"] == 1
    assert concepts[new_concept_id]["revision_no"] == 1
    assert concepts[CONCEPT_A_ID]["label"] == "函数极限"
    assert concepts[CONCEPT_A_ID]["locks"]["content"] is True
    assert concepts[CONCEPT_A_ID]["annotations"] == [{"kind": "importance", "value": "critical"}]
    assert result.snapshot["layout_items"][0]["view_id"] == view_id


def test_rejects_stale_edge_endpoint_revision() -> None:
    graph = valid_graph()
    patch = valid_patch()
    patch["operations"][0]["expected_target_revision_no"] = 4

    with pytest.raises(GraphPatchError) as raised:
        preview_graph_patch(graph, patch)

    assert raised.value.code == "revision_conflict"
    assert raised.value.details["rule"] == "target_revision_mismatch"


def test_rejects_duplicate_edge() -> None:
    graph = valid_graph()
    existing = deepcopy(valid_patch()["operations"][0]["edge"])
    existing["id"] = "00000000-0000-7000-8000-000000000030"
    graph["edges"] = [existing]

    with pytest.raises(GraphPatchError) as raised:
        preview_graph_patch(graph, valid_patch())

    assert raised.value.code == "validation_failed"
    assert raised.value.details["rule"] == "duplicate_edge"


def test_rejects_self_edge() -> None:
    patch = valid_patch()
    patch["operations"][0]["edge"]["target_concept_id"] = CONCEPT_A_ID

    with pytest.raises(GraphPatchError) as raised:
        preview_graph_patch(valid_graph(), patch)

    assert raised.value.code == "graph_cycle_detected"
    assert raised.value.details["operation_id"] == OP_ID
    assert raised.value.details["cycle_path"] == [CONCEPT_A_ID, CONCEPT_A_ID]


@settings(max_examples=35, deadline=None)
@given(st.integers(min_value=2, max_value=35), st.integers(min_value=0, max_value=33))
def test_any_forward_chain_edge_preserves_dag(node_count: int, source_index: int) -> None:
    source_index %= node_count - 1
    graph = valid_graph()
    graph["concepts"] = [
        {
            **graph["concepts"][0],
            "id": f"00000000-0000-7000-8000-{index + 100:012d}",
            "label": f"概念 {index}",
        }
        for index in range(node_count)
    ]
    graph["edges"] = [
        {
            **valid_patch()["operations"][0]["edge"],
            "id": f"00000000-0000-7000-8001-{index + 100:012d}",
            "source_concept_id": graph["concepts"][index]["id"],
            "target_concept_id": graph["concepts"][index + 1]["id"],
        }
        for index in range(source_index)
    ]
    patch = valid_patch()
    patch["operations"][0]["edge"].update(
        {
            "id": "00000000-0000-7000-8002-000000000100",
            "source_concept_id": graph["concepts"][source_index]["id"],
            "target_concept_id": graph["concepts"][source_index + 1]["id"],
        }
    )
    before_graph = deepcopy(graph)
    before_patch = deepcopy(patch)

    result = preview_graph_patch(graph, patch)

    assert result.snapshot["revision_no"] == 1
    assert graph == before_graph
    assert patch == before_patch


@settings(max_examples=25, deadline=None)
@given(st.integers(min_value=2, max_value=40))
def test_any_back_edge_over_a_chain_is_rejected_with_cycle_path(node_count: int) -> None:
    graph = valid_graph()
    graph["concepts"] = [
        {
            **graph["concepts"][0],
            "id": f"00000000-0000-7000-8003-{index + 100:012d}",
            "label": f"概念 {index}",
        }
        for index in range(node_count)
    ]
    graph["edges"] = [
        {
            **valid_patch()["operations"][0]["edge"],
            "id": f"00000000-0000-7000-8004-{index + 100:012d}",
            "source_concept_id": graph["concepts"][index]["id"],
            "target_concept_id": graph["concepts"][index + 1]["id"],
        }
        for index in range(node_count - 1)
    ]
    patch = valid_patch()
    patch["operations"][0]["edge"].update(
        {
            "id": "00000000-0000-7000-8005-000000000100",
            "source_concept_id": graph["concepts"][-1]["id"],
            "target_concept_id": graph["concepts"][0]["id"],
        }
    )

    with pytest.raises(GraphPatchError) as raised:
        preview_graph_patch(graph, patch)

    assert raised.value.code == "graph_cycle_detected"
    assert len(raised.value.details["cycle_path"]) == node_count + 1


def test_create_then_update_same_concept_is_atomic() -> None:
    graph = valid_graph()
    new_concept = {
        **graph["concepts"][0],
        "id": "00000000-0000-7000-8006-000000000100",
        "label": "草稿",
    }
    patch = valid_patch()
    patch["operations"] = [
        {
            "op_id": "00000000-0000-7000-8006-000000000101",
            "op": "create_concept",
            "concept": new_concept,
        },
        {
            "op_id": "00000000-0000-7000-8006-000000000102",
            "op": "update_concept",
            "target": {"type": "concept", "id": new_concept["id"]},
            "expected_updated_revision_no": 0,
            "evidence_ids": [],
            "changes": {"label": "确认后的概念"},
        },
    ]

    result = preview_graph_patch(graph, patch)

    created = next(item for item in result.snapshot["concepts"] if item["id"] == new_concept["id"])
    assert created["label"] == "确认后的概念"
    assert created["revision_no"] == 1


def test_rejects_duplicate_operation_target() -> None:
    patch = valid_patch()
    update = {
        "op_id": "00000000-0000-7000-8007-000000000100",
        "op": "update_concept",
        "target": {"type": "concept", "id": CONCEPT_A_ID},
        "expected_updated_revision_no": 0,
        "evidence_ids": [],
        "changes": {"label": "一次"},
    }
    patch["operations"] = [
        update,
        {
            **deepcopy(update),
            "op_id": "00000000-0000-7000-8007-000000000101",
            "changes": {"label": "二次"},
        },
    ]

    with pytest.raises(GraphPatchError) as raised:
        preview_graph_patch(valid_graph(), patch)

    assert raised.value.code == "validation_failed"
    assert raised.value.details["rule"] == "duplicate_operation_target"


def test_preview_supports_500_node_engineering_baseline() -> None:
    graph = valid_graph()
    graph["concepts"] = [
        {
            **graph["concepts"][0],
            "id": f"00000000-0000-7000-8014-{index + 100:012d}",
            "label": f"概念 {index}",
        }
        for index in range(500)
    ]
    graph["edges"] = [
        {
            **valid_patch()["operations"][0]["edge"],
            "id": f"00000000-0000-7000-8015-{index + 100:012d}",
            "source_concept_id": graph["concepts"][index]["id"],
            "target_concept_id": graph["concepts"][index + 1]["id"],
        }
        for index in range(499)
    ]
    patch = valid_patch()
    patch["operations"][0]["edge"].update(
        {
            "id": "00000000-0000-7000-8016-000000000100",
            "source_concept_id": graph["concepts"][0]["id"],
            "target_concept_id": graph["concepts"][-1]["id"],
            "edge_type": "related_to",
        }
    )

    result = preview_graph_patch(graph, patch)

    assert len(result.snapshot["concepts"]) == 500
    assert len(result.snapshot["edges"]) == 500


def test_delete_concept_removes_concept() -> None:
    graph = valid_graph()
    patch = valid_patch()
    patch["confirmed"] = True
    patch["operations"] = [
        {
            "op_id": "00000000-0000-7000-8017-000000000001",
            "op": "delete_concept",
            "target": {"type": "concept", "id": CONCEPT_B_ID},
            "expected_updated_revision_no": 0,
        }
    ]

    result = preview_graph_patch(graph, patch)

    assert result.status == "ready_to_apply"
    assert [c["id"] for c in result.snapshot["concepts"]] == [CONCEPT_A_ID]


def test_delete_locked_concept_rejected() -> None:
    graph = valid_graph()
    graph["concepts"][1]["locks"]["content"] = True
    patch = valid_patch()
    patch["confirmed"] = True
    patch["operations"] = [
        {
            "op_id": "00000000-0000-7000-8017-000000000002",
            "op": "delete_concept",
            "target": {"type": "concept", "id": CONCEPT_B_ID},
            "expected_updated_revision_no": 0,
        }
    ]

    with pytest.raises(GraphPatchError) as raised:
        preview_graph_patch(graph, patch)

    assert raised.value.code == "target_locked"


def test_delete_edge_removes_edge() -> None:
    graph = valid_graph()
    create = valid_patch()
    create["confirmed"] = True
    created = preview_graph_patch(graph, create)
    edge_id = created.snapshot["edges"][0]["id"]

    delete = valid_patch()
    delete["confirmed"] = True
    delete["base_revision_no"] = 1
    delete["patch_id"] = "00000000-0000-7000-8017-000000000003"
    delete["operations"] = [
        {
            "op_id": "00000000-0000-7000-8017-000000000004",
            "op": "delete_edge",
            "target": {"type": "edge", "id": edge_id},
        }
    ]

    result = preview_graph_patch(created.snapshot, delete)

    assert result.status == "ready_to_apply"
    assert result.snapshot["edges"] == []
