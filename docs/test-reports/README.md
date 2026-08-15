# 测试报告索引

当前已有工程骨架、本地验证、微积分 eval fixture 作者验证、v1 独立复核待签门、v2 离线 AI 机器复核证明，以及第 4–6 步本地持久化/API/搜索/导入/PDF 查看渲染/锁定撤销 prototype 验证（`TR-20260814-005..013`）；第 7 步 canonical LLM contract、mock、DeepSeek adapter 与受控 live smoke 已实现并有开发验证（定向测试 + live 5/5），但 **职责隔离 QA 尚未执行，`WORK-2026-007/008` 的 TR 报告待封存**；仍没有产品业务、人类 QA 签字或真实 Provider 金标评测：

| Report | Build | 范围 | 结论 | 关联 |
|---|---|---|---|---|
| [TR-20260813-001](TR-20260813-001_llm-config-static-validation.md) | documentation-only | LLM YAML/JSON/引用/能力/秘密/链接静态检查 | CONDITIONAL GO | WORK-2026-007 |
| [TR-20260813-002](TR-20260813-002_repository-skeleton-validation.md) | `bd66e8b` | 本地仓库、配置、安全、Python/Web 与浏览器骨架 | CONDITIONAL GO | WORK-2026-006 |
| [TR-20260813-003](TR-20260813-003_calculus-gold-dataset-validation.md) | `e918fdf` | 微积分金标 schema/语义/来源/许可、失败变异与代表页渲染 | CONDITIONAL GO | WORK-2026-004 |
| [TR-20260813-004](TR-20260813-004_calculus-independent-review-gate.md) | `232d0cd` | 微积分金标逐条复核包、内容绑定、分歧裁决与双签完成硬门 | CONDITIONAL GO | WORK-2026-004 |
| [TR-20260813-005](TR-20260813-005_calculus-ai-review-v2.md) | `ae834d9` | 离线 AI 学科/QA/裁决、证据/trace/provenance、安全变异与完整门 | GO（仅 prototype；correlated） | WORK-2026-004 |
| [TR-20260814-001](TR-20260814-001_mvp-scope-decisions.md) | `10f249b` | 个人 MVP 10/10 开发默认值、QA 修正和 WORK-2026-005 Ready 门 | GO（仅离线 contract；correlated） | WORK-2026-002/005 |
| [TR-20260814-002](TR-20260814-002_anchor-graphpatch-v1.md) | `b946855` | Anchor/GraphPatch v1、纯领域预演、无 runtime 文件 I/O、锁/DAG/evidence/revision | GO（仅 prototype；correlated） | WORK-2026-005 |
| [TR-20260814-003](TR-20260814-003_graph-replay-inverse.md) | `4fc8e60` | 最小 entity delta、顺序 replay、LIFO undo/redo、篡改/权限/无 I/O | GO（仅 prototype；correlated） | WORK-2026-011 |
| [TR-20260814-004](TR-20260814-004_knowledge-tree-web-demo.md) | `fff1ce6` | 三栏"知枝"工作台、编辑/增删/拖动/排布/锁定、会话 undo、桌面/移动浏览器 | GO（developer demo；correlated） | WORK-2026-012 |
| [TR-20260814-005](TR-20260814-005_local-sqlite-workspace.md) | `8e34a40` | 本地 SQLite 持久化内核：数据目录、migration v1、save/load 重启存活、备份/导出/删除、故障注入 | GO（仅 prototype；correlated） | WORK-2026-013 |
| [TR-20260814-006](TR-20260814-006_local-persist-api.md) | `e0a4c72` | FastAPI loopback sidecar、CORS/路径守卫、CourseGraph GET/PUT、Web 自动保存与状态 | GO（仅 prototype；correlated） | WORK-2026-014 |
| [TR-20260814-007](TR-20260814-007_fts5-search.md) | `d6c8e01` | FTS5 全文搜索：label/note 索引、search 端点、中文子串回退、Web 搜索定位 | GO（仅 prototype；correlated） | WORK-2026-015 |
| [TR-20260814-008](TR-20260814-008_safe-import.md) | `eee15d0` | schema v2、MD/TXT/PDF 受控导入、类型/大小/路径守卫、去重 | GO（仅 prototype；correlated） | WORK-2026-016 |
| [TR-20260814-009](TR-20260814-009_pdf-viewer-anchor.md) | `267fb7e` | schema v3、pypdf 页文本、页文本/锚点端点、漂移不误跳、金标 50 锚点 | GO（仅 prototype；correlated） | WORK-2026-017 |
| [TR-20260814-010](TR-20260814-010_pdfjs-render.md) | `d56e7ef` | PDF.js canvas 渲染、bbox 高亮、窄视口对齐、file/anchors 端点、真实浏览器验证 | GO（仅 prototype；correlated） | WORK-2026-018 |
| [TR-20260814-011](TR-20260814-011_patch-gate-undo-redo-lock-guard.md) | `a6a471a` | 持久化 GraphPatch 提交门、跨会话 undo/redo、锁定维度存储保护、Web 锁定/撤销、QA FAIL→修复 | GO（仅 prototype；correlated） | WORK-2026-019/020 |
| [TR-20260814-012](TR-20260814-012_recovery-history-ui.md) | `2cfa883` | 冲突预览、备份/恢复崩溃恢复、版本历史面板、URL 契约、QA FAIL→修复 | GO（仅 prototype；correlated） | WORK-2026-021 |
| [TR-20260814-013](TR-20260814-013_diff-based-save.md) | `7106621` | 普通编辑 patch 化保存、GraphPatch delete 契约、跨会话撤销覆盖所有编辑、QA FAIL→修复 | GO（仅 prototype；correlated） | WORK-2026-022 |
| [TR-20260814-014](TR-20260814-014_ai-draft-llm-extraction.md) | `1394a1e` | 第 8 步切片 2：LLM 概念抽取/关系候选离线契约 + 真实 DeepSeek live 冒烟（AI-DRAFT-LIVE-SMOKE-001，~$0.004）、失败关闭/噪声丢弃/evidence 绑定、QA PASS（0 P0/P1） | GO（仅 prototype；correlated） | WORK-2026-009 |
| [TR-20260814-015](TR-20260814-015_ai-draft-api-web.md) | `d47ce88` | 第 8 步切片 3：AI 草案 API 端点 + Web 生成/预览/接受/拒绝（`read_resource_text`、`POST /ai-draft`、DeepSeek 组合根、提交门接受）、QA FAIL→修复→PASS（0 P0/P1） | GO（仅 prototype；correlated） | WORK-2026-026 |
| [TR-20260814-016](TR-20260814-016_ai-draft-source-anchor.md) | `3c3dfa0` | 第 8 步切片 4：来源锚点落库 + 点来源跳回原文（`accept_ai_draft` 单事务、确定性锚点 id、`POST /ai-draft/accept`、Web 跳回原文）、QA PASS→修复→PASS（0 P0/P1） | GO（仅 prototype；correlated） | WORK-2026-027 |
| [TR-20260814-017](TR-20260814-017_answer-with-sources.md) | `9e06ebf` | 第 9 步切片 1：带来源问答（`build_answer_context` FTS5+反向回退、`POST /answer`、DeepSeek `answer_with_sources`、Web 提问/回答/来源跳转）、QA PASS→修复→PASS（0 P0/P1） | GO（仅 prototype；correlated） | WORK-2026-028 |
| [TR-20260814-018](TR-20260814-018_nl-to-graphpatch.md) | `9abd339` | 第 9 步切片 2：自然语言转 GraphPatch（`build_command_patch` label→id 映射、`POST /interpret`、DeepSeek `command_interpret`、Web 指令预览/接受/拒绝）、QA PASS→修复→PASS（0 P0/P1） | GO（仅 prototype；correlated） | WORK-2026-029 |
| [TR-20260814-019](TR-20260814-019_incremental-rebuild-kernel.md) | `120e349` | 第 9 步切片 3a：增量重建纯领域内核（`build_incremental_patch` 去重/混合端点/证据/DAG）、QA PASS→修复→PASS（0 P0/P1） | GO（仅 prototype；correlated） | WORK-2026-030 |

> WORK-2026-007（canonical LLM contract + mock + TC-LLM-001..009）与 WORK-2026-008
> （DeepSeek adapter + 金额预算 + 受控回退 + 受控 live smoke + 金标基线 + RB-PROV-001
> 演练）已完成实现与开发验证（`b2e215b`/`d81c574`/`a80f43d`/`042f937`/`dd49599`：
> 定向 56/56 + 33/33、live 5/5、金标 EVAL-LLM-001 基线、隔离 review 已修复 blocking）；
> 职责隔离 QA 尚未封存 TR 报告（`correlated_review` 已执行，最终 owner 接受待定）。

| [EVAL-LLM-001](EVAL-LLM-001_deepseek-gold-eval.md) | `042f937` | DeepSeek 微积分金标基线（概念抽取/关系/命令解释/带引用回答）与成本/延迟汇总 | 基线记录（质量阈值与 deployment 批准待 owner） | WORK-2026-008 |

正式执行时：

- 报告命名：`TR-YYYYMMDD-NNN_<slug>.md`；
- 原始证据放 `evidence/<TR-ID>/` 或受控存储；
- 失败证据不得删除；
- 签字后不得原位改写；
- 在此索引报告 ID、build、范围、结论和关联发布。
