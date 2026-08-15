# 工程计划

> document_id: PLAN-ROOT  
> status: draft  
> current_stage: `阶段 -1：架构与证据准备`  
> updated_at: 2026-08-14

## 当前结论

产品方向已由用户明确为个人使用、本地优先的 AI Agent App；学科复核和 QA 将由确定性 harness 编排的职责隔离 AI 子 Agent执行，并通过受控搜索/验证工具形成机器证明。本地 Git、依赖锁、模块/CI 骨架、LLM 配置校验、最小 React 状态页和 WORK-2026-004 的 review v2 离线 mock/replay 原型已经实现；`TR-20260813-005` 固化三轮学科与两轮 QA 机器证明，最终 QA PASS。由于无外部模型/Provider 独立性证明，结论标为 `correlated_review`，且 mock 状态保持 `inconclusive`；产品化 harness、远端仓库、托管 CI、Rust/Tauri、产品代码和运行环境仍未建立。

面向用户的自然语言阶段、可见里程碑和“继续推进”报告格式见 [知识树笔记 App 自然语言开发路线](USER_FACING_DEVELOPMENT_ROADMAP.md)。第 1–4 步已完成并通过职责隔离 QA（TR-20260814-001..007）。第 5 步已由 TR-008/009/010 验证完成：安全文件导入、PDF 页文本查看/锚点跳转、PDF.js 可视化渲染与 bbox 区域高亮，全部通过职责隔离 QA（TR-010 中 QA 发现 1 P1 窄视口 bbox 错位已由 `d56e7ef` 修复并经真实浏览器验证）；第 5 步标记 100%。第 6 步人工编辑安全感已完成（100%）：WORK-2026-019 后端持久化 GraphPatch 提交门 + 跨会话撤销/重做、WORK-2026-020 锁定维度存储保护 + WebUI 锁定/撤销接入（均经 `TR-20260814-011` 验证），WORK-2026-021 冲突预览 + 备份/恢复崩溃恢复 + 版本历史面板（经 `TR-20260814-012` 验证），WORK-2026-022 普通编辑 patch 化保存（GraphPatch delete 契约 + 后端 diff，经 `TR-20260814-013` 验证）；"不依赖 AI 也能使用"的手工 Alpha 完成；个人可用 MVP 粗略完成度约 75%。第 7 步（安全接入真实 AI）已完成（100%）：WORK-2026-007 冻结 canonical LLM contract + mock + TC-LLM-001..009（`b2e215b`）；WORK-2026-008 实现 DeepSeek OpenAI Chat Completions 协议适配器 + vendor profile + 金额预算 + 受控回退 + 受控 live smoke 5/5 + 金标 EVAL-LLM-001 基线 + RB-PROV-001 演练 + 隔离审查（`042f937`/`dd49599`）；workspace owner 已批准 DeepSeek deployment `enabled: true`（config 已生效，路由已验证指向 deepseek）。第 8 步（AI 自动生成知识树草案）切片 1（纯领域草案内核 + 离线编排，`136f7fa`）、切片 2（真实 DeepSeek 概念抽取/关系候选 + live 冒烟，`1394a1e`）、切片 3（草案 API 端点 + Web 生成/预览/接受/拒绝，`dfbcc30`，WORK-2026-026）与切片 4（来源锚点落库 + 点来源跳回原文，`38df493`，WORK-2026-027）已实现并经全仓门验证；"接受后点击树节点跳原文"与精确页/bbox 定位为后续增强。

## 当前阶段出口门

- [x] Proposal 存在；
- [x] 总体架构技术基线存在；
- [x] 开发、测试、发布和运维流程基线存在；
- [x] 用户批准个人 AI Agent App、AI 子 Agent复核/QA、机器证明与用户最终控制的产品方向；个人 MVP 安全默认值已在 WORK-2026-002 / PRD v0.3 / ADR-0016 记录，可支持可回滚离线开发，精确文档内容仍待 owner 确认；
- [x] 架构基线第 21 节十项问题已有决定、延期责任或失败关闭边界；金额预算、Embedding 和发布治理不被伪造为已批准；
- [ ] 确定仓库归属、公开性和许可证；
- [x] 复核执行角色确定为 `ai_subject_reviewer`、`ai_qa_auditor` 和按需 `ai_dispute_adjudicator`；技术/发布 Owner 仍待定；
- [x] 确定微积分金标资料及许可；MIT OCW RES.18-001 第 2 章已冻结并记录 CC BY-NC-SA 4.0 边界；
- [x] 冻结 Anchor v1、GraphPatch v1 和核心 enum 的 prototype contract（`TR-20260814-002`；正式 ADR owner 接受仍待阶段出口）。
- [x] 首家真实 LLM Provider 决策为 DeepSeek，兼容与配置基线存在；
- [ ] 批准 DeepSeek task budget、Embedding Provider 和大陆网络验收口径；

## 工作项

| ID | 工作项 | 状态 | Owner | 依赖 | 交付物 | 验证证据 |
|---|---|---|---|---|---|---|
| WORK-2026-001 | 审阅并批准架构与开发运维基线 | 待验收 | 项目负责人 | 无 | 批准记录/修订意见 | 文档状态变更 |
| WORK-2026-002 | 回答编码前待决问题 | 待验收 | 产品+技术 | 用户认可自然语言路线及安全默认值；精确 owner 批准和完整架构基线仍待验收 | PRD v0.3、ADR-0016、决策清单 | `8ff376d`/`10f249b`；`TR-20260814-001`：10/10、84/84 Python、Web 1/1、QA PASS（correlated） |
| WORK-2026-003 | 确定仓库、许可证与分支保护 | 未开始 | 项目负责人 | WORK-2026-001 | 仓库治理记录 | 本地/远端检查 |
| WORK-2026-004 | 建立微积分金标集、许可清单与 AI 自动复核 v2 原型 | 已完成 | 开发 + AI 学科/QA 子 Agent | MIT OCW RES.18-001 已冻结；ADR-0015 | v1 数据包；v2 machine attestation、mock harness、安全 fixture | v1 `e918fdf`/`232d0cd` + TR-003/004；v2 `73a74da..ae834d9` + TR-005，84/84 Python、QA PASS（correlated） |
| WORK-2026-005 | 冻结 Anchor/GraphPatch v1 | 已验证 prototype（正式验收待 owner） | 总工程师 | WORK-2026-002 离线默认值 QA 已通过；正式阶段出口仍待 owner | JSON Schema、纯领域 validator、生成 TS enum/Python runtime artifact、ADR | `44b6233` 原始红灯；`a25470c` QA FAIL；`1278e79` I/O 红灯；`5ff02a4` 修复；`b946855` QA PASS；`TR-20260814-002`，专项 50/50 + 集成 4/4、全仓 136/136、Web 1/1 |
| WORK-2026-006 | 建仓和最小 CI/证据骨架 | 待验收 | 开发+QA+运维 | WORK-2026-003（远端治理仍待定） | 本地 Git、CI workflow、锁文件、状态页 | `TR-20260813-002` CONDITIONAL GO；独立 QA/远端 CI 待验收 |
| WORK-2026-007 | 冻结 canonical LLM contract、配置 schema 与 DeepSeek adapter 契约 | 已完成 | AI+后端+QA+运维 | WORK-2026-001 | 多 LLM 基线、配置 v1、错误与 Runbook | `b5747ec` 红灯；`b2e215b` 实现；TC-LLM-001..009 mock 部分 56/56、全仓 314/314、Web 32/32、validator/Ruff/mypy/构建全绿 |
| WORK-2026-008 | DeepSeek 真实兼容验证与金标评测 | 已完成（owner 已批准 `enabled: true`） | AI+QA | WORK-2026-004/006/007 | live smoke、EVAL-LLM-001、成本/延迟报告 | `d6a7444` 红灯；`d81c574` 实现；`a80f43d` live smoke；`042f937` 金额预算/回退/金标/演练；`dd49599` review 修复；TC-DS-001..005 + 金额预算/回退 33/33、live smoke 5/5（~817 token）、EVAL-LLM-001 基线（~$0.0012）、RB-PROV-001 演练、隔离 review 已修；全仓 348/348 + 5 skipped；owner 已批准 deployment `enabled: true`（`config/llm/providers.yaml`） |
| WORK-2026-009 | 选择并验证 Embedding Provider | 未开始 | AI+检索+QA | WORK-2026-004/007 | embedding policy、索引版本策略 | Recall/成本/离线对照 |
| WORK-2026-010 | 产品化 AI 自动审查 Harness | 未开始 | AI 平台 + AI 学科/QA 子 Agent | WORK-2026-004 v2 prototype、WORK-2026-007；live 另依赖 008 | 通用 harness、角色策略、evidence ledger、状态机、owner risk acceptance | TC-AIREV-001..010 待执行 |
| WORK-2026-011 | 纯领域修改回放与 LIFO 撤销/重做 | 已验证 prototype（持久化/owner 待后续） | graph_revision domain + QA | WORK-2026-005 / TR-20260814-002 | immutable entity delta、history/replay/undo/redo、ADR-0005 | `2425718` 红灯；`4fc8e60` 实现；`TR-20260814-003` QA PASS；专项 18/18、既有 graph 50/50、全仓 154/154、Web 1/1 |
| WORK-2026-012 | 示例数据知识树 Web Demo | 已验证 developer demo | Web frontend + QA | WORK-2026-005/011 prototype verified | 三栏工作台、树画布、人工编辑/拖动/layout/会话 undo | `4caa76a` 原红灯；`5aab0e3` 实现；`c8c6bf9` QA P1 红灯；`fff1ce6` 修复；`TR-20260814-004` QA PASS；Web 6/6、Python 154/154 |
| WORK-2026-013 | 本地 SQLite 持久化工作区 prototype | 已验证 prototype（UI/API 接入待后续） | local persistence + QA | WORK-2026-005/011 prototype verified；WORK-2026-012 已收口 | 数据目录、SQLite schema/migration、save/load 重启存活、备份/导出/删除、回滚、故障注入证据 | `1420b68` 红灯；`8e34a40` 实现；`TR-20260814-005` QA PASS；目标 21/21、全仓 175/175、Web 6/6 |
| WORK-2026-014 | 本地持久化 API sidecar 与 Web 自动保存接入 | 已验证 prototype（Tauri/认证/FTS5 待后续） | api + web integration + QA | WORK-2026-013 prototype verified | `apps/api` FastAPI loopback、CourseGraph GET/PUT/备份、Web 自动保存与保存状态 | `4fe918b` 红灯；`6c0c33c` 实现；`e0a4c72` P2-1 修复；`TR-20260814-006` QA-001/002 PASS；API 8/8、全仓 183/183、Web 10/10 |
| WORK-2026-015 | FTS5 基础搜索（笔记/概念全文检索） | 已验证 prototype（第 4 步完成） | search + api + web + QA | WORK-2026-013/014 prototype verified | FTS5 索引、search 端点、Web 搜索框与结果定位 | `e451057` Ready；`eeba073` 实现；`d6c8e01` P2-2 修复；`TR-20260814-007` QA PASS；搜索 10/10、全仓 193/193、Web 12/12 |
| WORK-2026-016 | 安全文件导入与资源注册（Markdown/TXT/PDF） | 已验证 prototype（PDF 解析/查看器/跳转待后续） | import + storage + QA | WORK-2026-013/014/015 已验证 | schema v2（resource/resource_version）、受控导入、去重、API/Web 导入入口 | `50b3245` 红灯；`10e104f` 实现；`eee15d0` P2 修复；`TR-20260814-008` QA PASS；import 15/15、全仓 208/208、Web 15/15 |
| WORK-2026-017 | PDF 文本解析与 Anchor 来源跳转 | 已验证 prototype（PDF.js 渲染/bbox 高亮待后续） | parser + viewer + anchor + QA | WORK-2026-016 已验证（导入）；WORK-2026-005 Anchor 契约冻结 | schema v3（resource_segment/anchor）、pypdf 页文本、页文本/锚点端点、Web 查看器与跳转 | `53eb2cd` 红灯；`8c3c620` 实现；`267fb7e` P2 修复；`TR-20260814-009` QA PASS；viewer 10/10、全仓 218/218、Web 18/18 |
| WORK-2026-018 | PDF.js 可视化渲染与 bbox 区域高亮 | 已验证 prototype（第 5 步完成） | viewer-render + QA | WORK-2026-017 已验证（页文本/锚点）；pdfjs-dist 6.2.108 | PDF.js canvas 渲染、bbox 高亮层、file/anchors 端点、渲染视图与锚点联动 | `275d7c6` 红灯；`2601215` 实现；`d56e7ef` P1/P2 修复；`TR-20260814-010` QA FAIL→修复→浏览器验证；224/224、Web 20/20 |
| WORK-2026-019 | 持久化 GraphPatch 提交门与跨会话撤销/重做 | 已验证 prototype | persistence + api + QA | WORK-2026-005/011/013/014 已验证 | `apply_graph_patch`/`undo_graph`/`redo_graph`（重建→apply/undo/redo→原子提交）、持久化 initial graph + applied 栈指针、幂等拒绝、`POST graph/patches|undo|redo` + `GET history` 端点 | `4f5fbd3` Ready；`db3cb26` 红灯；`e0a5ed9` 实现；`a6a471a` QA 修复；`TR-20260814-011` QA FAIL→修复；全仓 243/243、Web 23/23 |
| WORK-2026-020 | 锁定维度存储保护与 WebUI 锁定/撤销接入 | 已验证 prototype | persistence + api + web + QA | WORK-2026-005/019 已实现 | `save_course_graph` 锁定维度保护（锁降级/内容变化/删除/revision 回退拒绝）；前端四维锁保真往返 + `toggleLock` patch 门 + 撤销/重做回退后端 + 编辑前查锁 | `618420c` 实现；`a6a471a` QA 修复；lock-guard 6/6、Web 23/23、全仓 243/243；`TR-20260814-011` QA FAIL→修复 |
| WORK-2026-021 | 冲突预览与备份/恢复崩溃恢复 UI | 已验证 prototype | recovery + api + web + QA | WORK-2026-019/020 已验证 | `list_backups`/`restore_backup_by_name`（路径守卫 + checksum 必需）+ `GET backups`/`POST restore` 端点（含 `_recovery_layout` db 缺失恢复）；前端错误码细化提示 + 侧边栏备份/恢复 + 版本历史面板 | `fb745bd` 实现；`2cd8270`/`8562ee7`/`2cfa883` QA 修复；backup_api 6/6、Web 27/27、全仓 249/249；`TR-20260814-012` QA FAIL→修复 |
| WORK-2026-022 | 普通编辑 patch 化保存与跨会话撤销 | 已验证 prototype | patch + persistence + QA | WORK-2026-005/019 已验证 | GraphPatch v1 新增 delete_concept/delete_edge；后端 save 改为 diff 生成 patch 走提交门（普通编辑保留历史、跨会话撤销覆盖所有编辑） | `ab50aa2` 实现；`7106621` QA 修复；diff_save_undo 4/4、delete 单元 3/3、全仓 256/256、Web 27/27；`TR-20260814-013` QA FAIL→修复 |
| WORK-2026-009 | AI 从笔记/资料自动生成知识树草案（第 8 步） | 切片 1+2 已实现（纯领域内核+离线编排；LLM 概念抽取/关系候选+live 冒烟） | AI + persistence + web + QA | WORK-2026-004/005/008/016/017/018 已验证 | 文档分块、别名合并、DAG 校验、自动布局、草案→GraphPatch、来源绑定（切片 1）；`LlmConceptExtractor`/`LlmRelationProvider` 经 canonical LLM port 真实抽取 + live 冒烟（切片 2）；批量接受/拒绝/Web（切片 3，见 WORK-2026-026） | `c9f2875` 红灯；`136f7fa` 切片 1 实现；`1394a1e` 切片 2 实现；TC-AIDRAFT-001..006 20/20 + 新 18/18、全仓 386/386 + 5 skipped、Web 32/32、live 冒烟 AI-DRAFT-LIVE-SMOKE-001（~$0.004） |
| WORK-2026-026 | AI 草案 API 端点与 Web 接受/拒绝（第 8 步切片 3） | 已验证 prototype（correlated） | api + web + ai-draft + QA | WORK-2026-009 切片 1+2、WORK-2026-014/016/017/019/022 已验证 | `read_resource_text`、`POST /ai-draft`（注入式 generator，503 `ai_not_available`）、DeepSeek 组合根（env-only）、Web 生成/预览/接受/拒绝 | `fe19106` Ready；`b5a38e1` 红灯；`dfbcc30` 实现；`d47ce88` QA P1 修复；ai-draft API 5/5 + resource_text 4/4、全仓 395/395 + 5 skipped、Web 35/35、QA `TR-20260814-015` PASS、live e2e 通过 |
| WORK-2026-027 | AI 草案来源锚点落库 + 点来源跳回原文（第 8 步切片 4） | 已验证 prototype（correlated） | ai-draft + persistence + api + web + QA | WORK-2026-026、WORK-2026-005/017/019/022 已验证 | `deterministic_uuidv7`、`accept_ai_draft`（单事务 patch+锚点）、`POST /ai-draft/accept`、generator 确定性资源级锚点 + evidence、Web 跳回原文 | `b7094bc` Ready；`2fcad41` 红灯；`38df493` 实现；`3c3dfa0` QA P2 修复；accept 7/7、全仓 402/402 + 5 skipped、Web 37/37、QA `TR-20260814-016` PASS、live e2e 通过 |
| WORK-2026-028 | 带来源问答（第 9 步切片 1） | 已验证 prototype（correlated） | retrieval + api + web + QA | WORK-2026-008/015/016/017/026/027 已验证 | `build_answer_context`（FTS5 + 反向子串回退）、`POST /answer`（注入式 generator，503）、DeepSeek `answer_with_sources`、Web 提问/回答/来源跳转 | `47d6c6f` 实现；`9e06ebf` QA P2 修复；answer 7/7、全仓 409/409 + 5 skipped、Web 38/38、QA `TR-20260814-017` PASS、live e2e 通过 |
| WORK-2026-029 | 自然语言转 GraphPatch（第 9 步切片 2） | 已验证 prototype（correlated） | command + api + web + QA | WORK-2026-008/005/019/022/028 已验证 | `build_command_patch`（label→id 严格映射 + set_lock/create_edge）、`POST /interpret`（注入式 generator，503）、DeepSeek `command_interpret`、Web 指令预览/接受/拒绝 | `b4fde38` 实现；`9a255d2`+`9abd339` QA P2 修复；command 12/12、全仓 421/421 + 5 skipped、Web 41/41、QA `TR-20260814-018` PASS、live e2e 通过 |
| WORK-2026-030 | 增量重建纯领域内核（第 9 步切片 3a） | 已验证 prototype（correlated） | domain + QA | WORK-2026-009 切片 1、WORK-2026-005 已验证 | `build_incremental_patch`（label 去重 + 混合端点 + 证据/DAG，proposed patch） | `da73951` 实现；`120e349` QA P2 修复；incremental 4/4、全仓 425/425 + 5 skipped、QA `TR-20260814-019` PASS |
| WORK-2026-031 | 增量重建 LLM 接线（第 9 步切片 3b） | 已验证 prototype（correlated） | ai-draft + api + QA | WORK-2026-030、WORK-2026-009 切片 1/2、WORK-2026-026 已验证 | `build_incremental_ai_draft`（去重/跨图关系/过滤）+ generator 改增量路径 + `/ai-draft` 增量 | `d012660` 实现；`f0459f4` QA P2 测试强化；incremental LLM 5/5、全仓 430/430 + 5 skipped、QA `TR-20260814-020` PASS、live e2e 通过 |

## 当前受阻项

| 项目 | 原因 | 解除条件 |
|---|---|---|
| 无实质受阻项 | DeepSeek live smoke/金标/演练已由 WORK-2026-008 完成，owner 已批准 `enabled: true` | — |

## 下一门

`第 9 步（对话、检索和持续整理）`：切片 1（带来源问答，`47d6c6f`+`9e06ebf`，WORK-2026-028，QA PASS `TR-20260814-017`）、切片 2（自然语言转 GraphPatch，`b4fde38`+`9a255d2`+`9abd339`，WORK-2026-029，QA PASS `TR-20260814-018`）、切片 3a（增量重建纯领域内核，`da73951`+`120e349`，WORK-2026-030，QA PASS `TR-20260814-019`）与切片 3b（增量重建 LLM 接线，`d012660`+`f0459f4`，WORK-2026-031，QA PASS `TR-20260814-020`）已实现并经全仓门验证。下一动作：闭合剩余第 9 步项（AI 修改历史；向量检索受 Embedding provider 未决阻塞）或经 owner 指引进入第 10 步（桌面封装）。owner 风险接受（认证边界）在 WORK-2026-010 前保持拒绝。
