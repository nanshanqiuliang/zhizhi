"""DeepSeek answer-with-sources wiring for the local API (WORK-2026-028, Step 9 slice 1).

Composition-root glue only: builds a DeepSeek adapter for the `answer_with_sources`
task profile and returns an `AnswerGenerator` closure that turns a question plus
citation-numbered context into a sourced answer. `build_deepseek_answer_generator`
returns `None` unless `DEEPSEEK_API_KEY` is provided (env only), so the endpoint
fails closed with 503 `ai_not_available` when AI is not wired.

The answer is plain text with `[n]` citation markers; the source refs themselves
are the deterministic FTS5 retrieval hits, not the model's invention.
"""

from __future__ import annotations

import hashlib
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

# apps/api is run as `python -m apps.api`; add the workspace source trees.
_ROOT = Path(__file__).resolve().parents[2]
for _src in ("packages/contracts-py/src", "packages/domain/src", "packages/infrastructure/src"):
    _path = str(_ROOT / _src)
    if _path not in sys.path:
        sys.path.insert(0, _path)
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from knowledge_tree_domain.ai_draft import uuid7  # noqa: E402
from knowledge_tree_infrastructure.llm.canonical import (  # noqa: E402
    Budget,
    CanonicalMessage,
    ContentPart,
    GenerationRequest,
    TraceContext,
)
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

# One AnswerGenerator turns (question, context, sources) into {answer, sources}.
AnswerGenerator = Callable[[str, str, list[JsonObject]], JsonObject]

_ANSWER_PROMPT = (
    "基于下面的本地知识片段回答用户问题。回答用中文，简洁准确；"
    "引用来源时使用方括号编号（如 [1]）。若片段不足以回答，请明确说明。\n\n"
    "本地知识片段：\n{context}\n\n问题：{question}"
)

_DEFAULT_CORRELATION_ID = "00000000-0000-7000-8000-000000000011"


def _profile_budget(profile: dict[str, Any]) -> Budget:
    raw = profile.get("budget", {})
    return Budget(
        max_attempts=int(raw.get("max_attempts", 1)),
        max_output_tokens=int(raw.get("max_output_tokens", 8192)),
        max_cost_usd=float(raw["max_cost_usd"]) if raw.get("max_cost_usd") is not None else None,
    )


def build_deepseek_answer_generator() -> AnswerGenerator | None:
    """Return a DeepSeek answer generator, or None when the key is not provided."""

    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        return None

    try:
        providers, policies = load_and_validate_llm_config(_ROOT)
        deepseek = providers.get("providers", {}).get("deepseek", {})
        if not isinstance(deepseek, dict) or deepseek.get("enabled") is not True:
            return None
        quality = deepseek.get("models", {}).get("quality", {})
        pricing_raw = deepseek.get("models", {}).get("fast", {}).get("pricing", {})
        if not isinstance(quality, dict) or not isinstance(quality.get("model_id"), str):
            return None
        pricing = Pricing(
            input_usd_per_mtok=float(pricing_raw.get("input_usd_per_mtok", 0.28)),
            output_usd_per_mtok=float(pricing_raw.get("output_usd_per_mtok", 1.14)),
        )
        adapter = DeepSeekLlmAdapter(
            api_key=key, config=DeepSeekConfig(model_id=quality["model_id"], pricing=pricing)
        )
        answer_profile = policies.get("task_profiles", {}).get("answer_with_sources", {})
        budget = _profile_budget(answer_profile)
    except (OSError, ValueError, KeyError, TypeError, RepositoryValidationError):
        return None

    def generate(question: str, context: str, sources: list[JsonObject]) -> JsonObject:
        prompt = _ANSWER_PROMPT.format(context=context or "（无匹配片段）", question=question)
        digest = hashlib.sha256((question + "\x00" + context).encode("utf-8")).hexdigest()[:16]
        request = GenerationRequest(
            model_run_id=uuid7(),
            task="answer_with_sources",
            messages=(
                CanonicalMessage(role="user", parts=(ContentPart(kind="text", value=prompt),)),
            ),
            model_policy="answer_with_sources",
            idempotency_key=f"answer-{digest}",
            budget=budget,
            trace_context=TraceContext(correlation_id=_DEFAULT_CORRELATION_ID),
        )
        result = adapter.generate(request, thinking="enabled", max_tokens=budget.max_output_tokens)
        return {"answer": (result.text or "").strip(), "sources": sources}

    return generate
