# 端到端追溯矩阵

> 当前处于阶段 -1。本表会随需求、实现和测试补全，不用“计划中”冒充证据。

| 源 ID | 目标/风险 | WORK/CHG | ADR/Contract | Commit/PR | Test Case/Run | Release | 运行 SLI/Runbook | 状态 |
|---|---|---|---|---|---|---|---|---|
| NFR-2026-001 | 锁定项在 AI 重建中误改为 0 | WORK-2026-005 | 待建 GraphPatch v1 | — | 待建 property/e2e | — | RB-DATA/GRAPH 待建 | planned |
| NFR-2026-002 | 数字 PDF 页级锚点 ≥98%，区域 ≥90% | WORK-2026-004/005 | calculus-gold.v1 eval fixture + historical review v1 + machine review v2；Anchor v1 待建 | `e918fdf`、`232d0cd`、`ae834d9` | TC-DATA-001..006 / TR-003/004；TC-AIREV / TR-005（50 个页级金标与 30/40/50 replay 已校验；产品区域指标未完成） | — | RB-ANCH-001 待建 | partially_verified |
| NFR-2026-003 | prerequisite 子图保持 DAG | WORK-2026-005 | GraphPatch v1 | — | TC-GRAPH 待建 | — | graph cycle metric | planned |
| NFR-2026-004 | 任务崩溃恢复不重复提交 | 待建 | Job lease contract 待建 | — | TC-JOB 待建 | — | RB-JOB-001 待建 | planned |
| NFR-2026-005 | 发布可还原、构建可验证 | WORK-2026-006 | ADR-0014 proposed；release manifest 待建 | `bd66e8b` | TR-20260813-002（本地骨架） | — | RB-REL-001 待建 | partially_verified |
| RISK-2026-004 | 遥测不得泄露敏感内容 | 待建 | telemetry catalog | — | security log test 待建 | — | RB-DIAG-001 待建 | planned |
| NFR-2026-006 | 多 LLM 不把厂商协议泄漏到领域层；首要兼容 DeepSeek | WORK-2026-006/007 | ADR-0013 / LLM compatibility v0.1 | `bd66e8b`（配置校验骨架） | TC-LLM-009 static/negative verified by TR-20260813-002；001..008 待建 | — | RB-PROV-001 draft | partially_verified |
| NFR-2026-007 | DeepSeek 失败可定位、重试有界且不重复副作用 | WORK-2026-007/008 | error/config/model-policy v1 | — | TC-LLM-005..008 待建 | — | RB-PROV-001 draft | planned |
| NFR-2026-008 | DeepSeek 进入路由前有真实质量/成本/延迟证据 | WORK-2026-004/008 | calculus-gold.v1 输入与 machine review v2 prototype 已建；capability snapshot + live eval contract 待建 | `e918fdf`、`232d0cd`、`ae834d9`（仅 eval input/offline harness） | TR-003/004 历史 CONDITIONAL GO；TR-005 offline GO；真实 EVAL-LLM-001 待建 | — | Provider SLI 待建 | partially_verified |
| REQ-2026-001 | 个人使用、本地优先 AI Agent App | WORK-2026-002/010 | PRD v0.3 `in_review`；ADR-0015/0016 `proposed` | `8ff376d`（决策基线）；本 superseding 修正候选 | 首版边界 10/10 映射、84/84 Python、Web 1/1；QA attempt 001 FAIL（批准语义/状态证据），复审待执行；实现/E2E 待建 | — | 用户手册待实现 | in_review |
| REQ-2026-006..010 | Windows 单用户、本地核心可离线；首批 MD/TXT/PDF；人工确认/锁定；粒度；备份删除 | WORK-2026-002/005 及后续产品工作项 | PRD v0.3 `in_review`；ADR-0016 `proposed` | `8ff376d`（开发默认值基线）；本 superseding 修正候选 | TC-PLAN-001..003：10/10 静态映射通过；完整门通过；QA attempt 001 FAIL，修正候选待复审；产品行为尚未实现 | — | 用户手册待实现 | in_review |
| REQ-2026-002..005 | Harness 自动搜索查证、AI 学科/QA/裁决子 Agent、机器证明与 owner 风险接受 | WORK-2026-004/010 | CHG-2026-001；ADR-0015；ROLE_CARDS v0.1；calculus machine review/policy v2 prototype | `73a74da`、`3f9b637`、`db0831b`、`ae834d9` | TC-AIREV-001..010 / TR-005：39/39 targeted、84/84 全套、学科 accept、QA PASS；live/owner 产品路径待 WORK-010 | — | AI review runbook 待建 | partially_verified |
| NFR-2026-009 | AI 审查 provenance、最小权限、隔离与同源披露 | WORK-2026-004/010 | machine review v2 / evidence ledger / role tool policy prototype | `ae834d9` | TR-005：run/prompt/context/artifact/session 隔离、同源披露、越权/注入/漂移/trace 变异通过 | — | review SLI/runbook 待建 | partially_verified |
| RISK-2026-010..012 | 同源偏差、搜索污染、harness 共同缺陷 | WORK-2026-004/010 | ADR-0015 / v2 replay source + tool policy prototype | `ae834d9` | TR-005：correlation/injection/false-citation/binding/replay 与 3 P1/3 P2 校准通过；真实搜索/跨实现仍待 | — | RB-AIREV-001 待建 | partially_verified |

## 完整性规则

- `implemented` 必须有 Commit/PR；
- `verified` 必须有 Test Run；
- `released` 必须有 Release manifest；
- 用户可见能力必须有用户手册；
- 高风险必须有 Runbook/恢复或明确不适用理由。
