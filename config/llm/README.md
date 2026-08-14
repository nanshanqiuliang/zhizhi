# LLM 配置说明

本目录是非敏感、多 Provider 兼容配置的版本化事实源：

- `providers.yaml`：协议、端点、secret reference、模型 alias、能力和网络韧性；
- `model-policies.yaml`：task profile、能力需求、路由、预算、重试和回退；
- `schema/*.schema.json`：配置结构契约。

当前只有 `mock` 为 enabled。DeepSeek 是首要真实 Provider，但必须等产品代码、受控密钥、`TC-LLM-001..009`、`EVAL-LLM-001` 和 `RB-PROV-001` 演练全部通过后才能改为 enabled。

进度（WORK-2026-007/008，第 7 步）：canonical LLM contract v1（`docs/contracts/llm.v1.schema.json`）已冻结并生成 Python runtime artifact；`knowledge_tree_infrastructure/llm/` 已实现 frozen DTO、稳定错误码（`LlmErrorCode` 15 码）、能力校验与 fingerprint、退避/预算/熔断纯函数、deployment 路由、确定性 mock adapter（WORK-2026-007），以及 DeepSeek OpenAI Chat Completions 协议适配器 + vendor profile + stdlib 传输 + resilience 接线（WORK-2026-008）；`TC-LLM-001..009` mock 部分 56/56、TC-DS-001..005 21/21、真实 live smoke 5/5（约 817 token）。DeepSeek deployment 仍 `enabled: false`：正式启用待微积分金标评测 `EVAL-LLM-001`、`RB-PROV-001` 演练与 QA 批准。

禁止把 API Key 写入本目录。开发隔离任务通过 `env://DEEPSEEK_API_KEY` 解析；桌面/运营使用系统 keychain/Stronghold 引用。模型和端点变更必须同时更新兼容基线、开发日志、测试证据和配置 fingerprint。

