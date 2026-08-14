# 端到端追溯矩阵

> 当前处于阶段 -1。本表会随需求、实现和测试补全，不用“计划中”冒充证据。

| 源 ID | 目标/风险 | WORK/CHG | ADR/Contract | Commit/PR | Test Case/Run | Release | 运行 SLI/Runbook | 状态 |
|---|---|---|---|---|---|---|---|---|
| NFR-2026-001 | 锁定项在 AI 重建中误改为 0 | WORK-2026-005 | GraphPatch v1 prototype；ADR-0004/0006/0012 proposed | `44b6233` 红灯；`a25470c` 实现；`1278e79` QA 红灯；`5ff02a4` 修复；`b946855` | TC-GRAPH-004 / TR-20260814-002：四维锁、actor spoof、输入不可变、专项 50/50、QA PASS；产品 E2E 待建 | — | RB-DATA/GRAPH 待建 | prototype_verified |
| NFR-2026-002 | 数字 PDF 页级锚点 ≥98%，区域 ≥90% | WORK-2026-004/005 | calculus-gold.v1 + machine review v2；Anchor v1 implementation candidate | `e918fdf`、`232d0cd`、`ae834d9`、`a25470c`、`5ff02a4` | TC-ANCH-001 selector/bbox/quote/UUID/hash 通过；50 个页级金标已验证；QA 复审/产品 resolver 指标未完成 | — | RB-ANCH-001 待建 | partially_verified |
| NFR-2026-003 | prerequisite 子图保持 DAG | WORK-2026-005 | GraphPatch v1 prototype；ADR-0001/0004 proposed | `44b6233` 红灯；`a25470c` 实现；`5ff02a4` I/O 修复；`b946855` | TC-GRAPH-003 / TR-20260814-002：Hypothesis 前向链/反向环、自环/重复边、cycle path、500 节点初值、QA PASS；产品 E2E 待建 | — | graph cycle metric 待产品化 | prototype_verified |
| NFR-2026-004 | 任务崩溃恢复不重复提交 | 待建 | Job lease contract 待建 | — | TC-JOB 待建 | — | RB-JOB-001 待建 | planned |
| NFR-2026-005 | 发布可还原、构建可验证 | WORK-2026-006 | ADR-0014 proposed；release manifest 待建 | `bd66e8b` | TR-20260813-002（本地骨架） | — | RB-REL-001 待建 | partially_verified |
| RISK-2026-004 | 遥测不得泄露敏感内容 | 待建 | telemetry catalog | — | security log test 待建 | — | RB-DIAG-001 待建 | planned |
| NFR-2026-006 | 多 LLM 不把厂商协议泄漏到领域层；首要兼容 DeepSeek | WORK-2026-006/007 | ADR-0013 / LLM compatibility v0.1 | `bd66e8b`（配置校验骨架） | TC-LLM-009 static/negative verified by TR-20260813-002；001..008 待建 | — | RB-PROV-001 draft | partially_verified |
| NFR-2026-007 | DeepSeek 失败可定位、重试有界且不重复副作用 | WORK-2026-007/008 | error/config/model-policy v1 | — | TC-LLM-005..008 待建 | — | RB-PROV-001 draft | planned |
| NFR-2026-008 | DeepSeek 进入路由前有真实质量/成本/延迟证据 | WORK-2026-004/008 | calculus-gold.v1 输入与 machine review v2 prototype 已建；capability snapshot + live eval contract 待建 | `e918fdf`、`232d0cd`、`ae834d9`（仅 eval input/offline harness） | TR-003/004 历史 CONDITIONAL GO；TR-005 offline GO；真实 EVAL-LLM-001 待建 | — | Provider SLI 待建 | partially_verified |
| REQ-2026-001 | 个人使用、本地优先 AI Agent App | WORK-2026-002/010 | PRD v0.3 `in_review`；ADR-0015/0016 `proposed` | `8ff376d`、`10f249b` | `TR-20260814-001`：首版边界 10/10、84/84 Python、Web 1/1、QA attempt 002 PASS；owner 精确验收/实现 E2E 待建 | — | 用户手册待实现 | defaults_verified |
| REQ-2026-006..010 | Windows 单用户、本地核心可离线；首批 MD/TXT/PDF；人工确认/锁定；粒度；备份删除 | WORK-2026-002/005 及后续产品工作项 | PRD v0.3 `in_review`；ADR-0016 `proposed` | `8ff376d`、`10f249b` | `TR-20260814-001`：TC-PLAN-001..003 和完整门 PASS；产品行为尚未实现 | — | 用户手册待实现 | defaults_verified |
| REQ-2026-002..005 | Harness 自动搜索查证、AI 学科/QA/裁决子 Agent、机器证明与 owner 风险接受 | WORK-2026-004/010 | CHG-2026-001；ADR-0015；ROLE_CARDS v0.1；calculus machine review/policy v2 prototype | `73a74da`、`3f9b637`、`db0831b`、`ae834d9` | TC-AIREV-001..010 / TR-005：39/39 targeted、84/84 全套、学科 accept、QA PASS；live/owner 产品路径待 WORK-010 | — | AI review runbook 待建 | partially_verified |
| NFR-2026-009 | AI 审查 provenance、最小权限、隔离与同源披露 | WORK-2026-004/010 | machine review v2 / evidence ledger / role tool policy prototype | `ae834d9` | TR-005：run/prompt/context/artifact/session 隔离、同源披露、越权/注入/漂移/trace 变异通过 | — | review SLI/runbook 待建 | partially_verified |
| RISK-2026-010..012 | 同源偏差、搜索污染、harness 共同缺陷 | WORK-2026-004/010 | ADR-0015 / v2 replay source + tool policy prototype | `ae834d9` | TR-005：correlation/injection/false-citation/binding/replay 与 3 P1/3 P2 校准通过；真实搜索/跨实现仍待 | — | RB-AIREV-001 待建 | partially_verified |
| RISK-2026-013 | Windows 路径空格致 PDF.js worker 加载失败 | WORK-2026-018 | public worker 固定 URL 规避 `@fs` 空格 | `2601215`/`d56e7ef` | TR-20260814-010：渲染/高亮/窄视口浏览器验证通过 | — | render Runbook 待建 | prototype_verified |
| RISK-2026-014 | headless canvas 渲染受限可能误报 | WORK-2026-018 | 真实浏览器人工验收；自动化只断言 canvas 存在 | `2601215` | TR-20260814-010：CDP 验证 + 用户手册人工清单 | — | render Runbook 待建 | prototype_verified |
| REQ-2026-008 / ADR-0005 | 修改可追溯并最终可撤销 | WORK-2026-005/011 | GraphPatch v1 prototype；ADR-0005 proposed | `4fc8e60` | TR-20260814-002/003：安全 preview、minimal delta、replay、LIFO undo/redo、篡改/权限、全仓 154/154、QA PASS；持久化/UI 待建 | — | DB/history Runbook 待建 | prototype_verified |
| REQ-2026-001/006/008 | 无 AI 也能人工查看、编辑知识树并撤销 | WORK-2026-012 | session-only React/SVG Demo；不改 canonical contract | `4caa76a` 原红灯；`5aab0e3` 实现；`c8c6bf9` QA P1 红灯；`fff1ce6` 修复 | TC-WEB-001..006 / TR-20260814-004：Web 6/6、全仓 154/154、desktop/mobile browser、QA attempt 002 PASS | — | `USER_MANUAL.md`；无运行 Runbook（无部署/持久状态） | verified_demo |
| REQ-2026-006/008 / ADR-0005 | 修改可追溯、可撤销且重启后内容仍在 | WORK-2026-013 | stdlib `sqlite3` workspace adapter；复用 graph v1 契约与 GraphHistory 语义 | `1420b68` 红灯；`8e34a40` 实现 | TC-PERS-001..006 / TR-20260814-005：目标 21/21、全仓 175/175、Web 6/6、QA PASS + live 变异 8/8；浏览器自动保存/API/UI 待接入 | `docs/USER_MANUAL.md` | 本地持久化 Runbook 待建 | prototype_verified |
| REQ-2026-006/008 / ADR-0011 | 浏览器↔本地 API 保存/加载闭环、自动保存与保存状态 | WORK-2026-014 | FastAPI loopback sidecar；Web PersistApi client + snapshot↔canonical 转换 | `4fe918b` 红灯；`6c0c33c` 实现；`e0a4c72` P2-1 修复 | TC-API-001..006 / TR-20260814-006：API 8/8、全仓 183/183、Web 10/10、QA-001/002 PASS、e2e smoke PASS；Tauri 打包/认证/token/FTS5 待后续 | `docs/USER_MANUAL.md` | sidecar Runbook 待建 | prototype_verified |
| REQ-2026-006/010 | 已保存笔记/概念可被全文检索 | WORK-2026-015 | FTS5 派生索引 + MATCH/子串回退；search 端点；Web 搜索框 | `e451057` Ready；`eeba073` 实现；`d6c8e01` P2-2 修复 | TC-SEARCH-001..003 / TR-20260814-007：搜索 10/10、全仓 193/193、Web 12/12、QA PASS、e2e smoke PASS；中文分词/文件内容检索待第 5 步 | `docs/USER_MANUAL.md` | 本地搜索 Runbook 待建 | prototype_verified |
| REQ-2026-006/010 / NFR-2026-002 / ADR-0001 | 本地资料可安全导入并注册为资源 | WORK-2026-016 | schema v2 resource/resource_version；受控存储 + 类型/大小/路径守卫 + 去重 | `50b3245` 红灯；`10e104f` 实现；`eee15d0` P2 修复 | TC-IMPORT-001..005 / TR-20260814-008：import 15/15、全仓 208/208、Web 15/15、QA PASS、e2e smoke PASS；PDF 解析/查看器/Anchor 跳转待第 5 步后续 | `docs/USER_MANUAL.md` | 导入 Runbook 待建 | prototype_verified |
| REQ-2026-010 / NFR-2026-002 / ADR-0001 | PDF 可查看原文页并从节点跳回锚点位置 | WORK-2026-017 | schema v3 resource_segment/anchor；pypdf 页文本；页文本/锚点端点；漂移不误跳 | `53eb2cd` 红灯；`8c3c620` 实现；`267fb7e` P2 修复 | TC-VIEW-001..005 / TR-20260814-009：viewer 10/10、全仓 218/218、Web 18/18、QA PASS、e2e smoke PASS（金标 50 锚点）；PDF.js 渲染/bbox 高亮待后续 | `docs/USER_MANUAL.md` | viewer Runbook 待建 | prototype_verified |
| REQ-2026-010 / NFR-2026-002 / ADR-0001 | PDF 可视化渲染与锚点区域高亮 | WORK-2026-018 | pdfjs canvas + public worker；bbox 高亮层；file/anchors 端点 | `275d7c6` 红灯；`2601215` 实现；`d56e7ef` P1/P2 修复 | TC-RENDER-001..004 + 浏览器 e2e / TR-20260814-010：224/224、Web 20/20、窄视口 bbox aligned、QA FAIL→修复验证；文本层联动/多页滚动待后续 | `docs/USER_MANUAL.md` | render Runbook 待建 | prototype_verified |
| NFR-2026-001/003 / REQ-2026-006/008 / ADR-0005 | 锁定项不被覆盖、失败/重启不重复写入、跨会话撤销 | WORK-2026-019 | 持久化 initial graph + applied 栈指针；GraphPatch 确认门 + 四维锁 + 单事务原子 | `4f5fbd3` Ready；`db3cb26` 红灯；`e0a5ed9` 实现；`49e78eb` 格式 | TC-GATE-001..006：apply→重放、跨会话 undo/redo、锁定维度拒绝、重复 change_id、篡改 record_tampered；全仓 237/237、Web 20/20；职责隔离 QA 待执行 | `docs/USER_MANUAL.md` | DB/history Runbook 待建 | implemented |
| NFR-2026-001 / REQ-2026-006/008 | 锁定项在整图保存/UI 层不被覆盖、可锁定/撤销 | WORK-2026-020 | `save_course_graph` 锁定维度保护；前端四维锁保真 + patch 门锁定 + 撤销回退后端 | `618420c` 实现；`b5e2680` 格式；`c70d339` 首跑修复 | TC-LOCK-001..004 + Web App.lock 2/2；全仓 241/241、Web 22/22；CDP 浏览器端到端（锁定→409→撤销）PASS；职责隔离 QA 待执行 | `docs/USER_MANUAL.md` | DB/history Runbook 待建 | implemented |

## 完整性规则

- `implemented` 必须有 Commit/PR；
- `verified` 必须有 Test Run；
- `released` 必须有 Release manifest；
- 用户可见能力必须有用户手册；
- 高风险必须有 Runbook/恢复或明确不适用理由。
