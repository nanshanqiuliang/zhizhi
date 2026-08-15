"""Offline AI draft orchestration (WORK-2026-009).

Wires the pure-domain draft kernel to injectable extractors so the same
pipeline can later run a DeepSeek concept extractor without touching domain
code. The default extractors are deterministic and offline, proving the
end-to-end "resource text -> AiDraft -> GraphPatch" path with zero network.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace
from typing import Any, Protocol

from knowledge_tree_domain.ai_draft import (
    AiDraft,
    DraftChunk,
    DraftConcept,
    DraftRelation,
    chunk_text,
    deterministic_uuidv7,
    merge_concept_candidates,
    normalize_concept_label,
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


def build_incremental_ai_draft(
    existing_graph: Mapping[str, Any],
    text: str,
    *,
    resource_id: str,
    extractor: ConceptExtractor,
    relation_provider: RelationCandidateProvider,
    chunk_id_factory: Callable[[], str] = uuid7,
    anchor_id_factory: Callable[[], str] | None = None,
    chunk_size: int = 1200,
    overlap: int = 200,
    max_chunks: int | None = None,
) -> AiDraft:
    """Incremental draft: extract new concepts and merge them into an existing graph.

    New candidates are extracted from the text and merged; any candidate whose
    normalized label matches an existing concept is dropped (no re-create). The
    relation provider then sees the union of existing placeholders (empty
    evidence) and new concepts, so it can propose relations across the graph
    boundary; relations with no new endpoint (existing↔existing) are dropped.
    `max_chunks` bounds the number of LLM extraction calls (cost/latency guard).
    """

    chunks = chunk_text(
        text,
        resource_id=resource_id,
        chunk_size=chunk_size,
        overlap=overlap,
        chunk_id_factory=chunk_id_factory,
    )
    if max_chunks is not None and len(chunks) > max_chunks:
        chunks = chunks[:max_chunks]
    if anchor_id_factory is not None:
        chunks = tuple(replace(chunk, anchor_id=anchor_id_factory()) for chunk in chunks)

    candidates: list[DraftConcept] = []
    for chunk in chunks:
        candidates.extend(extractor.extract(chunk))
    merged = merge_concept_candidates(candidates)

    existing_keys = {
        normalize_concept_label(str(concept["label"]))
        for concept in existing_graph.get("concepts", [])
        if isinstance(concept, dict) and isinstance(concept.get("label"), str)
    }
    existing_placeholders = tuple(
        DraftConcept(label=str(concept["label"]), aliases=(), confidence=1.0, evidence_ids=())
        for concept in existing_graph.get("concepts", [])
        if isinstance(concept, dict) and isinstance(concept.get("label"), str)
    )
    new_only = tuple(
        concept for concept in merged if normalize_concept_label(concept.label) not in existing_keys
    )
    all_concepts = existing_placeholders + new_only

    relations = relation_provider.provide(all_concepts)
    new_keys = {normalize_concept_label(concept.label) for concept in new_only}
    relations = tuple(
        relation
        for relation in relations
        if normalize_concept_label(relation.source_label) in new_keys
        or normalize_concept_label(relation.target_label) in new_keys
    )
    return AiDraft(concepts=all_concepts, relations=relations)


def build_workspace_ai_draft(
    existing_graph: Mapping[str, Any],
    texts: list[tuple[str, str]],
    *,
    extractor: ConceptExtractor,
    relation_provider: RelationCandidateProvider,
    chunk_id_factory: Callable[[], str] = uuid7,
    chunk_size: int = 1200,
    overlap: int = 200,
    max_chunks: int = 40,
) -> AiDraft:
    """Whole-workspace draft: extract/merge concepts across all resources.

    Each resource contributes its chunks (bound to a deterministic per-resource
    anchor id); candidates are merged across the whole corpus, existing labels
    are never re-created, and relations are proposed over the union of existing
    placeholders and new concepts. `max_chunks` bounds the total LLM calls so a
    huge corpus fails closed rather than blowing the budget.
    """

    candidates: list[DraftConcept] = []
    total_chunks = 0
    for resource_id, text in texts:
        anchor_id = deterministic_uuidv7(resource_id)
        chunks = chunk_text(
            text,
            resource_id=resource_id,
            chunk_size=chunk_size,
            overlap=overlap,
            chunk_id_factory=chunk_id_factory,
        )
        chunks = tuple(replace(chunk, anchor_id=anchor_id) for chunk in chunks)
        if total_chunks + len(chunks) > max_chunks:
            chunks = chunks[: max(0, max_chunks - total_chunks)]
        total_chunks += len(chunks)
        for chunk in chunks:
            candidates.extend(extractor.extract(chunk))
        if total_chunks >= max_chunks:
            break

    merged = merge_concept_candidates(candidates)

    existing_keys = {
        normalize_concept_label(str(concept["label"]))
        for concept in existing_graph.get("concepts", [])
        if isinstance(concept, dict) and isinstance(concept.get("label"), str)
    }
    existing_placeholders = tuple(
        DraftConcept(label=str(concept["label"]), aliases=(), confidence=1.0, evidence_ids=())
        for concept in existing_graph.get("concepts", [])
        if isinstance(concept, dict) and isinstance(concept.get("label"), str)
    )
    new_only = tuple(
        concept for concept in merged if normalize_concept_label(concept.label) not in existing_keys
    )
    all_concepts = existing_placeholders + new_only

    relations = relation_provider.provide(all_concepts)
    new_keys = {normalize_concept_label(concept.label) for concept in new_only}
    relations = tuple(
        relation
        for relation in relations
        if normalize_concept_label(relation.source_label) in new_keys
        or normalize_concept_label(relation.target_label) in new_keys
    )
    return AiDraft(concepts=all_concepts, relations=relations)
