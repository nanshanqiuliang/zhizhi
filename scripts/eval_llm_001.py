"""DeepSeek calculus gold evaluation — EVAL-LLM-001 (roadmap Step 7, live-gated).

Runs four offline/live sub-tasks against the frozen calculus gold dataset:
concept extraction, relation candidate, command interpretation and answer with
sources. Requires `RUN_LIVE_LLM_TESTS=1` and `DEEPSEEK_API_KEY`; reports
quality metrics, token usage, estimated cost and latency. The API key is read
from the environment only and never logged.

Usage:
    RUN_LIVE_LLM_TESTS=1 DEEPSEEK_API_KEY=... uv run python -m scripts.eval_llm_001
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# The workspace packages are source trees, not installed distributions; add
# them so `python -m scripts.eval_llm_001` resolves knowledge_tree_* like pytest.
_ROOT = Path(__file__).resolve().parents[1]
for _src in ("packages/contracts-py/src", "packages/domain/src", "packages/infrastructure/src"):
    _path = str(_ROOT / _src)
    if _path not in sys.path:
        sys.path.insert(0, _path)

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

GOLD_PATH = Path("evals/calculus-v1/gold.json")
REPORT_PATH = Path("evals/calculus-v1/eval-llm-001-live.json")

# Deploy-time price snapshot (USD per million tokens); recalibrate per provider.
PRICING = Pricing(input_usd_per_mtok=0.28, output_usd_per_mtok=1.14)


def _uuidv7(seq: int) -> str:
    # Deterministic valid UUIDv7 for reproducible eval runs.
    return f"00000000-0000-7000-8000-00000000{seq:04x}"


def _request(
    model_run_id: str, task: str, message: str, *, output_schema: Any = None
) -> GenerationRequest:
    return GenerationRequest(
        model_run_id=model_run_id,
        task=task,
        messages=(CanonicalMessage(role="user", parts=(ContentPart(kind="text", value=message),)),),
        model_policy=task,
        idempotency_key=f"eval-{model_run_id}",
        budget=Budget(max_attempts=1, max_output_tokens=1500, max_cost_usd=0.05),
        trace_context=TraceContext(correlation_id=model_run_id),
        output_schema=output_schema,
    )


def _parse_json(text: str | None) -> Any | None:
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def _run(adapter: DeepSeekLlmAdapter, request: GenerationRequest) -> tuple[Any, int, int, float]:
    started = time.monotonic()
    result = adapter.generate(request, thinking="disabled", max_tokens=1500)
    elapsed_ms = (time.monotonic() - started) * 1000.0
    return (
        _parse_json(result.text),
        result.usage.input_tokens,
        result.usage.output_tokens,
        elapsed_ms,
    )


def task_concept_extract(adapter: DeepSeekLlmAdapter, gold: Any) -> dict[str, Any]:
    gold_labels = {c["preferred_label_zh"] for c in gold["concepts"]}
    message = (
        "列出微积分「连续性与可导性」主题的核心概念。只输出 JSON 对象，格式："
        '{"concepts": [{"label": "概念名", "definition": "一句话定义"}]}，'
        "尽量覆盖极限、连续、导数、可导、增量、差分商等基础概念。"
    )
    data, in_tok, out_tok, ms = _run(
        adapter,
        _request(_uuidv7(0x11), "concept_extract", message),
    )
    labels = [c["label"] for c in (data or {}).get("concepts", []) if isinstance(c, dict)]
    hits = [label for label in labels if label in gold_labels]
    recall = len(hits) / len(gold_labels) if gold_labels else 0.0
    return {
        "task": "concept_extract",
        "gold_count": len(gold_labels),
        "extracted_count": len(labels),
        "matched": hits,
        "recall": round(recall, 4),
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "latency_ms": round(ms, 1),
        "parse_ok": data is not None,
    }


def task_relation_candidate(adapter: DeepSeekLlmAdapter, gold: Any) -> dict[str, Any]:
    label = {c["id"]: c["preferred_label_zh"] for c in gold["concepts"]}
    gold_pairs = {
        (r["source_concept_id"], r["target_concept_id"]) for r in gold["relations"]
    }
    sample = list(gold["relations"])[:10]
    positives = [
        f"{label[r['source_concept_id']]} -> {label[r['target_concept_id']]}" for r in sample
    ]
    negatives = [
        f"{label[r['target_concept_id']]} -> {label[r['source_concept_id']]}" for r in sample[:5]
    ]
    pairs = positives + negatives
    message = (
        "判断下列概念对是否满足「先修关系」（前者是学习后者的前提）。只输出 JSON 对象，格式："
        '{"pairs": [{"from": "概念A", "to": "概念B", "is_prerequisite": true或false}]}。概念对：'
        + json.dumps(pairs, ensure_ascii=False)
    )
    data, in_tok, out_tok, ms = _run(
        adapter,
        _request(_uuidv7(0x12), "relation_validate", message),
    )
    correct = 0
    judged = (data or {}).get("pairs", [])
    if isinstance(judged, list):
        for item in judged:
            if not isinstance(item, dict):
                continue
            # Map labels back to ids for scoring (best effort).
            pair_key = _resolve_pair(item, label, gold_pairs)
            if pair_key is not None:
                expected = pair_key in gold_pairs
                got = bool(item.get("is_prerequisite"))
                if got == expected:
                    correct += 1
    total = len(positives) + len(negatives)
    accuracy = correct / total if total else 0.0
    return {
        "task": "relation_candidate",
        "sample_size": total,
        "correct": correct,
        "accuracy": round(accuracy, 4),
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "latency_ms": round(ms, 1),
        "parse_ok": data is not None,
    }


def _resolve_pair(item: dict[str, Any], label: dict[str, str], gold_pairs: Any) -> Any | None:
    frm = item.get("from")
    to = item.get("to")
    if not isinstance(frm, str) or not isinstance(to, str):
        return None
    rev_label = {v: k for k, v in label.items()}
    frm_id = rev_label.get(frm, frm)
    to_id = rev_label.get(to, to)
    if (frm_id, to_id) in gold_pairs:
        return (frm_id, to_id)
    if (to_id, frm_id) in gold_pairs:
        return (to_id, frm_id)
    return None


def task_command_interpret(adapter: DeepSeekLlmAdapter, gold: Any) -> dict[str, Any]:
    message = (
        "把下面的中文操作命令解释成结构化 JSON。只输出 JSON 对象，格式："
        '{"action": "mark_important"或"create_edge"或"lock", "target": "概念名", '
        '"related": ["相关概念"]}。'
        '命令：「把极限和连续标为重点，并注明连续以极限为前提」。'
    )
    data, in_tok, out_tok, ms = _run(
        adapter,
        _request(_uuidv7(0x13), "command_interpret", message),
    )
    ok = isinstance(data, dict) and data.get("action") and data.get("target")
    return {
        "task": "command_interpret",
        "parse_ok": data is not None,
        "structurally_valid": bool(ok),
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "latency_ms": round(ms, 1),
    }


def task_answer_with_sources(adapter: DeepSeekLlmAdapter, gold: Any) -> dict[str, Any]:
    message = (
        "用一句话回答「什么是极限？」，并在回答后注明来源（如「来源：微积分教材第二章」）。"
        "只输出 JSON 对象，格式：{'answer': '...', 'sources': ['...']}。"
    )
    data, in_tok, out_tok, ms = _run(
        adapter,
        _request(_uuidv7(0x14), "answer_with_sources", message),
    )
    ok = isinstance(data, dict) and bool(data.get("answer")) and bool(data.get("sources"))
    return {
        "task": "answer_with_sources",
        "parse_ok": data is not None,
        "structurally_valid": bool(ok),
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "latency_ms": round(ms, 1),
    }


def main() -> int:
    if os.environ.get("RUN_LIVE_LLM_TESTS") != "1":
        print("SKIP: set RUN_LIVE_LLM_TESTS=1 and DEEPSEEK_API_KEY to run EVAL-LLM-001")
        return 0
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        print("FAIL: DEEPSEEK_API_KEY not set")
        return 1

    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    adapter = DeepSeekLlmAdapter(
        api_key=key,
        config=DeepSeekConfig(model_id="deepseek-v4-flash", pricing=PRICING),
    )

    results = [
        task_concept_extract(adapter, gold),
        task_relation_candidate(adapter, gold),
        task_command_interpret(adapter, gold),
        task_answer_with_sources(adapter, gold),
    ]

    total_in = sum(r["input_tokens"] for r in results)
    total_out = sum(r["output_tokens"] for r in results)
    cost = (
        total_in / 1e6 * PRICING.input_usd_per_mtok
        + total_out / 1e6 * PRICING.output_usd_per_mtok
    )

    report = {
        "eval_id": "EVAL-LLM-001",
        "generated_at": datetime.now(UTC).isoformat(),
        "model": "deepseek-v4-flash",
        "dataset": gold.get("dataset_id"),
        "results": results,
        "totals": {
            "input_tokens": total_in,
            "output_tokens": total_out,
            "estimated_cost_usd": round(cost, 8),
        },
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(
        f"\nEVAL-LLM-001 done: {total_in} in / {total_out} out tokens, "
        f"~${cost:.6f} USD, report -> {REPORT_PATH}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
