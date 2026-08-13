# ADR-0012：人工变更和锁定优先于 AI 草案

```yaml
status: proposed
date: 2026-08-14
decision_owner: workspace_owner / technical_lead (exact confirmation pending)
related_ids: [WORK-2026-005, REQ-2026-008, NFR-2026-001]
supersedes: null
```

## Context and decision

个人笔记 App 的信任基础是人工成果不会被 AI 重建覆盖。v1 分离 `content`、`relations`、`position`、`annotations` 四个锁；命中锁的变更以 `target_locked` 失败且不产生部分 snapshot。只有 user actor 可设置/解除锁；AI 不能借 set-lock operation 自行解锁。

真正三方合并、冲突 UI、operation log 和 undo/redo 不在 WORK-2026-005 内，后续实现仍必须保持“人工变更优先”。

## Consequences and rollback

- 每个修改 operation 绑定整图 base revision 与目标 revision，创建边同时绑定两个端点 revision。
- UI 可以分别解释四类锁，不能压缩成一个总开关后丢失语义。
- 锁语义改变必须新 schema/ADR 和迁移；不得以删除锁校验作为故障回滚。
