"""Unit tests for the whole-workspace AI draft kernel (WORK-2026-043)."""

from __future__ import annotations

from knowledge_tree_infrastructure.ai_draft import (
    HeuristicConceptExtractor,
    HeuristicRelationProvider,
    build_workspace_ai_draft,
)


def _graph() -> dict[str, object]:
    return {
        "schema_version": 1,
        "workspace_id": "00000000-0000-7000-8000-000000000001",
        "course_id": "00000000-0000-7000-8000-000000000002",
        "revision_no": 0,
        "concepts": [
            {"id": "c1", "label": "极限"},
        ],
        "edges": [],
        "layout_items": [],
    }


def test_build_workspace_ai_draft_merges_across_resources() -> None:
    draft = build_workspace_ai_draft(
        _graph(),
        [("r1", "# 连续\n\n极限的概念。"), ("r2", "# 导数\n\n变化率。")],
        extractor=HeuristicConceptExtractor(),
        relation_provider=HeuristicRelationProvider(),
    )

    labels = [concept.label for concept in draft.concepts]
    assert "极限" in labels  # existing concept stays a placeholder
    assert "连续" in labels
    assert "导数" in labels

    # New concepts bind evidence to a deterministic per-resource anchor.
    for concept in draft.concepts:
        if concept.label in {"连续", "导数"}:
            assert concept.evidence_ids
            assert concept.evidence_ids[0]

    # Relations span the whole corpus (existing placeholder + new concepts).
    pairs = {(relation.source_label, relation.target_label) for relation in draft.relations}
    assert ("极限", "连续") in pairs
    assert ("连续", "导数") in pairs


def test_build_workspace_ai_draft_drops_existing_duplicates() -> None:
    draft = build_workspace_ai_draft(
        _graph(),
        [("r1", "# 极限\n\n重复概念。"), ("r2", "# 极限\n\n再次出现。")],
        extractor=HeuristicConceptExtractor(),
        relation_provider=HeuristicRelationProvider(),
    )

    new_labels = [
        concept.label
        for concept in draft.concepts
        if concept.label not in {"极限"}
    ]
    assert new_labels == []  # existing label is never re-created
