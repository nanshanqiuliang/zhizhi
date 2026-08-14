# 测试报告索引

当前已有工程骨架、本地验证、微积分 eval fixture 作者验证、v1 独立复核待签门、v2 离线 AI 机器复核证明，以及第 4–5 步本地持久化/API/搜索/导入/PDF 查看渲染 prototype 验证（第 6 步锁定/撤销/提交门已由 TR-20260814-011 验证）；仍没有产品业务、人类 QA 签字或真实 Provider 测试：

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

正式执行时：

- 报告命名：`TR-YYYYMMDD-NNN_<slug>.md`；
- 原始证据放 `evidence/<TR-ID>/` 或受控存储；
- 失败证据不得删除；
- 签字后不得原位改写；
- 在此索引报告 ID、build、范围、结论和关联发布。
