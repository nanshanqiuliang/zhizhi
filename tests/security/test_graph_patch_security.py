from __future__ import annotations

from copy import deepcopy

import pytest

from knowledge_tree_domain import GraphPatchError, preview_graph_patch
from tests.contract.test_graph_contracts import CONCEPT_A_ID, OP_ID, valid_graph, valid_patch


def test_ai_patch_cannot_claim_apply_ready() -> None:
    graph = valid_graph()
    patch = valid_patch()
    patch["actor"] = {"type": "ai", "id": "draft-agent"}
    patch["confirmed"] = True

    result = preview_graph_patch(graph, patch)

    assert result.status == "requires_confirmation"


@pytest.mark.parametrize("dimension", ["content", "relations", "position", "annotations"])
def test_ai_cannot_modify_locked_dimension(dimension: str) -> None:
    graph = valid_graph()
    graph["concepts"][0]["locks"][dimension] = True
    graph_before = deepcopy(graph)
    patch = valid_patch()
    patch["actor"] = {"type": "ai", "id": "draft-agent"}
    patch["operations"] = [
        {
            "op_id": OP_ID,
            "op": "set_lock",
            "target": {"type": "concept", "id": CONCEPT_A_ID},
            "expected_updated_revision_no": 0,
            "dimension": dimension,
            "value": False,
        }
    ]

    with pytest.raises(GraphPatchError) as raised:
        preview_graph_patch(graph, patch)

    assert raised.value.code == "target_locked"
    assert graph == graph_before


def test_ai_prerequisite_edge_requires_evidence() -> None:
    graph = valid_graph()
    patch = valid_patch()
    patch["actor"] = {"type": "ai", "id": "draft-agent"}
    patch["operations"][0]["edge"]["origin"] = "ai"

    with pytest.raises(GraphPatchError) as raised:
        preview_graph_patch(graph, patch)

    assert raised.value.code == "evidence_required"
