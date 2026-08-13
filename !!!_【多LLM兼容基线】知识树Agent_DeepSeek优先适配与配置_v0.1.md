# 知识树 Agent：多 LLM 兼容基线（DeepSeek 优先）

> **文件标识：`!!! 多 LLM 兼容基线 / DeepSeek First`**  
> **document_id：`LLM-COMPAT-BASELINE-001`**  
> **版本：0.1（实施前兼容基线）**  
> **日期：2026-08-13**  
> **状态：配置与契约已规划，尚无产品代码、API Key 或真实 Provider 联调证据**  
> **上游基线：`!!!_【工程框架指导】知识树Agent_总体架构技术基线_v0.1.md`**  
> **配套流程：`!!!_【开发运维总纲】知识树Agent_全生命周期开发流程_v0.1.md`**  
> **版本化配置：`config/llm/providers.yaml`、`config/llm/model-policies.yaml`**

---

## 0. 决策结论

1. 首个真实 LLM Provider 选择 **DeepSeek API**；MVP 同时保留确定性的 `mock` Provider。
2. 内部领域与应用层只使用本文件定义的 canonical contract，不 import DeepSeek、OpenAI、Anthropic 或 Moonshot SDK 类型。
3. DeepSeek 首版走其稳定的 **OpenAI Chat Completions 兼容接口**；不能把“OpenAI 兼容”解释为 Responses API、字段、流事件、推理或结构化输出完全等价。
4. OpenAI 使用独立的 `openai_responses` 协议适配器；Kimi 使用带厂商 profile 的 `openai_chat_completions` 适配器；Claude 使用 `anthropic_messages` 适配器。
5. Provider 能力必须显式声明并在运行前校验，禁止依赖模型名称猜能力或在业务代码散落 `if provider == ...`。
6. 跨 Provider 自动回退只允许处理明确的瞬态故障；认证、余额、非法参数、schema 不兼容和安全拒绝不得盲目切换。
7. AI 永远只产出草案。即使发生回退，结果仍须通过本地 schema、GraphPatch、锁、权限、证据和 DAG 校验。

本文件中的具体模型 ID 是截至 2026-08-13 的配置快照，不是永久产品承诺。启动探测可以发现模型目录变化，但新模型不得自动进入任务路由；须经过金标评测、成本/延迟比较和配置评审。

---

## 1. 范围和非目标

### 1.1 本基线覆盖

- 文本生成、流式输出、结构化结果、工具调用和推理模式；
- Provider/模型能力注册、任务路由、预算、超时、重试、熔断和回退；
- OpenAI、Kimi/Moonshot、DeepSeek、Claude/Anthropic 的协议边界；
- 密钥引用、脱敏日志、model run 审计、契约测试、真实冒烟和 AI 金标评测；
- 本地/云端共用的非敏感版本化配置。

### 1.2 本基线暂不承诺

- 一套 SDK 覆盖所有厂商且行为完全一致；
- 所有 Provider 都支持图片、音频、文件、Web Search、Embedding 或严格 JSON Schema；
- 在没有用户配置 API Key 时调用真实模型；
- 自动选择未经批准的新模型或 Beta 端点；
- 通过日志永久保存模型思维内容、完整 prompt、完整 response 或用户资料。

### 1.3 LLM 与 Embedding 分离

`LLMProvider` 与 `EmbeddingProvider` 是两个独立端口。DeepSeek 作为首家 LLM Provider，不意味着向量嵌入也由 DeepSeek 提供。当前 DeepSeek 官方 API 目录未形成本文可批准的 Embedding 基线，因此 `multilingual_embedding` 必须单独选择本地或云端 Provider，并在选定前保持 `unresolved`；禁止拿聊天模型伪造 embedding。

---

## 2. 协议分层与目录结构

```text
Application task
  -> ModelRouter(task_profile, data_policy, budget)
  -> Canonical LLM Port
  -> Protocol Adapter
       openai_chat_completions
       openai_responses
       anthropic_messages
  -> Vendor Profile
       deepseek / kimi / openai / anthropic
  -> HTTP/SDK client
```

建议实现路径：

```text
packages/infrastructure/llm/
├─ canonical.py                 # 稳定 DTO，不含厂商 SDK 类型
├─ capabilities.py              # 能力集合与兼容校验
├─ router.py                    # task_profile -> deployment
├─ resilience.py                # timeout/retry/circuit/fallback
├─ errors.py                    # 厂商异常 -> 稳定错误码
├─ protocols/
│  ├─ openai_chat.py
│  ├─ openai_responses.py
│  └─ anthropic_messages.py
└─ vendors/
   ├─ deepseek.py
   ├─ kimi.py
   ├─ openai.py
   └─ anthropic.py
```

协议适配器负责请求/响应形状；厂商 profile 负责端点、专有参数、能力、限制和错误细节。二者必须分开，避免复制四套完整客户端，也避免把所有差异塞进一个不可维护的“万能 OpenAI Adapter”。

---

## 3. Canonical contract

### 3.1 核心数据结构

```python
ProviderId = Literal["mock", "deepseek", "openai", "kimi", "anthropic"]
ProtocolId = Literal[
    "mock",
    "openai_chat_completions",
    "openai_responses",
    "anthropic_messages",
]

@dataclass(frozen=True)
class ContentPart:
    kind: Literal["text", "image_ref", "tool_call", "tool_result"]
    value: object
    media_type: str | None = None

@dataclass(frozen=True)
class CanonicalMessage:
    role: Literal["system", "user", "assistant", "tool"]
    parts: tuple[ContentPart, ...]
    tool_call_id: str | None = None

@dataclass(frozen=True)
class GenerationRequest:
    task: str
    messages: tuple[CanonicalMessage, ...]
    output_schema: dict | None
    tools: tuple[ToolDefinition, ...]
    model_policy: str
    idempotency_key: str
    budget: Budget
    trace_context: TraceContext

@dataclass(frozen=True)
class GenerationResult:
    text: str | None
    typed_output: object | None
    tool_calls: tuple[CanonicalToolCall, ...]
    usage: CanonicalUsage
    finish_reason: CanonicalFinishReason
    provider_response_id: str | None
    provider: ProviderId
    protocol: ProtocolId
    model_id: str
    model_revision: str | None
    capability_snapshot: str
```

流式结果统一成有限事件集合：

```text
response.started
text.delta
tool_call.started / tool_call.arguments.delta / tool_call.completed
usage.updated
response.completed
response.failed
heartbeat
```

未知厂商事件不得原样穿透 UI。Adapter 应安全忽略已声明可忽略的扩展；对影响语义的未知事件必须以 `provider_protocol_mismatch` 失败并保留脱敏 fixture。

### 3.2 能力集合

每个 deployment 必须有版本化能力快照，至少包含：

```text
text_input / text_output / image_input
streaming / tool_calls / parallel_tool_calls
json_object / json_schema / strict_tool_schema
thinking / reasoning_effort / reasoning_replay
system_message / developer_message
usage_tokens / prompt_cache_usage / provider_request_id
web_search / file_search / embeddings
max_context_tokens / max_output_tokens
```

规则：

- `required_capabilities` 不满足时在发送网络请求前返回 `provider_capability_missing`；
- 配置声明与实时探测冲突时取更保守值、关闭相关路由并告警；
- 上下文和输出上限属于配置快照，不由业务代码硬编码；
- 能力变化属于兼容性变更，必须跑 Provider 契约测试和受影响 AI eval。

---

## 4. DeepSeek 首要兼容基线

### 4.1 稳定接入面

| 项目 | v0.1 决策 |
|---|---|
| Provider ID | `deepseek` |
| Protocol | `openai_chat_completions` |
| Base URL | `https://api.deepseek.com` |
| Chat endpoint | `/chat/completions` |
| Model discovery | `/models`，只用于探测和告警，不自动批准新模型 |
| Auth | Bearer；密钥只通过 `secret_ref` 在 composition root 解析 |
| 默认稳定模型别名 | `deepseek_fast -> deepseek-v4-flash`；`deepseek_quality -> deepseek-v4-pro` |
| 默认 Beta | 全部关闭；不得把 `/beta` 设为默认 base URL |

DeepSeek 当前官方文档同时提供 OpenAI 和 Anthropic 格式。项目首版只批准 OpenAI Chat Completions 格式，避免同一 Provider 出现两套会话序列化真相。只有当实测表明 Anthropic 格式能解决明确兼容问题时，才通过 ADR 增加第二 deployment。

### 4.2 显式参数规则

- 每次请求都显式设置 `thinking.type`，不依赖厂商默认值；
- `economy_structured`、`command_interpret` 默认 `thinking=disabled`；
- `reasoning_high` 默认 `thinking=enabled`、`reasoning_effort=high`；`max` 仅在金标证明收益后启用；
- thinking 模式下不发送 `temperature`、`top_p`、`presence_penalty`、`frequency_penalty`；即使服务端暂时忽略这些参数，Adapter 也应在本地拒绝矛盾配置；
- 使用 `max_tokens`，不得由通用层擅自改为其他厂商字段；
- 业务用户隔离标识必须是稳定、不可逆、无个人信息的值；若使用 `user_id`，通过 `extra_body` 发送且不得记录原值。

### 4.3 推理内容与工具调用

DeepSeek thinking + tool calls 存在重要的会话约束：发生工具调用时，模型返回的 `reasoning_content` 必须在后续工具轮次中完整回传，否则可能得到 HTTP 400。

因此：

1. Adapter 在一次 agent turn 的临时内存中保存 opaque reasoning state；
2. 只为维持 Provider 协议而回传，不解析、不展示、不写入领域表；
3. 默认不写日志、trace artifact 或诊断包，只记录存在性、字节数和 hash；
4. tool call 完成或请求失败后及时释放；需要崩溃恢复的任务只保存加密、短期、用户可清除的 provider continuation artifact，且须另行安全评审；
5. 丢失必要 reasoning state 时不得伪造，应返回 `provider_continuation_lost` 并从上一个安全 checkpoint 重启整个模型阶段。

### 4.4 结构化输出

稳定 v0.1 使用：

```text
response_format = {"type": "json_object"}
+ prompt 中明确出现 JSON 和目标示例
+ 本地 Pydantic/JSON Schema 严格校验
+ 失败时最多一次受预算约束的 repair/retry
+ 仍失败则 provider_schema_failed，绝不把半截 JSON 当草案
```

DeepSeek JSON Object 保证“合法 JSON”不等于符合本项目 schema，且官方提示可能出现空内容或因 token 上限截断。因此必须检查：空白、`finish_reason=length`、字段类型、额外字段、枚举、引用和业务不变量。

DeepSeek Beta strict tool schema 只作为隔离技术尖峰，要求独立 deployment、`allow_beta=true`、测试环境和显式 feature flag；未通过回归前不得承载生产 GraphPatch。

### 4.5 流式解析

- 支持标准 SSE delta，但 parser 必须容忍空行和 `: keep-alive` 注释；
- 每个 stream 设置首字节、空闲和总时限，长推理期间 heartbeat 不等于业务 token；
- 客户端取消后停止读取、结算已知 usage、将 model run 标记为 `cancelled`；
- 工具参数增量在 `completed` 前不得执行；JSON 未闭合时返回 `provider_stream_incomplete`；
- 断流不允许从中间 delta 直接续写图草案。若无厂商幂等恢复能力，创建新 attempt，从阶段 checkpoint 重跑。

### 4.6 DeepSeek HTTP 错误映射

| HTTP/条件 | 稳定错误码 | 自动重试 | 自动跨 Provider 回退 |
|---|---|---:|---:|
| 400 | `provider_invalid_request`；若缺 reasoning state 则 `provider_continuation_lost` | 否 | 否 |
| 401/403 | `provider_auth_failed` | 否 | 否 |
| 402 | `provider_balance_exhausted` | 否 | 否 |
| 422 | `provider_invalid_request` | 否 | 否 |
| 429 | `provider_rate_limited` | 是，尊重响应头并全抖动退避 | 只读任务可；写草案任务须策略显式允许 |
| 500/503 | `provider_unavailable` | 是，有界退避 | 可按任务策略 |
| DNS/connect/TLS | `provider_connection_failed` | 是，有界重试 | 可按任务策略 |
| read/idle/total timeout | `provider_timeout` | 取决于阶段与幂等性 | 可按任务策略 |
| JSON 空白/截断/schema 错 | `provider_schema_failed` | 最多一次修复 | 默认否 |
| 未知响应字段破坏语义 | `provider_protocol_mismatch` | 否 | 否，先隔离 deployment |

退避工程初值：`0.5s -> 1s -> 2s`，full jitter，单 attempt 最多 3 次网络请求；必须同时受 job deadline、token 和金额预算约束。不得对 401/402/400 无限重试。

### 4.7 DeepSeek 上线门

必须依次通过：

1. 无网络 mapper 单元测试；
2. 录制且脱敏的 HTTP/SSE fixture 契约测试；
3. sandbox/开发 Key 的真实 smoke：文本、JSON、thinking、tool、stream、429/5xx 注入；
4. 微积分金标：概念抽取、关系候选、命令解释、带引用回答；
5. 与 mock 基线对照幂等、取消、重试、预算和日志脱敏；
6. `RB-PROV-001` 演练；
7. QA 批准 model policy 与 capability snapshot。

真实 smoke 只能在显式 `RUN_LIVE_LLM_TESTS=1` 且 secret store 存在 `DEEPSEEK_API_KEY` 时运行；PR 默认不得访问真实 Provider，避免费用、波动和密钥风险。

---

## 5. 其他主流 Provider 兼容基线

| Provider | Protocol | v0.1 状态 | 必须独立处理的差异 |
|---|---|---|---|
| OpenAI API | `openai_responses` | 配置关闭、契约预留 | Responses items、Structured Outputs、tool/stream 事件、reasoning、官方托管工具 |
| Kimi/Moonshot | `openai_chat_completions` + `kimi` profile | 配置关闭、契约预留 | `thinking` 经 `extra_body`、`partial`、结构化输出与缓存字段、端点差异 |
| Claude/Anthropic | `anthropic_messages` | 配置关闭、契约预留 | content blocks、system 字段、tool_use/tool_result、stop reason、SSE 事件、thinking |
| 本地模型 | 待具体运行时 | 未选择 | 安装体积、硬件预算、模型能力、离线隐私、OpenAI 兼容程度 |

“配置关闭”表示 schema、ID 和路由结构已预留，但没有声明可用。只有具备真实 smoke、fixture、金标报告、密钥管理和 Runbook 证据后，才能设置 `enabled: true`。

OpenAI 官方当前建议 reasoning、tool calling 和 multi-turn 工作流使用 Responses API，因此 OpenAI 不复用 DeepSeek 的 Chat Completions wire adapter。Kimi 官方虽兼容 OpenAI Chat Completions，但存在专有扩展；Claude 使用 Messages API，必须使用原生协议适配器。

---

## 6. 路由、回退和熔断

### 6.1 路由只引用 deployment alias

业务只请求：

```text
economy_structured
reasoning_high
command_interpret
balanced_grounded
vision
multilingual_embedding
```

`model-policies.yaml` 再映射到有序 deployment。配置变更须生成 fingerprint；每次 model run 记录实际 provider、protocol、model、capability snapshot、policy version、attempt 和 fallback 原因。

### 6.2 回退矩阵

| 任务类别 | 默认自动回退 | 约束 |
|---|---:|---|
| 只读问答/解释 | 可以 | 保留引用要求；UI 标明实际模型；新 model run |
| 概念/关系草案 | 仅同一批准 policy 内 | 仍是草案；重新 schema/领域校验；不得拼接两个模型的半成品 |
| GraphPatch apply | 不适用 | LLM 无权直接 apply |
| 工具调用产生外部副作用 | 否 | 需要重新确认，不能因回退重复执行 |
| Embedding | 否 | 更换模型会改变向量空间，必须新建索引版本 |

只有 `provider_rate_limited`、`provider_unavailable`、`provider_connection_failed` 和经策略批准的 `provider_timeout` 可以触发自动回退。回退前检查剩余预算和截止时间；回退后禁止沿用不同协议的 opaque continuation state。

### 6.3 熔断

- key：`provider + endpoint + model_alias`；
- 连续失败阈值和窗口是工程初值，配置化而非硬编码；
- auth/balance 错误立即打开 deployment 级熔断，等待人工修复；
- half-open 只放行健康探测/少量请求；
- 本地单用户 UI 必须显示“暂不可用、预计重试、可选 Provider”，不得无限转圈。

---

## 7. 配置与秘密

### 7.1 文件职责

- `config/llm/providers.yaml`：协议、端点、secret reference、模型 alias、能力、超时和兼容开关；
- `config/llm/model-policies.yaml`：任务能力需求、候选 deployment、预算、重试和回退；
- 二者都是非敏感配置，进入版本控制并计算 canonical fingerprint；
- API Key 不得出现在 YAML、日志、截图、Bug、诊断包或测试 fixture。

### 7.2 合并优先级

```text
built-in safe defaults
  < versioned environment config
  < local user non-secret preferences
  < runtime secret resolution
```

生产/正式发布禁止任意环境变量覆盖非敏感行为配置。开发和 CI 的 live smoke 可以使用 `env://DEEPSEEK_API_KEY`，但只在隔离任务中解析；桌面版使用 OS keychain/Stronghold 引用。

### 7.3 启动校验

启动时必须校验：

- YAML schema/version、未知字段、重复 alias；
- HTTPS endpoint 和允许域；非开发模式禁止任意 base URL；
- secret reference 存在性，只报告引用状态不读取回显；
- task required capabilities 与 deployment capability 的包含关系；
- thinking 与 sampling 参数无冲突；
- context/output/预算为正且不超过批准上限；
- fallback 无环，且 embedding policy 不跨模型自动回退；
- Beta endpoint 必须同时满足环境、flag、policy 三重允许。

失败应阻断对应 deployment，不应让整个无 AI 桌面应用无法启动。

---

## 8. 可观测性与 Bug 定位

### 8.1 每个 model run 最少记录

```text
model_run_id / correlation_id / job_id / stage_run_id
task_profile / policy_version / policy_fingerprint
provider / protocol / endpoint_host / deployment_alias
model_id / model_revision / capability_snapshot
attempt / retry_reason / fallback_from / fallback_reason
request_bytes / response_bytes / input_tokens / output_tokens
latency_ms / time_to_first_token_ms / finish_reason / cache_usage
estimated_cost / budget_remaining / safe_error_code
prompt_version / schema_version / input_fingerprint / output_fingerprint
```

不得记录 API Key、Authorization、完整 URL query、原文、完整 prompt/response、tool 敏感结果或 `reasoning_content`。Provider request ID 可以记录；未知原始错误正文只能进入受控、脱敏、短保留期 artifact。

### 8.2 “第一个坏边界”定位顺序

```text
task policy selection
-> capability preflight
-> canonical request validation
-> vendor serialization
-> DNS/TLS/HTTP/auth/rate-limit
-> stream framing
-> vendor response mapping
-> JSON/schema validation
-> domain validation
-> draft persistence/revision
```

先用相同 `model_run_id` 和 config fingerprint 找第一处错误，禁止通过“换模型试试”掩盖 protocol mismatch。详细处置见 `docs/runbooks/RB-PROV-001.md`。

---

## 9. 测试矩阵与证据

| Test ID | 范围 | Mock/fixture | DeepSeek live | 其他 Provider live |
|---|---|---:|---:|---:|
| `TC-LLM-001` | canonical message/role/content mapping | 必须 | smoke | 启用前必须 |
| `TC-LLM-002` | JSON object + 本地 schema 成功/失败/截断/空白 | 必须 | 必须 | 启用前必须 |
| `TC-LLM-003` | SSE delta/heartbeat/断流/取消 | 必须 | 必须 | 启用前必须 |
| `TC-LLM-004` | tool call/结果/重复调用防护 | 必须 | 必须 | 启用前必须 |
| `TC-LLM-005` | thinking + tool reasoning state replay | 必须 | 必须 | 按能力 |
| `TC-LLM-006` | 400/401/402/422/429/5xx/timeout 映射 | 必须 | 可控 smoke | 启用前必须 |
| `TC-LLM-007` | retry/fallback/circuit/budget/idempotency | 必须 | 故障注入 | 启用前必须 |
| `TC-LLM-008` | 日志、trace、诊断包脱敏 | 必须 | 必须 | 启用前必须 |
| `TC-LLM-009` | capability/config schema/fingerprint | 必须 | 探测 | 启用前必须 |
| `EVAL-LLM-001` | 微积分抽取/关系/问答质量成本延迟 | fixture runner | 必须 | 路由前必须 |

Provider fixture 必须保存：请求 canonical hash、脱敏 wire request/response、HTTP 状态/头 allowlist、期望 canonical result/error、采集日期、文档版本和 fixture schema。不得保存真实用户内容和密钥。

---

## 10. 参考实现和官方依据

官方接口依据：

- [DeepSeek Chat Completion](https://api-docs.deepseek.com/api/create-chat-completion)
- [DeepSeek Thinking Mode](https://api-docs.deepseek.com/guides/thinking_mode)
- [DeepSeek JSON Output](https://api-docs.deepseek.com/guides/json_mode/)
- [DeepSeek Tool Calls](https://api-docs.deepseek.com/guides/tool_calls)
- [DeepSeek Error Codes](https://api-docs.deepseek.com/quick_start/error_codes/)
- [DeepSeek Rate Limit & Isolation](https://api-docs.deepseek.com/quick_start/rate_limit)
- [Kimi API 概述](https://platform.kimi.com/docs/api/overview)
- [Claude Messages API](https://platform.claude.com/docs/en/api/messages/create)
- [OpenAI Model Guidance](https://developers.openai.com/api/docs/guides/latest-model)

可参考代码：

- [Kimi Code Provider Configuration](https://github.com/MoonshotAI/kimi-code/blob/main/docs/en/configuration/providers.md)：参考 protocol type 与 model capability 分层、reasoning field 兼容；不直接采用其 CLI session/credential 语义。
- [Pydantic AI OpenAI Model Adapter](https://github.com/pydantic/pydantic-ai/blob/main/pydantic_ai_slim/pydantic_ai/models/openai.py)：参考 canonical parts、provider profile、usage 和 thinking mapping；不让框架模型成为本项目领域 DTO。
- [LiteLLM](https://github.com/BerriAI/litellm)：参考厂商异常映射、预算、路由与 proxy 测试；首版不引入其 proxy 作为必需运行时，避免增加一层故障和安全边界。

引入任何第三方代码前仍须记录 tag/commit、许可证、NOTICE、SBOM 和本项目修改；参考思想不等于允许复制。

---

## 11. 实施顺序

```text
1. 冻结 canonical DTO、capability enum、错误码和配置 schema
2. 实现 mock adapter 与全部失败 fixture
3. 实现 openai_chat protocol adapter
4. 实现 DeepSeek vendor profile 和非流式文本/JSON
5. 增加 streaming、thinking、tool reasoning replay
6. 增加 retry/circuit/budget 与受控 fallback
7. 运行 DeepSeek live smoke 和微积分金标
8. 批准 DeepSeek deployment，接入 AI 草案流水线
9. 按实际需求依次实现 OpenAI Responses、Kimi、Anthropic Messages
```

第 1–7 步没有证据时，不得把 DeepSeek 标为“已支持”；其他 Provider 不能因为配置文件中存在占位项就对用户宣称可用。

---

## 12. 签字检查表

- [x] 首家 LLM Provider 决策为 DeepSeek；
- [x] DeepSeek 稳定协议和默认 endpoint 已定义；
- [x] OpenAI/Kimi/Claude 协议扩展缝已定义；
- [x] 非敏感 Provider 与 model policy 配置已版本化；
- [x] 错误、重试、回退、熔断和定位顺序已定义；
- [x] 测试矩阵与 live test 启用条件已定义；
- [ ] canonical contract 已实现并通过单元测试；
- [ ] DeepSeek API Key 已进入受控 secret store；
- [ ] DeepSeek live smoke 已通过并形成测试报告；
- [ ] 微积分金标、成本与延迟门已批准；
- [ ] `RB-PROV-001` 已演练；
- [ ] DeepSeek deployment 已由 QA 批准为 enabled。

**当前结论：兼容架构和配置基线已经建立；真实 DeepSeek 兼容性仍须在产品代码、受控 API Key、live smoke 和金标评测完成后才能声明。**
