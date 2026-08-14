"""Red-light integration tests for the offline AI draft pipeline (WORK-2026-009).

`knowledge_tree_infrastructure.ai_draft` does not exist yet, so this file is
expected to fail at collection until the orchestration layer is implemented.
"""

from __future__ import annotations

from typing import Any

from knowledge_tree_domain import preview_graph_patch
from knowledge_tree_domain.ai_draft import build_draft_patch, validate_draft
from knowledge_tree_infrastructure.ai_draft import build_ai_draft

JsonObject = dict[str, Any]

WORKSPACE_ID = "00000000-0000-7000-8000-000000000001"
COURSE_ID = "00000000-0000-7000-8000-000000000002"
RESOURCE_ID = "00000000-0000-7000-8000-000000000003"
AI_ACTOR = {"type": "ai", "id": "ai-draft-pipeline"}

CALCULUS_MD = "\n\n".join(
    [
        "# 极限",
        "函数在一点趋近的值。",
        "# 连续",
        "函数在该点极限等于函数值。",
        "# 导数",
        "函数变化率的极限。",
    ]
)


def _anchor_factory() -> Any:
    state = {"n": 0}

    def factory() -> str:
        state["n"] += 1
        return f"00000000-0000-7000-9000-{state['n']:012d}"

    return factory


def _id_factory() -> Any:
    state = {"n": 0}

    def factory() -> str:
        state["n"] += 1
        return f"00000000-0000-7000-8000-{state['n']:012d}"

    return factory


def _empty_graph() -> JsonObject:
    return {
        "schema_version": 1,
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "revision_no": 0,
        "concepts": [],
        "edges": [],
        "layout_items": [],
    }


def test_build_ai_draft_extracts_concepts_and_relations_offline() -> None:
    draft = build_ai_draft(
        CALCULUS_MD,
        resource_id=RESOURCE_ID,
        anchor_id_factory=_anchor_factory(),
    )
    labels = [concept.label for concept in draft.concepts]
    assert labels == ["极限", "连续", "导数"]
    assert all(concept.evidence_ids for concept in draft.concepts)
    assert [(r.source_label, r.target_label) for r in draft.relations] == [
        ("极限", "连续"),
        ("连续", "导数"),
    ]
    validate_draft(draft)


def test_build_ai_draft_is_deterministic_and_produces_valid_patch() -> None:
    first = build_ai_draft(
        CALCULUS_MD,
        resource_id=RESOURCE_ID,
        anchor_id_factory=_anchor_factory(),
    )
    second = build_ai_draft(
        CALCULUS_MD,
        resource_id=RESOURCE_ID,
        anchor_id_factory=_anchor_factory(),
    )
    assert first == second

    patch = build_draft_patch(
        first,
        workspace_id=WORKSPACE_ID,
        course_id=COURSE_ID,
        base_revision_no=0,
        reason="AI 草案：微积分概念链",
        id_factory=_id_factory(),
    )
    preview = preview_graph_patch(_empty_graph(), patch, trusted_actor=AI_ACTOR)
    assert preview.status == "requires_confirmation"
    assert len(preview.snapshot["concepts"]) == 3
    assert len(preview.snapshot["edges"]) == 2


def test_build_ai_draft_without_anchor_factory_has_no_evidence() -> None:
    draft = build_ai_draft(CALCULUS_MD, resource_id=RESOURCE_ID)
    assert all(not concept.evidence_ids for concept in draft.concepts)
