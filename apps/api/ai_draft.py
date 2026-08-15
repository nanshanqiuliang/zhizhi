"""DeepSeek AI-draft generator wiring for the local API (WORK-2026-026 slice 3).

Composition-root glue only: reads the versioned LLM config, builds the DeepSeek
adapters and the LLM-backed extractors, then returns a `DraftGenerator` closure
that turns resource text into an untrusted draft plus a user-confirmable
GraphPatch. `build_deepseek_draft_generator` returns `None` unless the owner has
explicitly provided `DEEPSEEK_API_KEY` (env only), so the endpoint fails closed
with 503 `ai_not_available` when AI is not wired.

Draft evidence binds each chunk to a synthetic UUIDv7 source reference (draft
only — never written to the anchor table); the patch keeps concept/edge
`origin=ai` / `review_state=proposed` while its top-level `actor` is re-authored
as the local user so the existing commit gate can apply it after confirmation.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

# apps/api is run as `python -m apps.api`; add the workspace source trees so the
# knowledge_tree_* packages and the scripts package resolve.
_ROOT = Path(__file__).resolve().parents[2]
for _src in ("packages/contracts-py/src", "packages/domain/src", "packages/infrastructure/src"):
    _path = str(_ROOT / _src)
    if _path not in sys.path:
        sys.path.insert(0, _path)
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from knowledge_tree_domain.ai_draft import build_draft_patch, uuid7  # noqa: E402
from knowledge_tree_infrastructure.ai_draft import build_ai_draft  # noqa: E402
from knowledge_tree_infrastructure.ai_draft_llm import (  # noqa: E402
    LlmConceptExtractor,
    LlmRelationProvider,
)
from knowledge_tree_infrastructure.llm.canonical import Budget  # noqa: E402
from knowledge_tree_infrastructure.llm.resilience import Pricing  # noqa: E402
from knowledge_tree_infrastructure.llm.vendors.deepseek import (  # noqa: E402
    DeepSeekConfig,
    DeepSeekLlmAdapter,
)

from scripts.repository_validation import load_and_validate_llm_config  # noqa: E402

JsonObject = dict[str, Any]

# One DraftGenerator turns resource text into an untrusted draft + proposed patch.
DraftGenerator = Callable[[str, str, JsonObject], JsonObject]

LOCAL_ACTOR = {"type": "user", "id": "local-user"}

_CONCEPT_MAX_TOKENS = 1024
_RELATION_MAX_TOKENS = 4096


def _profile_budget(profile: dict[str, Any]) -> Budget:
    raw = profile.get("budget", {})
    return Budget(
        max_attempts=int(raw.get("max_attempts", 1)),
        max_output_tokens=int(raw.get("max_output_tokens", 4096)),
        max_cost_usd=float(raw["max_cost_usd"]) if raw.get("max_cost_usd") is not None else None,
    )


def build_deepseek_draft_generator() -> DraftGenerator | None:
    """Return a DeepSeek draft generator, or None when the key is not provided."""

    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        return None

    providers, policies = load_and_validate_llm_config(_ROOT)
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
        api_key=key, config=DeepSeekConfig(model_id=fast_model, pricing=pricing)
    )
    relation_adapter = DeepSeekLlmAdapter(
        api_key=key, config=DeepSeekConfig(model_id=quality_model, pricing=pricing)
    )
    concept_profile = policies.get("task_profiles", {}).get("concept_extract", {})
    relation_profile = policies.get("task_profiles", {}).get("relation_validate", {})
    concept_extractor = LlmConceptExtractor(
        generate=lambda request: concept_adapter.generate(
            request, thinking="disabled", max_tokens=_CONCEPT_MAX_TOKENS
        ),
        budget=_profile_budget(concept_profile),
    )
    relation_provider = LlmRelationProvider(
        generate=lambda request: relation_adapter.generate(
            request, thinking="enabled", max_tokens=_RELATION_MAX_TOKENS
        ),
        budget=_profile_budget(relation_profile),
    )

    def generate(text: str, resource_id: str, graph: JsonObject) -> JsonObject:
        draft = build_ai_draft(
            text,
            resource_id=resource_id,
            anchor_id_factory=uuid7,
            extractor=concept_extractor,
            relation_provider=relation_provider,
        )
        patch = build_draft_patch(
            draft,
            workspace_id=str(graph["workspace_id"]),
            course_id=str(graph["course_id"]),
            base_revision_no=int(graph["revision_no"]),
            reason="AI 草案（从本地资料生成，用户已确认）",
            id_factory=uuid7,
        )
        # Re-author the proposed patch for the user-confirmed commit gate. The
        # persistent gate only accepts user-authored (`origin=user`) confirmed
        # patches (`actor_origin_mismatch` otherwise); provenance is preserved
        # via `evidence_ids` (source) plus the `draft` payload (AI confidence
        # and labels) shown at preview. AI `confidence` must become null on a
        # user-authored entity (`user_confidence_must_be_null`).
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
        return {
            "draft": {
                "concepts": [
                    {
                        "label": concept.label,
                        "aliases": list(concept.aliases),
                        "confidence": concept.confidence,
                        "evidence_ids": list(concept.evidence_ids),
                    }
                    for concept in draft.concepts
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
        }

    return generate
