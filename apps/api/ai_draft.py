"""DeepSeek AI-draft generator wiring for the local API (WORK-2026-026/043).

Composition-root glue only: reads the versioned LLM config, builds the DeepSeek
adapters and the LLM-backed extractors, then returns generator closures that
turn resource text (single resource or the whole workspace corpus) into an
untrusted draft plus a user-confirmable GraphPatch. The builders return `None`
unless an API key is provided (explicitly or via `DEEPSEEK_API_KEY`), so the
endpoint fails closed with 503 `ai_not_available` when AI is not wired.

Harness constraints (the "mind-map agent" must obey all of these):
1. The agent output is always an *untrusted draft* — it never writes the
   database, never bypasses preview/confirmation, and never touches locks.
2. Every new concept/relation carries `evidence_ids` bound to a real imported
   resource anchor; accepted drafts materialize those anchors (single
   transaction) so claims stay traceable to the source files.
3. Structural validation is deterministic: dedupe, DAG/cycle rejection, schema
   validation and the persistent commit gate all run before any write.
4. Malformed model output fails closed with stable codes (`draft_extraction_failed`);
   budget/attempt caps apply per task profile.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from apps.api._runtime import ensure_source_paths, runtime_root

ensure_source_paths()

from knowledge_tree_domain.ai_draft import (  # noqa: E402
    AiDraft,
    build_incremental_patch,
    deterministic_uuidv7,
    normalize_concept_label,
    uuid7,
)
from knowledge_tree_infrastructure.ai_draft import (  # noqa: E402
    ConceptExtractor,
    RelationCandidateProvider,
    build_incremental_ai_draft,
    build_workspace_ai_draft,
)
from knowledge_tree_infrastructure.ai_draft_llm import (  # noqa: E402
    DraftExtractionError,
    LlmConceptExtractor,
    LlmRelationProvider,
)
from knowledge_tree_infrastructure.llm.canonical import Budget  # noqa: E402
from knowledge_tree_infrastructure.llm.resilience import Pricing  # noqa: E402
from knowledge_tree_infrastructure.llm.vendors.deepseek import (  # noqa: E402
    DeepSeekConfig,
    DeepSeekLlmAdapter,
)

from scripts.repository_validation import (  # noqa: E402
    RepositoryValidationError,
    load_and_validate_llm_config,
)

JsonObject = dict[str, Any]

# One DraftGenerator turns resource text into an untrusted draft + proposed patch.
DraftGenerator = Callable[[str, str, JsonObject], JsonObject]

# One WorkspaceDraftGenerator turns the whole corpus (resource_id, text) into a draft.
WorkspaceDraftGenerator = Callable[[list[tuple[str, str]], JsonObject], JsonObject]

LOCAL_ACTOR = {"type": "user", "id": "local-user"}

_CONCEPT_MAX_TOKENS = 1024
_RELATION_MAX_TOKENS = 8192
_MAX_CHUNKS = 40


def fail_soft_extractor(extractor: ConceptExtractor) -> ConceptExtractor:
    """Wrap an LLM extractor so one malformed chunk is skipped, not fatal.

    Only `DraftExtractionError` (bad model content on a single chunk) is
    swallowed; transport/auth errors (`LLMProviderError`) still propagate so a
    dead key or network failure surfaces as 502 instead of silently producing
    an empty draft.
    """

    class _Wrapper:
        def extract(self, chunk: Any) -> tuple[Any, ...]:
            try:
                return extractor.extract(chunk)
            except DraftExtractionError:
                return ()

    return _Wrapper()


def fail_soft_relation_provider(
    provider: RelationCandidateProvider,
) -> RelationCandidateProvider:
    """Wrap the relation provider: a malformed relation answer yields no edges."""

    class _Wrapper:
        def provide(self, concepts: tuple[Any, ...]) -> tuple[Any, ...]:
            try:
                return provider.provide(concepts)
            except DraftExtractionError:
                return ()

    return _Wrapper()


def _profile_budget(profile: dict[str, Any]) -> Budget:
    raw = profile.get("budget", {})
    return Budget(
        max_attempts=int(raw.get("max_attempts", 1)),
        max_output_tokens=int(raw.get("max_output_tokens", 4096)),
        max_cost_usd=float(raw["max_cost_usd"]) if raw.get("max_cost_usd") is not None else None,
    )


def _build_components(
    api_key: str,
) -> tuple[LlmConceptExtractor, LlmRelationProvider] | None:
    """Build the DeepSeek extractor/provider pair, failing closed on config errors."""

    try:
        providers, policies = load_and_validate_llm_config(runtime_root())
        deepseek = providers.get("providers", {}).get("deepseek", {})
        if not isinstance(deepseek, dict) or deepseek.get("enabled") is not True:
            return None
        fast_model = deepseek.get("models", {}).get("fast", {}).get("model_id")
        quality_model = deepseek.get("models", {}).get("quality", {}).get("model_id")
        pricing_raw = deepseek.get("models", {}).get("fast", {}).get("pricing", {})
        if not isinstance(fast_model, str) or not isinstance(quality_model, str):
            return None
        pricing = Pricing(
            input_usd_per_mtok=float(pricing_raw.get("input_usd_per_mtok", 0.28)),
            output_usd_per_mtok=float(pricing_raw.get("output_usd_per_mtok", 1.14)),
        )
        concept_adapter = DeepSeekLlmAdapter(
            api_key=api_key, config=DeepSeekConfig(model_id=fast_model, pricing=pricing)
        )
        relation_adapter = DeepSeekLlmAdapter(
            api_key=api_key, config=DeepSeekConfig(model_id=quality_model, pricing=pricing)
        )
        concept_profile = policies.get("task_profiles", {}).get("concept_extract", {})
        relation_profile = policies.get("task_profiles", {}).get("relation_validate", {})
        concept_extractor = LlmConceptExtractor(
            generate=lambda request: concept_adapter.generate(
                request, thinking="disabled", max_tokens=_CONCEPT_MAX_TOKENS
            ),
            budget=_profile_budget(concept_profile),
        )
        # Thinking mode spends tokens on reasoning_content first, which can
        # leave empty content for structured JSON tasks; relations are JSON
        # extraction, so run them non-thinking for reliable, direct output.
        relation_provider = LlmRelationProvider(
            generate=lambda request: relation_adapter.generate(
                request, thinking="disabled", max_tokens=_RELATION_MAX_TOKENS
            ),
            budget=_profile_budget(relation_profile),
        )
    except (OSError, ValueError, KeyError, TypeError, RepositoryValidationError):
        return None
    return concept_extractor, relation_provider


def _finalize_draft(graph: JsonObject, draft: AiDraft, evidence: list[JsonObject]) -> JsonObject:
    """Turn an AiDraft into the preview payload (patch + draft + evidence)."""

    patch = build_incremental_patch(
        graph,
        draft,
        workspace_id=str(graph["workspace_id"]),
        course_id=str(graph["course_id"]),
        base_revision_no=int(graph["revision_no"]),
        reason="AI 草案（从本地资料生成，用户已确认）",
        id_factory=uuid7,
    )
    # Re-author the proposed patch for the user-confirmed commit gate. The
    # persistent gate only accepts user-authored (`origin=user`) confirmed
    # patches (`actor_origin_mismatch` otherwise); provenance is preserved via
    # `evidence_ids` (source) plus the `draft` payload shown at preview. AI
    # `confidence` must become null on a user-authored entity.
    for operation in patch["operations"]:
        if operation["op"] == "create_concept":
            operation["concept"]["origin"] = "user"
            operation["concept"]["review_state"] = "accepted"
            operation["concept"]["confidence"] = None
        elif operation["op"] == "create_edge":
            operation["edge"]["origin"] = "user"
            operation["edge"]["review_state"] = "accepted"
            operation["edge"]["confidence"] = None
    patch["actor"] = dict(LOCAL_ACTOR)
    patch["confirmed"] = False
    existing_keys = {
        normalize_concept_label(str(concept["label"]))
        for concept in graph.get("concepts", [])
        if isinstance(concept, dict) and isinstance(concept.get("label"), str)
    }
    new_concepts = [
        concept
        for concept in draft.concepts
        if normalize_concept_label(concept.label) not in existing_keys
    ]
    return {
        "draft": {
            "concepts": [
                {
                    "label": concept.label,
                    "aliases": list(concept.aliases),
                    "confidence": concept.confidence,
                    "evidence_ids": list(concept.evidence_ids),
                }
                for concept in new_concepts
            ],
            "relations": [
                {
                    "source_label": relation.source_label,
                    "target_label": relation.target_label,
                    "edge_type": relation.edge_type,
                    "confidence": relation.confidence,
                    "evidence_ids": list(relation.evidence_ids),
                }
                for relation in draft.relations
            ],
        },
        "patch": patch,
        "evidence": evidence,
    }


def build_deepseek_draft_generator(api_key: str | None = None) -> DraftGenerator | None:
    """Return a single-resource DeepSeek draft generator, or None without a key."""

    key = api_key if api_key is not None else os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        return None
    components = _build_components(key)
    if components is None:
        return None
    concept_extractor, relation_provider = components

    def generate(text: str, resource_id: str, graph: JsonObject) -> JsonObject:
        anchor_id = deterministic_uuidv7(resource_id)
        draft = build_incremental_ai_draft(
            graph,
            text,
            resource_id=resource_id,
            anchor_id_factory=lambda: anchor_id,
            extractor=fail_soft_extractor(concept_extractor),
            relation_provider=fail_soft_relation_provider(relation_provider),
            max_chunks=_MAX_CHUNKS,
        )
        return _finalize_draft(
            graph,
            draft,
            [{"anchor_id": anchor_id, "resource_id": resource_id, "label": "AI 草案来源"}],
        )

    return generate


def build_deepseek_workspace_draft_generator(
    api_key: str | None = None,
) -> WorkspaceDraftGenerator | None:
    """Return a whole-workspace draft generator, or None without a key.

    The agent reads every imported resource (already extracted to text by the
    endpoint), merges concepts across the corpus and proposes relations — the
    same untrusted-draft harness constraints apply.
    """

    key = api_key if api_key is not None else os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        return None
    components = _build_components(key)
    if components is None:
        return None
    concept_extractor, relation_provider = components

    def generate(texts: list[tuple[str, str]], graph: JsonObject) -> JsonObject:
        draft = build_workspace_ai_draft(
            graph,
            texts,
            extractor=fail_soft_extractor(concept_extractor),
            relation_provider=fail_soft_relation_provider(relation_provider),
        )
        evidence = [
            {
                "anchor_id": deterministic_uuidv7(resource_id),
                "resource_id": resource_id,
                "label": "AI 草案来源",
            }
            for resource_id, _text in texts
        ]
        return _finalize_draft(graph, draft, evidence)

    return generate
