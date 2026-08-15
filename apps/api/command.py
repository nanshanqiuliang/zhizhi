"""DeepSeek command-interpretation wiring for the local API (WORK-2026-029).

Composition-root glue only: builds a DeepSeek adapter for the
`command_interpret` task profile and returns a `CommandGenerator` closure that
turns a natural-language command plus the current concept list into
`{summary, operations}` (operations reference concepts by label). Returns `None`
unless `DEEPSEEK_API_KEY` is provided (env only), so the endpoint fails closed
with 503 `ai_not_available` when AI is not wired.
"""

from __future__ import annotations

import json
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

# One CommandGenerator turns (command, concepts) into {summary, operations}.
CommandGenerator = Callable[[str, list[JsonObject]], JsonObject]

_COMMAND_PROMPT = (
    "把下面的中文操作命令解释成结构化 JSON 操作列表。"
    "当前概念（只能引用这些概念名，原样使用）：{labels}\n"
    "支持的操作：\n"
    '- {{"op":"set_lock","target":"概念名","dimension":"content"|"position","value":true|false}}\n'
    '- {{"op":"create_edge","source":"概念名","target":"概念名",'
    '"edge_type":"prerequisite_of"|"related_to"|"part_of"|"example_of"}}\n'
    "注意：create_edge 的 source 是 target 的先修（学习前提）。"
    '只输出 JSON 对象，格式：{{"summary":"一句话摘要","operations":[...]}}。\n'
    "命令：{command}"
)

_DEFAULT_CORRELATION_ID = "00000000-0000-7000-8000-000000000021"


def _profile_budget(profile: dict[str, Any]) -> Budget:
    raw = profile.get("budget", {})
    return Budget(
        max_attempts=int(raw.get("max_attempts", 1)),
        max_output_tokens=int(raw.get("max_output_tokens", 2048)),
        max_cost_usd=float(raw["max_cost_usd"]) if raw.get("max_cost_usd") is not None else None,
    )


def _extract_json_object(text: str) -> Any:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no_json_object")
    return json.loads(text[start : end + 1])


def build_deepseek_command_generator() -> CommandGenerator | None:
    """Return a DeepSeek command generator, or None when the key is not provided."""

    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        return None

    try:
        providers, policies = load_and_validate_llm_config(_ROOT)
        deepseek = providers.get("providers", {}).get("deepseek", {})
        if not isinstance(deepseek, dict) or deepseek.get("enabled") is not True:
            return None
        fast = deepseek.get("models", {}).get("fast", {})
        pricing_raw = deepseek.get("models", {}).get("fast", {}).get("pricing", {})
        if not isinstance(fast, dict) or not isinstance(fast.get("model_id"), str):
            return None
        pricing = Pricing(
            input_usd_per_mtok=float(pricing_raw.get("input_usd_per_mtok", 0.28)),
            output_usd_per_mtok=float(pricing_raw.get("output_usd_per_mtok", 1.14)),
        )
        adapter = DeepSeekLlmAdapter(
            api_key=key, config=DeepSeekConfig(model_id=fast["model_id"], pricing=pricing)
        )
        command_profile = policies.get("task_profiles", {}).get("command_interpret", {})
        budget = _profile_budget(command_profile)
    except (OSError, ValueError, KeyError, TypeError, RepositoryValidationError):
        return None

    def generate(command: str, concepts: list[JsonObject]) -> JsonObject:
        labels = ", ".join(str(concept["label"]) for concept in concepts if concept.get("label"))
        prompt = _COMMAND_PROMPT.format(labels=labels, command=command)
        request = GenerationRequest(
            model_run_id=uuid7(),
            task="command_interpret",
            messages=(
                CanonicalMessage(role="user", parts=(ContentPart(kind="text", value=prompt),)),
            ),
            model_policy="command_interpret",
            idempotency_key=f"command-{uuid7()}",
            budget=budget,
            trace_context=TraceContext(correlation_id=_DEFAULT_CORRELATION_ID),
        )
        result = adapter.generate(request, thinking="disabled", max_tokens=budget.max_output_tokens)
        data = _extract_json_object(result.text or "")
        if not isinstance(data, dict) or not isinstance(data.get("operations"), list):
            raise ValueError("operations_missing")
        return {
            "summary": str(data.get("summary", "")),
            "operations": [op for op in data["operations"] if isinstance(op, dict)],
        }

    return generate
