# RB-PROV-001：LLM Provider / DeepSeek 故障定位、降级与恢复

```yaml
status: draft
owner_role: AI后端+运维
risk: high
last_tested_at: null
test_report: null
review_due_at: 2026-09-13
related: [WORK-2026-007, WORK-2026-008, NFR-2026-006, NFR-2026-007]
```

## 目的与触发

- 症状/告警：AI 无输出、格式错误、长时间等待、401/402/429/5xx、断流、工具循环、fallback 异常；
- 错误码：全部 `provider_*`、`budget_exceeded`；
- 适用：DeepSeek 优先，也适用于后续 OpenAI/Kimi/Anthropic deployment；
- 当前限制：系统尚未实现，本 Runbook 未演练，不能视为已具备生产恢复能力。

## 前置、权限和禁止动作

- 保全 `correlation_id`、`job_id`、`stage_run_id`、`model_run_id`、时间窗、build、config/policy fingerprint；
- 只检查 secret 的 `present/rotated/revoked` 状态，不回显、不复制 API Key；
- 禁止在聊天、工单、日志或截图粘贴 Authorization、完整 prompt/response、用户原文和 `reasoning_content`；
- 禁止先无限重试、清空任务表、切 Beta endpoint 或直接修改生产 base URL；
- 若涉及外部副作用工具，先停该 task profile 的自动调用，避免重放。

## 快速判断

```text
config/capability preflight 失败 -> 禁用 deployment，修复版本化配置
401/403 -> 停止重试，验证 secret reference，必要时轮换
402 -> 停止重试，通知预算/账户 Owner；不得静默切换产生费用
429 -> 尊重响应头 + 有界抖动退避；持续发生则打开熔断/按批准策略回退
500/503/connect/timeout -> 检查范围和 Provider 状态；有界重试后熔断/回退
400/422 -> 比对脱敏 wire fixture、thinking 参数和 reasoning replay；不盲目回退
空 JSON/截断/schema 错 -> 检查 finish_reason/max_tokens/prompt/schema；不落草案
tool thinking 轮次 400 -> 检查 reasoning_content 是否在工具轮次中完整回传
stream 卡住 -> 区分 keep-alive 与 token；检查 idle/total timeout 和取消传播
fallback 后工具重复 -> 立即关闭该 policy fallback，按事故/高优先 Bug 处理
```

## 定位步骤

| Step | Action | Expected signal | Failure/Stop condition | Evidence to save |
|---:|---|---|---|---|
| 1 | 判断是否数据、安全或副作用风险 | 明确影响范围 | 可能重复写/泄密时立即停 AI | 影响、时间线、kill switch 状态 |
| 2 | 核对 build、环境、provider/policy config fingerprint | 与 release manifest 一致 | 漂移则停止诊断性重试 | manifest、fingerprint diff |
| 3 | 查看 model router 选择 | task、deployment、capability 满足 | 不满足即配置/路由根因 | task、alias、capability hash |
| 4 | 核对 secret 状态和 endpoint host | secret present、host allowlist 命中 | 禁止输出 secret 值 | 状态、轮换时间、host |
| 5 | 沿 trace 找首个失败 span | `provider.generate` 子边界明确 | 无 trace 则登记 observability gap | span、safe error、attempt |
| 6 | 按 HTTP/网络/stream/schema 分类 | 映射到稳定错误码 | 未知 wire 语义则隔离 deployment | status、允许头、大小/hash |
| 7 | DeepSeek 专查 thinking/tool replay | tool round 保留 opaque state | state 丢失则从 checkpoint 重启 | tool_call_id、存在性/hash |
| 8 | 用同版本脱敏 fixture 离线复现 | 稳定复现 mapper/parser | 仅 live 复现则标 Provider drift | fixture/version/test run |
| 9 | 检查 retry/fallback/budget | 次数有界、原因获批、fresh run | 副作用/partial 重用立即停 | attempt graph、budget |
| 10 | 写失败测试并修复 | TC-LLM 对应 case 先红后绿 | 不允许只延长超时/吞异常 | commit、test report |

## 错误处置

| 错误 | 快速缓解 | 永久恢复 | 允许回退 |
|---|---|---|---:|
| `provider_config_invalid` / `provider_capability_missing` | 隔离 deployment，保留手工功能 | 修复 schema/profile 并评审 | 否 |
| `provider_secret_missing` / `provider_auth_failed` | 关闭真实调用 | 配置/轮换/重新授权并 smoke | 否 |
| `provider_balance_exhausted` | 暂停对应 policy | 预算 Owner 处理并批准 | 仅人工批准 |
| `provider_rate_limited` | 退避、降并发、熔断 | 调整容量和 policy | 只按 policy |
| `provider_unavailable` / `provider_connection_failed` | 有界重试 | Provider/网络恢复后 half-open | 只按 policy |
| `provider_invalid_request` / `provider_protocol_mismatch` | 隔离 deployment | 更新 adapter/fixture/contract | 否 |
| `provider_schema_failed` | 丢弃结果，不创建草案 | prompt/schema/adapter 修复并 eval | 默认否 |
| `provider_continuation_lost` | 停止当前 attempt | 从上个安全阶段 checkpoint 全量重跑 | 不原位回退 |
| `provider_stream_incomplete` | 丢弃 partial | parser/timeout 修复，fresh run | 无副作用任务按 policy |

## DeepSeek 特有核对

1. `base_url` 是否仍为稳定 `https://api.deepseek.com`，没有误切 `/beta`；
2. model ID 是否在批准快照内，`/models` 变化是否仅告警而未自动升级；
3. thinking 是否显式设置；thinking 时是否误发 sampling 参数；
4. JSON prompt 是否明确要求 JSON，`finish_reason` 是否为 `length`，内容是否为空白；
5. tool round 是否把 assistant 的 `reasoning_content` 作为 opaque state 完整回传；
6. SSE 空行/`: keep-alive` 是否被错误当作完成或 JSON；
7. 429/500/503 是否只执行配置中的最大 attempt，job deadline/预算是否仍有效。

## 恢复与验证

- 先在 fixture 通过 TC-LLM 对应失败，再用受控开发 Key 运行最小 live smoke；
- 验证文本、JSON、stream、thinking/tool、取消、错误映射和脱敏；
- 对影响模型输出的变更运行 EVAL-LLM-001，不只验证 HTTP 200；
- 确认没有重复 tool call、GraphPatch、revision 或费用失控；
- half-open 后观察 schema failure、HTTP error、p95、fallback 和成本；
- 更新 BUG/INC、DEVELOPMENT_LOG、OPS_LOG、config fingerprint 和 Runbook 演练报告。

## 升级条件

- 任何密钥/原文/reasoning 泄露：安全事故，立即撤销密钥；
- AI 回退重复外部副作用、绕过锁/DAG 或产生不可撤销数据：P0/P1 事故；
- 某批准 deployment 大范围不可用且无安全降级：运营事故；
- 单一输入稳定触发 schema/protocol 错：Bug，并附最小脱敏 fixture；
- 未知 Provider 漂移导致 fixture 与 live 分叉：隔离 deployment，创建兼容变更。

## 维护记录

| Date | Change/Test | Result | Test Report | Reviewer |
|---|---|---|---|---|
| 2026-08-13 | 初始 DeepSeek 优先 Runbook 草案 | 未演练 | — | — |
| 2026-08-14 | DeepSeek adapter + 受控 live smoke 部分演练（文本/JSON/thinking/tool/stream、错误映射、脱敏） | live 5/5、离线契约 21/21；金标 EVAL-LLM-001 与完整演练待后续 | 开发验证（`a80f43d`），QA TR 待封存 | — |
