from __future__ import annotations

from copy import deepcopy

import pytest
from knowledge_tree_domain import GraphPatchError
from knowledge_tree_domain import preview_graph_patch as _preview_graph_patch

from tests.contract.test_graph_contracts import CONCEPT_A_ID, OP_ID, valid_graph, valid_patch


def preview_graph_patch(graph: dict[str, object], patch: dict[str, object]):  # type: ignore[no-untyped-def]
    return _preview_graph_patch(graph, patch, trusted_actor=patch["actor"])


def test_ai_patch_cannot_claim_apply_ready() -> None:
    graph = valid_graph()
    patch = valid_patch()
    patch["actor"] = {"type": "ai", "id": "draft-agent"}
    patch["confirmed"] = True
    patch["operations"][0]["edge"]["origin"] = "ai"
    patch["operations"][0]["edge"]["evidence_ids"] = ["00000000-0000-7000-8011-000000000100"]

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


@pytest.mark.parametrize("actor_type", ["ai", "import", "system"])
def test_non_user_patch_never_becomes_apply_ready(actor_type: str) -> None:
    patch = valid_patch()
    patch["actor"] = {"type": actor_type, "id": "draft-source"}
    patch["confirmed"] = True
    patch["operations"][0]["edge"]["origin"] = actor_type
    if actor_type == "ai":
        patch["operations"][0]["edge"]["evidence_ids"] = ["00000000-0000-7000-8011-000000000101"]

    result = preview_graph_patch(valid_graph(), patch)

    assert result.status == "requires_confirmation"


@pytest.mark.parametrize(
    ("dimension", "operation"),
    [
        (
            "content",
            {
                "op_id": "00000000-0000-7000-8008-000000000100",
                "op": "update_concept",
                "target": {"type": "concept", "id": CONCEPT_A_ID},
                "expected_updated_revision_no": 0,
                "evidence_ids": ["00000000-0000-7000-8011-000000000102"],
                "changes": {"label": "禁止覆盖"},
            },
        ),
        ("relations", valid_patch()["operations"][0]),
        (
            "position",
            {
                "op_id": "00000000-0000-7000-8008-000000000101",
                "op": "set_layout_item",
                "target": {"type": "concept", "id": CONCEPT_A_ID},
                "expected_updated_revision_no": 0,
                "layout_item": {
                    "view_id": "00000000-0000-7000-8008-000000000102",
                    "concept_id": CONCEPT_A_ID,
                    "x": 1,
                    "y": 2,
                    "pinned": False,
                    "revision_no": 0,
                },
            },
        ),
        (
            "annotations",
            {
                "op_id": "00000000-0000-7000-8008-000000000103",
                "op": "upsert_annotation",
                "target": {"type": "concept", "id": CONCEPT_A_ID},
                "expected_updated_revision_no": 0,
                "annotation": {"kind": "importance", "value": "critical"},
            },
        ),
    ],
)
def test_locked_dimension_rejects_matching_change(
    dimension: str, operation: dict[str, object]
) -> None:
    graph = valid_graph()
    graph["concepts"][0]["locks"][dimension] = True
    patch = valid_patch()
    patch["actor"] = {"type": "ai", "id": "draft-agent"}
    patch["operations"] = [deepcopy(operation)]
    if dimension == "relations":
        patch["operations"][0]["edge"]["origin"] = "ai"
        patch["operations"][0]["edge"]["evidence_ids"] = ["00000000-0000-7000-8011-000000000103"]

    with pytest.raises(GraphPatchError) as raised:
        preview_graph_patch(graph, patch)

    assert raised.value.code == "target_locked"
    assert raised.value.details["dimension"] == dimension


def test_ai_concept_requires_evidence_reference() -> None:
    graph = valid_graph()
    patch = valid_patch()
    patch["actor"] = {"type": "ai", "id": "draft-agent"}
    patch["operations"] = [
        {
            "op_id": "00000000-0000-7000-8009-000000000100",
            "op": "create_concept",
            "concept": {
                **graph["concepts"][0],
                "id": "00000000-0000-7000-8009-000000000101",
                "origin": "ai",
                "confidence": 0.9,
                "evidence_ids": [],
            },
        }
    ]

    with pytest.raises(GraphPatchError) as raised:
        preview_graph_patch(graph, patch)

    assert raised.value.code == "evidence_required"


def test_user_concept_cannot_claim_ai_confidence() -> None:
    graph = valid_graph()
    patch = valid_patch()
    patch["operations"] = [
        {
            "op_id": "00000000-0000-7000-8010-000000000100",
            "op": "create_concept",
            "concept": {
                **graph["concepts"][0],
                "id": "00000000-0000-7000-8010-000000000101",
                "confidence": 0.9,
            },
        }
    ]

    with pytest.raises(GraphPatchError) as raised:
        preview_graph_patch(graph, patch)

    assert raised.value.code == "validation_failed"
    assert raised.value.details["rule"] == "user_confidence_must_be_null"


@pytest.mark.parametrize("entity", ["concept", "edge"])
def test_ai_cannot_spoof_user_origin(entity: str) -> None:
    graph = valid_graph()
    patch = valid_patch()
    patch["actor"] = {"type": "ai", "id": "draft-agent"}
    if entity == "concept":
        patch["operations"] = [
            {
                "op_id": "00000000-0000-7000-8012-000000000100",
                "op": "create_concept",
                "concept": {
                    **graph["concepts"][0],
                    "id": "00000000-0000-7000-8012-000000000101",
                    "origin": "user",
                },
            }
        ]

    with pytest.raises(GraphPatchError) as raised:
        preview_graph_patch(graph, patch)

    assert raised.value.code == "validation_failed"
    assert raised.value.details["rule"] == "actor_origin_mismatch"


def test_ai_update_concept_requires_operation_evidence() -> None:
    patch = valid_patch()
    patch["actor"] = {"type": "ai", "id": "draft-agent"}
    patch["operations"] = [
        {
            "op_id": "00000000-0000-7000-8013-000000000100",
            "op": "update_concept",
            "target": {"type": "concept", "id": CONCEPT_A_ID},
            "expected_updated_revision_no": 0,
            "evidence_ids": [],
            "changes": {"label": "AI 建议名称"},
        }
    ]

    with pytest.raises(GraphPatchError) as raised:
        preview_graph_patch(valid_graph(), patch)

    assert raised.value.code == "evidence_required"
    assert raised.value.details["rule"] == "ai_concept_update_evidence"


def test_ai_payload_cannot_self_declare_user_actor() -> None:
    patch = valid_patch()
    patch["actor"] = {"type": "user", "id": "local-user"}
    patch["confirmed"] = True
    graph = valid_graph()
    graph_before = deepcopy(graph)
    patch_before = deepcopy(patch)

    with pytest.raises(GraphPatchError) as raised:
        _preview_graph_patch(
            graph,
            patch,
            trusted_actor={"type": "ai", "id": "draft-agent"},
        )

    assert raised.value.code == "permission_denied"
    assert raised.value.details["rule"] == "actor_context_mismatch"
    assert graph == graph_before
    assert patch == patch_before


def test_ai_cannot_set_an_unlocked_dimension() -> None:
    patch = valid_patch()
    patch["actor"] = {"type": "ai", "id": "draft-agent"}
    patch["operations"] = [
        {
            "op_id": "00000000-0000-7000-8017-000000000100",
            "op": "set_lock",
            "target": {"type": "concept", "id": CONCEPT_A_ID},
            "expected_updated_revision_no": 0,
            "dimension": "content",
            "value": True,
        }
    ]

    with pytest.raises(GraphPatchError) as raised:
        preview_graph_patch(valid_graph(), patch)

    assert raised.value.code == "validation_failed"
    assert raised.value.details["rule"] == "only_user_may_set_lock"
