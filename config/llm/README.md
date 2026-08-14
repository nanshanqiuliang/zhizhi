# LLM 配置说明

本目录是非敏感、多 Provider 兼容配置的版本化事实源：

- `providers.yaml`：协议、端点、secret reference、模型 alias、能力和网络韧性；
- `model-policies.yaml`：task profile、能力需求、路由、预算、重试和回退；
- `schema/*.schema.json`：配置结构契约。

当前只有 `mock` 为 enabled。DeepSeek 是首要真实 Provider，但必须等产品代码、受控密钥、`TC-LLM-001..009`、`EVAL-LLM-001` 和 `RB-PROV-001` 演练全部通过后才能改为 enabled。

进度（WORK-2026-007，第 7 步离线第 1 期，`b2e215b`）：canonical LLM contract v1（`docs/contracts/llm.v1.schema.json`）已冻结并生成 Python runtime artifact；`knowledge_tree_infrastructure/llm/` 已实现 frozen DTO、稳定错误码（`LlmErrorCode` 15 码）、能力校验与 fingerprint、退避/预算/熔断纯函数、deployment 路由与确定性 mock adapter；`TC-LLM-001..009` 的 mock 必须部分已执行（56/56）。OpenAI Chat Completions 协议适配器与 DeepSeek vendor profile（实施顺序 3–6）未开始；真实 live smoke 与金标（顺序 7）待 owner 提供受控 API Key 与预算。

禁止把 API Key 写入本目录。开发隔离任务通过 `env://DEEPSEEK_API_KEY` 解析；桌面/运营使用系统 keychain/Stronghold 引用。模型和端点变更必须同时更新兼容基线、开发日志、测试证据和配置 fingerprint。

