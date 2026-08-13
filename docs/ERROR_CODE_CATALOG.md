# 稳定错误码目录

> status: planned  
> 当前没有实现。本目录定义未来错误码的治理方式；正式错误码须与 API contract、日志、UI 和 Runbook 同步。

## 规则

- 错误码为稳定 `snake_case` 字符串；不复用、不改变既有含义；
- 用户文案可本地化，错误码不可随文案改变；
- 每个错误码声明 owner、层、重试语义、用户动作、日志事件、metric、Runbook 和测试；
- 未知异常对外映射 `internal_error`，内部保留 correlation ID 和受控 stack；
- 不把文件路径、SQL、Provider 原始秘密或用户内容编码到错误码/文案。

## 计划目录

| Code | Layer/Owner | Retryable | 用户动作 | Event/Metric | Runbook | Test | 状态 |
|---|---|---:|---|---|---|---|---|
| `validation_failed` | API/Domain | no | 修正输入 | validation.failed | — | 待建 | planned |
| `revision_conflict` | Graph | maybe | 刷新并处理冲突 | graph_patch.conflicted | RB-GRAPH 待建 | 待建 | planned |
| `target_locked` | Graph | no | 解锁或保留人工内容 | graph_patch.lock_rejected | RB-GRAPH 待建 | 待建 | planned |
| `graph_cycle_detected` | Graph | no | 修改关系 | graph_patch.cycle_rejected | RB-GRAPH 待建 | 待建 | planned |
| `evidence_required` | Graph/AI | no | 补证据或保持草案 | graph_patch.evidence_rejected | — | 待建 | planned |
| `anchor_ambiguous` | Anchor | no | 用户选择候选 | anchor.ambiguous | RB-ANCH-001 | 待建 | planned |
| `anchor_drifted` | Anchor | no | 修复锚点 | anchor.drifted | RB-ANCH-001 | 待建 | planned |
| `resource_missing` | Resource | maybe | 重新授权/定位文件 | resource.missing | RB-APP/ANCH | 待建 | planned |
| `unsupported_format` | Ingestion | no | 转换格式 | ingestion.rejected | — | 待建 | planned |
| `parse_failed` | Parser | depends | 重试/诊断 | ingestion.stage.failed | RB-JOB-001 | 待建 | planned |
| `provider_rate_limited` | Provider | yes | 稍后重试 | provider.rate_limited | RB-PROV-001 | 待建 | planned |
| `provider_schema_failed` | Provider/AI | depends | 重试或回退模型 | provider.schema_failed | RB-PROV-001 | 待建 | planned |
| `provider_capability_missing` | Router/Policy | no | 改用支持该能力的已批准模型 | provider.capability_missing | RB-PROV-001 | TC-LLM-009 | planned |
| `provider_config_invalid` | Config/Provider | no | 修复版本化配置 | provider.config_invalid | RB-PROV-001 | TC-LLM-009 | planned |
| `provider_secret_missing` | Secret/Provider | no | 配置或重新授权 API Key | provider.secret_missing | RB-PROV-001 | TC-LLM-008/009 | planned |
| `provider_auth_failed` | Provider | no | 检查、轮换或重新授权密钥 | provider.auth_failed | RB-PROV-001/RB-SEC-001 | TC-LLM-006 | planned |
| `provider_balance_exhausted` | Provider/Billing | no | 充值或人工批准替代 Provider | provider.balance_exhausted | RB-PROV-001 | TC-LLM-006 | planned |
| `provider_invalid_request` | Adapter/Provider | no | 检查 protocol、参数和 fixture | provider.invalid_request | RB-PROV-001 | TC-LLM-001/006 | planned |
| `provider_connection_failed` | Provider/Network | yes | 检查网络后重试 | provider.connection_failed | RB-PROV-001 | TC-LLM-006/007 | planned |
| `provider_timeout` | Provider/Network | depends | 稍后重试或按策略回退 | provider.timeout | RB-PROV-001 | TC-LLM-003/006/007 | planned |
| `provider_unavailable` | Provider | yes | 稍后重试或按策略回退 | provider.unavailable | RB-PROV-001 | TC-LLM-006/007 | planned |
| `provider_protocol_mismatch` | Adapter/Provider | no | 隔离 deployment 并更新适配器 | provider.protocol_mismatch | RB-PROV-001 | TC-LLM-001/003/006 | planned |
| `provider_stream_incomplete` | Adapter/Provider | depends | 从阶段 checkpoint 重跑 | provider.stream_incomplete | RB-PROV-001 | TC-LLM-003 | planned |
| `provider_continuation_lost` | Adapter/Provider | no in-place | 从安全 checkpoint 重启模型阶段 | provider.continuation_lost | RB-PROV-001 | TC-LLM-005 | planned |
| `job_lease_lost` | Job | yes by new owner | 等待安全恢复 | job.lease_lost | RB-JOB-001 | 待建 | planned |
| `job_cancelled` | Job | no | 可重新发起 | job.cancelled | RB-JOB-001 | 待建 | planned |
| `budget_exceeded` | Provider/Policy | no until approved | 调整预算/继续 | provider.budget_exceeded | RB-PROV-001 | 待建 | planned |
| `unsafe_path` | Security/Desktop | no | 重新选择授权路径 | security.path_rejected | RB-SEC 待建 | 待建 | planned |
| `permission_denied` | Security | no | 请求适当权限 | security.permission_denied | RB-SEC 待建 | 待建 | planned |
| `prompt_injection_suspected` | AI/Security | no auto retry | 审核来源 | security.prompt_injection | RB-SEC 待建 | 待建 | planned |
| `internal_error` | Boundary | depends | 复制 ID/导出诊断包 | application.internal_error | RB-DIAG-001 | 待建 | planned |

## 新错误码 Definition of Done

- [ ] contract 和前后端类型；
- [ ] 安全、脱敏且可行动的用户文案；
- [ ] 正确 HTTP/job/result 语义；
- [ ] event/span status/metric；
- [ ] 自动测试覆盖产生、传播和展示；
- [ ] 需要时有 Runbook；
- [ ] CHANGELOG/用户手册影响已判断。
