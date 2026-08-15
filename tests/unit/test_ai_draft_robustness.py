"""Red-light tests for draft-generation robustness (WORK-2026-044).

`build_incremental_ai_draft(max_chunks=...)` does not exist yet and the
fail-soft extractor wrappers are not implemented, so collection/execution is
expected to fail until the fixes land.
"""

from __future__ import annotations

import pytest
from knowledge_tree_domain.ai_draft import DraftChunk, DraftConcept
from knowledge_tree_infrastructure.ai_draft import build_incremental_ai_draft


class CountingExtractor:
    def __init__(self) -> None:
        self.calls = 0

    def extract(self, chunk: DraftChunk) -> tuple[DraftConcept, ...]:
        self.calls += 1
        return (DraftConcept(label="c", confidence=0.8, evidence_ids=()),)


class NoopRelations:
    def provide(self, concepts: tuple[DraftConcept, ...]) -> tuple:
        return ()


def _graph() -> dict[str, object]:
    return {
        "schema_version": 1,
        "workspace_id": "00000000-0000-7000-8000-000000000001",
        "course_id": "00000000-0000-7000-8000-000000000002",
        "revision_no": 0,
        "concepts": [],
        "edges": [],
        "layout_items": [],
    }


def test_incremental_draft_caps_chunks() -> None:
    extractor = CountingExtractor()
    long_text = "\n".join(f"# 概念{i}" for i in range(200))  # >40 chunks at 1200 chars
    draft = build_incremental_ai_draft(
        _graph(),
        long_text,
        resource_id="r1",
        extractor=extractor,
        relation_provider=NoopRelations(),
        max_chunks=2,
    )
    assert extractor.calls <= 2
    assert draft.concepts


def test_fail_soft_extractor_skips_bad_chunks() -> None:
    from knowledge_tree_infrastructure.ai_draft_llm import DraftExtractionError

    from apps.api.ai_draft import fail_soft_extractor

    class BadExtractor:
        def extract(self, chunk: DraftChunk) -> tuple[DraftConcept, ...]:
            if chunk.chunk_id == "bad":
                raise DraftExtractionError("draft_extraction_failed", details={"rule": "x"})
            return (DraftConcept(label="ok", confidence=0.8, evidence_ids=()),)

    wrapped = fail_soft_extractor(BadExtractor())
    good = DraftChunk(chunk_id="good", resource_id="r", text="t", start_offset=0, end_offset=1)
    bad = DraftChunk(chunk_id="bad", resource_id="r", text="t", start_offset=0, end_offset=1)
    assert [concept.label for concept in wrapped.extract(good)] == ["ok"]
    assert wrapped.extract(bad) == ()


def test_fail_soft_does_not_swallow_provider_errors() -> None:
    from knowledge_tree_infrastructure.llm.errors import LLMProviderError

    from apps.api.ai_draft import fail_soft_extractor

    class Failing:
        def extract(self, chunk: DraftChunk) -> tuple[DraftConcept, ...]:
            raise LLMProviderError("provider_connection_failed", details={"rule": "x"})

    wrapped = fail_soft_extractor(Failing())
    chunk = DraftChunk(chunk_id="a", resource_id="r", text="t", start_offset=0, end_offset=1)
    with pytest.raises(LLMProviderError):
        wrapped.extract(chunk)
