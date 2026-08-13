# 开发日志

> 用途：按时间记录已发生的技术变化、验证和遗留风险。计划项请写入 `ENGINEERING_PLAN.md`。

## 2026-08-13 — 建立流程基线

- 状态：已形成文档，未开始实现。
- 关联：WORK-2026-001。
- 变化：新增全生命周期开发/测试/发布/运维总纲和治理模板。
- 接口/数据库/Prompt 版本：尚未建立。
- 验证：仅进行 Markdown 静态复核；没有代码或运行测试。
- 遗留风险：仓库、负责人、金标数据、CI 和遥测尚未落地。

## 2026-08-13 — 建立本地仓库与最小质量门

- 关联 ID：WORK-2026-006、NFR-2026-005、NFR-2026-006、RISK-2026-004。
- 实际变化：初始化本地 Git；建立 `main` 基线和工作分支；新增 `AGENTS.md`、模块目录、uv/pnpm 锁文件、离线仓库/LLM 配置/秘密校验、最小 React 状态页和声明式 CI workflow。
- 影响模块/接口/schema/migration/prompt：只建立组合入口和包边界；复用 `config/llm/schema`，没有业务 API、数据库 migration、GraphPatch/Anchor 或 prompt 版本。
- 兼容性：Python 3.12、Node 24、pnpm 11 本地通过；TypeScript 固定到 6.0.2 以匹配 typescript-eslint；Rust/Tauri 未安装且未宣称通过。
- 验证与证据：提交 `bd66e8b`；`TR-20260813-002`；Python 10/10、Web 1/1、schema/秘密/type/lint/peer/build 与桌面/390px 浏览器检查通过。
- 性能/安全/运维影响：普通门禁禁止 live LLM；秘密扫描只报告位置和规则；无真实用户数据或网络模型费用。
- 回滚：回退 `bd66e8b` 可恢复到文档基线 `0a2a64d`；不删除用户原始文档。
- 遗留风险与下一步：远端治理、独立 QA、Rust/Tauri、许可证、SBOM/provenance、金标许可和核心 contract 尚未完成。

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

## 2026-08-13 — 建立微积分金标 fixture 并完成作者验证

- 关联 ID：WORK-2026-004、NFR-2026-002、NFR-2026-008、RISK-2026-001、RISK-2026-005。
- 实际变化：新增 MIT OCW RES.18-001 第 2 章 hash-pinned PDF、dataset card、NOTICE、作者/独立复核记录、`calculus-gold.v1` schema、30 个概念、40 条先修关系、50 个页级锚点，以及来源/许可/语义/DAG 校验 CLI。
- 影响模块/接口/schema/migration/prompt：仅新增 `evals/calculus-v1` 的 eval fixture contract；不创建产品 Anchor/GraphPatch contract、数据库 migration、API 或 prompt。
- 兼容性：新增锁定依赖 pypdf 6.15.0；数据集版本 `1.0.0-draft.1`，状态 `author_reviewed`，独立复核前禁止 `approved`。
- 验证与证据：实现提交 `e918fdf`；`TR-20260813-003` CONDITIONAL GO；金标合同/变异 14/14、仓库 Python 24/24、Web 1/1、完整本地门通过；官方 PDF 重下字节/hash 一致；7 页 144 DPI 渲染抽检清晰。
- 性能/安全/运维影响：无 LLM、数据库或用户数据；validator 拒绝路径逃逸、hash/许可漂移、加密 PDF、活动文档动作、嵌入文件、无证据边、环和伪批准状态；许可限制为 CC BY-NC-SA 4.0 非商业/署名/ShareAlike。
- 回滚：回退 `e918fdf` 可移除数据集和校验器；不得通过删除 NOTICE/来源记录绕过上游限制。
- 遗留风险与下一步：独立学科复核者和 QA 尚未指派；不得关闭 WORK-2026-004、进入产品代码或运行真实 DeepSeek。页级 fixture 也不证明 bbox/区域指标。

## 2026-08-13 — 建立微积分金标独立复核硬门

- 关联 ID：WORK-2026-004、NFR-2026-002、NFR-2026-008、RISK-2026-001、RISK-2026-005。
- 实际变化：新增 `independent-review.v1` schema、30/40/50 全量待签复核包、复核指南、领域校验器和 CLI；仓库默认门开始验证复核包，并在出现完成态时自动强制完整双签校验。
- 影响模块/接口/schema/migration/prompt：仅扩展 `evals/calculus-v1` 的 eval/review contract 和 CI 本地门；没有产品 API、数据库 migration、GraphPatch/Anchor 或 prompt 变化。
- 兼容性：复核包以排除可变审批元数据后的内容 SHA-256 绑定数据集；真实内容漂移会强制重新复核，最终签字元数据更新不会产生循环摘要。
- 验证与证据：实现提交 `232d0cd`；`TR-20260813-004` CONDITIONAL GO；43/43 Python、1/1 Web 和完整本地门通过；待签普通门通过，完成门按预期以 `calculus_review_invalid`/退出 1 阻断。
- 性能/安全/运维影响：无网络、LLM、数据库或用户数据；防止缺项、重复、摘要漂移、自签、自行裁决、未解决分歧、签字逆序和审批状态不同步。
- 回滚：回退 `232d0cd` 可移除复核门；这会重新暴露误批准风险，因此不得据此绕过 WORK-2026-004 关闭条件。
- 遗留风险与下一步：自动门不提供学科判断。项目负责人仍需指派两名不同人员完成学科复核与 QA；真实签字后创建新的增量报告，不改写已冻结报告。

## 2026-08-13 — 产品需求改为 AI Harness 自动机器复核

- 关联 ID：CHG-2026-001、ADR-0015、REQ-2026-001..005、NFR-2026-009、WORK-2026-004、WORK-2026-010。
- 实际变化：用户明确首版为个人、本地优先 AI Agent App；后续学科复核和 QA 由 harness 编排的职责隔离 AI 子 Agent执行，可调用受控本地检索/Web Search，必要时启动第三个裁决 Agent。
- 影响模块/接口/schema/migration/prompt：新增 PRD v0.2、AI review 角色卡、v2 machine-attestation 架构提案和 harness 工作项；v1 真人签字 contract 与已冻结 TR-003/004 原样保留，不用 AI 名称伪签。
- 兼容性：v2 将使用新 schema/version 和 content-addressed artifact；机器审查状态不映射为无修饰真人 `approved`，owner risk acceptance 单独建模。
- 验证与证据：本轮由 AI 学科设计子 Agent和 AI QA 设计子 Agent分别只读审查；共同要求 run/prompt/context 隔离、QA 绑定冻结学科 artifact、同源降级、证据 ledger、失败关闭和硬不变量不可豁免。实现测试尚未执行。
- 性能/安全/运维影响：未来每次自动复核至少两个模型运行，需要预算/超时/搜索轮次上限；Agent 只读最小权限，网页/PDF 指令不可信，不保存隐藏推理或全文镜像。
- 回滚：关闭 v2 review policy，保留所有 v1/v2 artifact 和失败 attempt，回到 `inconclusive`/用户手工检查；不得删除失败证据或回写伪批准。
- 遗留风险与下一步：当前继续 WORK-2026-004，先以失败测试实现 v2 contract、mock harness 和注入/越权/漂移 fixture；真实 Provider/Web 仍受 WORK-2026-007/008 gate 阻断。

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
