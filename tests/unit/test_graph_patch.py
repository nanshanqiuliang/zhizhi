from __future__ import annotations

from copy import deepcopy

import pytest

from knowledge_tree_domain import GraphPatchError, preview_graph_patch
from tests.contract.test_graph_contracts import (
    CONCEPT_A_ID,
    CONCEPT_B_ID,
    COURSE_ID,
    OP_ID,
    valid_graph,
    valid_patch,
)


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
