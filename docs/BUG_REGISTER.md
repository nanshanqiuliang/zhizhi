# 缺陷登记册

> 发现缺陷后使用 `templates/BUG_REPORT_TEMPLATE.md` 建详情，并在此登记索引。

## Open

| ID | 标题 | 严重度 | 优先级 | 状态 | 首见版本 | Owner | 目标版本 | 详情 |
|---|---|---|---|---|---|---|---|---|
| BUG-2026-001 | 空工作区（0 节点）渲染崩溃：读取 `selectedNode` 的 `tone` 时 undefined | P2 | 中 | confirmed | 2026-08-16 | web | 待立工作项 | QA `TR-20260815-008` P-008：`loadGraph` 返回空 concepts（契约合法，无 minItems）时 App 崩溃 `Cannot read properties of undefined (reading 'tone')`；在 16e72c4 隔离 worktree 复现同一崩溃，确认**非 WORK-2026-045 引入**；当前后端 `create_workspace` 恒建 1 个根节点故不触发。建议空态兜底（无节点时显示引导，不渲染选中详情）。 |

## Closed

| ID | 标题 | 根因类别 | 修复版本 | 回归报告 | 关闭日期 |
|---|---|---|---|---|---|
| — | 暂无 | — | — | — | — |

## 状态规则

`new → triaged → reproducing → confirmed → fixing → code_review → verification → ready_for_release → released → monitoring → closed`。

允许的终止状态：`duplicate`、`not_a_bug`、`cannot_reproduce`、`deferred`；必须附依据和重新开启条件。
