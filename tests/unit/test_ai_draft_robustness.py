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
