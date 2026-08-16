"""Pure-domain AI draft kernel (WORK-2026-009).

Deterministic, framework-free helpers that turn imported resource text into an
AI draft (concepts + relations) and then into a GraphPatch v1 candidate that
can only ever be applied through the existing commit gate. This module never
imports FastAPI, storage, an LLM SDK or a parser library, and never persists
anything: an AI draft is an untrusted draft until the user confirms it.
"""

from __future__ import annotations

import hashlib
import time
import unicodedata
import uuid as _uuid
from collections import deque
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

JsonObject = dict[str, Any]

_EDGE_TYPES = ("prerequisite_of", "related_to", "part_of", "example_of")
EdgeType = Literal["prerequisite_of", "related_to", "part_of", "example_of"]


class DraftError(ValueError):
    """A stable rejection that never includes note or source text."""

    def __init__(self, code: str, *, details: Mapping[str, Any]) -> None:
        self.code = code
        self.details = dict(details)
        super().__init__(f"{code}: AI draft rejected")


@dataclass(frozen=True, slots=True)
class DraftChunk:
    """A contiguous slice of resource text with optional anchor provenance."""

    chunk_id: str
    resource_id: str
    text: str
    start_offset: int
    end_offset: int
    anchor_id: str | None = None


@dataclass(frozen=True, slots=True)
class DraftConcept:
    """One extracted concept candidate with merged aliases and source binding."""

    label: str
    aliases: tuple[str, ...] = ()
    confidence: float = 1.0
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DraftRelation:
    """One candidate relation between two concept labels."""

    source_label: str
    target_label: str
    edge_type: str = "related_to"
    confidence: float = 1.0
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AiDraft:
    """A full untrusted draft; concepts then relations, both deterministic."""

    concepts: tuple[DraftConcept, ...]
    relations: tuple[DraftRelation, ...] = ()


def uuid7() -> str:
    """Generate a UUIDv7 string (48-bit ms timestamp + version/variant bits)."""

    now = int(time.time() * 1000)
    value = (now << 80) | (0x70 << 72) | (0x80 << 64) | (_uuid.uuid4().int & ((1 << 64) - 1))
    return str(_uuid.UUID(int=value))


def deterministic_uuidv7(seed: str) -> str:
    """Derive a stable UUIDv7 from a seed string (e.g. a resource id).

    Used for AI-draft source anchors so the same resource always yields the
    same anchor id, keeping repeated drafts idempotent.
    """

    digest = hashlib.sha256(seed.encode("utf-8")).digest()[:16]
    value = bytearray(digest)
    value[6] = (value[6] & 0x0F) | 0x70  # UUID version 7
    value[8] = (value[8] & 0x3F) | 0x80  # RFC 4122 variant
    return str(_uuid.UUID(bytes=bytes(value)))


# -- chunking -----------------------------------------------------------------


def _paragraph_spans(text: str) -> list[tuple[int, int]]:
    """Return (start, end) spans for non-blank paragraphs, newline-separated."""

    spans: list[tuple[int, int]] = []
    start = 0
    index = 0
    length = len(text)
    while index < length:
        if text[index] == "\n":
            if index > start and text[start:index].strip():
                spans.append((start, index))
            while index < length and text[index] == "\n":
                index += 1
            start = index
        else:
            index += 1
    if start < length and text[start:].strip():
        spans.append((start, length))
    return spans


def _overlap_tail(spans: list[tuple[int, int]], overlap: int) -> list[tuple[int, int]]:
    """Keep the trailing spans whose total length reaches `overlap` characters."""

    if overlap <= 0 or len(spans) <= 1:
        return []
    tail: list[tuple[int, int]] = []
    total = 0
    for span in reversed(spans[:-1]):
        if total >= overlap:
            break
        tail.append(span)
        total += span[1] - span[0]
    tail.reverse()
    return tail


def _make_chunk(
    spans: list[tuple[int, int]],
    text: str,
    *,
    resource_id: str,
    chunk_id_factory: Callable[[], str],
) -> DraftChunk:
    start = spans[0][0]
    end = spans[-1][1]
    return DraftChunk(
        chunk_id=chunk_id_factory(),
        resource_id=resource_id,
        text=text[start:end],
        start_offset=start,
        end_offset=end,
    )


def chunk_text(
    text: str,
    *,
    resource_id: str,
    chunk_size: int = 1200,
    overlap: int = 200,
    chunk_id_factory: Callable[[], str] = uuid7,
) -> tuple[DraftChunk, ...]:
    """Split text into paragraph-aligned chunks with bounded overlap.

    Chunks never split a paragraph in half: they are greedy runs of paragraphs
    up to `chunk_size` characters, and each chunk after the first re-includes
    up to `overlap` trailing characters from the previous chunk (rounded up to
    whole paragraphs). Deterministic for a fixed `chunk_id_factory`.
    """

    if not text or chunk_size <= 0:
        return ()
    spans = _paragraph_spans(text)
    chunks: list[DraftChunk] = []
    buffer: list[tuple[int, int]] = []
    buffer_len = 0
    for span in spans:
        span_len = span[1] - span[0]
        if buffer and buffer_len + span_len > chunk_size:
            chunks.append(
                _make_chunk(
                    buffer, text, resource_id=resource_id, chunk_id_factory=chunk_id_factory
                )
            )
            buffer = _overlap_tail(buffer, overlap)
            buffer_len = sum(end - start for start, end in buffer)
        buffer.append(span)
        buffer_len += span_len
    if buffer:
        chunks.append(
            _make_chunk(buffer, text, resource_id=resource_id, chunk_id_factory=chunk_id_factory)
        )
    return tuple(chunks)


# -- label normalization / alias merging --------------------------------------


def normalize_concept_label(label: str) -> str:
    """Fold case, full-width characters and whitespace into a stable key."""

    return " ".join(unicodedata.normalize("NFKC", label).casefold().strip().split())


def merge_concept_candidates(candidates: Iterable[DraftConcept]) -> tuple[DraftConcept, ...]:
    """Merge candidates sharing a normalized label, in first-seen order.

    The first label is kept verbatim; later variants become aliases. Evidence
    ids are unioned and confidence takes the maximum.
    """

    order: list[str] = []
    labels: dict[str, str] = {}
    aliases: dict[str, list[str]] = {}
    confidence: dict[str, float] = {}
    evidence: dict[str, set[str]] = {}
    for concept in candidates:
        key = normalize_concept_label(concept.label)
        if key not in labels:
            labels[key] = concept.label
            order.append(key)
            aliases[key] = []
            confidence[key] = concept.confidence
            evidence[key] = set(concept.evidence_ids)
        else:
            confidence[key] = max(confidence[key], concept.confidence)
            evidence[key] |= set(concept.evidence_ids)
        variants = [concept.label, *concept.aliases]
        for variant in variants:
            if variant != labels[key] and variant not in aliases[key]:
                aliases[key].append(variant)
    return tuple(
        DraftConcept(
            label=labels[key],
            aliases=tuple(aliases[key]),
            confidence=confidence[key],
            evidence_ids=tuple(sorted(evidence[key])),
        )
        for key in order
    )


# -- validation / DAG ---------------------------------------------------------


def _concept_keys(concepts: Iterable[DraftConcept]) -> dict[str, str]:
    result: dict[str, str] = {}
    for concept in concepts:
        key = normalize_concept_label(concept.label)
        if key in result:
            raise DraftError("draft_invalid", details={"rule": "duplicate_concept", "key": key})
        result[key] = concept.label
    return result


def _find_cycle(adjacency: Mapping[str, set[str]]) -> list[str] | None:
    state: dict[str, int] = {}
    stack: list[str] = []
    result: list[str] | None = None

    def visit(node: str) -> None:
        nonlocal result
        state[node] = 1
        stack.append(node)
        for neighbor in sorted(adjacency.get(node, ())):
            if state.get(neighbor, 0) == 0:
                visit(neighbor)
                if result is not None:
                    return
            elif state.get(neighbor, 0) == 1:
                index = stack.index(neighbor)
                result = [*stack[index:], neighbor]
                return
        stack.pop()
        state[node] = 2

    for node in sorted(adjacency):
        if state.get(node, 0) == 0:
            visit(node)
            if result is not None:
                break
    return result


def detect_prerequisite_cycle(relations: Iterable[DraftRelation]) -> list[str] | None:
    """Return the label cycle path for `prerequisite_of` edges, or None."""

    adjacency: dict[str, set[str]] = {}
    for relation in relations:
        if relation.edge_type == "prerequisite_of":
            adjacency.setdefault(relation.source_label, set()).add(relation.target_label)
    return _find_cycle(adjacency)


def validate_draft(draft: AiDraft) -> None:
    """Validate a draft's shape, endpoints, duplicates and DAG constraint."""

    if not draft.concepts:
        raise DraftError("draft_invalid", details={"rule": "no_concepts"})
    keys = _concept_keys(draft.concepts)
    for concept in draft.concepts:
        if not normalize_concept_label(concept.label):
            raise DraftError("draft_invalid", details={"rule": "empty_concept_label"})
        if not 0.0 <= concept.confidence <= 1.0:
            raise DraftError("draft_invalid", details={"rule": "concept_confidence_range"})

    seen_edges: set[tuple[str, str, str]] = set()
    adjacency: dict[str, set[str]] = {}
    for relation in draft.relations:
        if relation.edge_type not in _EDGE_TYPES:
            raise DraftError(
                "draft_invalid",
                details={"rule": "unknown_edge_type", "edge_type": relation.edge_type},
            )
        if not 0.0 <= relation.confidence <= 1.0:
            raise DraftError("draft_invalid", details={"rule": "relation_confidence_range"})
        source = normalize_concept_label(relation.source_label)
        target = normalize_concept_label(relation.target_label)
        if source == target:
            raise DraftError(
                "draft_invalid",
                details={"rule": "self_edge", "label": relation.source_label},
            )
        if source not in keys or target not in keys:
            raise DraftError(
                "draft_invalid",
                details={
                    "rule": "unknown_endpoint",
                    "source": relation.source_label,
                    "target": relation.target_label,
                },
            )
        edge_key = (source, target, relation.edge_type)
        if edge_key in seen_edges:
            raise DraftError(
                "draft_invalid",
                details={"rule": "duplicate_edge", "edge": relation.source_label},
            )
        seen_edges.add(edge_key)
        if relation.edge_type == "prerequisite_of":
            adjacency.setdefault(source, set()).add(target)

    cycle = _find_cycle(adjacency)
    if cycle is not None:
        raise DraftError("draft_cycle_detected", details={"rule": "cycle", "cycle_path": cycle})


# -- layout --------------------------------------------------------------------


def assign_draft_layout(
    concepts: Iterable[DraftConcept],
    relations: Iterable[DraftRelation],
    *,
    view_id: str,
    x_gap: float = 260.0,
    y_gap: float = 210.0,
) -> tuple[tuple[str, float, float], ...]:
    """Vertical tidy-tree layout along `prerequisite_of` edges (WORK-2026-054).

    Returns `(label, x, y)` tuples where x is a horizontal slot coordinate and
    y grows downward. Levels come from the longest prerequisite chain; each
    concept hangs under exactly one layout parent (its deepest prerequisite,
    so DAG multi-parent concepts are placed once), children are spread side by
    side with the parent centered over them, and concepts without any
    prerequisite edge form a bottom row instead of crowding the top.
    """

    labels = [concept.label for concept in concepts]
    label_set = set(labels)
    prereq_parents: dict[str, list[str]] = {label: [] for label in labels}
    has_prereq_edge: set[str] = set()
    adjacency: dict[str, list[str]] = {label: [] for label in labels}
    indegree: dict[str, int] = {label: 0 for label in labels}
    for relation in relations:
        if relation.edge_type != "prerequisite_of":
            continue
        source = relation.source_label
        target = relation.target_label
        if source not in label_set or target not in label_set or source == target:
            continue
        adjacency[source].append(target)
        indegree[target] += 1
        prereq_parents[target].append(source)
        has_prereq_edge.add(source)
        has_prereq_edge.add(target)

    # Longest-chain levels (topological, deterministic order).
    level: dict[str, int] = {}
    queue: deque[str] = deque(sorted(label for label in labels if indegree[label] == 0))
    for label in queue:
        level[label] = 0
    while queue:
        node = queue.popleft()
        for neighbor in sorted(adjacency[node]):
            level[neighbor] = max(level.get(neighbor, -1), level[node] + 1)
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)
    for label in labels:
        level.setdefault(label, 0)

    # Orphans (no prerequisite edge at all) go to their own bottom row; every
    # other concept hangs under its deepest prerequisite (level-1) parent.
    orphans = sorted(label for label in labels if label not in has_prereq_edge)
    orphan_set = set(orphans)
    primary_parent: dict[str, str] = {}
    for label in sorted(labels):
        if label in orphan_set:
            continue
        primary = None
        for parent in sorted(prereq_parents[label]):
            if level[parent] == level[label] - 1:
                primary = parent
                break
        if primary is None and prereq_parents[label]:
            primary = sorted(prereq_parents[label])[0]
        if primary is not None:
            primary_parent[label] = primary

    def _in_parent_cycle(node: str) -> bool:
        seen = set()
        current = node
        while current in primary_parent:
            if current in seen:
                return True
            seen.add(current)
            current = primary_parent[current]
        return False

    children_map: dict[str, list[str]] = {}
    roots: list[str] = []
    for label in sorted(labels):
        if label in orphan_set:
            continue
        chosen = primary_parent.get(label)
        if chosen is None or _in_parent_cycle(label):
            roots.append(label)
        else:
            children_map.setdefault(chosen, []).append(label)

    positions: dict[str, tuple[float, float]] = {}
    width_memo: dict[str, float] = {}

    def width_of(node: str) -> float:
        memo = width_memo.get(node)
        if memo is not None:
            return memo
        kids = children_map.get(node, [])
        width = x_gap
        if kids:
            width = max(x_gap, sum(width_of(child) for child in kids))
        width_memo[node] = width
        return width

    def place(node: str, left: float) -> None:
        width = width_of(node)
        positions[node] = (left + width / 2, level[node] * y_gap)
        cursor = left
        for child in children_map.get(node, []):
            place(child, cursor)
            cursor += width_of(child)

    cursor = 0.0
    for root in roots:
        place(root, cursor)
        cursor += width_of(root)

    tree_bottom = max((level[label] for label in labels if label not in orphan_set), default=0)
    orphan_row = (tree_bottom + 1) * y_gap
    for index, orphan in enumerate(orphans):
        positions[orphan] = ((index + 0.5) * x_gap, orphan_row)

    return tuple((label, *positions[label]) for label in labels)


# -- patch generation -----------------------------------------------------------


def _unique_sorted(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(set(values)))


def build_draft_patch(
    draft: AiDraft,
    *,
    workspace_id: str,
    course_id: str,
    base_revision_no: int,
    reason: str,
    actor_id: str = "ai-draft-pipeline",
    view_id: str | None = None,
    id_factory: Callable[[], str] = uuid7,
) -> JsonObject:
    """Convert an AI draft into a `proposed`, confirmation-required GraphPatch.

    AI concepts and `prerequisite_of` edges must carry non-empty `evidence_ids`
    or the commit gate would reject them; this mirrors that contract here so
    the failure is local and stable.
    """

    validate_draft(draft)
    if not reason.strip():
        raise DraftError("draft_invalid", details={"rule": "reason_required"})
    for concept in draft.concepts:
        if not concept.evidence_ids:
            raise DraftError(
                "draft_evidence_required",
                details={"rule": "ai_concept_evidence", "label": concept.label},
            )
    for relation in draft.relations:
        if relation.edge_type == "prerequisite_of" and not relation.evidence_ids:
            raise DraftError(
                "draft_evidence_required",
                details={
                    "rule": "ai_prerequisite_evidence",
                    "source": relation.source_label,
                    "target": relation.target_label,
                },
            )

    view = view_id if view_id is not None else id_factory()
    concept_ids = {concept.label: id_factory() for concept in draft.concepts}
    layout = assign_draft_layout(draft.concepts, draft.relations, view_id=view)
    layout_by_label = {label: (x, y) for label, x, y in layout}

    operations: list[JsonObject] = []
    for concept in draft.concepts:
        operations.append(
            {
                "op_id": id_factory(),
                "op": "create_concept",
                "concept": {
                    "id": concept_ids[concept.label],
                    "course_id": course_id,
                    "label": concept.label,
                    "origin": "ai",
                    "review_state": "proposed",
                    "confidence": concept.confidence,
                    "evidence_ids": list(_unique_sorted(concept.evidence_ids)),
                    "locks": {
                        "content": False,
                        "relations": False,
                        "position": False,
                        "annotations": False,
                    },
                    "annotations": [],
                    "revision_no": 0,
                },
            }
        )
    for relation in draft.relations:
        operations.append(
            {
                "op_id": id_factory(),
                "op": "create_edge",
                "expected_source_revision_no": 0,
                "expected_target_revision_no": 0,
                "edge": {
                    "id": id_factory(),
                    "course_id": course_id,
                    "source_concept_id": concept_ids[relation.source_label],
                    "target_concept_id": concept_ids[relation.target_label],
                    "edge_type": relation.edge_type,
                    "origin": "ai",
                    "review_state": "proposed",
                    "confidence": relation.confidence,
                    "evidence_ids": list(_unique_sorted(relation.evidence_ids)),
                    "locked": False,
                    "revision_no": 0,
                },
            }
        )
    for concept in draft.concepts:
        x, y = layout_by_label[concept.label]
        operations.append(
            {
                "op_id": id_factory(),
                "op": "set_layout_item",
                "target": {"type": "concept", "id": concept_ids[concept.label]},
                "expected_updated_revision_no": 0,
                "layout_item": {
                    "view_id": view,
                    "concept_id": concept_ids[concept.label],
                    "x": x,
                    "y": y,
                    "pinned": False,
                    "revision_no": 0,
                },
            }
        )

    return {
        "schema_version": 1,
        "patch_id": id_factory(),
        "workspace_id": workspace_id,
        "course_id": course_id,
        "base_revision_no": base_revision_no,
        "actor": {"type": "ai", "id": actor_id},
        "reason": reason,
        "requires_confirmation": True,
        "confirmed": False,
        "operations": operations,
    }


def build_incremental_patch(
    existing_graph: JsonObject,
    draft: AiDraft,
    *,
    workspace_id: str,
    course_id: str,
    base_revision_no: int,
    reason: str,
    actor_id: str = "ai-draft-pipeline",
    view_id: str | None = None,
    id_factory: Callable[[], str] = uuid7,
) -> JsonObject:
    """Merge a new-material draft into an existing graph as a proposed patch.

    Draft concepts whose normalized label matches an existing concept are mapped
    to that existing id (never re-created or re-laid-out); only genuinely new
    concepts get `create_concept` + `set_layout_item`. Edge endpoints resolve to
    existing or new ids with the correct `expected_*_revision_no`. New AI
    concepts and `prerequisite_of` edges must carry evidence (fail closed).
    """

    validate_draft(draft)
    if not reason.strip():
        raise DraftError("draft_invalid", details={"rule": "reason_required"})

    existing_by_key: dict[str, JsonObject] = {}
    for concept in existing_graph.get("concepts", []):
        if not isinstance(concept, dict) or not isinstance(concept.get("label"), str):
            continue
        key = normalize_concept_label(concept["label"])
        if key in existing_by_key:
            raise DraftError(
                "draft_invalid", details={"rule": "duplicate_existing_label", "key": key}
            )
        existing_by_key[key] = concept

    concept_ids: dict[str, str] = {}
    new_concepts: list[DraftConcept] = []
    for concept in draft.concepts:
        key = normalize_concept_label(concept.label)
        existing = existing_by_key.get(key)
        if existing is not None:
            concept_ids[key] = str(existing["id"])
        else:
            if not concept.evidence_ids:
                raise DraftError(
                    "draft_evidence_required",
                    details={"rule": "ai_concept_evidence", "label": concept.label},
                )
            concept_ids[key] = id_factory()
            new_concepts.append(concept)

    view = view_id if view_id is not None else id_factory()
    layout = assign_draft_layout(draft.concepts, draft.relations, view_id=view)
    layout_by_label = {label: (x, y) for label, x, y in layout}

    operations: list[JsonObject] = []
    for concept in new_concepts:
        key = normalize_concept_label(concept.label)
        operations.append(
            {
                "op_id": id_factory(),
                "op": "create_concept",
                "concept": {
                    "id": concept_ids[key],
                    "course_id": course_id,
                    "label": concept.label,
                    "origin": "ai",
                    "review_state": "proposed",
                    "confidence": concept.confidence,
                    "evidence_ids": list(_unique_sorted(concept.evidence_ids)),
                    "locks": {
                        "content": False,
                        "relations": False,
                        "position": False,
                        "annotations": False,
                    },
                    "annotations": [],
                    "revision_no": 0,
                },
            }
        )

    for relation in draft.relations:
        source_key = normalize_concept_label(relation.source_label)
        target_key = normalize_concept_label(relation.target_label)
        if relation.edge_type == "prerequisite_of" and not relation.evidence_ids:
            raise DraftError(
                "draft_evidence_required",
                details={
                    "rule": "ai_prerequisite_evidence",
                    "source": relation.source_label,
                    "target": relation.target_label,
                },
            )
        operations.append(
            {
                "op_id": id_factory(),
                "op": "create_edge",
                "expected_source_revision_no": int(
                    existing_by_key[source_key].get("revision_no", 0)
                    if source_key in existing_by_key
                    else 0
                ),
                "expected_target_revision_no": int(
                    existing_by_key[target_key].get("revision_no", 0)
                    if target_key in existing_by_key
                    else 0
                ),
                "edge": {
                    "id": id_factory(),
                    "course_id": course_id,
                    "source_concept_id": concept_ids[source_key],
                    "target_concept_id": concept_ids[target_key],
                    "edge_type": relation.edge_type,
                    "origin": "ai",
                    "review_state": "proposed",
                    "confidence": relation.confidence,
                    "evidence_ids": list(_unique_sorted(relation.evidence_ids)),
                    "locked": False,
                    "revision_no": 0,
                },
            }
        )

    for concept in new_concepts:
        key = normalize_concept_label(concept.label)
        x, y = layout_by_label[concept.label]
        operations.append(
            {
                "op_id": id_factory(),
                "op": "set_layout_item",
                "target": {"type": "concept", "id": concept_ids[key]},
                "expected_updated_revision_no": 0,
                "layout_item": {
                    "view_id": view,
                    "concept_id": concept_ids[key],
                    "x": x,
                    "y": y,
                    "pinned": False,
                    "revision_no": 0,
                },
            }
        )

    return {
        "schema_version": 1,
        "patch_id": id_factory(),
        "workspace_id": workspace_id,
        "course_id": course_id,
        "base_revision_no": base_revision_no,
        "actor": {"type": "ai", "id": actor_id},
        "reason": reason,
        "requires_confirmation": True,
        "confirmed": False,
        "operations": operations,
    }
