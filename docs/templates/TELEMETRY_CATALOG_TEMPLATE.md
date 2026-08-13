# 遥测字段目录

> 每个事件、span、metric 在实现前登记用途、基数、隐私和保留。未登记的敏感字段不得进入遥测。

## Event/Log

| event_name | 目的/触发 | level | 必需字段 | 禁止字段 | Sampling | Retention | Owner | Test ID |
|---|---|---|---|---|---|---|---|---|

## Span

| span_name | Parent | Start/End | Attributes | Status/Error | Content policy | Owner | Test ID |
|---|---|---|---|---|---|---|---|

## Metric

| metric | Type | Unit | Description | Allowed labels | Forbidden high-cardinality labels | Alert/SLO | Owner |
|---|---|---|---|---|---|---|---|

## 自定义字段

优先使用 OpenTelemetry semantic conventions。自定义字段使用 `knowledge_tree.*` 命名空间，记录类型、枚举、稳定性和迁移方式。

## 隐私检查

- [ ] 无密钥/token/cookie；
- [ ] 无文档/prompt 全文；
- [ ] 路径、用户和 workspace 使用脱敏或受控 ID；
- [ ] metrics label 基数有限；
- [ ] 用户可选遥测与诊断导出说明一致；
- [ ] 保留与删除策略可执行。
