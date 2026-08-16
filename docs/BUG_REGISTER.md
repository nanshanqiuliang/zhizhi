# 缺陷登记册

> 发现缺陷后使用 `templates/BUG_REPORT_TEMPLATE.md` 建详情，并在此登记索引。

## Open

| ID | 标题 | 严重度 | 优先级 | 状态 | 首见版本 | Owner | 目标版本 | 详情 |
|---|---|---|---|---|---|---|---|---|
| BUG-2026-001 | 空工作区（0 节点）渲染崩溃：读取 `selectedNode` 的 `tone` 时 undefined | P2 | 中 | ready_for_release | 2026-08-16 | web | 下一次产物重建 | QA `TR-20260815-008` P-008 首报：`loadGraph` 返回空 concepts（契约合法，无 minItems）时 App 崩溃 `Cannot read properties of undefined (reading 'tone')`；在 16e72c4 隔离 worktree 复现同一崩溃，确认**非 WORK-2026-045 引入**。修复 WORK-2026-049：复查发现共 4 条崩溃路径（空图加载 / 删除最后一个节点 `parent.id` / 撤销回空图 `restoreDrafts` / 渲染 `selectedNode.tone`），全部加运行时守卫 + 空态引导 UI；红灯 4 failed → 绿灯 4 passed（`App.empty.test.tsx`），QA `TR-20260816-001` PASS。产物重建发布后转 closed。 |

## Closed

| ID | 标题 | 根因类别 | 修复版本 | 回归报告 | 关闭日期 |
|---|---|---|---|---|---|
| — | 暂无 | — | — | — | — |

## 状态规则

`new → triaged → reproducing → confirmed → fixing → code_review → verification → ready_for_release → released → monitoring → closed`。

允许的终止状态：`duplicate`、`not_a_bug`、`cannot_reproduce`、`deferred`；必须附依据和重新开启条件。
