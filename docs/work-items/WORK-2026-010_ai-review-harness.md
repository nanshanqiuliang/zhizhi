# WORK-2026-010：产品化 AI 自动审查 Harness

```yaml
status: proposed
type: feature
owner: ai_platform_engineer
reviewers: [ai_subject_reviewer, ai_qa_auditor, workspace_owner]
related_ids: [REQ-2026-001, REQ-2026-002, REQ-2026-003, REQ-2026-004, REQ-2026-005, NFR-2026-009, ADR-0015, RISK-2026-010, RISK-2026-011]
target_stage: "阶段 0：技术尖峰"
risk: high
created_at: 2026-08-13T21:05:00+08:00
updated_at: 2026-08-13T21:05:00+08:00
```

## 问题与结果

- 用户/工程问题：个人 AI Agent App 需要自动完成证据搜索、学科复核和 QA，但不能依赖真人团队，也不能让概率模型直接批准自己的输出。
- 期望结果：确定性 harness 编排职责隔离的 AI 学科、QA 和裁决子 Agent，通过不可变 artifact、工具 allowlist、证据 ledger 和状态机完成机器审查。
- 成功如何被观察：冻结 fixture 可重放；已知错误被检出；提示注入/工具越权失败关闭；同源模型被降级披露；用户能查看机器证明和残余风险。

## 范围

- In scope：review v2 通用 contract、角色/工具策略、job state machine、content-addressed artifact、mock/replay SearchProvider、evidence ledger、同源性分类、owner risk acceptance、稳定错误码和安全 fixture。
- Out of scope：任意 Agent 写库、自动 GraphPatch apply、真人身份伪装、无限 Web 浏览、未受控 live Provider、团队审批系统。
- 受影响模块/接口/数据：未来 `packages/domain` review 模型、`services/worker` harness、LLM/Search ports、诊断/证据 schema；不把 SDK 类型放入领域层。
- 依赖和假设：WORK-2026-004 v2 prototype 提供金标用例；WORK-2026-007 提供 canonical LLM/tool contract；真实联网依赖 WORK-2026-008 live gate。

## 风险影响

- 数据/schema/migration：新增 evolvable JSON v2；v1 只读保留，不原位迁移签字语义。
- 安全/隐私：只读最小权限、域/来源策略、查询最小化、网页提示注入隔离、无秘密访问。
- 并发/幂等/恢复：每个 run/attempt UUIDv7；artifact hash 幂等；崩溃重放不重复副作用。
- 性能/容量/成本：限制 Agent 数、搜索轮次、tool rounds、token、费用和总时限；缓存绑定输入与策略 hash。
- 可观测性/诊断：记录运行身份、模型/提示/工具/输入摘要、状态、错误、成本和引用；不记录隐藏推理正文。
- 用户文档：解释联网、证据、机器审查等级、风险接受与失败恢复。

## 验收标准

- [ ] AC-1：v2 contract 缺失 actor/run/model/prompt/context/tool-policy/harness/input hash 任一项均失败。
- [ ] AC-2：学科与 QA 使用不同 run/prompt/context；QA 只读取冻结学科 artifact 并绑定其 SHA-256。
- [ ] AC-3：所有 accept 具有 claim/evidence 映射；低置信、冲突或搜索失败只能 abstain/dispute/inconclusive。
- [ ] AC-4：同模型/Provider 自动标记 `correlated_review`；共享 run/context 为不可豁免失败。
- [ ] AC-5：提示注入、工具越权、输入漂移、伪引用、漏项、未解决分歧和审计缺失均失败关闭。
- [ ] AC-6：owner risk acceptance 绑定身份、风险码、范围、内容 hash、policy、时间和到期时间；硬安全不变量不可豁免。
- [ ] 错误和恢复路径：429/5xx/超时/空结果/截断/schema 错/预算耗尽返回稳定错误或 `inconclusive`，不产生机器通过状态。
- [ ] 回滚/禁用方法：关闭 v2 policy，保留所有证据与 v1 数据；回退到用户手工检查，不删除失败 attempt。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-AIREV-001 | contract | actor/provenance/input manifest | 缺失/漂移失败 | 待执行 |
| TC-AIREV-002 | contract | 双 Agent artifact 隔离 | 共享 run/context 失败 | 待执行 |
| TC-AIREV-003 | property | 覆盖/重复/引用/分歧 | 任意非法组合失败 | 待执行 |
| TC-AIREV-004 | security | PDF/Web prompt injection | 不改变指令/权限 | 待执行 |
| TC-AIREV-005 | security | 工具 allowlist/secret/write | 越权调用失败 | 待执行 |
| TC-AIREV-006 | resilience | timeout/rate/schema/budget | inconclusive、可恢复 | 待执行 |
| TC-AIREV-007 | eval | 已知错误 seed/mutation 检出 | 达到冻结阈值 | 待校准 |
| TC-AIREV-008 | privacy | 日志/evidence 脱敏 | 无 key/隐藏推理/全文 | 待执行 |
| TC-AIREV-009 | policy | owner risk acceptance | 范围/期限/hash 有效 | 待执行 |
| TC-AIREV-010 | replay | harness 崩溃重放 | 无重复副作用 | 待执行 |

## 交付物与关闭

- Commit/PR：待实现。
- Contract/ADR/migration/prompt：ADR-0015；review/subject/QA/adjudication/evidence v2；三份版本化角色 prompt。
- Test Run：待创建。
- Release：阶段 0 原型，不发布。
- 观察结果：尚无实现证据。
- 未完成项的新 ID：真实 Provider/Web 验证归 WORK-2026-008；产品 UI/GraphPatch 接入另建阶段 1/2 工作项。
