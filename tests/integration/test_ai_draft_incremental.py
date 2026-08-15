"""Red-light tests for incremental rebuild LLM wiring (WORK-2026-031, Step 9 slice 3b).

`build_incremental_ai_draft` does not exist yet, so this file is expected to
fail at collection until implemented.
"""

from __future__ import annotations

from typing import Any

from knowledge_tree_domain import preview_graph_patch
from knowledge_tree_domain.ai_draft import (
    AiDraft,
    build_incremental_patch,
    normalize_concept_label,
)
from knowledge_tree_infrastructure.ai_draft import (
    HeuristicConceptExtractor,
    HeuristicRelationProvider,
    build_incremental_ai_draft,
)

JsonObject = dict[str, Any]

WORKSPACE_ID = "00000000-0000-7000-8000-000000000001"
COURSE_ID = "00000000-0000-7000-8000-000000000002"
RESOURCE_ID = "00000000-0000-7000-8000-000000000003"
LIMIT_ID = "00000000-0000-7000-8000-000000000101"
AI_ACTOR = {"type": "ai", "id": "ai-draft-pipeline"}

TEXT = "\n\n".join(["# 导数", "函数变化率的极限。", "# 连续", "极限等于函数值。"])


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


def _anchor_factory() -> Any:
    state = {"n": 0}

    def factory() -> str:
        state["n"] += 1
        return f"00000000-0000-7000-9000-{state['n']:012d}"

    return factory


def _counter() -> Any:
    state = {"n": 0}

    def factory() -> str:
        state["n"] += 1
        return f"00000000-0000-7000-9100-{state['n']:012d}"

    return factory


def test_incremental_ai_draft_dedupes_existing_and_filters_relations() -> None:
    draft = build_incremental_ai_draft(
        _existing_graph(),
        TEXT,
        resource_id=RESOURCE_ID,
        extractor=HeuristicConceptExtractor(),
        relation_provider=HeuristicRelationProvider(),
        anchor_id_factory=_anchor_factory(),
    )
    labels = [concept.label for concept in draft.concepts]
    # Existing "极限" is a placeholder; new "导数"/"连续" are appended.
    assert labels == ["极限", "导数", "连续"]
    new_keys = {"导数", "连续"}
    for relation in draft.relations:
        # No existing->existing relation survives the filter.
        assert (
            normalize_concept_label(relation.source_label) in new_keys
            or normalize_concept_label(relation.target_label) in new_keys
        )


def test_incremental_ai_draft_chains_to_valid_patch_without_duplicates() -> None:
    draft = build_incremental_ai_draft(
        _existing_graph(),
        TEXT,
        resource_id=RESOURCE_ID,
        extractor=HeuristicConceptExtractor(),
        relation_provider=HeuristicRelationProvider(),
        anchor_id_factory=_anchor_factory(),
    )
    patch = build_incremental_patch(
        _existing_graph(),
        draft,
        workspace_id=WORKSPACE_ID,
        course_id=COURSE_ID,
        base_revision_no=2,
        reason="增量：补充导数与连续",
        id_factory=_counter(),
    )
    creates = [op for op in patch["operations"] if op["op"] == "create_concept"]
    labels = [op["concept"]["label"] for op in creates]
    assert labels == ["导数", "连续"]
    assert LIMIT_ID not in [op["concept"]["id"] for op in creates]
    preview = preview_graph_patch(_existing_graph(), patch, trusted_actor=AI_ACTOR)
    assert preview.status == "requires_confirmation"
    assert len(preview.snapshot["concepts"]) == 3
