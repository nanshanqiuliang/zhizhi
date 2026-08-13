# 开发日志

> 用途：按时间记录已发生的技术变化、验证和遗留风险。计划项请写入 `ENGINEERING_PLAN.md`。

## 2026-08-13 — 建立流程基线

- 状态：已形成文档，未开始实现。
- 关联：WORK-2026-001。
- 变化：新增全生命周期开发/测试/发布/运维总纲和治理模板。
- 接口/数据库/Prompt 版本：尚未建立。
- 验证：仅进行 Markdown 静态复核；没有代码或运行测试。
- 遗留风险：仓库、负责人、金标数据、CI 和遥测尚未落地。

## 2026-08-13 — 建立多 LLM 兼容基线（DeepSeek 优先）

- 状态：兼容架构、非敏感配置和运维契约已形成；没有产品代码或真实 API 联调。
- 关联：WORK-2026-007、NFR-2026-006、ADR-0013（待正式建仓拆分）。
- 实际变化：新增根目录多 LLM 特殊基线；首家真实 LLM Provider 决策为 DeepSeek；预留 OpenAI Responses、Kimi Chat Completions 和 Anthropic Messages。
- 配置：新增 `config/llm/providers.yaml` 与 `config/llm/model-policies.yaml` v1；DeepSeek 保持 `enabled: false`，mock 为唯一已配置可用项。
- 兼容性：定义 canonical DTO、protocol adapter、vendor profile、capability snapshot、错误映射、有界重试、回退和熔断边界。
- 验证：官方文档核对和 Markdown/YAML 静态校验；没有 API Key、live smoke、金标或运行测试。
- 安全/运维：API Key 仅通过 secret reference；禁止记录 prompt/response/reasoning 正文；新增 `RB-PROV-001` 草案。
- 回滚：删除新增配置/基线并恢复原文档引用即可；尚无运行数据或 migration。
- 遗留风险：Embedding Provider、金额预算、live smoke、微积分金标、Provider adapter 和 QA 批准均未完成。

## 2026-08-12 — 建立总体架构技术基线

- 状态：已形成文档，未开始实现。
- 变化：定义模块化单体、本地 SQLite/云端 PostgreSQL、GraphPatch、Anchor、任务和可观测性方向。
- 验证：文档静态复核；没有原型或性能证据。
- 遗留风险：所有工程初值有待阶段 0 校准。

---

## 新条目模板

```markdown
## YYYY-MM-DD — <标题>

- 关联 ID：
- 实际变化：
- 影响模块/接口/schema/migration/prompt：
- 兼容性：
- 验证与证据：
- 性能/安全/运维影响：
- 回滚：
- 遗留风险与下一步：
```
