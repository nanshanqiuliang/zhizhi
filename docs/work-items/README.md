# 工作项详情目录

若尚未使用外部工单系统，在此保存 `WORK-YYYY-NNN_<slug>.md`。使用 `docs/templates/WORK_ITEM_TEMPLATE.md`，并将状态摘要同步到 `docs/ENGINEERING_PLAN.md`。

当前 AI 自动审查产品化工作项：[WORK-2026-010](WORK-2026-010_ai-review-harness.md)。它以 WORK-2026-004 的微积分 v2 prototype 为输入，不绕过当前主工作项。

当前产品主线：WORK-2026-005/011/012/013/014/015/016/017/018 已分别由 `TR-20260814-002..010` 验证。第 4 步完成；第 5 步完成（安全导入 + PDF 页文本/锚点跳转 + PDF.js 渲染/bbox 高亮）。第 6 步人工编辑安全感（撤销/锁定/崩溃恢复）已完成：由 [WORK-2026-019](WORK-2026-019_patch-gate-undo-redo.md)（后端持久化 GraphPatch 提交门 + 跨会话撤销/重做）、WORK-2026-020（锁定维度存储保护 + WebUI 锁定/撤销接入）、WORK-2026-021（冲突预览 + 备份/恢复 + 版本历史）、WORK-2026-022（普通编辑 patch 化保存）实现并经 `TR-20260814-011..013` 验证。第 7 步安全接入真实 AI 已完成：WORK-2026-007（canonical LLM contract + mock + TC-LLM-001..009，`b2e215b`）；WORK-2026-008（DeepSeek adapter + 金额预算 + 受控回退 + live smoke 5/5 + 金标 EVAL-LLM-001 基线 + RB-PROV-001 演练 + 隔离审查，`042f937`/`dd49599`）；DeepSeek deployment 经 owner 批准 `enabled: true`（`33874e5`）。第 8 步（[WORK-2026-009](WORK-2026-009_ai-draft-pipeline.md)）切片 1 已实现：纯领域草案内核（分块/别名合并/DAG 校验/自动布局/草案→GraphPatch）+ 离线编排，`c9f2875` 红灯 → `136f7fa` 实现，TC-AIDRAFT-001..006 20/20、全仓 368/368 + 5 skipped；切片 2（真实 DeepSeek 抽取）与切片 3（草案 API/Web）待做。
