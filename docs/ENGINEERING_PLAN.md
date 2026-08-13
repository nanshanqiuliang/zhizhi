# 工程计划

> document_id: PLAN-ROOT  
> status: draft  
> current_stage: `阶段 -1：架构与证据准备`  
> updated_at: 2026-08-13

## 当前结论

产品方向已由用户明确为个人使用、本地优先的 AI Agent App；学科复核和 QA 将由确定性 harness 编排的职责隔离 AI 子 Agent执行，并通过受控搜索/验证工具形成机器证明。本地 Git、依赖锁、模块/CI 骨架、LLM 配置校验、最小 React 状态页和 WORK-2026-004 的 review v2 离线 mock/replay 原型已经实现；`TR-20260813-005` 固化三轮学科与两轮 QA 机器证明，最终 QA PASS。由于无外部模型/Provider 独立性证明，结论标为 `correlated_review`，且 mock 状态保持 `inconclusive`；产品化 harness、远端仓库、托管 CI、Rust/Tauri、产品代码和运行环境仍未建立。

## 当前阶段出口门

- [x] Proposal 存在；
- [x] 总体架构技术基线存在；
- [x] 开发、测试、发布和运维流程基线存在；
- [x] 用户批准个人 AI Agent App、AI 子 Agent复核/QA、机器证明与用户最终控制的产品方向；其余 MVP 细项仍待 WORK-2026-002 冻结；
- [ ] 回答架构基线第 21 节待决问题；
- [ ] 确定仓库归属、公开性和许可证；
- [x] 复核执行角色确定为 `ai_subject_reviewer`、`ai_qa_auditor` 和按需 `ai_dispute_adjudicator`；技术/发布 Owner 仍待定；
- [x] 确定微积分金标资料及许可；MIT OCW RES.18-001 第 2 章已冻结并记录 CC BY-NC-SA 4.0 边界；
- [ ] 冻结 Anchor v1、GraphPatch v1 和核心 enum。
- [x] 首家真实 LLM Provider 决策为 DeepSeek，兼容与配置基线存在；
- [ ] 批准 DeepSeek task budget、Embedding Provider 和大陆网络验收口径；

## 工作项

| ID | 工作项 | 状态 | Owner | 依赖 | 交付物 | 验证证据 |
|---|---|---|---|---|---|---|
| WORK-2026-001 | 审阅并批准架构与开发运维基线 | 待验收 | 项目负责人 | 无 | 批准记录/修订意见 | 文档状态变更 |
| WORK-2026-002 | 回答编码前待决问题 | 未开始 | 产品+技术 | WORK-2026-001 | 决策清单 | ADR/计划更新 |
| WORK-2026-003 | 确定仓库、许可证与分支保护 | 未开始 | 项目负责人 | WORK-2026-001 | 仓库治理记录 | 本地/远端检查 |
| WORK-2026-004 | 建立微积分金标集、许可清单与 AI 自动复核 v2 原型 | 已完成 | 开发 + AI 学科/QA 子 Agent | MIT OCW RES.18-001 已冻结；ADR-0015 | v1 数据包；v2 machine attestation、mock harness、安全 fixture | v1 `e918fdf`/`232d0cd` + TR-003/004；v2 `73a74da..ae834d9` + TR-005，84/84 Python、QA PASS（correlated） |
| WORK-2026-005 | 冻结 Anchor/GraphPatch v1 | 未开始 | 总工程师 | WORK-2026-002 | JSON Schema、ADR | 契约测试设计 |
| WORK-2026-006 | 建仓和最小 CI/证据骨架 | 待验收 | 开发+QA+运维 | WORK-2026-003（远端治理仍待定） | 本地 Git、CI workflow、锁文件、状态页 | `TR-20260813-002` CONDITIONAL GO；独立 QA/远端 CI 待验收 |
| WORK-2026-007 | 冻结 canonical LLM contract、配置 schema 与 DeepSeek adapter 契约 | 规划完成/待实现 | AI+后端+QA+运维 | WORK-2026-001 | 多 LLM 基线、配置 v1、错误与 Runbook | TC-LLM-001..009 待执行 |
| WORK-2026-008 | DeepSeek 真实兼容验证与金标评测 | 未开始 | AI+QA | WORK-2026-004/006/007 | live smoke、EVAL-LLM-001、成本/延迟报告 | 受控 Key + 报告 + QA 签字 |
| WORK-2026-009 | 选择并验证 Embedding Provider | 未开始 | AI+检索+QA | WORK-2026-004/007 | embedding policy、索引版本策略 | Recall/成本/离线对照 |
| WORK-2026-010 | 产品化 AI 自动审查 Harness | 未开始 | AI 平台 + AI 学科/QA 子 Agent | WORK-2026-004 v2 prototype、WORK-2026-007；live 另依赖 008 | 通用 harness、角色策略、evidence ledger、状态机、owner risk acceptance | TC-AIREV-001..010 待执行 |

## 当前受阻项

| 项目 | 原因 | 解除条件 |
|---|---|---|
| 后续技术尖峰 | WORK-2026-004 已完成；架构/产品待决项、Anchor/GraphPatch contract、预算、真实 API Key 和其余 MVP 细项仍未完成 | 先完成 WORK-2026-001/002 的 owner 决策，再按依赖推进 WORK-2026-005/007；不得直接跳到 live |
| DeepSeek live smoke | 无产品代码、受控 API Key、CI 隔离任务或金标资料 | WORK-2026-004/006/007 完成并配置 secret store |

## 下一门

`Gate A：阶段 -1 出口验收`。WORK-2026-004 已以 `TR-20260813-005` 完成离线 prototype 收口；v1 数据/门禁和 `TR-20260813-003/004` 仍是不可改写的历史证据，不被 AI 伪签。下一动作按依赖回到 WORK-2026-001/002：由 workspace owner 审阅基线并回答架构第 21 节待决问题，随后才冻结 WORK-2026-005 的 Anchor/GraphPatch v1。真实 Provider/Web Search 在 WORK-2026-007/008 的 opt-in、秘密、预算和来源策略门完成前保持关闭；owner 风险接受在 WORK-2026-010 建立认证边界前也保持拒绝。
