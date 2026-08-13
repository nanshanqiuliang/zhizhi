# 工程模板索引

复制模板到对应目录后再填写；不要直接修改模板文件来记录一次执行。

| 模板 | 新记录位置 | 用途 |
|---|---|---|
| `WORK_ITEM_TEMPLATE.md` | 工单系统或 `docs/work-items/` | 需求/工程工作项 |
| `CHANGE_REQUEST_TEMPLATE.md` | `docs/changes/` | 正常、高风险、紧急变更 |
| `BUG_REPORT_TEMPLATE.md` | `docs/bugs/` | Bug 复现、修复、验证 |
| `TEST_REPORT_TEMPLATE.md` | `docs/test-reports/` | 一次不可变测试执行 |
| `RELEASE_MANIFEST_TEMPLATE.md` | `docs/releases/<version>/` | 候选/正式发布 |
| `INCIDENT_POSTMORTEM_TEMPLATE.md` | `docs/incidents/` | 事故响应与复盘 |
| `RUNBOOK_TEMPLATE.md` | `docs/runbooks/` | 可执行排障/恢复程序 |
| `ADR_TEMPLATE.md` | `docs/adr/` | 长期技术决策 |
| `TELEMETRY_CATALOG_TEMPLATE.md` | `docs/observability/` | event/metric/span 字段与隐私 |
| `DIAGNOSTIC_BUNDLE_TEMPLATE.md` | `docs/diagnostics/` | 用户诊断包 contract |

所有 `[...]` 和 `<...>` 占位符必须处理；不适用写 `N/A + 理由`，不可留空制造歧义。
