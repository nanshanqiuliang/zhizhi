# WORK-2026-008：DeepSeek OpenAI Chat Completions adapter 与受控 live smoke（第 7 步真实接入第 1 期）

```yaml
status: implemented
type: feature
owner: Codex (llm-adapter + infra role)
reviewers: [ai_qa_auditor, workspace_owner]
related_ids: [LLM-COMPAT-BASELINE-001, NFR-2026-006, NFR-2026-007, NFR-2026-008, WORK-2026-004, WORK-2026-007, OPS-2026-003, RB-PROV-001]
target_stage: "阶段 1 / 自然语言第 7 步（安全接入第一个真实 AI）"
risk: high
created_at: 2026-08-14T23:00:00+08:00
updated_at: 2026-08-14T23:15:00+08:00
```

## 问题与结果

- 用户/工程问题：WORK-2026-007 已冻结 canonical LLM contract 并验证 mock provider，但尚无任何真实协议适配器；多 LLM 基线第 11 节实施顺序 3–6（openai_chat_completions 协议适配器、DeepSeek vendor profile、streaming/thinking/tool reasoning replay、retry/circuit/budget 接入）与顺序 7（DeepSeek live smoke）均未开始。用户已提供受控 DeepSeek API Key 并给出 3 元人民币测试预算上限，要求推进第 7 步真实接入。
- 期望结果：实现 `openai_chat_completions` 协议适配器与 DeepSeek vendor profile（stdlib 传输、显式 thinking 参数、reasoning_content 工具轮回传、SSE 流解析、HTTP 错误映射到稳定错误码），接入已有 resilience（退避/预算/熔断），以脱敏录制 fixture 做无网络契约测试；在 `RUN_LIVE_LLM_TESTS=1` + `DEEPSEEK_API_KEY` 双重显式门控下运行受控 live smoke（文本/JSON/thinking/tool/stream 最小请求），报告实际 token 用量，总费用远低于 3 元。
- 成功如何被观察：离线 fixture 断言 OpenAI wire 请求/响应/SSE 与 canonical 契约双向映射正确、错误码映射正确、fixture 不含密钥；live smoke 在 env 门控下对真实 `deepseek-v4-flash`/`deepseek-v4-pro` 完成最小调用并返回符合契约的结果与 usage；预算未超；日志不含密钥。

## 范围

- In scope：
  - `packages/infrastructure/src/knowledge_tree_infrastructure/llm/protocols/openai_chat.py`：canonical↔OpenAI Chat Completions 请求/响应/SSE 双向映射（消息/角色/内容、工具调用、usage、finish_reason、reasoning_content 回传）。
  - `packages/infrastructure/src/knowledge_tree_infrastructure/llm/vendors/deepseek.py`：DeepSeek vendor profile（endpoint、显式 `thinking.type`、thinking 模式禁发 sampling 参数、`max_tokens`、错误映射、模型 ID 快照）+ `DeepSeekLlmAdapter`。
  - `packages/infrastructure/src/knowledge_tree_infrastructure/llm/http_client.py`：stdlib `urllib.request` 传输（POST JSON + SSE 流式逐行解析 + connect/first-byte/idle/total 超时），不引入新依赖、不依赖厂商 SDK。
  - resilience 接线：`AttemptBudget` + `CircuitBreaker` + 退避；401/402/400/422 不重试，429/5xx/连接错误可重试。
  - `apps`/scripts 侧 composition root 的 `env://DEEPSEEK_API_KEY` 解析（不落盘、不硬编码）。
  - 离线 fixture 契约测试：`tests/contract/test_deepseek_adapter.py`（请求序列化、响应/SSE 映射、错误映射、脱敏）。
  - live smoke：`tests/e2e/test_deepseek_live_smoke.py`（`RUN_LIVE_LLM_TESTS=1` + `DEEPSEEK_API_KEY` 才运行；探测模型目录 + 最小文本/JSON/thinking/tool/stream）。
- Out of scope：OpenAI Responses / Kimi / Anthropic 协议适配器（实施顺序 9）；微积分金标评测 `EVAL-LLM-001` 与质量/成本/延迟门（后续工作项，本轮只做 live smoke 连通性）；AI 草案流水线接入（第 8 步）；DeepSeek deployment 设为 `enabled: true` 的正式批准（需完整 live + eval + RB-PROV-001 演练）；密钥存储（keychain/Stronghold）；TS 端与 Web UI。
- 受影响模块/接口/数据：扩展 `knowledge_tree_infrastructure/llm/`（新增 protocols/vendors/http_client 子模块）；新增两个测试文件；无 canonical contract/migration/prompt 变更；config/llm YAML 语义不变（模型 ID 快照已与真实 `/models` 探测一致）。
- 依赖和假设：WORK-2026-007 的 canonical contract、错误码、resilience、router 已验证；DeepSeek 稳定协议为 OpenAI Chat Completions（`https://api.deepseek.com/chat/completions`）；真实模型目录为 `deepseek-v4-flash`/`deepseek-v4-pro`（2026-08-14 `/models` 探测确认）；live smoke 仅在显式 env 门控下运行；API Key 只经环境变量进入 composition root，绝不写入文件/日志/git。

## 设计边界

- 领域/适配器不 import 厂商 SDK；传输用 stdlib `urllib`；vendor 差异（thinking、reasoning_content、错误细节）封装在 `vendors/deepseek.py`，不散落业务代码。
- 显式 thinking：每次请求都设置 `thinking.type`；`economy_structured`/`command_interpret` 默认 `disabled`，`reasoning_high` 默认 `enabled`；thinking 模式不发送 temperature/top_p/presence_penalty/frequency_penalty，本地拒绝矛盾配置。
- reasoning_content：只在 agent turn 临时内存中为维持 Provider 协议回传，不解析、不展示、不写日志/领域表；丢失时返回 `provider_continuation_lost` 而非伪造。
- SSE：容忍空行与 `: keep-alive`；`[DONE]` 结束；JSON 未闭合 → `provider_stream_incomplete`；工具参数在 `completed` 前不执行。
- 错误映射沿用基线 4.6；401/402 立即打开熔断且不重试；退避 500→1000→2000ms full jitter；`AttemptBudget` 超限 → `budget_exceeded`。
- 脱敏：HTTP 请求/响应 fixture 与日志不含 Authorization、API Key、完整 prompt/response、reasoning_content；Provider request id 可记录。

## 风险影响

- 数据/schema/migration：无 schema/migration；新增纯 Python 模块与测试。
- 安全/隐私：API Key 只经 `env://` 解析；live smoke 受 env 门控；fixture 脱敏；secret scan 不得命中。
- 并发/幂等/恢复：live 调用非幂等（生成类任务），重试受预算约束；取消/断流不续写中间 delta。
- 性能/容量/成本：live smoke 用最小 `max_tokens`（16–128），总 token 预计 < 数十 K，费用远低于 3 元；真实调用只在测试环境显式启用。
- 可观测性/诊断：稳定错误码 + `model_run_id`/`provider_response_id`；不落正文。
- 用户文档：路线第 7 步进度更新；明确"真实 DeepSeek adapter 已实现并完成受控 smoke，但 deployment 仍 `enabled: false`，正式批准待金标/RB-PROV-001"。

## 验收标准

- [ ] AC-1 (c1)：`openai_chat` 协议适配器将合法 GenerationRequest 序列化为 OpenAI wire 请求（消息/角色/内容、工具、`thinking.type`、`max_tokens`、`response_format`），并拒绝矛盾配置（thinking + sampling）。
- [ ] AC-2 (c2)：OpenAI 响应/SSE 流正确映射回 canonical GenerationResult/LlmStreamEvent（文本、JSON、tool_calls、usage、finish_reason、reasoning_content 回传；`[DONE]`/空行/keep-alive 容忍）。
- [ ] AC-3 (c3)：HTTP 错误映射正确：400/422→provider_invalid_request、401/403→provider_auth_failed、402→provider_balance_exhausted、429→provider_rate_limited、500/503→provider_unavailable、连接/超时→provider_connection_failed/provider_timeout；断流/坏 JSON→provider_stream_incomplete/provider_schema_failed。
- [ ] AC-4 (c4)：resilience 接线：401/402/400/422 不重试且立即熔断；429/5xx/连接错误有界重试；AttemptBudget 超限→budget_exceeded。
- [ ] AC-5 (c5)：离线 fixture 契约测试全部通过且 fixture/日志不含密钥、正文、reasoning_content。
- [ ] AC-6 (c6)：live smoke（env 门控）对真实 DeepSeek 完成最小文本/JSON/thinking/tool/stream 调用并返回符合契约的结果与 usage；实际费用 < 3 元且报告用量。
- [ ] AC-7 (c7)：repository 门：validator、Ruff、scripts + strict package mypy、全仓 pytest（live 用例默认 skip）、contracts-ts drift/tsc、Web 32/32、pnpm build 全绿。
- [ ] 错误和恢复路径：调用方基于稳定 code 决定重试/回退/提示；live 失败不掩盖离线契约测试结果。
- [ ] 回滚/禁用方法：回退本工作项提交即回到 mock-only；DeepSeek deployment 保持 `enabled: false`；红灯与证据保留；密钥不随提交进入仓库。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-DS-001 | contract | OpenAI 请求序列化（消息/工具/thinking/response_format） | wire 请求字段正确、矛盾配置拒绝 | 待红灯/TR |
| TC-DS-002 | contract | OpenAI 响应映射（文本/JSON/tool_calls/usage/finish_reason） | canonical GenerationResult 正确 | 待红灯/TR |
| TC-DS-003 | contract | SSE 流解析（delta/reasoning/keep-alive/[DONE]/断流） | 事件序列正确、stream_incomplete | 待红灯/TR |
| TC-DS-004 | contract | HTTP 错误映射（401/402/422/429/5xx/连接/超时） | 稳定错误码、重试语义 | 待红灯/TR |
| TC-DS-005 | security | fixture/日志脱敏 | 无 key/正文/reasoning_content | 待红灯/TR |
| TC-DS-LIVE-001..005 | e2e (live) | 模型探测/文本/JSON/thinking/tool/stream | 真实结果 + usage，费用 < 3 元 | 待 live |
| TC-REPO-001 | repository | 全仓门 | validator/Ruff/mypy/pytest/pnpm | 待 TR |

## 交付物与关闭

- Commit/PR：分支 `feature/WORK-2026-008-deepseek-adapter-live`；Ready → 红灯 `d6a7444`（1 collection error）→ 实现 `d81c574` → live smoke + timeout 修复 `a80f43d` → 文档收口。
- Contract/ADR/migration/prompt：无新 canonical contract/ADR/migration/prompt；复用 `docs/contracts/llm.v1.schema.json` 与 config/llm v1。
- Test Run：离线 fixture 契约测试 TC-DS-001..005 21/21；live smoke 5/5（RUN_LIVE_LLM_TESTS=1 + DEEPSEEK_API_KEY，约 817 token，费用远低于 3 元）；全仓 pytest 335/335 + 5 skipped；validator/Ruff/strict mypy（25 文件）/contracts-ts drift/pnpm build 全绿；职责隔离 QA 待执行。
- Release：无托管发布；DeepSeek deployment 保持 `enabled: false`（正式批准待金标/RB-PROV-001）。
- 观察结果：DeepSeek OpenAI Chat Completions adapter 真实可用（受控 smoke 验证）；密钥从未落盘。
- 未完成项的新 ID：微积分金标评测 `EVAL-LLM-001` 与质量/成本/延迟门、`RB-PROV-001` 演练、DeepSeek deployment 正式批准、AI 草案流水线接入（第 8 步）。
