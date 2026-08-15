"""LLM-backed concept extraction and relation proposal for the AI draft pipeline.

Implements the same `ConceptExtractor` / `RelationCandidateProvider` protocols as
the offline heuristics in `knowledge_tree_infrastructure.ai_draft`, but answers
come from the canonical LLM port using the `concept_extract` and
`relation_validate` task profiles (WORK-2026-009 slice 2).

Safety model:
- No vendor SDK and no storage here: the concrete adapter (DeepSeek, mock,
  fixture) is injected at the composition root as a bound `generate` callable.
- AI output is an untrusted draft. Every item is parsed and shape-validated;
  structural violations fail closed with a stable `DraftExtractionError`, while
  content-level noise (unknown endpoint labels, self edges, duplicate edges) is
  dropped so a noisy model answer cannot corrupt the whole draft.
- Evidence binding still comes from the chunk anchor, so the resulting patch
  can only ever pass the commit gate with real source binding.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from typing import Any

from knowledge_tree_domain.ai_draft import (
    DraftChunk,
    DraftConcept,
    DraftRelation,
    normalize_concept_label,
    uuid7,
)

from knowledge_tree_infrastructure.llm.canonical import (
    Budget,
    CanonicalMessage,
    ContentPart,
    GenerationRequest,
    GenerationResult,
    TraceContext,
)
from knowledge_tree_infrastructure.llm.vendors.deepseek import DeepSeekLlmAdapter

JsonObject = dict[str, Any]

_EDGE_TYPES = frozenset({"prerequisite_of", "related_to", "part_of", "example_of"})

# Fixed valid UUIDv7 used as the default trace correlation id (deterministic).
_DEFAULT_CORRELATION_ID = "00000000-0000-7000-8000-000000000001"

# ---------------------------------------------------------------------------
# prompts / output schemas (JSON-mode friendly: the word "JSON" appears in both)
# ---------------------------------------------------------------------------

CONCEPT_EXTRACT_PROMPT = (
    "从下面的文本中抽取树状知识结构所需的核心概念。"
    "只输出 JSON 对象，格式："
    '{{"concepts": [{{"label": "概念名", "aliases": ["别名"], "confidence": 0.8}}]}}'
    "。要求：label 必填且非空；aliases 可选；confidence 在 0 到 1 之间；"
    "每个概念只出现一次；优先输出定义、定理、方法等可作为知识树节点的概念。"
    "\n\n文本：\n{text}"
)

RELATION_PROMPT = (
    "下面是已抽取的概念列表。判断哪些概念之间存在「先修关系」"
    "（前者是学习后者的前提），并输出候选关系。"
    "只输出 JSON 对象，格式："
    '{{"relations": [{{"from": "概念A", "to": "概念B", '
    '"type": "prerequisite_of", "confidence": 0.7}}]}}'
    "。要求：from/to 必须是列表中的概念名且不得相同；type 只能取 "
    "prerequisite_of/related_to/part_of/example_of；confidence 在 0 到 1 之间。"
    "\n\n概念列表：\n{labels}"
)

CONCEPT_EXTRACT_OUTPUT_SCHEMA: JsonObject = {
    "type": "object",
    "properties": {
        "concepts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "aliases": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number"},
                },
                "required": ["label"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["concepts"],
    "additionalProperties": False,
}

RELATION_OUTPUT_SCHEMA: JsonObject = {
    "type": "object",
    "properties": {
        "relations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "from": {"type": "string"},
                    "to": {"type": "string"},
                    "type": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["from", "to", "type"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["relations"],
    "additionalProperties": False,
}


class DraftExtractionError(ValueError):
    """A stable, identifier-only rejection from an LLM-backed draft extractor.

    Never carries note/source text or reasoning content.
    """

    def __init__(self, code: str, *, details: Mapping[str, Any]) -> None:
        self.code = code
        self.details = dict(details)
        super().__init__(f"{code}: AI draft extraction rejected")


def _extract_json_object(text: str) -> Any:
    """Pull the first balanced-looking JSON object out of a model answer."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise DraftExtractionError("draft_extraction_failed", details={"rule": "no_json_object"})
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        raise DraftExtractionError(
            "draft_extraction_failed", details={"rule": "invalid_json"}
        ) from None


def _budget(max_output_tokens: int) -> Budget:
    return Budget(max_attempts=1, max_output_tokens=max_output_tokens)


# ---------------------------------------------------------------------------
# concept extraction
# ---------------------------------------------------------------------------


class LlmConceptExtractor:
    """Extract concept candidates from a single chunk via the LLM port."""

    def __init__(
        self,
        *,
        generate: Callable[[GenerationRequest], GenerationResult],
        task: str = "concept_extract",
        budget: Budget | None = None,
        trace_context: TraceContext | None = None,
        id_factory: Callable[[], str] = uuid7,
    ) -> None:
        self._generate = generate
        self._task = task
        self._budget = budget or _budget(4096)
        self._trace = trace_context or TraceContext(correlation_id=_DEFAULT_CORRELATION_ID)
        self._id_factory = id_factory

    def extract(self, chunk: DraftChunk) -> tuple[DraftConcept, ...]:
        """Ask the LLM to extract concepts, then shape-validate the answer."""
        if not chunk.text.strip():
            return ()
        request = GenerationRequest(
            model_run_id=self._id_factory(),
            task=self._task,
            messages=(
                CanonicalMessage(
                    role="user",
                    parts=(
                        ContentPart(
                            kind="text",
                            value=CONCEPT_EXTRACT_PROMPT.format(text=chunk.text),
                        ),
                    ),
                ),
            ),
            model_policy=self._task,
            idempotency_key=f"draft-{chunk.chunk_id}",
            budget=self._budget,
            trace_context=self._trace,
            output_schema=CONCEPT_EXTRACT_OUTPUT_SCHEMA,
        )
        result = self._generate(request)
        if result.typed_output is not None:
            data: Any = result.typed_output
        else:
            data = _extract_json_object(result.text or "")
        return self._concepts_from(data, chunk)

    def _concepts_from(self, data: Any, chunk: DraftChunk) -> tuple[DraftConcept, ...]:
        if not isinstance(data, dict) or not isinstance(data.get("concepts"), list):
            raise DraftExtractionError(
                "draft_extraction_failed", details={"rule": "missing_concepts_list"}
            )
        evidence = (chunk.anchor_id,) if chunk.anchor_id is not None else ()
        concepts: list[DraftConcept] = []
        for item in data["concepts"]:
            if not isinstance(item, dict):
                raise DraftExtractionError(
                    "draft_extraction_failed", details={"rule": "concept_item_not_object"}
                )
            label = item.get("label")
            if not isinstance(label, str) or not label.strip():
                raise DraftExtractionError(
                    "draft_extraction_failed", details={"rule": "concept_label_missing"}
                )
            confidence = item.get("confidence", 0.8)
            if (
                not isinstance(confidence, (int, float))
                or isinstance(confidence, bool)
                or not 0.0 <= confidence <= 1.0
            ):
                raise DraftExtractionError(
                    "draft_extraction_failed",
                    details={"rule": "concept_confidence_range", "label": label},
                )
            aliases = item.get("aliases", ())
            if not isinstance(aliases, (list, tuple)) or not all(
                isinstance(alias, str) and alias.strip() for alias in aliases
            ):
                raise DraftExtractionError(
                    "draft_extraction_failed",
                    details={"rule": "concept_aliases_invalid", "label": label},
                )
            concepts.append(
                DraftConcept(
                    label=label.strip(),
                    aliases=tuple(alias.strip() for alias in aliases),
                    confidence=float(confidence),
                    evidence_ids=evidence,
                )
            )
        return tuple(concepts)


# ---------------------------------------------------------------------------
# relation proposal
# ---------------------------------------------------------------------------


class LlmRelationProvider:
    """Propose candidate relations for an ordered concept list via the LLM port."""

    def __init__(
        self,
        *,
        generate: Callable[[GenerationRequest], GenerationResult],
        task: str = "relation_validate",
        budget: Budget | None = None,
        trace_context: TraceContext | None = None,
        id_factory: Callable[[], str] = uuid7,
    ) -> None:
        self._generate = generate
        self._task = task
        self._budget = budget or _budget(8192)
        self._trace = trace_context or TraceContext(correlation_id=_DEFAULT_CORRELATION_ID)
        self._id_factory = id_factory

    def provide(self, concepts: tuple[DraftConcept, ...]) -> tuple[DraftRelation, ...]:
        """Ask the LLM to propose prerequisite relations, then shape-validate."""
        if len(concepts) < 2:
            return ()
        labels = [concept.label for concept in concepts]
        digest = hashlib.sha256("\x00".join(labels).encode("utf-8")).hexdigest()[:16]
        request = GenerationRequest(
            model_run_id=self._id_factory(),
            task=self._task,
            messages=(
                CanonicalMessage(
                    role="user",
                    parts=(
                        ContentPart(
                            kind="text",
                            value=RELATION_PROMPT.format(
                                labels="\n".join(f"- {label}" for label in labels)
                            ),
                        ),
                    ),
                ),
            ),
            model_policy=self._task,
            idempotency_key=f"draft-relations-{digest}",
            budget=self._budget,
            trace_context=self._trace,
            output_schema=RELATION_OUTPUT_SCHEMA,
        )
        result = self._generate(request)
        if result.typed_output is not None:
            data: Any = result.typed_output
        else:
            data = _extract_json_object(result.text or "")
        return self._relations_from(data, concepts)

    def _relations_from(
        self, data: Any, concepts: tuple[DraftConcept, ...]
    ) -> tuple[DraftRelation, ...]:
        if not isinstance(data, dict) or not isinstance(data.get("relations"), list):
            raise DraftExtractionError(
                "draft_extraction_failed", details={"rule": "missing_relations_list"}
            )
        by_key = {normalize_concept_label(concept.label): concept for concept in concepts}
        evidence_by_key = {
            normalize_concept_label(concept.label): tuple(sorted(set(concept.evidence_ids)))
            for concept in concepts
        }
        relations: list[DraftRelation] = []
        seen: set[tuple[str, str, str]] = set()
        for item in data["relations"]:
            if not isinstance(item, dict):
                raise DraftExtractionError(
                    "draft_extraction_failed", details={"rule": "relation_item_not_object"}
                )
            source = item.get("from")
            target = item.get("to")
            edge_type = item.get("type")
            if (
                not isinstance(source, str)
                or not source.strip()
                or not isinstance(target, str)
                or not target.strip()
            ):
                raise DraftExtractionError(
                    "draft_extraction_failed", details={"rule": "relation_endpoint_missing"}
                )
            if not isinstance(edge_type, str) or edge_type not in _EDGE_TYPES:
                raise DraftExtractionError(
                    "draft_extraction_failed",
                    details={"rule": "relation_type_invalid", "type": edge_type},
                )
            confidence = item.get("confidence", 0.7)
            if (
                not isinstance(confidence, (int, float))
                or isinstance(confidence, bool)
                or not 0.0 <= confidence <= 1.0
            ):
                raise DraftExtractionError(
                    "draft_extraction_failed", details={"rule": "relation_confidence_range"}
                )
            source_key = normalize_concept_label(source)
            target_key = normalize_concept_label(target)
            if source_key not in by_key or target_key not in by_key:
                continue  # unknown endpoint label: content noise, drop the edge
            if source_key == target_key:
                continue  # self edge: content noise, drop the edge
            edge_key = (source_key, target_key, edge_type)
            if edge_key in seen:
                continue  # duplicate edge: content noise, drop the duplicate
            seen.add(edge_key)
            evidence = tuple(
                sorted(set(evidence_by_key[source_key]) | set(evidence_by_key[target_key]))
            )
            relations.append(
                DraftRelation(
                    source_label=by_key[source_key].label,
                    target_label=by_key[target_key].label,
                    edge_type=edge_type,
                    confidence=float(confidence),
                    evidence_ids=evidence,
                )
            )
        return tuple(relations)


# ---------------------------------------------------------------------------
# DeepSeek composition helpers (thinking disabled for extraction, enabled for
# relation judging, mirroring the concept_extract / relation_validate profiles)
# ---------------------------------------------------------------------------


def deepseek_concept_extractor(
    adapter: DeepSeekLlmAdapter,
    *,
    max_tokens: int | None = None,
    budget: Budget | None = None,
    trace_context: TraceContext | None = None,
    id_factory: Callable[[], str] = uuid7,
) -> LlmConceptExtractor:
    """Bind a DeepSeek adapter to `LlmConceptExtractor` (thinking disabled)."""
    return LlmConceptExtractor(
        generate=lambda request: adapter.generate(
            request, thinking="disabled", max_tokens=max_tokens
        ),
        budget=budget,
        trace_context=trace_context,
        id_factory=id_factory,
    )


def deepseek_relation_provider(
    adapter: DeepSeekLlmAdapter,
    *,
    max_tokens: int | None = None,
    budget: Budget | None = None,
    trace_context: TraceContext | None = None,
    id_factory: Callable[[], str] = uuid7,
) -> LlmRelationProvider:
    """Bind a DeepSeek adapter to `LlmRelationProvider` (thinking disabled).

    Relations are structured JSON extraction: thinking mode spends tokens on
    `reasoning_content` first and can leave empty content, so it is disabled
    for reliability (WORK-2026-043).
    """
    return LlmRelationProvider(
        generate=lambda request: adapter.generate(
            request, thinking="disabled", max_tokens=max_tokens
        ),
        budget=budget,
        trace_context=trace_context,
        id_factory=id_factory,
    )
