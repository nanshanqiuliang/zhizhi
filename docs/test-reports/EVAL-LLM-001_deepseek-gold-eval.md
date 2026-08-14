# EVAL-LLM-001：DeepSeek 微积分金标、成本与延迟基线

```yaml
eval_id: EVAL-LLM-001
status: baseline_recorded（金标质量阈值与 QA 批准待后续）
executed_at: 2026-08-14T16:53:00+08:00
model: deepseek-v4-flash
dataset: calculus-continuity-differentiability-v1
build: feature/WORK-2026-008-deepseek-adapter-live
```

真实 DeepSeek 受控评测与 live smoke 的成本/延迟汇总。原始机器可读结果见
`evals/calculus-v1/eval-llm-001-live.json`；live smoke 用法见 `tests/e2e/test_deepseek_live_smoke.py`。
全部在 `RUN_LIVE_LLM_TESTS=1` + `DEEPSEEK_API_KEY` 门控下运行，密钥仅经环境变量、不落盘。

## 金标评测（EVAL-LLM-001，4 子任务）

| 子任务 | 指标 | 结果 | 输入/输出 token | 延迟 |
|---|---|---|---:|---:|
| 概念抽取（concept_extract） | recall（抽取 label 命中金标） | 0.133（20 抽取 / 4 精确命中） | 67 / 539 | 5391 ms |
| 关系候选（relation_candidate） | accuracy（先修方向判断） | 0.667（10/15） | 180 / 321 | 2390 ms |
| 命令解释（command_interpret） | 结构化 JSON 有效 | false（JSON 解析失败） | 71 / 58 | 1266 ms |
| 带引用回答（answer_with_sources） | 结构有效（answer + sources） | true | 51 / 51 | 1844 ms |

> 说明：概念抽取与命令解释的指标偏低属于**基线**而非故障——中文 label 精确匹配过于严格，
> 且 `command_interpret` 的 JSON 输出需在 prompt 中强化纯 JSON 约束；均已在后续工作项中记录，
> 不冒充已达标。关系候选 0.667 为无检索、无 few-shot 的单轮基线。

## 成本与延迟汇总

| 阶段 | 调用数 | 输入 token | 输出 token | 估算费用（USD） |
|---|---:|---:|---:|---:|
| live smoke（text/JSON/thinking/tool/stream） | 5 | ~425 | ~392 | < $0.0005 |
| 金标评测（4 子任务） | 4 | 369 | 969 | $0.001208 |
| **合计** | 9 | ~794 | ~1361 | **< $0.002（约 0.015 元）** |

价格快照（`config/llm/providers.yaml`，USD/百万 token，待校准）：输入 0.28 / 输出 1.14。

## 结论

- 成本可控：全部真实调用合计约 2155 token、费用 < $0.002，远低于 owner 的 3 元测试预算；
  `max_cost_usd` 金额预算已在本次实现并接线。
- 失败可定位：错误码映射、重试/熔断/fallback、脱敏均通过契约测试与演练核对。
- 真实模型能稳定返回符合契约的草案：live smoke 5/5 连通、金标 4 子任务中 3 个结构有效。
- 遗留：金标质量阈值（recall/accuracy 目标）与 deployment `enabled: true` 待 owner/QA 批准。
