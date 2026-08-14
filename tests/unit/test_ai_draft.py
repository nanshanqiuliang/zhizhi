"""Red-light unit tests for the pure-domain AI draft kernel (WORK-2026-009).

These tests target `knowledge_tree_domain.ai_draft`, which does not exist yet,
so they are expected to fail at collection until the module is implemented.
"""

from __future__ import annotations

from typing import Any

import pytest
from knowledge_tree_domain.ai_draft import (
    AiDraft,
    DraftChunk,
    DraftConcept,
    DraftRelation,
    assign_draft_layout,
    chunk_text,
    detect_prerequisite_cycle,
    merge_concept_candidates,
    normalize_concept_label,
    validate_draft,
)

RESOURCE_ID = "00000000-0000-7000-8000-000000000003"


def _chunk(text: str, *, chunk_id: str, anchor_id: str | None = None) -> DraftChunk:
    return DraftChunk(
        chunk_id=chunk_id,
        resource_id=RESOURCE_ID,
        text=text,
        start_offset=0,
        end_offset=len(text),
        anchor_id=anchor_id,
    )


def _concept(
    label: str, *, confidence: float = 0.8, evidence: tuple[str, ...] = ()
) -> DraftConcept:
    return DraftConcept(
        label=label,
        aliases=(),
        confidence=confidence,
        evidence_ids=evidence,
    )


# -- chunking ---------------------------------------------------------------


def test_chunk_text_empty_returns_no_chunks() -> None:
    assert chunk_text("", resource_id=RESOURCE_ID) == ()


def test_chunk_text_short_text_is_single_chunk() -> None:
    chunks = chunk_text("极限与连续", resource_id=RESOURCE_ID)
    assert len(chunks) == 1
    assert chunks[0].text == "极限与连续"
    assert chunks[0].start_offset == 0
    assert chunks[0].end_offset == len("极限与连续")


def test_chunk_text_splits_on_paragraph_boundaries_without_splitting_paragraphs() -> None:
    paragraphs = ["极限的定义。", "连续的定义。", "导数的定义。", "积分的定义。"]
    text = "\n\n".join(paragraphs)
    chunks = chunk_text(text, resource_id=RESOURCE_ID, chunk_size=20, overlap=0)
    assert len(chunks) >= 2
    # Every chunk must be a concatenation of whole paragraphs (no partial sentence).
    for chunk in chunks:
        assert chunk.text in text or chunk.text.endswith("。")
        assert all(paragraph in text for paragraph in chunk.text.split("\n") if paragraph)


def _counter_factory() -> Any:
    state = {"n": 0}

    def factory() -> str:
        state["n"] += 1
        return f"00000000-0000-7000-8000-{state['n']:012d}"

    return factory


def test_chunk_text_is_deterministic() -> None:
    text = "第一段。\n\n第二段。\n\n第三段。\n\n第四段。"
    first = chunk_text(
        text, resource_id=RESOURCE_ID, chunk_size=16, overlap=4, chunk_id_factory=_counter_factory()
    )
    second = chunk_text(
        text, resource_id=RESOURCE_ID, chunk_size=16, overlap=4, chunk_id_factory=_counter_factory()
    )
    assert first == second


# -- label normalization / alias merging ------------------------------------


def test_normalize_concept_label_folds_case_whitespace_and_fullwidth() -> None:
    assert normalize_concept_label("Limits") == "limits"
    assert normalize_concept_label("  极限  ") == "极限"
    assert normalize_concept_label("ＡＢＣ") == "abc"
    assert normalize_concept_label("连续  函数") == "连续 函数"


def test_merge_concept_candidates_deduplicates_and_merges_evidence() -> None:
    merged = merge_concept_candidates(
        [
            _concept("极限", confidence=0.6, evidence=("00000000-0000-7000-8000-000000000010",)),
            _concept(" 极限 ", confidence=0.9, evidence=("00000000-0000-7000-8000-000000000011",)),
            _concept("LIMIT", confidence=0.5, evidence=("00000000-0000-7000-8000-000000000012",)),
        ]
    )
    assert len(merged) == 2  # 极限(合并 极限/极限/LIMIT?) + limits
    by_label = {concept.label: concept for concept in merged}
    limit = by_label["极限"]
    assert limit.confidence == 0.9
    assert set(limit.evidence_ids) == {
        "00000000-0000-7000-8000-000000000010",
        "00000000-0000-7000-8000-000000000011",
    }
    assert by_label["LIMIT"].confidence == 0.5


# -- relation validation / DAG ----------------------------------------------


def test_validate_draft_rejects_self_edge() -> None:
    draft = AiDraft(
        concepts=(_concept("极限", evidence=("00000000-0000-7000-8000-000000000010",)),),
        relations=(
            DraftRelation(
                source_label="极限",
                target_label="极限",
                edge_type="prerequisite_of",
                confidence=0.8,
                evidence_ids=("00000000-0000-7000-8000-000000000011",),
            ),
        ),
    )
    with pytest.raises(ValueError):
        validate_draft(draft)


def test_validate_draft_rejects_unknown_endpoint() -> None:
    draft = AiDraft(
        concepts=(_concept("极限", evidence=("00000000-0000-7000-8000-000000000010",)),),
        relations=(
            DraftRelation(
                source_label="极限",
                target_label="不存在",
                edge_type="related_to",
                confidence=0.8,
                evidence_ids=(),
            ),
        ),
    )
    with pytest.raises(ValueError):
        validate_draft(draft)


def test_detect_prerequisite_cycle_returns_path() -> None:
    relations = (
        DraftRelation("A", "B", "prerequisite_of", 0.8, ()),
        DraftRelation("B", "C", "prerequisite_of", 0.8, ()),
        DraftRelation("C", "A", "prerequisite_of", 0.8, ()),
    )
    path = detect_prerequisite_cycle(relations)
    assert path is not None
    assert len(path) >= 3


def test_detect_prerequisite_cycle_none_when_acyclic() -> None:
    relations = (
        DraftRelation("A", "B", "prerequisite_of", 0.8, ()),
        DraftRelation("B", "C", "prerequisite_of", 0.8, ()),
        DraftRelation("B", "D", "related_to", 0.8, ()),
    )
    assert detect_prerequisite_cycle(relations) is None


# -- layout ------------------------------------------------------------------


def test_assign_draft_layout_layers_prerequisites_topologically() -> None:
    concepts = (_concept("A"), _concept("B"), _concept("C"), _concept("D"))
    relations = (
        DraftRelation("A", "B", "prerequisite_of", 0.8, ()),
        DraftRelation("B", "C", "prerequisite_of", 0.8, ()),
        DraftRelation("A", "D", "prerequisite_of", 0.8, ()),
    )
    layout = assign_draft_layout(
        concepts, relations, view_id="00000000-0000-7000-8000-000000000004"
    )
    by_label = {item[0]: item[1:] for item in layout}
    assert len(layout) == 4
    # A precedes B precedes C along the prerequisite chain (y strictly increasing).
    assert by_label["A"][1] < by_label["B"][1] < by_label["C"][1]
    # D is a sibling of B on the same layer.
    assert by_label["D"][1] == by_label["B"][1]
