"""Offline AI draft orchestration (WORK-2026-009).

Wires the pure-domain draft kernel to injectable extractors so the same
pipeline can later run a DeepSeek concept extractor without touching domain
code. The default extractors are deterministic and offline, proving the
end-to-end "resource text -> AiDraft -> GraphPatch" path with zero network.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Protocol

from knowledge_tree_domain.ai_draft import (
    AiDraft,
    DraftChunk,
    DraftConcept,
    DraftRelation,
    chunk_text,
    merge_concept_candidates,
    uuid7,
)


class ConceptExtractor(Protocol):
    """Extract concept candidates from a single chunk."""

    def extract(self, chunk: DraftChunk) -> tuple[DraftConcept, ...]: ...


class RelationCandidateProvider(Protocol):
    """Propose relations for an ordered concept list."""

    def provide(self, concepts: tuple[DraftConcept, ...]) -> tuple[DraftRelation, ...]: ...


class HeuristicConceptExtractor:
    """Deterministic offline extractor: `#`-heading lines become concepts."""

    def extract(self, chunk: DraftChunk) -> tuple[DraftConcept, ...]:
        evidence = (chunk.anchor_id,) if chunk.anchor_id is not None else ()
        concepts: list[DraftConcept] = []
        for line in chunk.text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                label = stripped.lstrip("#").strip()
                if label:
                    concepts.append(
                        DraftConcept(label=label, confidence=0.8, evidence_ids=evidence)
                    )
        return tuple(concepts)


class HeuristicRelationProvider:
    """Chain concepts in document order as `prerequisite_of` (offline)."""

    def provide(self, concepts: tuple[DraftConcept, ...]) -> tuple[DraftRelation, ...]:
        relations: list[DraftRelation] = []
        for source, target in zip(concepts, concepts[1:], strict=False):
            evidence = tuple(sorted(set(source.evidence_ids) | set(target.evidence_ids)))
            relations.append(
                DraftRelation(
                    source_label=source.label,
                    target_label=target.label,
                    edge_type="prerequisite_of",
                    confidence=0.6,
                    evidence_ids=evidence,
                )
            )
        return tuple(relations)


def build_ai_draft(
    text: str,
    *,
    resource_id: str,
    chunk_id_factory: Callable[[], str] = uuid7,
    anchor_id_factory: Callable[[], str] | None = None,
    extractor: ConceptExtractor | None = None,
    relation_provider: RelationCandidateProvider | None = None,
    chunk_size: int = 1200,
    overlap: int = 200,
) -> AiDraft:
    """Turn resource text into a validated AiDraft (offline, deterministic).

    `anchor_id_factory` binds each chunk to a source anchor id that flows into
    concept/relation evidence; without it the draft has no evidence and the
    resulting patch would be rejected by the commit gate (fail closed).
    """

    chunks = chunk_text(
        text,
        resource_id=resource_id,
        chunk_size=chunk_size,
        overlap=overlap,
        chunk_id_factory=chunk_id_factory,
    )
    if anchor_id_factory is not None:
        chunks = tuple(replace(chunk, anchor_id=anchor_id_factory()) for chunk in chunks)

    concept_extractor = extractor if extractor is not None else HeuristicConceptExtractor()
    relation_resolver = (
        relation_provider if relation_provider is not None else HeuristicRelationProvider()
    )

    candidates: list[DraftConcept] = []
    for chunk in chunks:
        candidates.extend(concept_extractor.extract(chunk))
    concepts = merge_concept_candidates(candidates)
    relations = relation_resolver.provide(concepts)
    return AiDraft(concepts=concepts, relations=relations)
