# AI 自动审查文档

本目录维护个人 AI Agent App 的机器审查角色、策略、contract 和后续运行说明。

- [角色卡](ROLE_CARDS.md)：AI 学科复核、AI QA 和按需分歧裁决的职责、权限与完成条件。
- 正式产品需求：`../PRODUCT_REQUIREMENTS.md`。
- 架构决策：`../adr/ADR-0015-ai-review-harness.md`。
- 当前 prototype：`../work-items/WORK-2026-004_calculus-gold-dataset.md`。
- 产品化工作项：`../work-items/WORK-2026-010_ai-review-harness.md`。
- v2 contract：`../../evals/calculus-v1/schema/machine-review.schema.json`。
- v2 role/tool policy：`../../evals/calculus-v1/review-policy.v2.json`。
- 可重放验证：`uv run python -m scripts.validate_ai_review_harness`。

WORK-2026-004 的离线 prototype 已由 `TR-20260813-005` 固化。它生成 content-addressed subject/QA/按需裁决 artifact，绑定 30/40/50 数据、角色 run/prompt/context/tool policy、证据 ledger 和每条 replay claim 的工具 trace；提示注入、越权、漂移、伪引用、trace 篡改、未裁决分歧会失败关闭。职责隔离 QA 最终 PASS，但因无外部模型/Provider 独立性证明而标记 `correlated_review`。

真实 Provider/Web、产品状态机、持久化、UI、认证 owner 风险接受和 `RB-AIREV-001` 仍归后续 gate。当前 validator 明确拒绝 `controlled_live` 和任何 owner acceptance artifact，mock 始终为 `inconclusive`/非产品可用，因此不声明产品自动复核能力已上线。
