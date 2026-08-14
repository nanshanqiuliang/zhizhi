# 工作项详情目录

若尚未使用外部工单系统，在此保存 `WORK-YYYY-NNN_<slug>.md`。使用 `docs/templates/WORK_ITEM_TEMPLATE.md`，并将状态摘要同步到 `docs/ENGINEERING_PLAN.md`。

当前 AI 自动审查产品化工作项：[WORK-2026-010](WORK-2026-010_ai-review-harness.md)。它以 WORK-2026-004 的微积分 v2 prototype 为输入，不绕过当前主工作项。

当前产品主线：WORK-2026-005/011/012/013/014/015/016/017/018 已分别由 `TR-20260814-002..010` 验证。第 4 步完成；第 5 步完成（安全导入 + PDF 页文本/锚点跳转 + PDF.js 渲染/bbox 高亮）。第 6 步人工编辑安全感（撤销/锁定/崩溃恢复）已完成：由 [WORK-2026-019](WORK-2026-019_patch-gate-undo-redo.md)（后端持久化 GraphPatch 提交门 + 跨会话撤销/重做）、WORK-2026-020（锁定维度存储保护 + WebUI 锁定/撤销接入）、WORK-2026-021（冲突预览 + 备份/恢复 + 版本历史）、WORK-2026-022（普通编辑 patch 化保存）实现并经 `TR-20260814-011..013` 验证。第 7 步安全接入真实 AI 已开始：WORK-2026-007（canonical LLM contract + mock adapter + TC-LLM-001..009 mock 契约测试）已实现（`b2e215b`）；协议适配器/DeepSeek vendor profile 与真实 live smoke 待后续（live 需 owner API Key/预算）。Demo 与 prototype 不接真实 AI，不得把未实现能力宣称为已保存/已上线。
