"""Red-light contract tests for AI draft → GraphPatch v1 conversion (WORK-2026-009).

The generated patch must pass the canonical graph-patch contract and the pure
`preview_graph_patch` commit gate under an `ai` trusted actor, so AI drafts can
never bypass preview/confirmation.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest
from knowledge_tree_contracts import validate_contract
from knowledge_tree_domain import preview_graph_patch
from knowledge_tree_domain.ai_draft import (
    AiDraft,
    DraftConcept,
    DraftRelation,
    build_draft_patch,
    uuid7,
)

JsonObject = dict[str, Any]

WORKSPACE_ID = "00000000-0000-7000-8000-000000000001"
COURSE_ID = "00000000-0000-7000-8000-000000000002"
AI_ACTOR = {"type": "ai", "id": "ai-draft-pipeline"}

EVIDENCE_A = "00000000-0000-7000-8000-000000000010"
EVIDENCE_B = "00000000-0000-7000-8000-000000000011"
EVIDENCE_AB = "00000000-0000-7000-8000-000000000012"


def _concept(label: str, evidence: str, confidence: float = 0.8) -> DraftConcept:
    return DraftConcept(label=label, aliases=(), confidence=confidence, evidence_ids=(evidence,))


def _chain_draft() -> AiDraft:
    return AiDraft(
        concepts=(
            _concept("极限", EVIDENCE_A),
            _concept("连续", EVIDENCE_B),
        ),
        relations=(
            DraftRelation(
                source_label="极限",
                target_label="连续",
                edge_type="prerequisite_of",
                confidence=0.7,
                evidence_ids=(EVIDENCE_AB,),
            ),
        ),
    )


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


def _counter_factory() -> Any:
    state = {"n": 0}

    def factory() -> str:
        state["n"] += 1
        return f"00000000-0000-7000-8000-{state['n']:012d}"

    return factory


def test_build_draft_patch_passes_contract_and_preview_gate() -> None:
    patch = build_draft_patch(
        _chain_draft(),
        workspace_id=WORKSPACE_ID,
        course_id=COURSE_ID,
        base_revision_no=0,
        reason="AI 草案：微积分概念链",
        id_factory=_counter_factory(),
    )
    validate_contract("graph_patch", patch)
    preview = preview_graph_patch(_empty_graph(), patch, trusted_actor=AI_ACTOR)
    assert preview.status == "requires_confirmation"
    assert len(preview.snapshot["concepts"]) == 2
    assert len(preview.snapshot["edges"]) == 1
    assert len(preview.snapshot["layout_items"]) == 2


def test_build_draft_patch_is_ai_proposed_and_requires_confirmation() -> None:
    patch = build_draft_patch(
        _chain_draft(),
        workspace_id=WORKSPACE_ID,
        course_id=COURSE_ID,
        base_revision_no=0,
        reason="AI 草案",
        id_factory=_counter_factory(),
    )
    assert patch["actor"] == {"type": "ai", "id": "ai-draft-pipeline"}
    assert patch["requires_confirmation"] is True
    assert patch["confirmed"] is False
    concepts = [op["concept"] for op in patch["operations"] if op["op"] == "create_concept"]
    edges = [op["edge"] for op in patch["operations"] if op["op"] == "create_edge"]
    assert concepts and edges
    for concept in concepts:
        assert concept["origin"] == "ai"
        assert concept["review_state"] == "proposed"
        assert concept["confidence"] is not None
        assert concept["evidence_ids"]
        assert concept["locks"]["content"] is False
    for edge in edges:
        assert edge["origin"] == "ai"
        assert edge["review_state"] == "proposed"
        assert edge["evidence_ids"]


def test_build_draft_patch_creates_concepts_before_layout_items() -> None:
    patch = build_draft_patch(
        _chain_draft(),
        workspace_id=WORKSPACE_ID,
        course_id=COURSE_ID,
        base_revision_no=0,
        reason="AI 草案",
        id_factory=_counter_factory(),
    )
    operations = patch["operations"]
    create_indices = [i for i, op in enumerate(operations) if op["op"] == "create_concept"]
    layout_indices = [i for i, op in enumerate(operations) if op["op"] == "set_layout_item"]
    assert create_indices and layout_indices
    assert max(create_indices) < min(layout_indices)


def test_build_draft_patch_rejects_prerequisite_cycle() -> None:
    draft = AiDraft(
        concepts=(
            _concept("A", EVIDENCE_A),
            _concept("B", EVIDENCE_B),
            _concept("C", EVIDENCE_AB),
        ),
        relations=(
            DraftRelation("A", "B", "prerequisite_of", 0.8, (EVIDENCE_A,)),
            DraftRelation("B", "C", "prerequisite_of", 0.8, (EVIDENCE_B,)),
            DraftRelation("C", "A", "prerequisite_of", 0.8, (EVIDENCE_AB,)),
        ),
    )
    with pytest.raises(ValueError):
        build_draft_patch(
            draft,
            workspace_id=WORKSPACE_ID,
            course_id=COURSE_ID,
            base_revision_no=0,
            reason="cycle",
            id_factory=_counter_factory(),
        )


def test_build_draft_patch_rejects_ai_concept_without_evidence() -> None:
    draft = AiDraft(
        concepts=(DraftConcept(label="极限", aliases=(), confidence=0.8, evidence_ids=()),),
        relations=(),
    )
    with pytest.raises(ValueError):
        build_draft_patch(
            draft,
            workspace_id=WORKSPACE_ID,
            course_id=COURSE_ID,
            base_revision_no=0,
            reason="missing evidence",
            id_factory=_counter_factory(),
        )


def test_uuid7_generates_valid_v7_identifiers() -> None:
    value = uuid7()
    identifier = UUID(value)
    assert identifier.version == 7
