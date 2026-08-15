"""Integration tests for incremental rebuild LLM wiring (WORK-2026-031, Step 9 slice 3b)."""

from __future__ import annotations

from typing import Any

from knowledge_tree_domain import preview_graph_patch
from knowledge_tree_domain.ai_draft import build_incremental_patch
from knowledge_tree_infrastructure.ai_draft import (
    HeuristicConceptExtractor,
    HeuristicRelationProvider,
    build_ai_draft,
    build_incremental_ai_draft,
)

JsonObject = dict[str, Any]

WORKSPACE_ID = "00000000-0000-7000-8000-000000000001"
COURSE_ID = "00000000-0000-7000-8000-000000000002"
RESOURCE_ID = "00000000-0000-7000-8000-000000000003"
AI_ACTOR = {"type": "ai", "id": "ai-draft-pipeline"}


def _graph(*labels: str) -> JsonObject:
    def concept(index: int, label: str) -> JsonObject:
        return {
            "id": f"00000000-0000-7000-8000-0000000001{index:02d}",
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
            "revision_no": 2,
        }

    return {
        "schema_version": 1,
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "revision_no": 2,
        "concepts": [concept(index, label) for index, label in enumerate(labels)],
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


def test_incremental_ai_draft_dedupes_colliding_candidate_and_keeps_placeholder_evidence() -> None:
    text = "\n\n".join(
        ["# 极限", "函数趋近的值。", "# 导数", "变化率的极限。", "# 连续", "极限等于函数值。"]
    )
    draft = build_incremental_ai_draft(
        _graph("极限"),
        text,
        resource_id=RESOURCE_ID,
        extractor=HeuristicConceptExtractor(),
        relation_provider=HeuristicRelationProvider(),
        anchor_id_factory=_anchor_factory(),
    )
    labels = [concept.label for concept in draft.concepts]
    # Colliding "极限" candidate is dropped; the placeholder + two new remain.
    assert labels == ["极限", "导数", "连续"]
    placeholder = draft.concepts[0]
    assert placeholder.evidence_ids == ()
    assert all(concept.evidence_ids for concept in draft.concepts[1:])


def test_incremental_ai_draft_filters_existing_to_existing_relations() -> None:
    text = "\n\n".join(["# 导数", "变化率的极限。"])
    draft = build_incremental_ai_draft(
        _graph("极限", "连续"),
        text,
        resource_id=RESOURCE_ID,
        extractor=HeuristicConceptExtractor(),
        relation_provider=HeuristicRelationProvider(),
        anchor_id_factory=_anchor_factory(),
    )
    # Chain would be 极限->连续 (existing->existing, dropped) and 连续->导数 (kept).
    pairs = [(relation.source_label, relation.target_label) for relation in draft.relations]
    assert pairs == [("连续", "导数")]


def test_incremental_ai_draft_chains_to_valid_patch_without_duplicates() -> None:
    text = "\n\n".join(["# 导数", "函数变化率的极限。", "# 连续", "极限等于函数值。"])
    draft = build_incremental_ai_draft(
        _graph("极限"),
        text,
        resource_id=RESOURCE_ID,
        extractor=HeuristicConceptExtractor(),
        relation_provider=HeuristicRelationProvider(),
        anchor_id_factory=_anchor_factory(),
    )
    patch = build_incremental_patch(
        _graph("极限"),
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
    preview = preview_graph_patch(_graph("极限"), patch, trusted_actor=AI_ACTOR)
    assert preview.status == "requires_confirmation"
    assert len(preview.snapshot["concepts"]) == 3


def test_deepseek_draft_generator_fails_closed_without_key(monkeypatch: Any) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    from apps.api.ai_draft import build_deepseek_draft_generator

    assert build_deepseek_draft_generator() is None


def test_incremental_ai_draft_empty_graph_matches_full_draft() -> None:
    text = "\n\n".join(["# 导数", "变化率的极限。", "# 连续", "极限等于函数值。"])
    incremental = build_incremental_ai_draft(
        _graph(),
        text,
        resource_id=RESOURCE_ID,
        extractor=HeuristicConceptExtractor(),
        relation_provider=HeuristicRelationProvider(),
        anchor_id_factory=_anchor_factory(),
    )
    full = build_ai_draft(
        text,
        resource_id=RESOURCE_ID,
        extractor=HeuristicConceptExtractor(),
        relation_provider=HeuristicRelationProvider(),
        anchor_id_factory=_anchor_factory(),
    )
    assert incremental == full
