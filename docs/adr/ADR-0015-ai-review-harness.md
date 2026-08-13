# ADR-0015：以确定性 Harness 编排 AI 学科复核与 AI QA

```yaml
status: proposed
date: 2026-08-13
decision_owner: workspace_owner / technical_lead
related_ids: [CHG-2026-001, REQ-2026-002, REQ-2026-003, REQ-2026-004, REQ-2026-005, NFR-2026-009, WORK-2026-004, WORK-2026-010]
supersedes: null
```

## Context

- 个人用户应用不能把组建真人学科/QA 团队作为持续开发和产品运行的硬依赖。
- 当前 v1 review contract 只能比较 reviewer 字符串，不能证明 Agent run、模型、上下文、提示词、工具或证据链隔离。
- 多 Agent 仍可能共享模型、训练数据、搜索索引和 harness 缺陷，角色名不同不等于认识论独立。
- Web/PDF 内容可能包含提示注入；AI 输出不得拥有直接写库或批准权限。

## Decision Drivers

- 自动化、可重放、可追溯；
- 学科判断和 QA 主动证伪职责分离；
- 搜索证据可核验且不过度保存受版权保护内容；
- 同源偏差显式披露；
- Agent 无权绕过确定性 schema、权限、锁和状态机。

## Considered Options

### Option A：继续要求两名真人

- 优点：组织意义上的独立责任更清晰。
- 缺点/风险：不符合个人产品和用户明确需求，成为不可满足的持续依赖。

### Option B：两个 AI 名称写入 v1 reviewer 字段

- 优点：改动小。
- 缺点/风险：伪造 v1 语义，缺少运行、证据和隔离信息，无法审计；拒绝采用。

### Option C：v2 机器证明 + 确定性 harness

- 优点：符合个人产品，能够自动搜索查证、失败关闭、记录证据和披露同源性。
- 缺点/风险：实现成本更高，仍不能消除模型共同偏差；需要用户承担最终风险接受责任。

## Decision

- 选择：Option C。
- 理由：把概率性判断限制在结构化 artifact，把权限、状态转换和安全门放在可测试的确定性 harness 中。
- 明确不解决：不把 AI 子 Agent 宣称为真人；不保证知识结论绝对正确；不在 live gate 前启用真实搜索或 Provider；不允许 Agent 自动执行 GraphPatch 或审批写入。

## Consequences

- 新增 `ai_subject_reviewer`、`ai_qa_auditor`，按需新增 `ai_dispute_adjudicator`。
- review v2 使用 machine attestation，不复用 v1 human signoff；状态区分 `machine_verified`、`inconclusive` 和 owner risk acceptance。
- 每个 run 记录 actor/run/lineage、provider/model/revision、prompt/context/tool-policy/harness/input/output hash、工具轨迹与资源预算。
- 同模型/Provider 允许作为降级模式，但必须标 `correlated_review`，不能静默宣称强独立。
- QA 必须绑定冻结的学科产物 hash，不能读取其隐藏推理或共享可变会话。

## Rollback or Migration

- 触发：安全门可绕过、已知错误检出率不达标、证据无法复跑或成本超限。
- 路径：关闭 v2 policy；保留所有 artifact 和 v1 历史记录；回到 `inconclusive` 与用户手工处理，不回写伪批准状态。

## Evidence and Review

- Prototype/Test：WORK-2026-004 v2 prototype 与 WORK-2026-010 产品化 harness 待实现。
- 批准：产品方向已由用户确认；架构状态在 contract/安全 fixture 通过前保持 proposed。
- 复审条件/日期：v2 schema 完成、首次 mock 双 Agent replay、首次 opt-in live search 前。
