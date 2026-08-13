# 测试报告索引

当前已有工程骨架、本地验证、微积分 eval fixture 作者验证、v1 独立复核待签门，以及 v2 离线 AI 机器复核证明；仍没有产品业务、人类 QA 签字或真实 Provider 测试：

| Report | Build | 范围 | 结论 | 关联 |
|---|---|---|---|---|
| [TR-20260813-001](TR-20260813-001_llm-config-static-validation.md) | documentation-only | LLM YAML/JSON/引用/能力/秘密/链接静态检查 | CONDITIONAL GO | WORK-2026-007 |
| [TR-20260813-002](TR-20260813-002_repository-skeleton-validation.md) | `bd66e8b` | 本地仓库、配置、安全、Python/Web 与浏览器骨架 | CONDITIONAL GO | WORK-2026-006 |
| [TR-20260813-003](TR-20260813-003_calculus-gold-dataset-validation.md) | `e918fdf` | 微积分金标 schema/语义/来源/许可、失败变异与代表页渲染 | CONDITIONAL GO | WORK-2026-004 |
| [TR-20260813-004](TR-20260813-004_calculus-independent-review-gate.md) | `232d0cd` | 微积分金标逐条复核包、内容绑定、分歧裁决与双签完成硬门 | CONDITIONAL GO | WORK-2026-004 |
| [TR-20260813-005](TR-20260813-005_calculus-ai-review-v2.md) | `ae834d9` | 离线 AI 学科/QA/裁决、证据/trace/provenance、安全变异与完整门 | GO（仅 prototype；correlated） | WORK-2026-004 |
| [TR-20260814-001](TR-20260814-001_mvp-scope-decisions.md) | `10f249b` | 个人 MVP 10/10 开发默认值、QA 修正和 WORK-2026-005 Ready 门 | GO（仅离线 contract；correlated） | WORK-2026-002/005 |
| [TR-20260814-002](TR-20260814-002_anchor-graphpatch-v1.md) | `b946855` | Anchor/GraphPatch v1、纯领域预演、无 runtime 文件 I/O、锁/DAG/evidence/revision | GO（仅 prototype；correlated） | WORK-2026-005 |
| [TR-20260814-003](TR-20260814-003_graph-replay-inverse.md) | `4fc8e60` | 最小 entity delta、顺序 replay、LIFO undo/redo、篡改/权限/无 I/O | GO（仅 prototype；correlated） | WORK-2026-011 |

正式执行时：

- 报告命名：`TR-YYYYMMDD-NNN_<slug>.md`；
- 原始证据放 `evidence/<TR-ID>/` 或受控存储；
- 失败证据不得删除；
- 签字后不得原位改写；
- 在此索引报告 ID、build、范围、结论和关联发布。
