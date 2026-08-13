# 工程文档地图

> 状态：draft baseline  
> 建立日期：2026-08-13

本目录用于保存知识树 Agent 的可执行工程事实。根目录三份特殊标记文件是最高层指导：

1. `!!!_【工程框架指导】知识树Agent_总体架构技术基线_v0.1.md`
2. `!!!_【开发运维总纲】知识树Agent_全生命周期开发流程_v0.1.md`
3. `!!!_【多LLM兼容基线】知识树Agent_DeepSeek优先适配与配置_v0.1.md`

## 当前事实源

| 文件 | 用途 |
|---|---|
| `ENGINEERING_PLAN.md` | 当前阶段与工作项 |
| `DEVELOPMENT_LOG.md` | 技术变化时间线 |
| `OPS_LOG.md` | 环境、发布和运行问题 |
| `BUG_REGISTER.md` | 缺陷索引 |
| `RISK_REGISTER.md` | 风险索引 |
| `TRACEABILITY_MATRIX.md` | 需求到证据的映射 |
| `ENVIRONMENT_INVENTORY.md` | 环境、组件、配置和构建身份 |
| `ERROR_CODE_CATALOG.md` | 稳定错误码、归属、重试和排障入口 |
| `CHANGELOG.md` | 用户可见版本变化 |
| `USER_MANUAL.md` | 已实现用户行为和诊断说明 |
| `../config/llm/providers.yaml` | 非敏感 Provider/协议/能力/端点配置 |
| `../config/llm/model-policies.yaml` | 任务模型路由、预算、重试和回退配置 |

## 目录

```text
docs/
├─ adr/              架构决策
├─ bugs/             详细缺陷记录
├─ changes/          变更申请与执行结果
├─ diagnostics/      诊断包 contract 和脱敏规则
├─ incidents/        已发生事故的复盘
├─ observability/    遥测目录、SLI/SLO、查询和告警
├─ releases/         发布 manifest、签字、回滚记录
├─ runbooks/         当前有效的运维和排障步骤
├─ test-reports/     不可变测试报告
├─ templates/        新记录的模板
└─ work-items/       工作项详情（无工单系统时使用）
```

## 维护规则

- 计划不等于完成；状态只能由证据更新。
- 寄存器写摘要并链接详细报告，不粘贴大段原始日志。
- 测试报告、发布 manifest 和事故复盘签字后不可原位重写。
- 原始用户资料、秘密、数据库、未脱敏日志和诊断包不得提交。
- 文档链接失效或字段不再适用时，修复文档属于对应变更的 Definition of Done。
