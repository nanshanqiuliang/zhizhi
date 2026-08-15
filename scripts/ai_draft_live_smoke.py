"""Live DeepSeek AI-draft generation smoke (WORK-2026-009 slice 2, live-gated).

Runs the real DeepSeek adapter through the LLM-backed draft extractors
(`knowledge_tree_infrastructure.ai_draft_llm`) over a short calculus sample,
then converts the resulting draft into a GraphPatch and proves the commit gate
accepts it as `requires_confirmation` (never auto-applied).

Gated by `RUN_LIVE_LLM_TESTS=1` and `DEEPSEEK_API_KEY`; the API key is read
from the environment only and is never written to a file. The JSON report
contains concept labels, relation label pairs and token usage only — no note
text, no reasoning content, no secret.

Usage:
    RUN_LIVE_LLM_TESTS=1 DEEPSEEK_API_KEY=... uv run python -m scripts.ai_draft_live_smoke
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
for _src in ("packages/contracts-py/src", "packages/domain/src", "packages/infrastructure/src"):
    _path = str(_ROOT / _src)
    if _path not in sys.path:
        sys.path.insert(0, _path)
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from knowledge_tree_domain import preview_graph_patch  # noqa: E402
from knowledge_tree_domain.ai_draft import build_draft_patch, validate_draft  # noqa: E402
from knowledge_tree_infrastructure.ai_draft import build_ai_draft  # noqa: E402
from knowledge_tree_infrastructure.ai_draft_llm import (  # noqa: E402
    LlmConceptExtractor,
    LlmRelationProvider,
)
from knowledge_tree_infrastructure.llm.canonical import (  # noqa: E402
    Budget,
    GenerationRequest,
    GenerationResult,
)
from knowledge_tree_infrastructure.llm.resilience import Pricing  # noqa: E402
from knowledge_tree_infrastructure.llm.vendors.deepseek import (  # noqa: E402
    DeepSeekConfig,
    DeepSeekLlmAdapter,
)

from scripts.repository_validation import load_and_validate_llm_config  # noqa: E402

REPORT_PATH = Path("evals/calculus-v1/ai-draft-live-smoke.json")

WORKSPACE_ID = "00000000-0000-7000-8000-000000000001"
COURSE_ID = "00000000-0000-7000-8000-000000000002"
RESOURCE_ID = "00000000-0000-7000-8000-000000000003"
AI_ACTOR = {"type": "ai", "id": "ai-draft-pipeline"}

SAMPLE_TEXT = "\n\n".join(
    [
        "# 极限",
        "函数在一点趋近的值称为极限。",
        "# 连续",
        "若函数在某点的极限等于函数值，则称函数在该点连续。",
        "# 导数",
        "导数是函数变化率的极限，导数的存在以连续为前提。",
        "# 可导",
        "函数在某点可导当且仅当导数存在。",
    ]
)

CONCEPT_MAX_TOKENS = 1024
# Thinking mode spends tokens on reasoning_content first; keep enough headroom
# for the JSON answer (DeepSeek V4 with too-small max_tokens ends with
# finish_reason=length and empty content).
RELATION_MAX_TOKENS = 4096


class _UsageTracker:
    """Wrap an adapter to accumulate token usage for the cost report."""

    def __init__(self, adapter: DeepSeekLlmAdapter) -> None:
        self._adapter = adapter
        self.input_tokens = 0
        self.output_tokens = 0

    def generate(self, request: GenerationRequest, **kwargs: Any) -> GenerationResult:
        result = self._adapter.generate(request, **kwargs)
        self.input_tokens += result.usage.input_tokens
        self.output_tokens += result.usage.output_tokens
        return result


def _profile_budget(profile: dict[str, Any]) -> Budget:
    raw = profile.get("budget", {})
    return Budget(
        max_attempts=int(raw.get("max_attempts", 1)),
        max_output_tokens=int(raw.get("max_output_tokens", 4096)),
        max_cost_usd=float(raw["max_cost_usd"]) if raw.get("max_cost_usd") is not None else None,
    )


def main() -> int:
    if os.environ.get("RUN_LIVE_LLM_TESTS") != "1":
        print("SKIP: set RUN_LIVE_LLM_TESTS=1 and DEEPSEEK_API_KEY to run the live smoke")
        return 0
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        print("FAIL: DEEPSEEK_API_KEY not set")
        return 1

    providers, policies = load_and_validate_llm_config(_ROOT)
    deepseek = providers.get("providers", {}).get("deepseek", {})
    if not isinstance(deepseek, dict) or deepseek.get("enabled") is not True:
        print("FAIL: deepseek provider is not enabled in config/llm/providers.yaml")
        return 1
    fast_model = deepseek.get("models", {}).get("fast", {}).get("model_id")
    quality_model = deepseek.get("models", {}).get("quality", {}).get("model_id")
    pricing_raw = deepseek.get("models", {}).get("fast", {}).get("pricing", {})
    if not isinstance(fast_model, str) or not isinstance(quality_model, str):
        print("FAIL: deepseek fast/quality model ids missing in providers.yaml")
        return 1
    pricing = Pricing(
        input_usd_per_mtok=float(pricing_raw.get("input_usd_per_mtok", 0.28)),
        output_usd_per_mtok=float(pricing_raw.get("output_usd_per_mtok", 1.14)),
    )

    concept_tracker = _UsageTracker(
        DeepSeekLlmAdapter(api_key=key, config=DeepSeekConfig(model_id=fast_model, pricing=pricing))
    )
    relation_tracker = _UsageTracker(
        DeepSeekLlmAdapter(
            api_key=key, config=DeepSeekConfig(model_id=quality_model, pricing=pricing)
        )
    )

    concept_profile = policies.get("task_profiles", {}).get("concept_extract", {})
    relation_profile = policies.get("task_profiles", {}).get("relation_validate", {})
    extractor = LlmConceptExtractor(
        generate=lambda request: concept_tracker.generate(
            request, thinking="disabled", max_tokens=CONCEPT_MAX_TOKENS
        ),
        budget=_profile_budget(concept_profile),
    )
    provider = LlmRelationProvider(
        generate=lambda request: relation_tracker.generate(
            request, thinking="enabled", max_tokens=RELATION_MAX_TOKENS
        ),
        budget=_profile_budget(relation_profile),
    )

    started = time.monotonic()
    draft = build_ai_draft(
        SAMPLE_TEXT,
        resource_id=RESOURCE_ID,
        anchor_id_factory=_anchor_factory(),
        extractor=extractor,
        relation_provider=provider,
    )
    validate_draft(draft)
    patch = build_draft_patch(
        draft,
        workspace_id=WORKSPACE_ID,
        course_id=COURSE_ID,
        base_revision_no=0,
        reason="AI 草案：微积分概念链（live DeepSeek 抽取）",
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
    elapsed_ms = (time.monotonic() - started) * 1000.0

    total_in = concept_tracker.input_tokens + relation_tracker.input_tokens
    total_out = concept_tracker.output_tokens + relation_tracker.output_tokens
    cost = (
        total_in / 1e6 * pricing.input_usd_per_mtok + total_out / 1e6 * pricing.output_usd_per_mtok
    )

    report = {
        "eval_id": "AI-DRAFT-LIVE-SMOKE-001",
        "generated_at": datetime.now(UTC).isoformat(),
        "models": {"concept_extract": fast_model, "relation_validate": quality_model},
        "chunks": 1,
        "concepts": [concept.label for concept in draft.concepts],
        "relations": [
            [relation.source_label, relation.target_label, relation.edge_type]
            for relation in draft.relations
        ],
        "preview_status": preview.status,
        "patch_operations": len(patch["operations"]),
        "usage": {
            "input_tokens": total_in,
            "output_tokens": total_out,
            "estimated_cost_usd": round(cost, 8),
        },
        "latency_ms": round(elapsed_ms, 1),
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(
        f"\nAI-DRAFT-LIVE-SMOKE done: {total_in} in / {total_out} out tokens, "
        f"~${cost:.6f} USD, preview={preview.status}, report -> {REPORT_PATH}"
    )
    if preview.status != "requires_confirmation":
        print("FAIL: expected preview status requires_confirmation")
        return 1
    return 0


def _anchor_factory() -> Any:
    state = {"n": 0}

    def factory() -> str:
        state["n"] += 1
        return f"00000000-0000-7000-9000-{state['n']:012d}"

    return factory


if __name__ == "__main__":
    raise SystemExit(main())
