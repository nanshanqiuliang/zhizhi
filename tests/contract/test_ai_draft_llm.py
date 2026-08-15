"""Offline contract tests for LLM-backed AI draft extractors (WORK-2026-009 slice 2).

These tests exercise `knowledge_tree_infrastructure.ai_draft_llm` against the
deterministic mock LLM adapter only: no network, no API key, no real provider.
They prove the extractor/provider shape-validate untrusted model answers,
bind chunk-anchor evidence, fail closed on structural violations, drop
content-level noise, and still produce a GraphPatch that passes the commit gate.
"""

from __future__ import annotations

from typing import Any

import pytest
from knowledge_tree_domain import preview_graph_patch
from knowledge_tree_domain.ai_draft import (
    DraftChunk,
    DraftConcept,
    build_draft_patch,
    validate_draft,
)
from knowledge_tree_infrastructure.ai_draft import build_ai_draft
from knowledge_tree_infrastructure.ai_draft_llm import (
    DraftExtractionError,
    LlmConceptExtractor,
    LlmRelationProvider,
)
from knowledge_tree_infrastructure.llm.errors import LLMProviderError
from knowledge_tree_infrastructure.llm.mock import MockLlmAdapter, MockScript

RESOURCE_ID = "00000000-0000-7000-8000-000000000003"
WORKSPACE_ID = "00000000-0000-7000-8000-000000000001"
COURSE_ID = "00000000-0000-7000-8000-000000000002"
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

CONCEPT_SCRIPT = MockScript(
    typed_output={
        "concepts": [
            {"label": "极限", "aliases": ["limit"], "confidence": 0.9},
            {"label": "连续", "confidence": 0.85},
            {"label": "导数", "confidence": 0.8},
        ]
    }
)

RELATION_SCRIPT = MockScript(
    typed_output={
        "relations": [
            {"from": "极限", "to": "连续", "type": "prerequisite_of", "confidence": 0.7},
            {"from": "连续", "to": "导数", "type": "prerequisite_of", "confidence": 0.7},
        ]
    }
)


def _mock() -> MockLlmAdapter:
    return MockLlmAdapter(model_id="mock-deterministic-v1")


def _chunk(
    text: str = "# 极限\n\n极限的定义。",
    *,
    anchor: str = "00000000-0000-7000-9000-000000000001",
) -> DraftChunk:
    return DraftChunk(
        chunk_id="chunk-1",
        resource_id=RESOURCE_ID,
        text=text,
        start_offset=0,
        end_offset=len(text),
        anchor_id=anchor,
    )


def _concepts() -> tuple[DraftConcept, ...]:
    return (
        DraftConcept(
            label="极限",
            aliases=(),
            confidence=0.9,
            evidence_ids=("00000000-0000-7000-9000-000000000001",),
        ),
        DraftConcept(
            label="连续",
            aliases=(),
            confidence=0.85,
            evidence_ids=("00000000-0000-7000-9000-000000000002",),
        ),
        DraftConcept(
            label="导数",
            aliases=(),
            confidence=0.8,
            evidence_ids=("00000000-0000-7000-9000-000000000003",),
        ),
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


# -- concept extraction ------------------------------------------------------


def test_concept_extractor_parses_typed_output_and_binds_anchor() -> None:
    extractor = LlmConceptExtractor(
        generate=lambda request: _mock().generate(request, script=CONCEPT_SCRIPT)
    )
    concepts = extractor.extract(_chunk())
    assert [concept.label for concept in concepts] == ["极限", "连续", "导数"]
    assert concepts[0].aliases == ("limit",)
    assert concepts[0].confidence == 0.9
    assert concepts[0].evidence_ids == ("00000000-0000-7000-9000-000000000001",)
    assert all(concept.evidence_ids for concept in concepts)


def test_concept_extractor_parses_fenced_text_json() -> None:
    script = MockScript(text='```json\n{"concepts": [{"label": "极限", "confidence": 0.7}]}\n```')
    extractor = LlmConceptExtractor(
        generate=lambda request: _mock().generate(request, script=script)
    )
    concepts = extractor.extract(_chunk())
    assert [concept.label for concept in concepts] == ["极限"]
    assert concepts[0].confidence == 0.7


def test_concept_extractor_without_anchor_has_no_evidence() -> None:
    extractor = LlmConceptExtractor(
        generate=lambda request: _mock().generate(request, script=CONCEPT_SCRIPT)
    )
    concepts = extractor.extract(_chunk(anchor=None))
    assert all(not concept.evidence_ids for concept in concepts)


def test_concept_extractor_empty_chunk_returns_no_concepts() -> None:
    extractor = LlmConceptExtractor(
        generate=lambda request: _mock().generate(request, script=CONCEPT_SCRIPT)
    )
    assert extractor.extract(_chunk(text="   ")) == ()


def test_concept_extractor_rejects_invalid_json() -> None:
    extractor = LlmConceptExtractor(
        generate=lambda request: _mock().generate(request, script=MockScript(text="not json"))
    )
    with pytest.raises(DraftExtractionError) as raised:
        extractor.extract(_chunk())
    assert raised.value.code == "draft_extraction_failed"
    assert raised.value.details["rule"] == "no_json_object"


def test_concept_extractor_rejects_missing_concepts_list() -> None:
    extractor = LlmConceptExtractor(
        generate=lambda request: _mock().generate(
            request, script=MockScript(text='{"labels": ["极限"]}')
        )
    )
    with pytest.raises(DraftExtractionError) as raised:
        extractor.extract(_chunk())
    assert raised.value.details["rule"] == "missing_concepts_list"


def test_concept_extractor_rejects_item_without_label() -> None:
    script = MockScript(typed_output={"concepts": [{"confidence": 0.9}]})
    extractor = LlmConceptExtractor(
        generate=lambda request: _mock().generate(request, script=script)
    )
    with pytest.raises(DraftExtractionError) as raised:
        extractor.extract(_chunk())
    assert raised.value.details["rule"] == "concept_label_missing"


def test_concept_extractor_rejects_out_of_range_confidence() -> None:
    script = MockScript(typed_output={"concepts": [{"label": "极限", "confidence": 1.5}]})
    extractor = LlmConceptExtractor(
        generate=lambda request: _mock().generate(request, script=script)
    )
    with pytest.raises(DraftExtractionError) as raised:
        extractor.extract(_chunk())
    assert raised.value.details["rule"] == "concept_confidence_range"


def test_concept_extractor_rejects_invalid_aliases() -> None:
    script = MockScript(typed_output={"concepts": [{"label": "极限", "aliases": [1]}]})
    extractor = LlmConceptExtractor(
        generate=lambda request: _mock().generate(request, script=script)
    )
    with pytest.raises(DraftExtractionError) as raised:
        extractor.extract(_chunk())
    assert raised.value.details["rule"] == "concept_aliases_invalid"


def test_concept_extractor_propagates_provider_error_without_masking_domain() -> None:
    extractor = LlmConceptExtractor(
        generate=lambda request: _mock().generate(
            request, script=MockScript(failure="provider_rate_limited")
        )
    )
    with pytest.raises(LLMProviderError) as raised:
        extractor.extract(_chunk())
    assert raised.value.code == "provider_rate_limited"
    # The pure-domain validator keeps working independently of the extractor.
    draft = build_ai_draft(
        CALCULUS_MD, resource_id=RESOURCE_ID, anchor_id_factory=_anchor_factory()
    )
    validate_draft(draft)


# -- relation proposal -------------------------------------------------------


def test_relation_provider_parses_and_binds_union_evidence() -> None:
    provider = LlmRelationProvider(
        generate=lambda request: _mock().generate(request, script=RELATION_SCRIPT)
    )
    relations = provider.provide(_concepts())
    assert [(r.source_label, r.target_label, r.edge_type) for r in relations] == [
        ("极限", "连续", "prerequisite_of"),
        ("连续", "导数", "prerequisite_of"),
    ]
    assert relations[0].evidence_ids == (
        "00000000-0000-7000-9000-000000000001",
        "00000000-0000-7000-9000-000000000002",
    )
    assert relations[1].evidence_ids == (
        "00000000-0000-7000-9000-000000000002",
        "00000000-0000-7000-9000-000000000003",
    )
    assert all(0.0 <= relation.confidence <= 1.0 for relation in relations)


def test_relation_provider_drops_unknown_endpoints_and_self_edges() -> None:
    script = MockScript(
        typed_output={
            "relations": [
                {"from": "极限", "to": "连续", "type": "prerequisite_of", "confidence": 0.7},
                {
                    "from": "极限",
                    "to": "不存在的概念",
                    "type": "prerequisite_of",
                    "confidence": 0.7,
                },
                {"from": "极限", "to": "极限", "type": "prerequisite_of", "confidence": 0.7},
            ]
        }
    )
    provider = LlmRelationProvider(
        generate=lambda request: _mock().generate(request, script=script)
    )
    relations = provider.provide(_concepts())
    assert [(r.source_label, r.target_label) for r in relations] == [("极限", "连续")]


def test_relation_provider_dedupes_duplicate_edges() -> None:
    script = MockScript(
        typed_output={
            "relations": [
                {"from": "极限", "to": "连续", "type": "prerequisite_of", "confidence": 0.7},
                {"from": "极限", "to": "连续", "type": "prerequisite_of", "confidence": 0.9},
            ]
        }
    )
    provider = LlmRelationProvider(
        generate=lambda request: _mock().generate(request, script=script)
    )
    assert len(provider.provide(_concepts())) == 1


def test_relation_provider_rejects_unknown_edge_type() -> None:
    script = MockScript(
        typed_output={"relations": [{"from": "极限", "to": "连续", "type": "depends_on"}]}
    )
    provider = LlmRelationProvider(
        generate=lambda request: _mock().generate(request, script=script)
    )
    with pytest.raises(DraftExtractionError) as raised:
        provider.provide(_concepts())
    assert raised.value.details["rule"] == "relation_type_invalid"


def test_relation_provider_rejects_missing_endpoint() -> None:
    script = MockScript(typed_output={"relations": [{"from": "极限", "type": "prerequisite_of"}]})
    provider = LlmRelationProvider(
        generate=lambda request: _mock().generate(request, script=script)
    )
    with pytest.raises(DraftExtractionError) as raised:
        provider.provide(_concepts())
    assert raised.value.details["rule"] == "relation_endpoint_missing"


def test_relation_provider_short_list_skips_call() -> None:
    provider = LlmRelationProvider(
        generate=lambda request: pytest.fail("must not call the model for <2 concepts")
    )
    assert provider.provide((_concepts()[0],)) == ()


# -- end-to-end offline draft ------------------------------------------------


def test_llm_draft_pipeline_produces_valid_confirmation_required_patch() -> None:
    mock = _mock()
    extractor = LlmConceptExtractor(
        generate=lambda request: mock.generate(request, script=CONCEPT_SCRIPT)
    )
    provider = LlmRelationProvider(
        generate=lambda request: mock.generate(request, script=RELATION_SCRIPT)
    )
    draft = build_ai_draft(
        CALCULUS_MD,
        resource_id=RESOURCE_ID,
        anchor_id_factory=_anchor_factory(),
        extractor=extractor,
        relation_provider=provider,
    )
    validate_draft(draft)
    assert [concept.label for concept in draft.concepts] == ["极限", "连续", "导数"]
    assert all(concept.evidence_ids for concept in draft.concepts)
    assert [(r.source_label, r.target_label) for r in draft.relations] == [
        ("极限", "连续"),
        ("连续", "导数"),
    ]

    patch = build_draft_patch(
        draft,
        workspace_id=WORKSPACE_ID,
        course_id=COURSE_ID,
        base_revision_no=0,
        reason="AI 草案：微积分概念链（LLM 抽取）",
        id_factory=_id_factory(),
    )
    empty_graph = {
        "schema_version": 1,
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "revision_no": 0,
        "concepts": [],
        "edges": [],
        "layout_items": [],
    }
    preview = preview_graph_patch(empty_graph, patch, trusted_actor=AI_ACTOR)
    assert preview.status == "requires_confirmation"
    assert len(preview.snapshot["concepts"]) == 3
    assert len(preview.snapshot["edges"]) == 2


def test_llm_draft_pipeline_is_deterministic_for_same_scripts() -> None:
    def run() -> Any:
        mock = _mock()
        draft = build_ai_draft(
            CALCULUS_MD,
            resource_id=RESOURCE_ID,
            anchor_id_factory=_anchor_factory(),
            extractor=LlmConceptExtractor(
                generate=lambda request: mock.generate(request, script=CONCEPT_SCRIPT)
            ),
            relation_provider=LlmRelationProvider(
                generate=lambda request: mock.generate(request, script=RELATION_SCRIPT)
            ),
        )
        return draft

    first, second = run(), run()
    assert first == second
