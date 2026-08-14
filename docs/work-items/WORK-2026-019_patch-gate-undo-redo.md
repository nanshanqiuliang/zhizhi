# WORK-2026-019：受保护的持久化 GraphPatch 提交门与跨会话撤销/重做

```yaml
status: implemented
type: feature
owner: Codex (persistence + api role)
reviewers: [ai_qa_auditor, workspace_owner]
related_ids: [REQ-2026-006, REQ-2026-008, NFR-2026-001, NFR-2026-003, ADR-0005, ADR-0006, WORK-2026-005, WORK-2026-011, WORK-2026-013, WORK-2026-014, TR-20260814-002, TR-20260814-003, TR-20260814-005, TR-20260814-006]
target_stage: "阶段 1 / 自然语言第 6 步"
risk: high
created_at: 2026-08-14T16:20:00+08:00
updated_at: 2026-08-14T16:50:00+08:00
```

## 问题与结果

- 用户/工程问题：第 6 步（人工编辑安全感）要求"版本历史、撤销/重做、节点/关系/位置分别锁定、冲突预览、崩溃恢复、重复任务保护"。WORK-2026-011 已在纯内存领域证明 apply/replay/LIFO undo/redo，WORK-2026-013 已能整图 save/load 并持久化 history record，但两者尚未打通：API 仍只有整图 PUT（绕过锁定与 revision 语义、无撤销），持久化层没有"把已确认 GraphPatch 安全落盘 + 跨会话撤销/重做"的受保护提交门。第 6 步完成标志"重建知识树时锁定项误改为 0；失败或重启不会重复写入"未兑现。
- 期望结果：新增一个持久化的受保护提交门：通过 GraphPatch v1 确认门应用修改（锁定维度、revision 冲突、确认门强制），把变更记录追加到持久历史，支持跨会话 LIFO undo/redo；图与历史在同一事务原子落盘；重复 change_id 跨会话幂等拒绝；篡改历史或图/历史不一致时失败关闭。
- 成功如何被观察：对一个已落盘工作区应用两条合法 user patch 后重开进程，能从初始图+记录重放得到同一语义图；undo 恢复上一语义状态、redo 恢复下一语义状态；对已 `set_lock` 的维度应用修改 patch 被 `target_locked` 拒绝；重复 change_id 第二次提交被拒绝；中断写入不产生部分图或部分历史。

## 范围

- In scope：`packages/infrastructure` 新增 `apply_graph_patch`（重建→apply→原子提交）、`undo_graph`、`redo_graph`（重建→undo/redo→原子提交）；持久化"初始图"（`meta.course_graph_initial`）作为重放起点；`save_course_graph` 采用"整图替换 + 历史重置"语义（写入 initial、清空 history）；`apps/api` 新增 `POST .../graph/patches`、`POST .../graph/undo`、`POST .../graph/redo`、`GET .../history`；受保护提交门与撤销/重做的集成/安全测试。
- Out of scope：前端 patch 化保存与锁定/撤销 UI（后续 work item）；任意历史点跳转；三方合并；周期快照压缩；公开 delete/tombstone GraphPatch；多进程并发；数据加密；真实 AI/Provider/网络；owner 认证。
- 受影响模块/接口/数据：扩展 `packages/infrastructure/workspace.py`、`packages/infrastructure/__init__.py`、`apps/api/main.py`；复用 GraphPatch v1 与 GraphHistory 语义；不修改 canonical JSON Schema，不引入 migration（复用 schema v3 `meta`/`history_records` 表）。
- 依赖和假设：`TR-20260814-002/003/005/006` 已验证 Anchor/GraphPatch v1、纯领域 undo/redo、SQLite 持久化与 API sidecar；公开 GraphPatch 仍是唯一受保护写入请求语言；`history_records` 已存在且 `record_from_json` 已做 digest 校验；单进程本地单用户。

## 设计边界

- 持久化不变式：`meta.course_graph` = 当前图（revision_no=N）；`meta.course_graph_initial` = 初始图（revision_no=0，首次落盘时写入）；`history_records` = 按应用顺序 append 的全部 record（N 条）。重建 = `GraphHistory.replay(initial, records)` 并用语义 hash 校验重放结果与保存的当前图一致，不一致即 `history_conflict`。
- apply 走 `GraphHistory.apply_patch`（确认门 + 四维锁 + revision 冲突 + duplicate change_id 全部强制）；undo/redo 只移动栈指针，不追加/删除 record。
- 图 + record + initial 在同一 SQLite 事务内提交；任何一步失败整体回滚，不产生部分状态。
- 整图 `save_course_graph` 语义为"整图替换 + 历史重置"：写入 current、覆盖 initial=当前图、清空 history_records，避免整图快照与增量历史混用后出现不可重放的幽灵状态。
- 锁维度内容不被绕过：锁定语义完全复用 GraphPatch 的 `_ensure_unlocked`/`_apply_set_lock`，不另造第二套锁判断。

## 风险影响

- 数据/schema/migration：无新表/migration；复用 `meta`（新增 `course_graph_initial` key）与 `history_records`。旧库（无 initial、history 空）向后兼容：首次 patch 时把当前图固化为 initial。
- 安全/隐私：record 仅含变化实体 before/after JSON 与语义 hash，不落 reason/prompt/secret/来源全文；错误 details 只含 rule/change_id/revision/hash 标识。
- 并发/幂等/恢复：单进程本地；写操作单事务原子；重复 change_id 跨会话拒绝；WAL 已启用；篡改 record 由 digest 校验失败关闭。
- 性能/容量/成本：重建 = 一次 load + 逐 record replay，O(record 数)；500 节点工程初值；无模型费用。
- 可观测性/诊断：稳定错误码 `patch_invalid`/`patch_revision_conflict`/`target_locked`/`permission_denied`/`history_empty`/`history_conflict`/`record_tampered`/`workspace_corrupt`；诊断不含正文。
- 用户文档：更新 USER_MANUAL 与路线第 6 步进度；明确"受保护提交门/跨会话撤销为后端与 API 能力，前端 UI 接入属后续"，不把未接入能力宣称为用户已可见。

## 验收标准

- [ ] AC-1 (c1)：`apply_graph_patch` 对已确认 user patch 生成 record 并原子落盘（图 + record + initial 同一事务）；非 user、未确认、schema 非法、revision 冲突、重复 change_id 均被稳定拒绝且不产生部分写入。
- [ ] AC-2 (c2)：跨会话重放：apply 两条合法 patch 后重开进程，重放得到与 apply 序列相同的语义图；undo 恢复上一语义、redo 恢复下一语义，revision 单调。
- [ ] AC-3 (c3)：对已 `set_lock` 的维度应用修改 patch 被 `target_locked` 拒绝，锁定项不被覆盖（重建/保存锁定项误改为 0）。
- [ ] AC-4 (c4)：重复 change_id 跨会话第二次提交被拒绝；图/历史/initial 在同一事务，故障注入（截断/垃圾字节）失败关闭且不产生部分图或部分历史。
- [ ] AC-5 (c5)：历史或图被篡改（record digest 篡改、图与历史不一致）加载/重建失败关闭为 `record_tampered`/`history_conflict`。
- [ ] AC-6 (c6)：`GET .../history` 列出已应用记录（change_id + before/after revision），`POST .../graph/undo|redo` 空栈返回 `history_empty`，缺失 workspace 返回 404。
- [ ] 错误和恢复路径：调用方基于 code 决定刷新/禁用撤销，不自动猜测合并；损坏可检测并提示恢复备份。
- [ ] 回滚/禁用方法：回退本工作项提交即回到整图 PUT-only；不改变已验证 GraphPatch preview 与纯领域 history；红灯与 FAIL evidence 保留。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-GATE-001 | integration | apply patch → 落盘 → 重开重放 | 语义一致、revision 单调 | 待红灯/TR |
| TC-GATE-002 | integration | 跨会话 undo/redo | 恢复前/后语义、栈空 `history_empty` | 待红灯/TR |
| TC-GATE-003 | security | 锁定维度修改 / 非 user / 未确认 / revision 冲突 | `target_locked`/`permission_denied`/`patch_revision_conflict` | 待红灯/TR |
| TC-GATE-004 | integrity | 重复 change_id / record 篡改 / 图历史不一致 | 幂等拒绝 / `record_tampered` / `history_conflict` | 待红灯/TR |
| TC-GATE-005 | failure | 截断/垃圾字节/中断写入 | 稳定错误、无部分状态 | 待红灯/TR |
| TC-GATE-006 | api | patches/undo/redo/history 端点 | 正/负路径、404、错误码 | 待红灯/TR |
| TC-REPO-001 | repository | 全仓门 | validator/Ruff/mypy/pytest/Web | 待 TR |

## 交付物与关闭

- Commit/PR：分支 `feature/WORK-2026-019-patch-gate`；Ready `4f5fbd3`，红灯 `db3cb26`（apply_graph_patch ImportError），实现 `e0a5ed9`，格式修复 `49e78eb`。
- Contract/ADR/migration/prompt：无新 canonical contract/ADR/migration/prompt；复用 schema v3。
- Test Run：定向 integration/security 13/13（apply→重放、跨会话 undo/redo、锁定维度拒绝、未确认/过期 base revision、重复 change_id、篡改 record_tampered）；全仓门 `49e78eb`（repository validator、Ruff、scripts + strict package mypy、`python -m pytest` 237/237、locked pnpm install/peers/check/build）；职责隔离 QA 待执行。
- Release：无托管发布；本地 API 可演示受保护提交与撤销。
- 观察结果：持久化提交门 + 跨会话撤销/重做 prototype 已验证；前端 patch 化保存与锁定/撤销 UI 属后续。
- 未完成项的新 ID：前端 patch 化保存 + 锁定/撤销 UI（WORK-2026-020）、PUT 退役或降级为仅初始化、任意历史点跳转、三方合并。
