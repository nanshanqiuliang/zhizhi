# 测试报告索引

当前只有工程骨架和本地验证，没有产品业务或真实 Provider 测试：

| Report | Build | 范围 | 结论 | 关联 |
|---|---|---|---|---|
| [TR-20260813-001](TR-20260813-001_llm-config-static-validation.md) | documentation-only | LLM YAML/JSON/引用/能力/秘密/链接静态检查 | CONDITIONAL GO | WORK-2026-007 |
| [TR-20260813-002](TR-20260813-002_repository-skeleton-validation.md) | `bd66e8b` | 本地仓库、配置、安全、Python/Web 与浏览器骨架 | CONDITIONAL GO | WORK-2026-006 |

正式执行时：

- 报告命名：`TR-YYYYMMDD-NNN_<slug>.md`；
- 原始证据放 `evidence/<TR-ID>/` 或受控存储；
- 失败证据不得删除；
- 签字后不得原位改写；
- 在此索引报告 ID、build、范围、结论和关联发布。
