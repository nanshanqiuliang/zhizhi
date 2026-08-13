# 工程计划

> document_id: PLAN-ROOT  
> status: draft  
> current_stage: `阶段 -1：架构与证据准备`  
> updated_at: 2026-08-13

## 当前结论

工程尚未建仓、尚无代码、CI、测试执行或运行环境。Proposal、架构基线和开发运维流程基线已经形成，但均尚待用户/项目负责人批准。

## 当前阶段出口门

- [x] Proposal 存在；
- [x] 总体架构技术基线存在；
- [x] 开发、测试、发布和运维流程基线存在；
- [ ] 用户批准 MVP 范围和安全默认；
- [ ] 回答架构基线第 21 节待决问题；
- [ ] 确定仓库归属、公开性和许可证；
- [ ] 确定角色与负责人；
- [ ] 确定微积分金标资料及许可；
- [ ] 冻结 Anchor v1、GraphPatch v1 和核心 enum。
- [x] 首家真实 LLM Provider 决策为 DeepSeek，兼容与配置基线存在；
- [ ] 批准 DeepSeek task budget、Embedding Provider 和大陆网络验收口径；

## 工作项

| ID | 工作项 | 状态 | Owner | 依赖 | 交付物 | 验证证据 |
|---|---|---|---|---|---|---|
| WORK-2026-001 | 审阅并批准架构与开发运维基线 | 待验收 | 项目负责人 | 无 | 批准记录/修订意见 | 文档状态变更 |
| WORK-2026-002 | 回答编码前待决问题 | 未开始 | 产品+技术 | WORK-2026-001 | 决策清单 | ADR/计划更新 |
| WORK-2026-003 | 确定仓库、许可证与分支保护 | 未开始 | 项目负责人 | WORK-2026-001 | 仓库治理记录 | 本地/远端检查 |
| WORK-2026-004 | 建立微积分金标集与许可清单 | 未开始 | 产品/学科+QA | WORK-2026-002 | dataset card、标注 | 双人复核 |
| WORK-2026-005 | 冻结 Anchor/GraphPatch v1 | 未开始 | 总工程师 | WORK-2026-002 | JSON Schema、ADR | 契约测试设计 |
| WORK-2026-006 | 建仓和最小 CI/证据骨架 | 未开始 | 开发+QA+运维 | WORK-2026-003 | Git、CI、锁文件 | clean build |
| WORK-2026-007 | 冻结 canonical LLM contract、配置 schema 与 DeepSeek adapter 契约 | 规划完成/待实现 | AI+后端+QA+运维 | WORK-2026-001 | 多 LLM 基线、配置 v1、错误与 Runbook | TC-LLM-001..009 待执行 |
| WORK-2026-008 | DeepSeek 真实兼容验证与金标评测 | 未开始 | AI+QA | WORK-2026-004/006/007 | live smoke、EVAL-LLM-001、成本/延迟报告 | 受控 Key + 报告 + QA 签字 |
| WORK-2026-009 | 选择并验证 Embedding Provider | 未开始 | AI+检索+QA | WORK-2026-004/007 | embedding policy、索引版本策略 | Recall/成本/离线对照 |

## 当前受阻项

| 项目 | 原因 | 解除条件 |
|---|---|---|
| 技术尖峰实施 | 当前仅授权文档与兼容配置；范围、资料、仓库和真实 API Key 未批准 | 完成阶段 -1 出口门并取得相应实施输入 |
| DeepSeek live smoke | 无产品代码、受控 API Key、CI 隔离任务或金标资料 | WORK-2026-004/006/007 完成并配置 secret store |

## 下一门

`Gate A：建仓授权`。通过前不开始产品代码。
