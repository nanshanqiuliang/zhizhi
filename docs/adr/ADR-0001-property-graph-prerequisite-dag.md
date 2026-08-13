# ADR-0001：底层使用属性图，先修关系投影保持 DAG

```yaml
status: proposed
date: 2026-08-14
decision_owner: technical_lead (confirmation pending)
related_ids: [WORK-2026-005, NFR-2026-003]
supersedes: null
```

## Context and decision

知识并不总是一棵只有一个父节点的树；同一概念可有多种关系和多个来源。v1 因此保存属性图，只对 `prerequisite_of` 活跃子图强制无自环、无重复边和无有向环。树状界面是该图的一个可编辑投影，而不是底层数据损失性限制。

本工作项的可回滚离线默认值足以实现和测试该 contract；正式 `accepted` 仍待技术负责人确认。

## Consequences and rollback

- GraphPatch validator 在每次预览中检查端点、重复边和 cycle path。
- 其他关系可形成环；UI 布局不得被写回成知识语义。
- 若未来改用 JSON-LD 或图数据库，v1 节点/边语义可映射；若决策改变，新增 superseding ADR 和 schema 版本，不原位改写 v1。
