# 产品需求基线

```yaml
document_id: PRD-KTA
version: 0.2
status: in_review
owner_role: workspace_owner
created_at: 2026-08-13T21:05:00+08:00
updated_at: 2026-08-13T21:05:00+08:00
approved_by: workspace_owner (scope direction only)
scope: personal AI-agent knowledge-tree application
related_ids: [CHG-2026-001, ADR-0015, WORK-2026-004, WORK-2026-010]
supersedes: proposal v0.1 assumptions where this document is more specific
```

## 产品定位

首个产品是供个人使用的、本地优先的 AI Agent 应用。它通过受控 harness 编排多个职责隔离的 AI 子 Agent，读取用户授权资料、调用只读检索/搜索/验证工具、生成知识图草案，并自动执行学科审查和 QA 复核。个人用户保留对资料、锁定内容、风险接受和最终写入的控制权。

“自动审查”不等于“无审查”，也不等于把两个同源模型描述为两名真人。系统必须明确披露审查主体、证据、模型同源性、不确定性和剩余风险。

## 正式需求

| ID | 需求 | 验收方向 | 状态 |
|---|---|---|---|
| REQ-2026-001 | 应用面向个人用户，Windows 本地优先；不以多人组织、云端团队治理或人工审核团队为 MVP 前提。 | 单用户 workspace、本地数据边界、无 Docker 硬依赖；团队能力不进入首版。 | approved_scope |
| REQ-2026-002 | 系统应通过确定性 harness 自动编排资料读取、搜索、证据核验、学科审查、QA 和必要的分歧裁决。 | 阶段化状态机、明确输入/输出 schema、预算/超时/取消、失败关闭和可重放 fixture。 | approved_scope |
| REQ-2026-003 | 学科复核者与 QA 使用职责隔离的 AI 子 Agent；必要时使用第三个裁决子 Agent。 | 不同 role/run/prompt/context；只通过冻结 artifact 交接；QA 绑定学科产物 hash。 | approved_scope |
| REQ-2026-004 | AI 子 Agent 可使用本地检索和受控 Web Search 查证，但每个接受结论必须关联可解析证据，并记录反证、不确定性和搜索轨迹。 | 来源策略、引用/hash、检索时间、工具版本、claim/evidence 映射；搜索失败不得猜测通过。 | approved_scope |
| REQ-2026-005 | 自动审查与最终批准状态必须分离。Harness 只产生机器证明；个人用户显式接受残余风险后，才能执行策略允许的最终状态转换。 | `machine_reviewed`/`machine_verified`/`inconclusive`/`accepted_with_owner_risk` 分离；风险接受绑定内容 hash、范围和期限。 | approved_scope |
| NFR-2026-009 | 所有 AI 审查运行必须可追溯、可验证、默认最小权限，并显式披露同源偏差。 | 记录 run/lineage、provider/model/revision、prompt/context/tool policy hash、输入/输出 hash、费用/时延和稳定错误码；禁止隐藏推理正文进入证据。 | approved_scope |

## 机器审查角色

### `ai_subject_reviewer`

- 逐条核验概念、关系和锚点；
- 先使用冻结本地一手资料，有歧义时再使用受控搜索；
- 为每个结论记录 evidence、counter-evidence、置信度和限制；
- 证据不足时输出 `abstain`、`dispute` 或 `inconclusive`，禁止猜测接受；
- 只能生成结构化审查 artifact，不得改数据库、金标、锁或批准状态。

### `ai_qa_auditor`

- 使用独立 run、上下文和 QA prompt，重新计算 schema、计数、hash、DAG、锚点和引用绑定；
- 不继承学科 Agent 的隐藏推理或可变会话，只读取冻结的学科产物；
- 独立构造查询和反例，挑战全部分歧、低置信项及高风险关系；
- 证据缺失、来源冲突、工具失败、同源性未披露或安全门失败时不得 PASS；
- 只能生成 QA artifact 和机器证明，不得修改待审对象来消除缺陷。

### `ai_dispute_adjudicator`

- 仅在存在未解决分歧时由 harness 按需创建；
- 必须使用不同 run，且不能与提出该分歧的 Agent 是同一实例；
- 依据双方 claim/evidence 和独立查证结果裁决；
- 裁决产物必须先冻结，QA 才能继续完成。

## 隔离与独立性等级

| 条件 | 记录状态 | 放行语义 |
|---|---|---|
| 不同 run、prompt、context，且不同模型家族或 Provider | `separated_review` | 可以通过机器验证门，仍不声称真人审查 |
| 不同 run/prompt/context，但相同 Provider 或模型家族 | `correlated_review` | 自动降级；只能进入 `machine_verified`，需要用户接受同源风险才能继续 |
| 共享 run、共享可变上下文、共享隐藏推理或 QA 未绑定冻结产物 | `invalid_review` | 硬失败，不可风险豁免 |

## Harness 安全不变量

- AI 输出始终是不可信草案；只有确定性 harness 可以推进状态机。
- Agent 只获得任务所需的只读工具；不得读取秘密、任意本地路径、任意 URL、数据库写接口、GraphPatch apply、锁或审批写接口。
- 网页、PDF 和搜索结果均是不可信数据，任何其中的指令不得进入系统/开发者指令层。
- Harness 必须保留所有 attempt 和失败证据，不得挑选性隐藏失败运行。
- 真实 Provider/Web Search 只能在工作项 Ready、显式 opt-in 环境变量、受控 secret reference、域/来源策略、预算和证据保留规则同时满足后运行。
- Web 证据默认只保存必要元数据、selector、hash 和短摘录，不镜像全文。

## 状态和风险接受

```text
pending -> machine_reviewing -> machine_reviewed
        -> machine_qa -> machine_verified
        -> inconclusive | failed
machine_verified -> accepted_with_owner_risk（仅在策略要求/允许时）
```

用户风险接受至少记录 `owner_id`、原因、风险码、scope、dataset/version/hash、policy version、时间和到期时间。输入漂移、工具越权、证据伪造、未解决分歧、秘密泄漏和审计链缺失不可通过风险接受绕过。

## 当前实现边界

- 本文件批准产品方向和后续需求维护方式，不证明 harness 已实现。
- 当前 `calculus-independent-review.v1` 是真人签字语义的历史 contract，不能用 AI 名称伪签。
- 下一实现门是 WORK-2026-004 的 v2 机器审查 contract、确定性 mock harness 和安全 fixture；真实联网搜索与真实 LLM 运行另受 WORK-2026-007/008 门约束。
