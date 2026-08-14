# 稳定错误码目录

> status: partially_implemented
> WORK-2026-005 已在纯领域 prototype 实现五个 Graph/Anchor 校验错误；API、日志、UI 和 Runbook 传播仍待后续工作项。

## 规则

- 错误码为稳定 `snake_case` 字符串；不复用、不改变既有含义；
- 用户文案可本地化，错误码不可随文案改变；
- 每个错误码声明 owner、层、重试语义、用户动作、日志事件、metric、Runbook 和测试；
- 未知异常对外映射 `internal_error`，内部保留 correlation ID 和受控 stack；
- 不把文件路径、SQL、Provider 原始秘密或用户内容编码到错误码/文案。

## 已验证实现（WORK-2026-013..018，第 4–5 步）

以下错误码已在 `knowledge_tree_infrastructure`/`apps.api` 实现并有集成测试；
HTTP 语义与用户文案见用户手册，证据为 `TR-20260814-005..010`。

| Code | Layer/Owner | HTTP | Retryable | 用户动作 | Test | 状态 |
|---|---|---:|---|---|---|---|
| `workspace_missing` | API/Storage | 404 | no | 创建/选择工作区或先保存 | TC-PERS/API/IMPORT/VIEW | verified |
| `workspace_corrupt` | API/Storage | 500 | no | 从备份恢复或重建 | TC-PERS-005 | verified |
| `migration_conflict` | Storage | 500 | no | 使用支持的 schema 版本 | TC-PERS-003 | verified |
| `graph_invalid` | API/Graph | 422 | no | 修正图数据 | TC-API-003 | verified |
| `search_invalid_query` | API/Search | 422 | no | 修正搜索词（长度/语法） | TC-SEARCH-002 | verified |
| `import_type_rejected` | API/Import | 422 | no | 导入白名单类型 | TC-IMPORT-003 | verified |
| `import_too_large` | API/Import | 422 | no | 缩小文件（≤25 MiB） | TC-IMPORT-003 | verified |
| `import_failed` | API/Import | 422 | no | 重试并检查存储 | TC-IMPORT-003 | verified |
| `file_not_found` | API/Storage | 404 | no | 重新导入资源 | TC-RENDER-001 | verified |
| `parse_failed` | API/Parser | 422 | maybe | 重新导入/诊断 PDF | TC-VIEW-001 | verified |
| `parse_pending` | API/Parser | 422 | no | 先解析资源 | TC-VIEW-002 | verified |
| `page_out_of_range` | API/Viewer | 422 | no | 选择有效页 | TC-VIEW-002 | verified |
| `source_changed` | API/Anchor | 422 | no | 重新导入最新资料 | TC-VIEW-004 | verified |
| `anchor_invalid` | API/Anchor | 422 | no | 修正 page/payload | TC-VIEW-003 | verified |

## 计划目录

| Code | Layer/Owner | Retryable | 用户动作 | Event/Metric | Runbook | Test | 状态 |
|---|---|---:|---|---|---|---|---|
| `validation_failed` | API/Domain | no | 修正输入 | validation.failed | — | TC-GRAPH/ANCH | prototype |
| `revision_conflict` | Graph | maybe | 刷新并处理冲突 | graph_patch.conflicted | RB-GRAPH 待建 | TC-GRAPH-005 | prototype |
| `target_locked` | Graph | no | 解锁或保留人工内容 | graph_patch.lock_rejected | RB-GRAPH 待建 | TC-GRAPH-004 | prototype |
| `graph_cycle_detected` | Graph | no | 修改关系 | graph_patch.cycle_rejected | RB-GRAPH 待建 | TC-GRAPH-003 | prototype |
| `evidence_required` | Graph/AI | no | 补证据或保持草案 | graph_patch.evidence_rejected | — | TC-GRAPH-004 | prototype |
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
| `permission_denied` | Security | no | 请求适当权限 | security.permission_denied | RB-SEC 待建 | TC-GRAPH-004 actor spoof | prototype |
| `prompt_injection_suspected` | AI/Security | no auto retry | 审核来源 | security.prompt_injection | RB-SEC 待建 | 待建 | planned |
| `review_input_drifted` | AI Review/Harness | no | 重新冻结输入并重跑 | ai_review.input_drifted | RB-AIREV-001 待建 | TC-AIREV-001 | prototype |
| `review_provenance_invalid` | AI Review/Harness | no | 检查 run/prompt/tool/input manifest | ai_review.provenance_invalid | RB-AIREV-001 待建 | TC-AIREV-001/002 | prototype |
| `review_tool_denied` | AI Review/Security | no | 检查角色工具策略 | ai_review.tool_denied | RB-AIREV-001 待建 | TC-AIREV-004/005 | prototype |
| `review_evidence_invalid` | AI Review/Evidence | depends | 补充或重新获取证据 | ai_review.evidence_invalid | RB-AIREV-001 待建 | TC-AIREV-003/007 | prototype |
| `review_inconclusive` | AI Review/Policy | yes with new run | 查看缺证据/冲突/预算原因 | ai_review.inconclusive | RB-AIREV-001 待建 | TC-AIREV-006 | prototype |
| `review_correlated_agents` | AI Review/Policy | no automatic strong pass | 使用不同模型或由 owner 接受残余风险 | ai_review.correlated | RB-AIREV-001 待建 | TC-AIREV-002/009 | prototype |
| `internal_error` | Boundary | depends | 复制 ID/导出诊断包 | application.internal_error | RB-DIAG-001 | 待建 | planned |

## 新错误码 Definition of Done

- [x] contract 和前后端类型（`workspace.py`/`main.py`/`api.ts`）；
- [x] 安全、脱敏且可行动的用户文案（用户手册"失败与恢复"）；
- [x] 正确 HTTP/job/result 语义（见"已验证实现"表）；
- [ ] event/span status/metric（遥测未建立，后续工作项）；
- [x] 自动测试覆盖产生、传播和展示（TC-PERS/API/SEARCH/IMPORT/VIEW/RENDER）；
- [x] 需要时有 Runbook（本地存储/viewer Runbook 待建，记录于 TRACEABILITY_MATRIX）；
- [x] CHANGELOG/用户手册影响已判断（CHANGELOG 保持空：无正式发布；用户手册已更新）。

> 遥测 metric 为唯一未勾选项，归后续可观测性工作项；其余项在 WORK-2026-013..018 已交付。
