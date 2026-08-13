# ADR-0004：GraphPatch 是知识图的唯一公共写协议

```yaml
status: proposed
date: 2026-08-14
decision_owner: technical_lead (confirmation pending)
related_ids: [WORK-2026-005, NFR-2026-001, NFR-2026-003]
supersedes: null
```

## Context and decision

前端、导入器和 AI 若直接修改存储，会绕过 revision、锁、证据和 DAG。v1 将所有持久图修改表达为版本化 GraphPatch；纯领域 preview 先校验并返回候选快照，真正事务、operation log、inverse patch 和持久化留给后续工作项。

GraphPatch v1 的最小 operation 白名单为 `create_concept`、`update_concept`、`create_edge`、`set_lock`、`upsert_annotation`、`set_layout_item`。schema 是 enum/字段的唯一事实源。

## Consequences and rollback

- 调用者不能绕过 preview/confirmation；失败不返回部分结果。
- 数据库/API/UI 必须映射该 contract，不能维护另一份写语义。
- 可通过回退未接入产品的 v1 实现禁用尖峰；语义变化必须发布新 schema/ADR。
