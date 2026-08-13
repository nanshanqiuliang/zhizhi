# 工程计划

> document_id: PLAN-ROOT  
> status: draft  
> current_stage: `阶段 -1：架构与证据准备`  
> updated_at: 2026-08-13

## 当前结论

本地 Git 仓库、依赖锁、模块/CI 骨架、LLM 配置校验与最小 React 状态页已经实现并通过本地验证；远端仓库、托管 CI、Rust/Tauri、产品代码和运行环境仍未建立。Proposal、架构基线和开发运维流程基线仍待用户/项目负责人正式批准。

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
| WORK-2026-004 | 建立微积分金标集与许可清单 | 待验收 | 产品/学科+QA | 用户已指定 MIT OCW RES.18-001；独立复核者待定 | Chapter 2 PDF、dataset card、30 概念、40 关系、50 页级锚点 | `e918fdf` + `TR-20260813-003` CONDITIONAL GO；独立学科/QA 待完成 |
| WORK-2026-005 | 冻结 Anchor/GraphPatch v1 | 未开始 | 总工程师 | WORK-2026-002 | JSON Schema、ADR | 契约测试设计 |
| WORK-2026-006 | 建仓和最小 CI/证据骨架 | 待验收 | 开发+QA+运维 | WORK-2026-003（远端治理仍待定） | 本地 Git、CI workflow、锁文件、状态页 | `TR-20260813-002` CONDITIONAL GO；独立 QA/远端 CI 待验收 |
| WORK-2026-007 | 冻结 canonical LLM contract、配置 schema 与 DeepSeek adapter 契约 | 规划完成/待实现 | AI+后端+QA+运维 | WORK-2026-001 | 多 LLM 基线、配置 v1、错误与 Runbook | TC-LLM-001..009 待执行 |
| WORK-2026-008 | DeepSeek 真实兼容验证与金标评测 | 未开始 | AI+QA | WORK-2026-004/006/007 | live smoke、EVAL-LLM-001、成本/延迟报告 | 受控 Key + 报告 + QA 签字 |
| WORK-2026-009 | 选择并验证 Embedding Provider | 未开始 | AI+检索+QA | WORK-2026-004/007 | embedding policy、索引版本策略 | Recall/成本/离线对照 |

## 当前受阻项

| 项目 | 原因 | 解除条件 |
|---|---|---|
| 技术尖峰实施 | 本地仓库骨架已建立，但范围批准、金标资料、正式核心 contract 和真实 API Key 仍未完成 | 完成阶段 -1 出口门并取得相应实施输入 |
| DeepSeek live smoke | 无产品代码、受控 API Key、CI 隔离任务或金标资料 | WORK-2026-004/006/007 完成并配置 secret store |
| WORK-2026-004 关闭 | 作者复核与自动门已通过，但高风险金标不能由作者自行批准 | 项目负责人指派独立学科复核者和 QA，逐条复核 30 概念/40 关系/50 页级锚点并记录分歧/签字 |

## 下一门

`Gate A：阶段 -1 出口验收`。WORK-2026-004 的实现提交 `e918fdf` 和作者验证 `TR-20260813-003` 已形成，资料按 CC BY-NC-SA 4.0 仅用于非商业研发并保留署名/ShareAlike；数据集仍是 `author_reviewed`，不是 `approved`。下一动作仅安排独立学科/QA 复核；该签字、远端治理、项目许可证、核心 contract 和其余待决问题未完成前，不开始第 3 步或产品代码。
