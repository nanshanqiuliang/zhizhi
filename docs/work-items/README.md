# 工作项详情目录

若尚未使用外部工单系统，在此保存 `WORK-YYYY-NNN_<slug>.md`。使用 `docs/templates/WORK_ITEM_TEMPLATE.md`，并将状态摘要同步到 `docs/ENGINEERING_PLAN.md`。

当前 AI 自动审查产品化工作项：[WORK-2026-010](WORK-2026-010_ai-review-harness.md)。它以 WORK-2026-004 的微积分 v2 prototype 为输入，不绕过当前主工作项。

当前产品主线：WORK-2026-005/011/012/013 已分别由 `TR-20260814-002/003/004/005` 验证。本地 SQLite 持久化 prototype 已完成（WORK-2026-013）；当前工作项为第 4 步的 [WORK-2026-014 本地持久化 API sidecar 与 Web 自动保存接入](WORK-2026-014_local-persist-api.md)，从失败 persistence API 红灯开始实现。Demo 与 prototype 不接真实 AI，不得把内存交互或未接入浏览器的存储宣称为已保存产品能力。
