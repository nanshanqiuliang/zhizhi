# ADR-0005：操作日志保存最小变更，快照只作为恢复加速

```yaml
status: proposed
date: 2026-08-14
decision_owner: workspace_owner
related_ids: [WORK-2026-011, REQ-2026-008, NFR-2026-001, ADR-0004]
supersedes: null
```

## Context

- 约束、问题、事实和未知：GraphPatch v1 已能生成无副作用候选图，但尚无回放/撤销证明。每次只保存整图快照会放大空间、难以审计具体变更；允许外部或 AI 提交 inverse 又会扩大删除权限和篡改面。
- 架构/安全/运维/数据影响：未来本地数据库需支持断点恢复、审计和撤销；当前阶段只允许无 I/O 纯领域 prototype，不能把内存证明冒充持久恢复。

## Decision Drivers

- 公开写入仍只有 GraphPatch；AI 只产生草案。
- inverse 必须由可信领域层从已验证 before/after 状态确定性生成。
- 回放与撤销必须检测乱序、篡改和 revision 冲突。
- 记录应以最小变化为主，周期快照只优化启动，不成为唯一真相。

## Considered Options

### Option A：每次保存完整图快照

- 优点：实现简单、恢复直接。
- 缺点/风险：空间随图大小线性增长；难以解释单次变化；不符合架构中“revision 不是独立业务真相”的边界。

### Option B：保存外部 forward/inverse GraphPatch

- 优点：接口看似统一。
- 缺点/风险：当前公开白名单不足以表达删除创建项；开放 inverse DTO 会让 AI/导入器获得不必要的 tombstone/restore 能力。

### Option C：可信领域层生成 entity delta，周期快照加速

- 优点：记录最小、可审计、可验证 hash/revision；公开 GraphPatch 权限不扩大；可重放/撤销。
- 缺点/风险：需要版本化 delta contract、compaction 和迁移策略；内容字段落盘后的隐私保护另需设计。

## Decision

- 选择：以 Option C 作为 prototype 方向。WORK-2026-011 先实现内存、LIFO、无 I/O 的 entity delta/replay/undo/redo；持久 operation log 和 periodic snapshot 另设工作项。
- 理由：在不扩大外部/AI 权限的情况下证明可逆语义，并为后续 SQLite 事务和恢复留下明确输入。
- 明确不解决：数据库 schema、任意历史分支、三方合并、跨进程 crash recovery、日志加密/压缩和 UI。

## Consequences

- 正面：GraphPatch 继续是唯一公共写协议；内部 inverse 可单独强化；history 冲突可失败关闭。
- 负面/技术债：prototype record 仍是 Python 内部类型；持久化前必须冻结 JSON Schema、迁移、保留/压缩和隐私策略。
- 对接口、迁移、测试、可观测性、运维的要求：属性测试覆盖 apply/undo/redo；记录绑定 hash/revision；持久化阶段必须做断电/损坏/重复 replay 故障注入。

## Rollback or Migration

- 回滚/替代触发：若 delta 无法稳定覆盖 GraphPatch 语义或性能不达标，禁用 history prototype，不回退 GraphPatch 安全门。
- 路径与成本：独立模块尚未接产品，可直接回退；未来 schema 只能通过版本化迁移替换，不原位改写历史记录。

## Evidence and Review

- Prototype/Test：WORK-2026-011 待从失败测试实现。
- 批准：`proposed`；没有 workspace-owner 正式签字。
- 复审条件/日期：WORK-2026-011 QA 和 SQLite 持久化工作项 Ready 前复审。
