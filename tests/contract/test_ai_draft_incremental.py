"""Red-light tests for incremental rebuild kernel (WORK-2026-030, Step 9 slice 3a).

`build_incremental_patch` does not exist yet, so this file is expected to fail
at collection until implemented.
"""

from __future__ import annotations

from typing import Any

import pytest
from knowledge_tree_domain import preview_graph_patch
from knowledge_tree_domain.ai_draft import (
    AiDraft,
    DraftConcept,
    DraftRelation,
    build_incremental_patch,
)

JsonObject = dict[str, Any]

WORKSPACE_ID = "00000000-0000-7000-8000-000000000001"
COURSE_ID = "00000000-0000-7000-8000-000000000002"
LIMIT_ID = "00000000-0000-7000-8000-000000000101"
AI_ACTOR = {"type": "ai", "id": "ai-draft-pipeline"}
EVIDENCE = "00000000-0000-7000-9000-000000000001"


def _existing_graph() -> JsonObject:
    return {
        "schema_version": 1,
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "revision_no": 2,
        "concepts": [
            {
                "id": LIMIT_ID,
                "course_id": COURSE_ID,
                "label": "极限",
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
                "revision_no": 2,
            }
        ],
        "edges": [],
        "layout_items": [],
    }


def _counter() -> Any:
    state = {"n": 0}

    def factory() -> str:
        state["n"] += 1
        return f"00000000-0000-7000-9100-{state['n']:012d}"

    return factory


def test_incremental_patch_dedupes_existing_and_resolves_mixed_endpoints() -> None:
    draft = AiDraft(
        concepts=(
            DraftConcept(label="极限", confidence=0.8, evidence_ids=()),  # existing
            DraftConcept(label="导数", confidence=0.8, evidence_ids=(EVIDENCE,)),  # new
        ),
        relations=(DraftRelation("极限", "导数", "prerequisite_of", 0.7, (EVIDENCE,)),),
    )
    patch = build_incremental_patch(
        _existing_graph(),
        draft,
        workspace_id=WORKSPACE_ID,
        course_id=COURSE_ID,
        base_revision_no=2,
        reason="增量：补充导数",
        id_factory=_counter(),
    )
    creates = [op for op in patch["operations"] if op["op"] == "create_concept"]
    layouts = [op for op in patch["operations"] if op["op"] == "set_layout_item"]
    edges = [op for op in patch["operations"] if op["op"] == "create_edge"]
    assert [op["concept"]["label"] for op in creates] == ["导数"]
    assert [op["layout_item"]["concept_id"] for op in layouts] == [creates[0]["concept"]["id"]]
    edge = edges[0]
    assert edge["edge"]["source_concept_id"] == LIMIT_ID
    assert edge["edge"]["target_concept_id"] == creates[0]["concept"]["id"]
    assert edge["expected_source_revision_no"] == 2
    assert edge["expected_target_revision_no"] == 0


def test_incremental_patch_rejects_new_concept_without_evidence() -> None:
    draft = AiDraft(
        concepts=(DraftConcept(label="导数", confidence=0.8, evidence_ids=()),),
        relations=(),
    )
    with pytest.raises(ValueError):
        build_incremental_patch(
            _existing_graph(),
            draft,
            workspace_id=WORKSPACE_ID,
            course_id=COURSE_ID,
            base_revision_no=2,
            reason="x",
            id_factory=_counter(),
        )


def test_incremental_patch_preview_requires_confirmation() -> None:
    draft = AiDraft(
        concepts=(DraftConcept(label="导数", confidence=0.8, evidence_ids=(EVIDENCE,)),),
        relations=(),
    )
    patch = build_incremental_patch(
        _existing_graph(),
        draft,
        workspace_id=WORKSPACE_ID,
        course_id=COURSE_ID,
        base_revision_no=2,
        reason="增量：补充导数",
        id_factory=_counter(),
    )
    preview = preview_graph_patch(_existing_graph(), patch, trusted_actor=AI_ACTOR)
    assert preview.status == "requires_confirmation"
    assert len(preview.snapshot["concepts"]) == 2
