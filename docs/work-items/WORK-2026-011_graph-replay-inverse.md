# WORK-2026-011：实现纯领域修改回放与 LIFO 撤销/重做

```yaml
status: ready
type: spike
owner: Codex (graph_revision domain role)
reviewers: [graph_qa_fresh, workspace_owner]
related_ids: [REQ-2026-008, NFR-2026-001, NFR-2026-003, ADR-0004, ADR-0005, ADR-0006, ADR-0012, TR-20260814-002]
target_stage: "阶段 0 / 自然语言第 2B 步"
risk: high
created_at: 2026-08-14T01:32:00+08:00
updated_at: 2026-08-14T01:32:00+08:00
```

## 问题与结果

- 用户/工程问题：WORK-2026-005 已能安全预演 GraphPatch，但还不能证明已确认修改可以从记录重放、撤销和重做。若直接依赖整图快照或让 AI 构造删除/逆操作，会破坏审计、锁和权限边界。
- 期望结果：建立不依赖框架/数据库/文件的纯领域 history prototype；只接受已经通过 GraphPatch v1 确认门的 user patch，内部从变更前后状态生成不可由 AI 提交的最小 entity delta，支持确定性重放和 LIFO undo/redo。
- 成功如何被观察：连续应用两次合法 patch 后可从初始图和记录重建同一语义图；undo 恢复上一语义状态，redo 恢复下一语义状态；revision 单调递增；篡改、乱序、空栈和非 user apply 以稳定错误失败且不产生部分结果。

## 范围

- In scope：内存 `GraphHistory`、不可变 `GraphChangeRecord`/entity delta、apply-ready user patch 接入、记录生成、确定性 replay、LIFO undo/redo、redo 分支清空、语义 hash、revision 单调性、冲突/篡改检测、属性/安全/无 I/O 测试。
- Out of scope：SQLite/operation-log 表、周期快照、跨进程恢复、API/UI、任意历史点跳转、三方合并、公开 delete/tombstone GraphPatch、批量 history 压缩、持久化数据加密、AI/Provider/网络、真实用户内容。
- 受影响模块/接口/数据：`packages/domain` 和 `tests/unit|property|security`；不修改 GraphPatch v1 canonical schema，不引入 migration。
- 依赖和假设：`TR-20260814-002` 已验证 Anchor/GraphPatch v1 prototype；公开 GraphPatch 仍是唯一写入请求语言，history 只消费 `ready_to_apply` 结果；内部 inverse delta 是可信领域派生物，不是新的外部 DTO。

## 设计边界

- 一条 record 只保存发生变化的 concept/edge/layout 的 before/after canonical JSON，不把整图快照作为日志真相。
- record 同时绑定 patch/change ID、before/after 语义 hash 与 revision；重放/撤销前先验证当前语义状态，拒绝乱序或篡改。
- hash 排除 revision 数字但保留全部业务语义；apply/undo/redo 每次把 graph revision 加一，并把受影响实体 revision 更新到新值。
- undo/redo 只允许 LIFO。undo 后应用新 patch 必须清空 redo 栈；本 spike 不实现任意分支合并。
- 创建节点/边的撤销由内部 delta 删除对应新实体；不向 AI 或公开 GraphPatch 添加 delete 权限。

## 风险影响

- 数据/schema/migration：新增 Python 内部类型，不改 canonical JSON Schema/数据库；未来持久化 contract 必须单独版本化和迁移。
- 安全/隐私：仅 fixture；record 会包含变化字段，未来落盘前必须另设内容保护/诊断脱敏门。本 spike 不记录 reason、prompt、secret 或来源全文。
- 并发/幂等/恢复：只证明单进程 LIFO 语义；hash/revision 冲突失败关闭，不宣称跨进程恢复或幂等 apply 已完成。
- 性能/容量/成本：每次 diff/hash 为 O(V+E)，500 节点工程初值；无模型费用。
- 可观测性/诊断：稳定错误 `history_empty|history_conflict|permission_denied|validation_failed`；details 只含 rule/change/expected hash/revision 等标识，不含 label/annotation 正文。
- 用户文档：仍无用户可见功能；路线进度可更新，但 USER_MANUAL 不声明 undo 已可用。

## 验收标准

- [ ] AC-1：合法 confirmed user GraphPatch 可生成 delta record 并追加 undo stack；AI/import/system 或未确认 patch 不可进入 history。
- [ ] AC-2：从初始 graph 顺序 replay records 得到与原 apply 序列相同的业务语义；输入/record 不变且无文件/网络/数据库 I/O。
- [ ] AC-3：undo/redo 对 create/update/edge/lock/annotation/layout 六类 operation 恢复前/后语义，revision 严格递增。
- [ ] AC-4：乱序 record、篡改 delta/hash、history snapshot 漂移、重复 change ID、空栈均稳定失败，不返回部分状态。
- [ ] AC-5：undo 后应用新 patch 清空 redo；record 不包含整图快照、patch reason 或可信 actor 凭据。
- [ ] AC-6：属性测试证明 `apply → undo` 语义等于原图、`undo → redo` 语义等于 apply 后图（revision 除外）。
- [ ] 错误和恢复路径：调用方基于 code/details 刷新 history 或禁用撤销；不自动猜测/合并冲突。
- [ ] 回滚/禁用方法：回退独立 history 模块/导出即可，不改变已验证 GraphPatch preview；红灯与 FAIL evidence 保留。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-HIST-001 | unit | start/apply/record | ready user 追加不可变 delta | 待红灯/TR |
| TC-HIST-002 | unit/property | replay 两个 record | 语义相同、revision 合法、确定性 | 待红灯/TR |
| TC-HIST-003 | unit/property | 六类 operation undo/redo | 往返语义相等 | 待红灯/TR |
| TC-HIST-004 | security | non-user/unconfirmed/actor spoof | 不产生 history record | 待红灯/TR |
| TC-HIST-005 | integrity | tamper/order/duplicate/empty | 稳定错误且输入不变 | 待红灯/TR |
| TC-HIST-006 | purity | 禁用 Path/open/socket/subprocess | 仍可完成内存路径 | 待红灯/TR |

## 交付物与关闭

- Commit/PR：分支 `feature/WORK-2026-011-graph-replay-inverse`；Ready 文档后先提交失败测试，再实现最小 pure-domain 模块。
- Contract/ADR/migration/prompt：ADR-0005 proposal；不改 GraphPatch v1 schema；无 migration/prompt。
- Test Run：待红灯、完整本地门和职责隔离 QA。
- Release：无；仅阶段 0 prototype。
- 观察结果：待实现，不提前声明可撤销产品能力。
- 未完成项的新 ID：持久 SQLite operation log/periodic snapshot、API、UI history 面板、跨进程恢复和 merge 分别后续建项。
