# 端到端追溯矩阵

> 当前处于阶段 -1。本表会随需求、实现和测试补全，不用“计划中”冒充证据。

| 源 ID | 目标/风险 | WORK/CHG | ADR/Contract | Commit/PR | Test Case/Run | Release | 运行 SLI/Runbook | 状态 |
|---|---|---|---|---|---|---|---|---|
| NFR-2026-001 | 锁定项在 AI 重建中误改为 0 | WORK-2026-005 | 待建 GraphPatch v1 | — | 待建 property/e2e | — | RB-DATA/GRAPH 待建 | planned |
| NFR-2026-002 | 数字 PDF 页级锚点 ≥98%，区域 ≥90% | WORK-2026-004/005 | Anchor v1 待建 | — | TC-ANCHOR 待建 | — | RB-ANCH-001 待建 | planned |
| NFR-2026-003 | prerequisite 子图保持 DAG | WORK-2026-005 | GraphPatch v1 | — | TC-GRAPH 待建 | — | graph cycle metric | planned |
| NFR-2026-004 | 任务崩溃恢复不重复提交 | 待建 | Job lease contract 待建 | — | TC-JOB 待建 | — | RB-JOB-001 待建 | planned |
| NFR-2026-005 | 发布可还原、构建可验证 | WORK-2026-006 | ADR-0014 proposed；release manifest 待建 | `bd66e8b` | TR-20260813-002（本地骨架） | — | RB-REL-001 待建 | partially_verified |
| RISK-2026-004 | 遥测不得泄露敏感内容 | 待建 | telemetry catalog | — | security log test 待建 | — | RB-DIAG-001 待建 | planned |
| NFR-2026-006 | 多 LLM 不把厂商协议泄漏到领域层；首要兼容 DeepSeek | WORK-2026-006/007 | ADR-0013 / LLM compatibility v0.1 | `bd66e8b`（配置校验骨架） | TC-LLM-009 static/negative verified by TR-20260813-002；001..008 待建 | — | RB-PROV-001 draft | partially_verified |
| NFR-2026-007 | DeepSeek 失败可定位、重试有界且不重复副作用 | WORK-2026-007/008 | error/config/model-policy v1 | — | TC-LLM-005..008 待建 | — | RB-PROV-001 draft | planned |
| NFR-2026-008 | DeepSeek 进入路由前有真实质量/成本/延迟证据 | WORK-2026-008 | capability snapshot + eval contract | — | EVAL-LLM-001 待建 | — | Provider SLI 待建 | planned |

## 完整性规则

- `implemented` 必须有 Commit/PR；
- `verified` 必须有 Test Run；
- `released` 必须有 Release manifest；
- 用户可见能力必须有用户手册；
- 高风险必须有 Runbook/恢复或明确不适用理由。
