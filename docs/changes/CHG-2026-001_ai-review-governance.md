# CHG-2026-001：个人 AI Agent 与自动机器复核治理变更

```yaml
status: approved
class: high_risk
owner: workspace_owner
requested_window: 2026-08-13 onward
affected_environments: [local-dev, future-test, future-production]
related_ids: [REQ-2026-001, REQ-2026-002, REQ-2026-003, REQ-2026-004, REQ-2026-005, NFR-2026-009, ADR-0015, WORK-2026-004, WORK-2026-010]
```

## 变更内容与动机

- 当前状态：Proposal 已倾向个人本地应用，但 WORK-2026-004 的复核 contract 仍要求两名真人；没有可运行的 AI review harness。
- 要改变什么：把产品和工程 QA/复核的默认执行主体明确为职责隔离的 AI 子 Agent，由确定性 harness 编排搜索、查证、审查、QA 和分歧裁决。
- 为什么现在改变：个人项目不以组建人工 QA/学科团队为前提，自动审查本身也是核心产品能力。
- 不执行的影响：当前工作项永久依赖不存在的真人团队，且无法验证产品最关键的 Agent 编排价值。

## 影响分析

- 用户/数据/隐私/安全：个人用户获得自动复核能力；搜索可能外发查询，必须最小化、可见、可关闭，不上传未授权原文。
- 服务/模块/Provider/依赖：新增 review harness、AI role profile、SearchProvider、evidence ledger、policy engine；仍保持领域层与 LLM/搜索 SDK 解耦。
- API/schema/migration/config/flags：新增 review v2/attestation contract 和任务策略；保留 v1 历史 contract，不原位改写冻结报告。
- 资源、成本和容量：每次审查至少两个 Agent run；需要预算、超时、缓存和搜索轮次上限。
- 并发任务与旧客户端兼容：v1 只读保留；v2 使用新 schema/version，不把旧签字自动迁移成机器证明。

## 实施计划

| Step | 操作 | Owner | 预期信号 | 失败停止条件 |
|---:|---|---|---|---|
| 1 | 冻结 v2 schema、角色卡、状态和错误码 | 架构/AI QA | contract tests 可描述全部状态 | 角色/批准边界不清 |
| 2 | 实现确定性 mock harness 和 content-addressed artifact 交接 | 开发 | 双 Agent replay fixture 可重跑 | Agent 获得写权限 |
| 3 | 实现注入、来源冲突、漂移、超时和同源降级测试 | AI QA | 失败关闭且有稳定错误码 | 任一硬不变量可绕过 |
| 4 | 用 AI 学科/QA 子 Agent执行冻结微积分数据复核 | Harness | 30/40/50 覆盖和机器证明 | 证据/运行身份不完整 |
| 5 | 满足 live gate 后再启用真实 Provider 和 Web Search | AI/运维 | 受控报告、预算和脱敏证据 | 无 opt-in/secret/source policy |

## 验证

- 变更前基线：TR-20260813-003/004，v1 待真人签字。
- 冒烟测试：未来 TC-AIREV-001..012；本次仅文档/schema 设计校验。
- 数据完整性：任何待审输入、prompt、tool policy、harness 或证据摘要变化使旧 attestation 失效。
- 指标/日志/trace 查询：run/lineage、工具调用、来源、token/成本/延迟和稳定错误码；不保存隐藏思维链。
- 观察期：实现后以冻结 fixture 与 opt-in live run 分开记录。

## 回滚

- 触发条件：机器审查无法识别已知错误、安全隔离失败或成本不可控。
- 最晚安全回滚点：任何自动状态转换前。
- 数据/schema 兼容：保留 v1 和所有 v2 artifact；回滚只禁用 v2 harness，不删除失败证据。
- 回滚步骤：关闭 review policy/deployment，回到 `inconclusive`/用户手工检查模式。
- 回滚后验证：数据 hash、锁、revision 和审计记录不变。

## 审批与结果

- 产品：用户已明确批准个人 AI Agent + harness 自动复核方向。
- 技术：ADR-0015 proposed，待 v2 contract/原型证据。
- QA：AI QA 子 Agent完成只读设计审查；实现验证待 WORK-2026-004/010。
- 运维：真实 Provider/Web 未启用。
- 安全/隐私：最小权限、失败关闭、来源/提示注入隔离为硬门。
- 最终决定：approved
- 实际开始/结束：2026-08-13 / 进行中
- 结果和证据：需求与治理基线已更新；产品实现尚未完成。
