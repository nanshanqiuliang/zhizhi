from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from knowledge_tree_contracts import ContractValidationError, validate_contract
from knowledge_tree_contracts import graph_v1 as graph_contract_module

JsonObject = dict[str, Any]

WORKSPACE_ID = "00000000-0000-7000-8000-000000000001"
COURSE_ID = "00000000-0000-7000-8000-000000000002"
RESOURCE_ID = "00000000-0000-7000-8000-000000000003"
RESOURCE_VERSION_ID = "00000000-0000-7000-8000-000000000004"
CONCEPT_A_ID = "00000000-0000-7000-8000-000000000005"
CONCEPT_B_ID = "00000000-0000-7000-8000-000000000006"
PATCH_ID = "00000000-0000-7000-8000-000000000007"
OP_ID = "00000000-0000-7000-8000-000000000008"


def valid_anchor() -> JsonObject:
    return {
        "schema_version": 1,
        "resource_id": RESOURCE_ID,
        "resource_version_id": RESOURCE_VERSION_ID,
        "source_state": {
            "content_hash": f"sha256:{'a' * 64}",
            "parser": "fixture_parser",
            "parser_version": "1.0.0",
        },
        "selectors": [
            {"type": "page_bbox", "page": 1, "bbox_norm": [0.1, 0.2, 0.8, 0.9]},
            {"type": "text_position", "start": 4, "end": 12},
        ],
        "status": "valid",
    }


def concept(concept_id: str, label: str) -> JsonObject:
    return {
        "id": concept_id,
        "course_id": COURSE_ID,
        "label": label,
        "origin": "user",
        "review_state": "accepted",
        "confidence": None,
        "evidence_ids": [],
        "locks": {
            "content": False,
            "relations": False,
            "position": False,
            "annotations": False,
        },
        "annotations": [],
        "revision_no": 0,
    }


def valid_graph() -> JsonObject:
    return {
        "schema_version": 1,
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "revision_no": 0,
        "concepts": [concept(CONCEPT_A_ID, "极限"), concept(CONCEPT_B_ID, "连续")],
        "edges": [],
        "layout_items": [],
    }


def valid_patch() -> JsonObject:
    return {
        "schema_version": 1,
        "patch_id": PATCH_ID,
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "base_revision_no": 0,
        "actor": {"type": "user", "id": "local-user"},
        "reason": "补充先修关系",
        "requires_confirmation": True,
        "confirmed": False,
        "operations": [
            {
                "op_id": OP_ID,
                "op": "create_edge",
                "expected_source_revision_no": 0,
                "expected_target_revision_no": 0,
                "edge": {
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
                },
            }
        ],
    }


@pytest.mark.parametrize(
    ("contract_name", "factory"),
    [("anchor", valid_anchor), ("course_graph", valid_graph), ("graph_patch", valid_patch)],
)
def test_v1_contract_accepts_minimal_valid_document(contract_name: str, factory: Any) -> None:
    document = factory()
    before = deepcopy(document)

    validate_contract(contract_name, document)

    assert document == before


@pytest.mark.parametrize(
    "bbox",
    [
        [0.8, 0.2, 0.1, 0.9],
        [0.1, 0.9, 0.8, 0.2],
        [-0.1, 0.2, 0.8, 0.9],
        [0.1, 0.2, 1.1, 0.9],
    ],
)
def test_anchor_rejects_invalid_bbox(bbox: list[float]) -> None:
    anchor = valid_anchor()
    anchor["selectors"] = [{"type": "page_bbox", "page": 1, "bbox_norm": bbox}]

    with pytest.raises(ContractValidationError) as raised:
        validate_contract("anchor", anchor)

    assert raised.value.code == "validation_failed"


def test_anchor_rejects_reversed_text_position() -> None:
    anchor = valid_anchor()
    anchor["selectors"] = [{"type": "text_position", "start": 12, "end": 4}]

    with pytest.raises(ContractValidationError) as raised:
        validate_contract("anchor", anchor)

    assert raised.value.code == "validation_failed"


def test_anchor_rejects_excessive_quote() -> None:
    anchor = valid_anchor()
    anchor["selectors"] = [{"type": "text_quote", "exact": "x" * 513}]

    with pytest.raises(ContractValidationError) as raised:
        validate_contract("anchor", anchor)

    assert raised.value.code == "validation_failed"


def test_contract_rejects_unknown_fields() -> None:
    graph = valid_graph()
    graph["provider_payload"] = {"vendor": "must_not_leak"}

    with pytest.raises(ContractValidationError) as raised:
        validate_contract("course_graph", graph)

    assert raised.value.code == "validation_failed"


def test_canonical_schema_is_valid_draft_2020_12_and_defines_enums_once() -> None:
    root = (
        Path(__file__).resolve().parents[2] / "docs/contracts/knowledge-tree-graph.v1.schema.json"
    )
    schema = json.loads(root.read_text(encoding="utf-8"))

    Draft202012Validator.check_schema(schema)
    assert schema["$defs"]["Origin"]["enum"] == ["user", "ai", "import", "system"]
    assert schema["$defs"]["LockDimension"]["enum"] == [
        "content",
        "relations",
        "position",
        "annotations",
    ]


def test_contract_rejects_non_uuidv7_business_id() -> None:
    graph = valid_graph()
    graph["course_id"] = "00000000-0000-4000-8000-000000000002"

    with pytest.raises(ContractValidationError) as raised:
        validate_contract("course_graph", graph)

    assert raised.value.code == "validation_failed"


def test_contract_rejects_invalid_content_hash() -> None:
    anchor = valid_anchor()
    anchor["source_state"]["content_hash"] = "sha256:not-a-digest"

    with pytest.raises(ContractValidationError) as raised:
        validate_contract("anchor", anchor)

    assert raised.value.code == "validation_failed"


def test_runtime_contract_validation_does_not_read_repository_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph_contract_module._load_graph_contract_document.cache_clear()

    def reject_runtime_file_read(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("runtime contract validation must not read repository files")

    monkeypatch.setattr(Path, "read_text", reject_runtime_file_read)

    validate_contract("course_graph", valid_graph())


@pytest.mark.parametrize(
    "selector",
    [
        {"type": "text_quote", "exact": "x" * 512, "prefix": "定义", "suffix": "结论"},
        {"type": "heading_path", "path": ["第三章", "连续函数"]},
    ],
)
def test_anchor_accepts_remaining_selector_boundaries(selector: JsonObject) -> None:
    anchor = valid_anchor()
    anchor["selectors"] = [selector]

    validate_contract("anchor", anchor)


def test_graph_patch_accepts_large_operation_set() -> None:
    """WORK-2026-046: one mind-map draft exceeds the old 100-op cap.

    A whole-corpus generation (max 40 chunks) produces create_concept +
    set_layout_item (+create_edge) per concept, so >100 operations is the normal
    case for a dense source such as paper.pdf, not an error.
    """

    patch = valid_patch()
    patch["operations"] = [deepcopy(patch["operations"][0]) for _ in range(150)]

    validate_contract("graph_patch", patch)


def test_graph_patch_enforces_operation_bound() -> None:
    """WORK-2026-046: the bound is raised from 100, not removed.

    A patch with one more operation than the canonical cap must still fail
    closed with the stable `maxItems` rule.
    """

    root = (
        Path(__file__).resolve().parents[2] / "docs/contracts/knowledge-tree-graph.v1.schema.json"
    )
    schema = json.loads(root.read_text(encoding="utf-8"))
    bound = schema["$defs"]["GraphPatch"]["properties"]["operations"]["maxItems"]
    assert isinstance(bound, int) and bound >= 101

    patch = valid_patch()
    patch["operations"] = [deepcopy(patch["operations"][0]) for _ in range(bound + 1)]

    with pytest.raises(ContractValidationError) as raised:
        validate_contract("graph_patch", patch)

    assert raised.value.code == "validation_failed"
    assert raised.value.details["rule"] == "maxItems"
