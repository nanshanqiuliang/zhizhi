# WORK-2026-007：冻结 canonical LLM contract、配置 schema 与 DeepSeek adapter 契约（第 7 步离线第 1 期）

```yaml
status: implemented
type: feature
owner: Codex (llm-contract + infra role)
reviewers: [ai_qa_auditor, workspace_owner]
related_ids: [LLM-COMPAT-BASELINE-001, REQ-2026-006, NFR-2026-001, WORK-2026-005, WORK-2026-006, WORK-2026-010, TR-20260814-002]
target_stage: "阶段 1 / 自然语言第 7 步（安全接入第一个真实 AI）"
risk: high
created_at: 2026-08-14T22:30:00+08:00
updated_at: 2026-08-14T22:40:00+08:00
```

## 问题与结果

- 用户/工程问题：第 7 步（安全接入真实 AI/DeepSeek）当前只有静态配置与离线审核基础：`config/llm/providers.yaml`、`model-policies.yaml` 与 JSON Schema 已存在并有 repository 校验器，但没有 canonical LLM contract（消息/请求/结果/能力/错误码的版本化契约来源），没有实现 LLM port 的任何 adapter，`TC-LLM-001..009` 契约测试全部未执行。多 LLM 兼容基线第 11 节实施顺序的第 1–2 步（冻结 canonical DTO/capability/错误码/配置 schema、实现 mock adapter 与全部失败 fixture）尚未开始。
- 期望结果：新增 `docs/contracts/llm.v1.schema.json` 作为 canonical LLM contract 唯一手写来源（ProviderId/ProtocolId/消息/请求/结果/能力集合/稳定错误码/预算/追踪上下文），生成 Python runtime artifact（冷启动无 repository 文件 I/O），提供 schema-backed 校验器；实现确定性 `mock` provider adapter（文本/JSON/流式/tool/thinking/失败注入），实现能力校验、稳定错误码映射、退避/预算/熔断纯函数与 deployment 解析；以 JSON Schema 驱动契约测试覆盖 `TC-LLM-001..009` 的 mock 必须部分。
- 成功如何被观察：对任意合法 `GenerationRequest`，mock adapter 可确定性返回非流式结果与流式事件序列；注入 `provider_auth_failed`/`provider_rate_limited`/`provider_unavailable`/`provider_timeout`/`provider_schema_failed`/`provider_protocol_mismatch`/`provider_continuation_lost`/`provider_stream_incomplete` 均映射为稳定错误码；缺能力时在发送前返回 `provider_capability_missing`；相同 idempotency_key + 相同脚本产生相同输出；错误 details 不含正文/密钥；repository 门通过（validator/Ruff/mypy/pytest/pnpm）。

## 范围

- In scope：
  - `docs/contracts/llm.v1.schema.json`（canonical LLM contract v1：ProviderId/ProtocolId/ContentPart/CanonicalMessage/ToolDefinition/CanonicalToolCall/CanonicalUsage/FinishReason/Budget/TraceContext/GenerationRequest/GenerationResult/CapabilitySet/CapabilityName/LlmErrorCode）。
  - 生成脚本扩展（`packages/contracts-ts/scripts/generate.mjs`）产出 `packages/contracts-py/src/knowledge_tree_contracts/_generated_llm_v1_schema.py`，`--check` 检测 Python artifact 漂移；本轮不生成 TS（Web 尚未消费 LLM contract，接入属第 8 步）。
  - `packages/contracts-py` 新增 `llm_v1.py`（schema-backed 校验器 + 稳定常量，冷启动无文件 I/O）。
  - `packages/infrastructure/src/knowledge_tree_infrastructure/llm/`：`canonical.py`（frozen DTO，无厂商 SDK 类型）、`errors.py`（稳定错误码）、`capabilities.py`（能力校验 + fingerprint）、`resilience.py`（退避/预算/熔断纯函数）、`router.py`（deployment 解析，纯 dict 输入不读文件）、`mock.py`（确定性 mock provider + 全部失败 fixture）。
  - 契约测试：`tests/contract/test_llm_contract.py`（TC-LLM-001/002/009 + schema/artifact 校验）、`tests/contract/test_llm_mock_adapter.py`（TC-LLM-003..008 mock 部分）。
  - `scripts/repository_validation.py` 集成 `load_llm_contract_schema`（canonical schema 自校验），`scripts/validate_repository.py` 调用之。
- Out of scope：`openai_chat_completions`/`openai_responses`/`anthropic_messages` 协议适配器与 DeepSeek/OpenAI/Kimi/Anthropic vendor profile 的 HTTP 实现（实施顺序第 3–6 步，下一期）；真实 DeepSeek live smoke、金标评测、RB-PROV-001 演练（实施顺序第 7–8 步，需要 owner 提供受控 API Key 与预算，WORK-2026-008）；TS 端 LLM enum 生成；Web/API/worker 接入 AI；Embedding；任何真实 Provider 网络调用；密钥存储。
- 受影响模块/接口/数据：新增 `docs/contracts/llm.v1.schema.json`、contracts-py `llm_v1.py` 与生成 artifact、infrastructure `llm/` 子包、两个契约测试文件；扩展 `scripts/repository_validation.py` 与 `scripts/validate_repository.py`、`packages/contracts-ts/scripts/generate.mjs`、`packages/contracts-py/__init__.py`、`packages/infrastructure/__init__.py`。不修改 graph v1 contract、不引入 migration/新依赖、不改现有 config YAML 语义。
- 依赖和假设：`LLM-COMPAT-BASELINE-001` 第 2/3/4/6/7/9 节为契约来源；`TR-20260814-002` 已验证"JSON Schema 为唯一契约来源 + 生成 artifact 运行时无 repo I/O"模式；现有 `scripts/repository_validation.load_and_validate_llm_config` 已校验 config YAML 的 schema 与语义；不启用任何真实 Provider（所有 provider 除 `mock` 外 `enabled: false` 保持不变）。

## 设计边界

- Canonical contract 是唯一手写契约来源：`llm.v1.schema.json` 的 `$defs` 定义 ProviderId/ProtocolId/CapabilityName/LlmErrorCode/FinishReason 等 enum；代码中禁止出现与 schema 不同步的第二份 enum 字面量列表（生成 artifact 直接内嵌 schema JSON，校验器以 `$ref` 消费）。
- 运行时 DTO（`canonical.py`）为 frozen dataclass，全部字段可 JSON 序列化，不 import 任何厂商 SDK；`mock` protocol 与 provider 不依赖网络。
- 错误码是稳定 `snake_case`，来自 schema `LlmErrorCode` enum；`LLMProviderError.details` 只含标识与规则，不含正文、prompt、reasoning 或密钥。
- 幂等：相同 `idempotency_key` + 相同 `MockScript` 产出相同结果；重复 tool_call_id 拒绝。
- 脱敏：canonical 序列化默认不落 `reasoning_content`（仅存在性/字节数/hash 可记录）；测试断言错误 details 与 fixture 不含密钥模式。
- 退避初值沿用基线：`500ms -> 1s -> 2s`、full jitter、单 attempt 最多 3 次网络请求（mock 中为确定性纯函数，不做真实 sleep）；401/402/400 不重试；429/500/503 可重试；auth/balance 错误立即打开 deployment 级熔断。
- 预算：`AttemptBudget` 在超限时返回 `budget_exceeded`；`model_run_cancelled` 标记取消的 run。

## 风险影响

- 数据/schema/migration：新增 `llm.v1.schema.json` 与生成 artifact；不引入 migration；graph v1 contract 不变。
- 安全/隐私：本轮无网络、无密钥解析、无真实调用；错误 details 与 fixture 均脱敏；secret scan 规则（`sk-`/`sk_` 等）不得被 fixture 命中。
- 并发/幂等/恢复：mock 为无状态确定性实现（流式迭代器除外）；幂等键与重放语义在测试中强制。
- 性能/容量/成本：无真实费用；退避/预算为纯函数。
- 可观测性/诊断：稳定错误码来自 schema enum；`capability_fingerprint` 为版本化快照 hash。
- 用户文档：路线图第 7 步进度更新为"离线契约层已冻结、mock 已验证；真实适配待 API Key/预算"；不把 mock 宣称为真实 DeepSeek 支持。

## 验收标准

- [ ] AC-1 (c1)：`llm.v1.schema.json` 通过 JSON Schema 自校验；enum 值与多 LLM 基线一致（ProviderId 含 mock/deepseek/openai/kimi/anthropic；ProtocolId 含 mock/openai_chat_completions/openai_responses/anthropic_messages；LlmErrorCode 覆盖基线 4.6 全部稳定错误码）。
- [ ] AC-2 (c2)：生成 artifact 与 schema 无漂移（`pnpm --filter @knowledge-tree/contracts-ts generate --check` 通过）；contracts-py 冷启动校验不读 repository 文件（导入 artifact 字符串）。
- [ ] AC-3 (c3)：`validate_llm_payload` 接受合法 GenerationRequest/GenerationResult，拒绝未知字段/非法 enum/非法 uuidv7/负 token；错误路径稳定。
- [ ] AC-4 (c4)：mock adapter 非流式与流式生成：确定性文本/JSON、流事件序列（started/delta/usage.updated/completed）、heartbeat、断流 `provider_stream_incomplete`、取消 `model_run_cancelled`、tool_call 事件与重复调用防护、thinking 存在性 + tool 轮 reasoning state 回传、`provider_continuation_lost`。
- [ ] AC-5 (c5)：失败注入全映射：auth_failed/balance_exhausted/rate_limited/unavailable/connection_failed/timeout/schema_failed/protocol_mismatch → 稳定错误码；缺能力时发送前 `provider_capability_missing`；budget 超限 `budget_exceeded`。
- [ ] AC-6 (c6)：resilience 纯函数：退避序列确定性、401/402 不重试、熔断 closed→open→half-open 状态机、预算检查；相同 idempotency_key + 相同脚本结果一致。
- [ ] AC-7 (c7)：脱敏：错误 details 与 fixture 不含正文/密钥/reasoning；secret scan 无新增命中。
- [ ] AC-8 (c8)：repository 门：validator、Ruff format/lint、scripts + strict package mypy、全仓 pytest、locked pnpm install/peers/check/build 全绿。
- [ ] 错误和恢复路径：调用方基于稳定 code 决定重试/回退/提示；不自动猜测合并；未启用 provider 不被路由。
- [ ] 回滚/禁用方法：回退本工作项提交即回到无 LLM port 状态；不影响 graph contract、持久化、导入、查看器与第 6 步全部已验证能力；红灯与证据保留。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-LLM-001 | contract | canonical message/role/content mapping | 合法消息校验通过、非法 role 拒绝、往返一致 | 待红灯/TR |
| TC-LLM-002 | contract | JSON object + 本地 schema 成功/失败/截断/空白 | 合法 typed_output 通过；截断/空白 → `provider_schema_failed` | 待红灯/TR |
| TC-LLM-003 | contract | 流事件序列/heartbeat/断流/取消 | 事件顺序正确、`provider_stream_incomplete`/`model_run_cancelled` | 待红灯/TR |
| TC-LLM-004 | contract | tool call/结果/重复调用防护 | 事件完整、重复 tool_call_id 拒绝 | 待红灯/TR |
| TC-LLM-005 | contract | thinking + tool reasoning state replay | 存在性保留、`provider_continuation_lost` | 待红灯/TR |
| TC-LLM-006 | contract | 错误映射（401/402/422/429/5xx/timeout） | 稳定错误码、不重试 401/402 | 待红灯/TR |
| TC-LLM-007 | contract | retry/backoff/circuit/budget/idempotency | 确定性退避、熔断状态机、`budget_exceeded`、幂等 | 待红灯/TR |
| TC-LLM-008 | contract | 日志/trace/诊断脱敏 | 错误 details 与 fixture 无正文/密钥 | 待红灯/TR |
| TC-LLM-009 | contract | capability/config schema/fingerprint | 能力缺失发送前拒绝、fingerprint 稳定 | 待红灯/TR |
| TC-REPO-001 | repository | 全仓门 | validator/Ruff/mypy/pytest/pnpm | 待 TR |

## 交付物与关闭

- Commit/PR：分支 `feature/WORK-2026-007-llm-contract`；Ready（本文档）→ 红灯 `b5747ec`（2 collection errors）→ 实现 `b2e215b` → 文档收口 `ed8d87f`。
- Contract/ADR/migration/prompt：新增 `docs/contracts/llm.v1.schema.json`（canonical，版本 v1）与生成 artifact；无 ADR/migration/prompt 变更。
- Test Run：TC-LLM-001..009 mock 部分 56/56；全仓 pytest 314/314；repository validator、Ruff、scripts + strict package mypy、contracts-ts drift/tsc、Web 32/32、pnpm build 全绿；职责隔离 QA 待执行（按总纲流程）。
- Release：无托管发布；无真实 Provider 启用（除 `mock` 外全部 `enabled: false`）。
- 观察结果：第 7 步离线契约层冻结；`TC-LLM-001..009` mock 必须部分执行完毕。
- 未完成项的新 ID：openai_chat_completions 协议适配器 + DeepSeek vendor profile + streaming/thinking/tool wire 实现（实施顺序 3–5）；retry/circuit/budget 与受控 fallback 接入真实 adapter（实施顺序 6）；DeepSeek live smoke 与微积分金标（实施顺序 7，WORK-2026-008，需 owner API Key/预算）；TS enum 生成与 Web 接入（第 8 步）。
