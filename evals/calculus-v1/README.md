# Calculus Gold Dataset v1

本目录是阶段 0 入口所需的非商业微积分金标 fixture，不是产品内置教材，也不是完整课程镜像。

## 冻结范围

- 来源：Gilbert Strang, *Calculus*, Chapter 2: Derivatives；MIT OpenCourseWare RES.18-001；
- 主题：导数、斜率、割线/切线、极限、连续性和“可导推出连续”；
- 规模：30 concepts / 40 prerequisite relations / 50 page-level anchors；
- 资源：`source/mit-ocw-res-18-001-chapter-02-derivatives.pdf`，52 pages；
- 许可：CC BY-NC-SA 4.0，仅非商业使用。详见 `NOTICE.md` 与 `DATASET_CARD.md`。

## 文件

- `gold.json`：人工编写的金标数据；
- `schema/gold.schema.json`：eval fixture v1 contract；
- `DATASET_CARD.md`：范围、标注方法、已知限制和使用门；
- `NOTICE.md`：署名、许可、修改与商用限制；
- `REVIEW.md`：作者复核和独立学科复核状态；
- `independent-review.json`：绑定数据摘要的 30/40/50 逐条待签复核包；
- `INDEPENDENT_REVIEW_GUIDE.md`：独立学科和 QA 的分离复核步骤；
- `review-policy.v2.json`：版本化角色 prompt、context scope、工具 allowlist 和风险豁免边界；
- `schema/machine-review.schema.json`：v2 subject/QA/裁决/evidence machine attestation contract；
- `source/`：哈希固定的上游第 2 章 PDF。

## 验证

```powershell
uv run python -m scripts.validate_calculus_dataset
uv run pytest tests/contract/test_calculus_dataset.py
uv run python -m scripts.validate_calculus_review
uv run python -m scripts.validate_ai_review_harness
```

任何 hash、许可、计数、引用、DAG 或复核覆盖校验失败都会阻断后续 parser/AI eval。`--require-complete` 在独立学科和 QA 双签前应稳定失败，因此本数据集当前不能成为批准的质量基线。

## v2 需求迁移说明

用户已在 CHG-2026-001 中明确采用 AI 子 Agent自动复核。当前 `independent-review.json` 和 `--require-complete` 属于 v1 真人签字 contract，作为历史证据保留，不得把 AI 名称填入其中伪造真人签字。现有 v2 原型仅使用确定性 mock/replay SearchProvider，并按 anchor 绑定的冻结 PDF 页文本建立 replay hash；subject/QA 各 120 条 trace 与 claim、query/result hash、tool、status 和有效 role policy 绑定。无论配置为同源还是跨 Provider/模型 fixture，都强制输出 `inconclusive`、`subject_evidence_established=false`、`product_eligible=false`，并拒绝 `controlled_live` 与未认证 owner artifact。它不联网、不调用真实 LLM，也不把数据集状态提升为真人 `approved`。验证证据见 `../../docs/test-reports/TR-20260813-005_calculus-ai-review-v2.md`。
