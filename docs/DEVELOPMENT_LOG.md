# 开发日志

> 用途：按时间记录已发生的技术变化、验证和遗留风险。计划项请写入 `ENGINEERING_PLAN.md`。

## 2026-08-14 — 实现 DeepSeek OpenAI Chat Completions adapter 与受控 live smoke（WORK-2026-008，第 7 步真实接入第 1 期）

- 关联 ID：WORK-2026-008、LLM-COMPAT-BASELINE-001、NFR-2026-006/007/008、WORK-2026-007、OPS-2026-003、TC-DS-001..005、TC-DS-LIVE-001..005。
- 实际变化：`knowledge_tree_infrastructure/llm/protocols/openai_chat.py` 实现 canonical↔OpenAI Chat Completions 双向映射（消息/角色/内容、tool_calls、`response_format=json_object`、显式 `thinking.type`、reasoning_content 工具轮回传、usage/finish_reason、SSE 流解析容忍空行/keep-alive/`[DONE]`）；`vendors/deepseek.py` 实现 DeepSeek vendor profile（endpoint、模型 ID 快照、HTTP 错误映射按基线 4.6）+ `DeepSeekLlmAdapter`（有界重试/退避/熔断接线，auth/balance 立即熔断不重试）；`http_client.py` 用 stdlib `urllib` 传输（POST JSON + SSE 逐行，单 read 超时；Python 3.12 socket 不接受 timeout tuple）；`tests/e2e/test_deepseek_live_smoke.py` 在 `RUN_LIVE_LLM_TESTS=1` + `DEEPSEEK_API_KEY` 双重门控下跑真实 smoke。
- 影响模块/接口/schema/migration/prompt：扩展 `knowledge_tree_infrastructure/llm/`（新增 protocols/vendors/http_client 子模块 + 两个测试文件）；无 canonical contract/migration/prompt 变更；config/llm YAML 语义不变（模型 ID 快照与真实 `/models` 探测一致）。
- 兼容性：传输不依赖厂商 SDK；thinking 模式禁发 sampling 参数；reasoning_content 只临时回传不展示/不落盘；SSE 断流返回 `provider_stream_incomplete` 不续写中间 delta。
- 验证与证据：红灯 `d6a7444`（1 collection error）；实现 `d81c574` + 修复 `a80f43d`；离线契约 21/21（TC-DS-001..005）；live smoke 5/5（真实 DeepSeek：text/JSON/thinking/tool/stream，约 817 token，费用远低于 3 元）；全仓 pytest 335/335 + 5 skipped；validator/Ruff/strict mypy（25 文件）/contracts-ts drift/pnpm build 全绿。
- 性能/安全/运维影响：live 仅 env 门控运行；密钥只经环境变量进入 composition root，绝不落盘/日志/git；错误 details 与 fixture 脱敏；退避 500→1000→2000ms；预算受 max_tokens/attempt 约束。
- 回滚：回退 `d81c574`/`a80f43d` 即回到 mock-only；DeepSeek deployment 保持 `enabled: false`；红灯与 evidence 保留。
- 遗留风险与下一步：微积分金标评测 `EVAL-LLM-001` 与质量/成本/延迟门、`RB-PROV-001` 演练、DeepSeek deployment 正式批准（`enabled: true`）未做；AI 草案流水线接入（第 8 步）未开始；职责隔离 QA 待执行。

## 2026-08-14 — 冻结 canonical LLM contract 与 mock adapter（WORK-2026-007，第 7 步离线第 1 期）

- 关联 ID：WORK-2026-007、LLM-COMPAT-BASELINE-001、REQ-2026-006、NFR-2026-001、TC-LLM-001..009、WORK-2026-006。
- 实际变化：新增 `docs/contracts/llm.v1.schema.json` 作为 canonical LLM contract 唯一手写来源（ProviderId/ProtocolId/MessageRole/ContentPartKind/FinishReason/CapabilityName/LlmErrorCode 15 码/ContentPart/CanonicalMessage/ToolDefinition/CanonicalToolCall/CanonicalUsage/Budget/TraceContext/GenerationRequest/GenerationResult/CapabilitySet）；`packages/contracts-ts/scripts/generate.mjs` 扩展为同时生成 `_generated_llm_v1_schema.py` 并在 `--check` 检测漂移（TS 侧待第 8 步 Web 消费时生成）；contracts-py 新增 `llm_v1.py`（schema-backed 校验器，冷启动无 repo I/O）；`knowledge_tree_infrastructure/llm/` 新增 canonical（frozen DTO 无厂商 SDK 类型）/errors（稳定错误码）/capabilities（能力校验 + sha256 fingerprint）/resilience（确定性退避 + AttemptBudget + CircuitBreaker）/router（deployment 解析，纯 dict 输入）/mock（确定性 MockLlmAdapter：文本/JSON/流式/tool/thinking/失败注入）。
- 影响模块/接口/schema/migration/prompt：新增 LLM canonical contract v1 与生成 artifact、infrastructure llm 子包；扩展 repository 门（`load_llm_contract_schema` + REQUIRED_PATHS）；无 migration/prompt；graph v1 contract 不变；config/llm YAML 语义不变。
- 兼容性：enum 全部从 schema 派生（无第二份手写 enum）；`["string","null"]` + format 陷阱以 `anyOf` 规避；运行时 DTO 往返经 canonical 校验。
- 验证与证据：红灯 `b5747ec`（2 collection errors）；实现 `b2e215b`；契约/安全定向 56/56（TC-LLM-001..009 mock 必须部分）；全仓 pytest 314/314；repository validator、Ruff、scripts + strict package mypy、contracts-ts drift/tsc、Web 32/32、pnpm build 全绿。
- 性能/安全/运维影响：无网络、无密钥解析、无真实费用；错误 details 与 fixture 脱敏（无正文/密钥/reasoning）；401/402 不重试、auth/balance 立即熔断、退避 500→1000→2000ms full jitter 确定性。
- 回滚：回退 `b2e215b` 即回到无 LLM port 状态；不影响 graph contract、持久化、导入、查看器与第 6 步全部已验证能力；红灯保留。
- 遗留风险与下一步：协议适配器（openai_chat_completions）与 DeepSeek vendor profile 的 HTTP 实现（实施顺序 3–6）未开始；DeepSeek live smoke 与金标（实施顺序 7）待 owner 提供受控 API Key 与预算（WORK-2026-008）；TS enum 与 Web 接入属第 8 步；mock 不是真实 DeepSeek 支持。

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

## 2026-08-13 — 实现微积分 AI 机器复核 v2 离线原型

- 关联 ID：WORK-2026-004、ADR-0015、REQ-2026-002..005、NFR-2026-009、RISK-2026-010..012。
- 实际变化：以失败测试起步新增 `calculus-machine-review.v2` JSON Schema、版本化角色 prompt/context/tool policy、content-addressed subject/QA/裁决 artifact、证据 ledger、只读 ReplaySearchProvider 和稳定 CLI；默认仓库门开始复放同源 mock 双角色审查。
- 影响模块/接口/schema/migration/prompt：仅扩展 `evals/calculus-v1` prototype contract 和 `scripts` 离线工具；三角色 prompt/context 版本为 `*.v2.mock.1`；无产品 API、数据库 migration、GraphPatch/Anchor 或真实 LLM SDK。
- 兼容性：v1 真人签字 contract/历史证据原样保留；mock/replay 无论模型相关性均固定为 `inconclusive`/非产品可用，不能进入 `machine_reviewed`/`machine_verified` 或由 owner 风险接受提升；真实状态转换留给后续受控实现。
- 验证与证据：初版 TC-AIREV 原型测试 28/28、完整本地门 71/71 Python/1 Web；学科子 Agent随后提出证据自证、claim 绑定、范围和裁决 ledger 缺陷，修复后当前 75/75 Python 通过，完整增量门与正式 TR 待完成。
- 性能/安全/运维影响：无网络、模型费用、秘密、数据库或用户内容；提示注入、工具越权、输入漂移、伪引用、低置信 accept、共享 run/session/prompt/context、未裁决分歧、超时和预算失败均失败关闭或转 inconclusive。
- 回滚：回退本轮实现提交可禁用 v2 prototype；保留 v1 数据、历史 TR 和所有失败证据，不得据此启用真人 `approved` 或真实 Provider。
- 遗留风险与下一步：冻结实现提交和不可变 TR，执行隔离 AI 学科/QA 复核；随后再决定 WORK-2026-004 是否可关闭。真实联网与产品化状态机仍归 WORK-2026-007/008/010。

## 2026-08-13 — 修复 AI 学科子 Agent首轮复核争议

- 关联 ID：WORK-2026-004、RISK-2026-010..012、TC-AIREV-001..010。
- 实际变化：根据冻结提交 `73a74da` 的隔离 AI 学科 machine attestation，将 replay evidence 改为绑定冻结 PDF 页文本 hash；新增不可误读的 mock-only assurance 并强制 `inconclusive`；校验 finding/evidence 同 claim 与支持/反证立场；允许每个 claim 多证据；为裁决增加 evidence ledger/tool trace/confidence/uncertainty；修正数据集 2.1..2.7 范围与 a036 措辞。
- 影响模块/接口/schema/migration/prompt：`calculus-machine-review.v2` 原型 schema 向前演进；数据集升为 `1.0.0-draft.2` 并刷新 v1 pending review content hash；无产品 migration 或 live prompt。
- 兼容性：`1.0.0-draft.1` 的 TR-003/004 保持不可变历史证据；新的待签 review packet 绑定 draft.2，不改写旧报告。
- 验证与证据：新增失败测试先复现全部争议；第一次修复后 75/75 Python 通过。隔离学科 resumed audit 又发现 controlled-live assurance 组合和裁决 position 两个绕过；第二轮失败测试复现后已修复，当前 77/77 Python 通过，完整本地门、修复提交和复核重跑待执行。
- 性能/安全/运维影响：首次进程内建 PDF 页文本索引，随后按 PDF/hash 缓存；不联网，不保存全文到 artifact，只保存页 locator 与 hash。
- 回滚：回退本轮修复提交恢复初版原型，但会重新暴露误读/错绑风险，因此不得用于放行。
- 遗留风险与下一步：冻结修复提交，要求同一学科角色复核争议是否解决；再将冻结学科 attestation hash 交给隔离 QA。

## 2026-08-13 — 完成 AI 机器复核 v2 离线原型与隔离 QA 收口

- 关联 ID：WORK-2026-004、ADR-0015、REQ-2026-002..005、NFR-2026-009、RISK-2026-010..012、TR-20260813-005。
- 实际变化：隔离学科 attempt 003 接受 `db0831b` 后，独立 QA attempt 001 对冻结提交发现 3 P1/3 P2；以 8 个红灯回归修复 live 重标、trace 缺失/篡改、伪 owner、claim 替换、tool-policy 自证和裁决 session 复用，形成 `ae834d9`。QA attempt 002 复放全部缺陷及额外组合后 PASS，未发现新 P0/P1/P2。
- 影响模块/接口/schema/migration/prompt：subject/QA trace contract 固定为每个 120 claims 精确覆盖；validator 把 trace 绑定到 claim/query/result/tool/status，把 provenance 绑定到有效 role policy/harness，并要求三角色 session 隔离。当前 prototype 显式拒绝 `controlled_live` 和任何 owner acceptance artifact；无数据库 migration 或 live prompt。
- 兼容性：v1 `TR-20260813-003/004` 和 QA FAIL attempt 001 原样保留；attempt 002 通过 `supersedes` 追加而非改写。mock 仍为 `inconclusive`/`product_eligible=false`，不映射为人类 `approved`。
- 验证与证据：`TR-20260813-005`；targeted 39/39，完整 pytest 84/84、Web 1/1；repository validator、Ruff format/lint、mypy、pnpm frozen install/peers/check/build 全通过。学科/QA 同源独立性无外部证明，保守披露 `correlated_review`。
- 性能/安全/运维影响：无网络、模型费用、秘密、数据库、真实用户内容或常驻进程；120-claim trace 只做本地确定性 replay。任何真实 Provider、Web Search 或 owner 身份使用继续失败关闭。
- 回滚：回退 `ae834d9` 会重新暴露 QA 已证明的状态/证据绕过，不得用于放行；如需禁用，整体关闭 v2 policy/harness 并保留所有失败/通过 artifact。
- 遗留风险与下一步：WORK-2026-004 的离线 prototype 已完成；真实 Provider/live eval 归 WORK-2026-007/008，认证 owner/产品状态机/通用 harness 归 WORK-2026-010，Anchor/GraphPatch 产品 contract 归 WORK-2026-005。RISK-2026-010..012 保持 open。

## 2026-08-13 — 建立面向用户的自然语言开发路线与进度口径

- 关联 ID：PLAN-ROOT、WORK-2026-002、WORK-2026-005、WORK-2026-007、WORK-2026-010。
- 实际变化：将 Proposal/架构中的技术阶段转换为第 0–11 步用户路线，分别描述产品目标、完成标志、当前状态和可见里程碑；约定用户说“继续推进”时固定报告当前自然语言步骤、本步进度、MVP 粗略进度、本轮成果、验证和下一动作。
- 影响模块/接口/schema/migration/prompt：仅新增 `docs/USER_FACING_DEVELOPMENT_ROADMAP.md` 并链接工程计划、README 与恢复检查点；无产品代码、schema、migration 或 prompt 变化。
- 兼容性：技术事实仍以工程计划、工作项、提交和测试报告为准；百分比只依据已提交且可验证的产品能力，不把文档/测试数量误算为 App 功能。
- 验证与证据：路线与 Proposal 的 2 周尖峰、8–12 周个人 MVP、16–24 周 Beta，以及架构阶段 0–3/实现顺序逐项对齐；仓库文档链接和默认门复验。
- 性能/安全/运维影响：无运行时影响；真实 Provider/Web 与未认证 owner acceptance 保持关闭。
- 回滚：回退本条文档提交即可；不影响已冻结的 WORK-2026-004 证据。
- 遗留风险与下一步：当前为自然语言第 1 步（约 40%），MVP 粗略 10%–15%；下一次“继续推进”先完成 WORK-2026-002 的首版决策记录，再进入第 2 步 Anchor/GraphPatch contract。

## 2026-08-14 — 冻结个人笔记 App 首版产品边界

- 关联 ID：WORK-2026-002、ADR-0016、REQ-2026-006..010。
- 实际变化：把架构第 21 节十项待决问题逐项映射为首版决定或失败关闭边界；PRD 升为 v0.3，冻结 Windows 单用户、本地核心可离线、Markdown/TXT/PDF 首发、AI 持久修改默认预览确认、四维锁定、标准概念粒度和 workspace 备份/逻辑删除承诺。
- 影响模块/接口/schema/migration/prompt：只更新产品/架构/计划事实源；为后续 Anchor/GraphPatch contract 提供输入，不创建产品 schema、migration 或 prompt。
- 兼容性：不改变 WORK-2026-004 历史 evidence；PPTX/DOCX/OCR、多平台、云端多人和完整 Obsidian 导入明确后置。
- 验证与证据：TC-PLAN-001..003 的静态映射、仓库门和独立一致性复核待执行；当前自然语言第 1 步推进到约 90%。
- 性能/安全/运维影响：核心功能目标为无 Docker 本地运行；金额预算、Embedding、真实 Provider/Web、远端仓库/许可证仍未批准并保持禁用/未发布。
- 回滚：范围改变必须新建 superseding ADR/CHG，不原位把已接受默认值改成另一含义。
- 遗留风险与下一步：完成独立一致性复核并提交 WORK-2026-002；随后进入自然语言第 2 步，创建 Ready 的 WORK-2026-005 并从失败契约测试开始。

## 2026-08-14 — 修正首版边界的 owner 批准与证据状态

- 关联 ID：WORK-2026-002、ADR-0016、REQ-2026-001、REQ-2026-006..010。
- 实际变化：隔离 QA 对冻结提交 `8ff376d` 返回 FAIL（1 P1/2 P2）；产品边界本身 10/10 完整，但 PRD/ADR 把 workspace owner 的正式批准写得过早，提交中的工作项/计划/追踪状态仍写“待提交/待验证”，且 correlated-review 描述与当前失败关闭策略不一致。
- 影响模块/接口/schema/migration/prompt：将 PRD v0.3 恢复为 `in_review`、ADR-0016 恢复为 `proposed`，明确安全默认值只授权可回滚离线 prototype；同步工作项、工程计划、路线图、追踪矩阵、checkpoint 和 QA 证据。不修改运行 contract、migration 或 prompt。
- 兼容性：保留 `8ff376d` 作为不可变决策基线和首次 FAIL，不改写历史证明；后续通过 superseding 提交与 QA attempt 002 收口。
- 验证与证据：`evidence/TR-20260814-001/ai-product-qa-attempt-001.md`；修正后的 repository validator、Ruff、mypy、84/84 Python、pnpm frozen install/peers、Web 1/1 和生产构建通过，复审待执行。
- 性能/安全/运维影响：无运行时影响；真实 Provider/Web、用户数据、数据库与 owner 风险接受继续关闭。
- 回滚：不得回到伪造 owner 批准语义；若默认边界改变，应创建 superseding ADR/CHG。
- 遗留风险与下一步：要求同一 QA 角色审查本 superseding 提交的完整 SHA；通过后将 WORK-2026-005 改为 Ready 并以失败契约测试启动第 2 步。

## 2026-08-14 — 首版开发默认值 QA 通过并开放离线 GraphPatch 尖峰

- 关联 ID：WORK-2026-002、WORK-2026-005、ADR-0016、TR-20260814-001。
- 实际变化：职责隔离 QA attempt 002 对 `10f249b3021da1577aa17eb114d3b44c20a2b0a2` 给出 PASS，attempt 001 的 1 P1/2 P2 全部关闭且原始失败证据保留；WORK-2026-005 由 `proposed` 提升为 `ready`，自然语言开发进入第 2 步。
- 影响模块/接口/schema/migration/prompt：本阶段仅固化验证报告和 Ready 状态，尚未新增 Anchor/GraphPatch schema、validator、migration 或 prompt。
- 兼容性：PRD v0.3 继续 `in_review`、ADR-0016 继续 `proposed`；QA PASS 不冒充 workspace-owner 精确批准、阶段出口或发布授权。
- 验证与证据：`TR-20260814-001`；10/10 决策映射、84/84 Python、Web 1/1 和完整本地门通过；QA attempt 002 为 0 P0/P1/P2、无新发现、`correlated_review`。
- 性能/安全/运维影响：无运行时影响；无网络、Provider、用户数据、数据库或费用。
- 回滚：回退 Ready/证据收口提交即可停止尖峰；不得删除失败 attempt 或回退到伪 owner 批准表述。
- 遗留风险与下一步：切换 `feature/WORK-2026-005-anchor-graphpatch-v1`，从失败 Anchor/GraphPatch schema 契约测试开始；Gate A 和精确 owner 验收仍开放。

## 2026-08-14 — 建立 Anchor/GraphPatch v1 红灯契约基线

- 关联 ID：WORK-2026-005、TC-GRAPH-001..005、TC-ANCH-001。
- 实际变化：新增 Anchor、CourseGraph、GraphPatch 正/负契约测试，以及 preview/确认、revision、DAG、跨课程端点、四维锁和 AI evidence 安全测试；测试路径加入 contracts/domain 源目录。
- 影响模块/接口/schema/migration/prompt：只新增测试和测试导入路径；尚未创建 schema、领域实现、migration 或 prompt。
- 兼容性：既有 84 个 Python 测试未被改写；本红灯目标套件在收集阶段因两个预期公共 API 缺失而失败。
- 验证与证据：`uv run pytest tests/contract/test_graph_contracts.py tests/unit/test_graph_patch.py tests/security/test_graph_patch_security.py -q`，exit 1，3 个收集错误；`ContractValidationError`、`GraphPatchError` 尚不存在。
- 性能/安全/运维影响：无运行时、网络、数据库、Provider、用户数据或费用。
- 回滚：回退本红灯提交即可移除未实现测试；不得以删除测试替代实现关键不变量。
- 遗留风险与下一步：实现 JSON Schema 单一事实源、schema-backed Python contract API 和纯领域 preview；再补全六类 operation 与属性/容量测试。

## 2026-08-14 — 实现 Anchor/GraphPatch v1 纯领域 prototype

- 关联 ID：WORK-2026-005、ADR-0001、ADR-0004、ADR-0006、ADR-0012、TC-GRAPH-001..005、TC-ANCH-001。
- 实际变化：新增 canonical Draft 2020-12 schema、schema-backed Python contract API、schema 生成的 TypeScript enum、纯 GraphPatch preview，以及六类 operation、确认、revision、四维锁、DAG/cycle path、AI evidence/origin 防伪和输入不可变验证。
- 影响模块/接口/schema/migration/prompt：新增 `knowledge-tree-graph.v1.schema.json` 和 GraphPatch/Anchor/CourseGraph v1 prototype；新增 Hypothesis 开发依赖与 CI schema/type drift 门；无 migration、API 或 prompt。
- 兼容性：旧 placeholder TS contract 被生成入口替换；前端/存储尚未消费该 contract。新增边必须绑定 source/target revision；AI update 携带 operation evidence IDs。
- 验证与证据：红灯 `44b6233`；该冻结点实际为专项 49/49 加仓库集成 4/4，曾误写为“目标 53/53”，由后续 QA 指出并更正；Ruff、严格 mypy、schema self-check、repository validator 和 TypeScript generation drift/tsc 通过。
- 性能/安全/运维影响：无网络/文件写/数据库/Provider/用户数据；错误 details 只含 rule/ID/revision/cycle path，不含正文。首轮实现仍有冷启动 schema 文件读，已在后续 superseding 修复中移除；500 节点容量初值仍待产品基准测试。
- 回滚：回退实现提交和 schema/generator 即可禁用未接入产品的 prototype；不得回退红灯测试来规避不变量。
- 遗留风险与下一步：完整门、500 节点线性验证、冻结实现 SHA 和 QA；真正 persistence/operation log/inverse/undo/API/UI/resolver 仍后置。

## 2026-08-14 — 修复 GraphPatch 运行时 schema I/O 并重交 QA

- 关联 ID：WORK-2026-005、TR-20260814-002、TC-GRAPH-001。
- 实际变化：职责隔离 QA attempt 001 对 `a25470c` 返回 FAIL（1 P1/1 P2）：合同冷启动间接读取仓库 JSON Schema，且三文件专项测试 49 项被误记为 53 项。`1278e79` 先以拦截 `Path.read_text` 的失败测试复现；`5ff02a4` 令现有 generator 从 canonical JSON Schema 生成 Python runtime artifact，并把它纳入 drift check。
- 影响模块/接口/schema/migration/prompt：canonical JSON Schema 仍是唯一手工事实源；新增的是确定性派生产物，不新增/手写第二套 enum。Python 合同公共 API 和 GraphPatch 语义不变；无 migration/API/prompt。
- 兼容性：安装后运行不再依赖仓库 `docs/` 布局；TypeScript 与 Python 生成物必须同时与 canonical schema 一致。
- 验证与证据：失败 attempt 保存在 `evidence/TR-20260814-002/ai-graph-qa-attempt-001.md`；修复后专项 50/50、仓库集成 4/4、全仓 Python 136/136、Web 1/1，repository validator、Ruff、两层 mypy、生成漂移/tsc、locked installs/peers 和 build 全通过。
- 性能/安全/运维影响：GraphPatch/contract 冷启动不再文件 I/O；仍无网络、数据库、Provider、用户数据或常驻进程。
- 回滚：不得回退到运行时读取仓库 schema 的实现；若生成链异常，应让 drift gate 失败并停止交付，不得手改派生 schema。
- 遗留风险与下一步：职责隔离 QA attempt 002 已对 `b946855` PASS，0 P0/P1/P2、无新发现；`TR-20260814-002` 已生成并把 WORK-005 移入 verification。正式 ADR/owner 接受仍待阶段出口；operation log/inverse/undo 属于下一独立工作项。

## 2026-08-14 — 完成纯领域修改回放与 LIFO 撤销/重做 prototype

- 关联 ID：WORK-2026-011、ADR-0005、REQ-2026-008、TR-20260814-003。
- 实际变化：在 `2425718` 两组预期 ImportError 红灯后，`4fc8e60` 新增不可变 GraphHistory/GraphChangeRecord/EntityDelta、语义 hash、两条记录顺序 replay 和 LIFO undo/redo；undo 后新 apply 清空 redo。history 只接受 confirmed user GraphPatch，内部 inverse 不扩展 AI/导入器公共删除权限。
- 影响模块/接口/schema/migration/prompt：新增纯领域 `graph_history.py` 和 `validate_course_graph()` 复用入口；不改 GraphPatch canonical schema、数据库或 prompt。record 只保存变化实体 before/after canonical JSON、index、revision、hash 和 digest，不保存整图、patch reason 或 actor credential。
- 兼容性：既有 GraphPatch preview 公共语义不变；history snapshot 对调用方返回副本；revision 在 apply/undo/redo 中单调递增，语义 hash 排除 revision。
- 验证与证据：history/security/property 18/18、既有 graph 50/50、全仓 Python 154/154、Web 1/1 和完整门通过；`TR-20260814-003` 的职责隔离 QA attempt 001 PASS，0 P0/P1/P2、无新发现，并主动变异 delta/digest/hash/revision/order/duplicate/LIFO/no-I/O。
- 性能/安全/运维影响：O(V+E) 内存 prototype；无文件/网络/数据库/Provider/用户数据；错误 details 不含 label/annotation 正文。
- 回滚：回退独立 history 模块/export 即可禁用，不能回退 GraphPatch 锁/DAG/确认门；失败红灯和 QA 证据保留。
- 遗留风险与下一步：ADR-0005 owner 接受、持久 operation log/周期快照、崩溃恢复和 UI history 面板未完成。自然语言第 2 步底层 prototype 收口，下一主项进入第 3 步示例数据知识树网页。

## 2026-08-14 — 实现会话内可操作知识树 Web Demo

- 关联 ID：WORK-2026-012、REQ-2026-001、REQ-2026-006、REQ-2026-008、TR-20260814-004。
- 实际变化：在 `4caa76a` 的 5/5 红灯后，`5aab0e3` 把工程状态页替换为“知枝”三栏工作台；提供 8 节点示例树、节点/笔记编辑、添加子概念、叶节点删除、pointer 拖动、自动排布、位置锁、重置和会话内 undo/redo。
- 影响模块/接口/schema/migration/prompt：仅修改 `apps/web` 和用户/工程文档；不改 canonical graph schema、Python domain、API、migration 或 prompt。Web 内存历史不冒充 WORK-2026-011 持久产品集成。
- 兼容性：桌面保持三栏，窄屏按课程→画布→详情堆叠；画布内部可横向滚动但 document 不横溢；首次移动视图居中当前节点。
- 验证与证据：Web 6/6、全仓 Python 154/154、repository validator/Ruff/mypy/locked dependencies/peers/contracts generation/check/build 全通过；浏览器 1440×900 和 390×844 的编辑/历史/拖动/锁/layout/增删/重置、溢出和 console 验证 PASS。QA attempt 001 的移动端能力边界 P1 由 `c8c6bf9`/`fff1ce6` 关闭；attempt 002 PASS，见 `TR-20260814-004`。
- 性能/安全/运维影响：仅 8–12 节点演示规模；无网络、Provider、secret、真实用户数据、浏览器存储、文件或数据库写。界面明确“示例数据 / 仅本次会话 / AI 未连接”。
- 回滚：回退 `5aab0e3` 恢复状态页；不影响 contracts/domain 或历史证据。
- 遗留风险与下一步：刷新/关闭会丢失修改；无导入、来源跳转、AI 或安装包。QA 通过后关闭本项，并以独立 Ready 工作项从持久化/restart 红灯进入自然语言第 4 步。

## 2026-08-14 — 实现本地 SQLite 持久化工作区 prototype

- 关联 ID：WORK-2026-013、ADR-0005、REQ-2026-006、REQ-2026-008、TR-20260814-005。
- 实际变化：新增 `packages/infrastructure` 的 stdlib `sqlite3` workspace adapter：数据目录布局/校验、版本化 migration v1（`PRAGMA user_version`）、CourseGraph 原子保存/加载（复用 `validate_course_graph`）、备份（在线备份 + sha256 sidecar）、恢复（校验和 + WAL 侧车清理）、导出 JSON、purge manifest 删除、history records 落盘与 digest 防篡改 JSON 往返；CI mypy 覆盖 infrastructure。
- 影响模块/接口/schema/migration/prompt：新增 workspace adapter 与 `tests/integration|unit` 持久化测试；复用 `knowledge-tree-graph.v1` canonical schema 与 `GraphHistory` 记录语义；不修改既有 domain/contract 公共 API 语义；无 prompt 变化。
- 兼容性：Python 3.12 标准库 sqlite3 3.45.3；`_connect` 上下文管理器确保提交并关闭句柄，避免 Windows 文件锁；WAL 侧车在 restore/purge 时清理。
- 验证与证据：红灯 `1420b68`（2 个预期 collection ImportError）；实现 `8e34a40` 后目标 21/21、全仓 Python 175/175、Web 6/6、Ruff、strict mypy（contracts/domain/infrastructure）、repository validator、pnpm frozen install/peers/check/build 全通过；QA attempt 001 PASS（0 P0/P1/P2，静态推演）；本会话 live 重放八类变异全部失败关闭。
- 性能/安全/运维影响：仅测试目录写 SQLite；无网络、Provider、secret、真实用户数据或费用；错误 details 只含 rule/版本号/ID，不含正文。
- 回滚：回退 `8e34a40` 可禁用持久化 prototype；红灯测试保留，不得以删除测试替代不变量。
- 遗留风险与下一步：浏览器自动保存/API/UI 接入、FTS5 搜索、导入、加密、多进程、云端与真实 Provider 仍关闭；下一工作项从失败 persistence API 红灯进入第 4 步 UI/API 接入。

## 2026-08-14 — 实现本地持久化 API sidecar 与 Web 自动保存

- 关联 ID：WORK-2026-014、ADR-0005、ADR-0011、REQ-2026-006、REQ-2026-008、TR-20260814-006。
- 实际变化：新增 `apps/api` FastAPI composition root（loopback、CORS 精确白名单、`/api/health`、CourseGraph GET/PUT、backup，扁平化错误响应，路径遍历拒绝）；Web 端新增 `api.ts`（PersistApi、uuidv7、snapshot↔canonical 转换、http client）并接入 App（挂载加载、600ms debounce 自动保存、连接/保存状态显示、API 不可达降级）；`packages/infrastructure` 补充 `__init__.py`；CI 覆盖 apps。
- 影响模块/接口/schema/migration/prompt：新增 `apps/api` 与 Web API client；复用 graph v1 契约与 workspace adapter；无新 canonical contract/migration/prompt。
- 兼容性：新增 fastapi/uvicorn/httpx2 依赖（已锁定）；`uv run pytest` 因旧 venv 重定位改用 `uv run python -m pytest`；API 只绑定 127.0.0.1。
- 验证与证据：红灯 `4fe918b`（API 1 个 ImportError + Web 4 个新测试失败）；实现 `6c0c33c` 后 API 7/7、全仓 182/182、Web 10/10；QA attempt 001 PASS（0 P0/P1，3 P2）；P2-1 修复 `e0a4c72` 后 API 8/8、全仓 183/183，QA attempt 002 PASS；真实 uvicorn e2e smoke 全通过。
- 性能/安全/运维影响：loopback 单用户；CORS 白名单；错误 details 不含正文；无网络出站、Provider、secret、真实用户数据或费用。
- 回滚：回退 `e0a4c72` 可回到纯内存 Demo；红灯测试保留，不得以删除测试替代不变量。
- 遗留风险与下一步：Tauri 打包、认证/token（ADR-0011/SPK-009）、FTS5 搜索、导入、加密、多进程、云端与真实 Provider 仍关闭；P2-2（加载竞态）与 P2-3（关闭前 debounce 不 flush）为原型已知边界，记录于 QA 报告。

## 2026-08-14 — 实现 FTS5 基础搜索（笔记/概念全文检索）

- 关联 ID：WORK-2026-015、REQ-2026-006、REQ-2026-010、TR-20260814-007。
- 实际变化：workspace adapter 新增 FTS5 派生索引（`concept_search` 虚拟表，save 事务内原子重建）、`search_course_graph`（MATCH 主查 + 中文子串回退、query 长度/语法守卫、snippet 截断）、`SearchResult`；`apps/api` 新增 `GET /api/workspaces/{id}/search?q=...`（422 search_invalid_query/404）；Web 新增搜索框、结果下拉、点击定位、失败提示。
- 影响模块/接口/schema/migration/prompt：扩展 infrastructure/api/web；FTS5 表为派生索引，无新 canonical contract/migration/prompt。
- 兼容性：sqlite3 3.45.3 内置 FTS5；unicode61 对中文整串分词的限制由子串回退覆盖（明确记录为中文分词边界）。
- 验证与证据：Ready `e451057`；实现 `eeba073` 后搜索 10/10、全仓 193/193、Web 12/12；QA attempt 001 PASS（0 P0/P1，3 P2）；P2-2 修复 `d6c8e01`；真实 uvicorn e2e 中文搜索通过。流程偏差已披露：红灯测试与实现合并提交，红灯真实性经父提交 worktree/QA 双重复核。
- 性能/安全/运维影响：只读搜索端点；查询守卫与 snippet 截断；错误不含正文；无网络出站、Provider、secret、真实用户数据或费用。
- 回滚：回退 `d6c8e01` 可移除搜索；红灯测试保留，不得以删除测试替代不变量。
- 遗留风险与下一步：中文分词、模糊/纠错、文件内容检索（第 5 步）仍关闭；本工作项完成后第 4 步标记 100%，下一主项进入第 5 步导入资料与来源跳转。

## 2026-08-14 — 实现安全文件导入与资源注册

- 关联 ID：WORK-2026-016、REQ-2026-006、REQ-2026-010、NFR-2026-002、TR-20260814-008。
- 实际变化：schema v2 migration（resource/resource_version 表）；`import_resource`（类型/大小/路径守卫、SHA-256 去重、先落盘后提交、UUIDv7 磁盘文件名）、`list_resources`；API POST/GET resources 端点；Web 导入控件与资源列表；新增 python-multipart 依赖。
- 影响模块/接口/schema/migration/prompt：扩展 infrastructure/api/web；PRAGMA user_version 1→2（向前兼容）；无新 canonical contract/prompt。
- 兼容性：旧 v1 库自动迁移保留数据；文件只存受控数据目录；客户端文件名仅作 display_name。
- 验证与证据：Ready `293c0ef`；红灯 `50b3245`（API 1 ImportError + Web 3 失败）；实现 `10e104f` 后 import 14/14、全仓 207/207、Web 15/15；QA attempt 001 PASS（0 P0/P1，5 P2）；P2-1/P2-3 修复 `eee15d0` 后 import 15/15、全仓 208/208；真实 uvicorn e2e 通过。
- 性能/安全/运维影响：受控存储 + 路径逃逸拒绝 + 类型/大小守卫；错误不含正文；无网络出站、Provider、secret、真实用户数据或费用。
- 回滚：回退 `eee15d0` 可回到 v1 库（迁移前数据保留）；红灯测试保留，不得以删除测试替代不变量。
- 遗留风险与下一步：PDF 解析/查看器、Markdown 渲染、Anchor 生成与来源跳转、url/note 资源仍关闭，由第 5 步后续工作项承接。

## 2026-08-14 — 实现 PDF 文本解析与 Anchor 来源跳转

- 关联 ID：WORK-2026-017、REQ-2026-010、NFR-2026-002、TR-20260814-009。
- 实际变化：schema v3 migration（resource_segment + anchor 表）；`parse_pdf_resource`（pypdf 页文本、幂等、storage_key 越界守卫）、`get_page_text`（越界/未解析/漂移守卫）、`register_anchor`/`list_anchors`（UPSERT 返回实际 id、缺失资源 404）；API parse/pages/anchors 端点；Web 页文本查看器（打开/翻页/锚点跳转/漂移提示）。
- 影响模块/接口/schema/migration/prompt：扩展 infrastructure/api/web；PRAGMA user_version 2→3（向前兼容）；消费 Anchor v1 契约；无新 canonical contract/prompt。
- 兼容性：v2 库自动迁移保留数据；pypdf 6.15.0 已有；页文本 ≤ 单页提取。
- 验证与证据：Ready `2829ff2`；红灯 `53eb2cd`（API 1 ImportError + Web 3 失败）；实现 `8c3c620` 后 viewer 8/8、全仓 216/216、Web 18/18；QA attempt 001 PASS（0 P0/P1，6 P2）；P2 修复 `267fb7e` 后 viewer 10/10、全仓 218/218；真实 uvicorn e2e（金标 PDF 52 页）通过。
- 性能/安全/运维影响：只读受控资源；漂移不误跳；错误不含正文；无网络出站、Provider、secret、真实用户数据或费用。
- 回滚：回退 `267fb7e` 可回到导入-only；红灯测试保留，不得以删除测试替代不变量。
- 遗留风险与下一步：PDF.js 可视化渲染、bbox 高亮、Markdown/TXT 查看器、OCR、中文分词仍关闭，由第 5 步后续工作项承接。

## 2026-08-14 — 实现 PDF.js 可视化渲染与 bbox 区域高亮

- 关联 ID：WORK-2026-018、REQ-2026-010、NFR-2026-002、TR-20260814-010。
- 实际变化：`apps/web` 新增 PdfRenderer（pdfjs canvas 渲染、public worker 规避 Windows `@fs` 空格、bbox 高亮覆盖层、canvas 撑开容器保证窄视口对齐）；API 新增 file 端点与 anchors POST；`get_resource_file_path`（storage_key 越界守卫 + 文件缺失 404）；build 产物含 worker。
- 影响模块/接口/schema/migration/prompt：扩展 infrastructure/api/web；无 schema/migration；public/pdf.worker.min.mjs 为 Apache-2.0 运行时资源；无新 canonical contract/prompt。
- 兼容性：pdfjs-dist 6.2.108；dev/build 用同一 public worker URL；窄视口（≤800px）bbox 对齐。
- 验证与证据：Ready `54a108b`；红灯 `275d7c6`（API 2 失败 + Web 2 失败）；实现 `2601215` 后 223/223、Web 20/20；QA attempt 001 FAIL（1 P1：窄视口 bbox 错位 + 7 P2）；修复 `d56e7ef` 后 224/224、Web 20/20；真实浏览器（CDP）完整渲染/高亮/窄视口验证 aligned。
- 性能/安全/运维影响：本地 canvas 渲染无网络；file 端点受控读取 + 越界守卫；错误不含正文；无 Provider、secret、真实用户数据或费用。
- 回滚：回退 `d56e7ef` 可回到页文本查看器；不影响既有持久化/导入/跳转证据。
- 遗留风险与下一步：文本层与页面文本高亮联动、多页连续滚动渲染、Markdown/TXT 可视化渲染、OCR、中文分词仍关闭；本工作项完成后第 5 步标记 100%，下一主项进入第 6 步人工编辑安全感。

## 2026-08-14 — 新增人工验证启动入口与用户手册重写

- 关联 ID：WORK-2026-014/018、REQ-2026-010。
- 实际变化：新增 `uv run python -m apps.api --data-root <dir> [--port N] [--origin URL]` 启动入口（loopback + Vite dev origins 默认允许，供人工验证直接启动本地 API）；补 `apps/__init__.py`/`apps/api/__init__.py` 修正 mypy 包识别（此前 main.py 被同时匹配为 "main" 与 "apps.api.main"）；重写 `docs/USER_MANUAL.md` 为当前已验证能力手册（持久化/保存状态、FTS5 搜索、安全导入、PDF 页文本与渲染视图、锚点跳转与 bbox 高亮、漂移保护）+ 分步人工验收清单。
- 影响模块/接口/schema/migration/prompt：新增 `apps/api/__main__.py` 与两个 `__init__.py`；无 schema/migration/prompt 变化。
- 兼容性：`python -m apps.api` 通过 sys.path 加载 packages 源树，行为与 pytest 一致；mypy 覆盖 11 源文件。
- 验证与证据：`ff02c3e`（启动入口）+ `356a75e`（手册）；health 200、allowed origin 200、evil origin 无 ACAO 头；全仓 224/224、mypy 11 源文件、ruff 全绿、repository validator PASS。
- 性能/安全/运维影响：无部署或常驻服务变化；数据目录默认用户主目录 `knowledge-tree-data`，文档提示用户自选位置。
- 回滚：回退 `ff02c3e` 即恢复无启动入口状态（临时脚本仍可用）；`356a75e` 仅文档。
- 遗留风险与下一步：无新增风险；人工验收清单为端到端补充，自动化未覆盖部分（关闭重开、非默认端口、漂移场景）由用户在真实浏览器按手册执行。

## 2026-08-14 — 收口 PDF.js 渲染验证并标记第 5 步完成

- 关联 ID：WORK-2026-018、TR-20260814-010、REQ-2026-010。
- 实际变化：生成 TR-20260814-010 报告与 evidence 包（QA attempt 001 FAIL 记录 + P1/P2 修复说明 + 浏览器验证结果），同步全部文档（DEVELOPMENT_LOG、OPS_LOG、ENGINEERING_PLAN、TRACEABILITY_MATRIX、路线图、checkpoint、work-items README、WORK-2026-018 状态），第 5 步标记 100%、MVP 约 70%。
- 影响模块/接口/schema/migration/prompt：仅文档与证据；无代码/schema/migration/prompt 变化。
- 验证与证据：`ecd03b4`；收口后 validator、Ruff、pytest 224/224、Web 20/20、浏览器自动检测（CDP 完整渲染/高亮/窄视口 aligned）全绿。
- 回滚：回退 `ecd03b4` 仅撤销文档收口；不影响实现提交与证据。
- 遗留风险与下一步：第 5 步完成；下一主项为第 6 步人工编辑安全感（WORK-2026-019），真实 Provider/Web 与 owner 接受保持禁用。

## 2026-08-14 — 交付检查第一轮：同步本地门、错误码、风险与手册

- 关联 ID：WORK-2026-013..018。
- 实际变化：`bf35b18` 关闭 DoD 缺口——AGENTS.md/README 本地门命令更新（ruff 覆盖 packages/apps、mypy 含 packages+apps/api、pytest 用 `python -m pytest`）；README 当前状态更新为第 4–5 步能力与双终端启动；DEVELOPMENT_LOG 补启动入口/手册条目；ERROR_CODE_CATALOG 新增"已验证实现"表（14 个错误码）并勾选 DoD 清单（仅遥测 metric 留空）；RISK_REGISTER/TRACEABILITY_MATRIX 新增 RISK-2026-013/014；checkpoint 记录启动入口与人工验收交接。
- 验证与证据：`bf35b18`；validator、Ruff、pytest 224/224、Web 20/20 全绿。
- 回滚：回退 `bf35b18` 仅撤销文档修正；不影响实现与证据。
- 遗留风险与下一步：交付检查持续进行（见下一条）。

## 2026-08-14 — 交付检查第二轮：报告索引、环境清单与 CI 命令

- 关联 ID：WORK-2026-013..018、TR-20260814-005..010。
- 实际变化：`f56c99e`——test-reports/README.md 索引补 TR-004..010；ENVIRONMENT_INVENTORY.md local-dev 更新到第 4–5 步 prototype 状态；CI pytest 统一为 `uv run python -m pytest`（消除 Windows venv 重定位歧义）；OPS_LOG 登记该环境缺口；全量核验 13 个 TR 证据 checksums 逐字节匹配（无漂移）。
- 验证与证据：`f56c99e`；validator、Ruff、pytest 224/224、Web 20/20 全绿。
- 回滚：回退 `f56c99e` 仅撤销文档/CI 命令修正；不影响实现与证据。
- 遗留风险与下一步：人工验收按 `docs/USER_MANUAL.md` 清单执行；第 6 步待建。

## 2026-08-14 — 实现持久化 GraphPatch 提交门与跨会话撤销/重做

- 关联 ID：WORK-2026-019、REQ-2026-006/008、NFR-2026-001/003、ADR-0005、WORK-2026-005/011/013/014。
- 实际变化：`packages/infrastructure` 新增 `apply_graph_patch`/`undo_graph`/`redo_graph`——从持久化初始图（`meta.course_graph_initial`）+ 记录日志重建历史，经 `GraphHistory.apply_patch`（确认门 + 四维锁 + revision 冲突 + 重复 change_id）后把图/记录/初始图/栈指针（`meta.course_graph_applied`）单事务原子提交；`save_course_graph` 改为整图替换语义（覆盖 initial、清空历史）；`apps/api` 新增 `POST .../graph/patches|undo|redo` 与 `GET .../history`，服务端固定 trusted actor 为 local-user。
- 影响模块/接口/schema/migration/prompt：扩展 infrastructure/api；无新 canonical contract/ADR/migration/prompt；复用 schema v3 的 `meta`/`history_records` 表。
- 兼容性：旧库（无 initial、history 空）向后兼容，首次 patch 固化 initial；undo/redo 后 revision 保持单调（保留运行时 revision）；幂等拒绝跨会话重复 change_id。
- 验证与证据：Ready `4f5fbd3`；红灯 `db3cb26`（apply_graph_patch ImportError）；实现 `e0a5ed9` + 格式 `49e78eb`；定向 13/13、全仓 237/237、Web 20/20、validator/Ruff/mypy/锁依赖/构建全绿；职责隔离 QA 待执行。
- 性能/安全/运维影响：单事务原子防部分写入；record 仅含变化实体 before/after 与语义 hash，不落 reason/secret/来源全文；无网络/Provider/真实用户数据或费用。
- 回滚：回退 `e0a5ed9` 即回到整图 PUT-only；不改 GraphPatch preview 与纯领域 history；红灯保留。
- 遗留风险与下一步：前端仍整图 PUT 保存（后端已加整图替换语义）；跨会话撤销/锁定前端 UI 待 WORK-2026-020；职责隔离 QA 签字后生成 TR 证据。

## 2026-08-14 — 锁定维度存储保护与 WebUI 锁定/撤销接入

- 关联 ID：WORK-2026-020、REQ-2026-006/008、NFR-2026-001/003、ADR-0005、WORK-2026-005/011/019。
- 实际变化：后端 `save_course_graph` 新增锁定维度保护（`_guard_locked_dimensions`）——整图替换时拒绝锁降级（`lock_downgraded`）、锁定维度内容变化（`content_changed`）、锁定概念删除（`concept_deleted`），锁定项在存储边界不被覆盖；前端 `api.ts` 四维锁保真往返（`locks`/`revision` 读写）并新增 `applyPatch`/`undoGraph`/`redoGraph` 与 `buildSetLockPatch`；`App.tsx` 统一 `toggleLock(content|position)`——有后端走 patch 门 `set_lock`（先 `saveGraph` 同步首跑基础图）、无后端会话内；撤销/重做在会话栈空时回退后端 `undo/redo`；节点卡片显示内容锁标记。
- 影响模块/接口/schema/migration/prompt：扩展 infrastructure/api/web；无新 canonical contract/ADR/migration/prompt。
- 兼容性：锁保真后整图 PUT 不再丢失四维锁；`positionLocked` 与 `locks.position`/`layout.pinned` 一致；无后端（`<App />`）行为保持会话内不变，既有组件测试不受影响。
- 验证与证据：后端 lock-guard 4/4；Web 新增 `App.lock.test.tsx` 2/2；全仓 pytest 241/241、Web 22/22、validator/Ruff/mypy/锁依赖/构建全绿；真实浏览器 CDP 端到端（点击锁定内容→后端 locks.content=true→锁定后改 label 409 target_locked→撤销→锁解除）PASS。
- 性能/安全/运维影响：锁保护为纯内存 diff（O(概念数)），无网络/Provider/真实用户数据或费用；错误仅含 target_id/dimension/rule，不落正文。
- 回滚：回退 `618420c`/`c70d339` 即回到无锁保护/无锁定 UI 状态；不改变已验证 GraphPatch 提交门与纯领域 history。
- 遗留风险与下一步：普通编辑（增删改/拖动）仍走整图 PUT（清空历史），其跨会话撤销尚未覆盖；冲突预览 UI、崩溃恢复 UI、前端 patch 化保存待后续；职责隔离 QA 待执行。

## 2026-08-14 — WORK-2026-019/020 职责隔离 QA 收口（TR-20260814-011）

- 关联 ID：WORK-2026-019/020、TR-20260814-011、NFR-2026-001/003、ADR-0005。
- 实际变化：职责隔离 QA（graph_qa_fresh）对冻结 `c70d339` 返回 FAIL（2 P0、3 P1、3 P2）；修复 `a6a471a` 关闭 P0-2（撤销/重做补自动保存）、P1-1（content 锁护整个 concept）、P1-2（`_guard_revision_monotonic` 拒绝 revision 回退，新增 `revision_conflict` 409）、P1-3（前端编辑前查锁）、P2-1（positionLocked 兼容旧 pinned）、P2-3（body 上限 10 MiB），各配回归测试；P0-1（普通编辑跨会话撤销）与 P2-2（单用户并发 TOCTOU）记为边界（归 WORK-2026-021 / 单用户本地）。
- 影响模块/接口/schema/migration/prompt：扩展 infrastructure/api/web；新增稳定错误码 `revision_conflict`；无 schema/migration/prompt 变化。
- 兼容性：旧库向后兼容；content 锁语义与 domain 门对齐（保护整个 concept）；positionLocked 兼容 `layout_items.pinned` 旧数据。
- 验证与证据：`0ecdb1b` 封存 QA 报告 + evidence + TR 报告；全仓 pytest 243/243（lock guard 6/6）、Web 23/23、validator/Ruff/mypy/锁依赖/构建全绿；QA attempt 001 FAIL 记录 + 修复说明保留于 `evidence/TR-20260814-011/`。
- 性能/安全/运维影响：锁保护纯内存 diff；body 上限防大 payload；错误仅含标识，不落正文/secret。
- 回滚：回退 `a6a471a` 回到 QA 前实现；QA FAIL evidence 保留；不回退既已验证 GraphPatch/纯领域 history。
- 遗留风险与下一步：第 6 步核心完成标志已兑现（锁定项不被覆盖、失败/重启不重复写入）；普通编辑跨会话撤销、冲突预览 UI、崩溃恢复 UI 归 WORK-2026-021；真实 Provider/Web 与 owner 接受保持禁用。

## 2026-08-14 — 冲突预览与备份/恢复 UI（WORK-2026-021）

- 关联 ID：WORK-2026-021、REQ-2026-006/008、NFR-2026-001、WORK-2026-019/020。
- 实际变化：后端新增 `list_backups`/`restore_backup_by_name`（纯文件名 + backups_dir 内 + 存在三重守卫）与 `GET .../backups`、`POST .../restore` 端点（`backup_invalid` 422 / `backup_checksum_mismatch` 409）；前端 `api.ts` 新增 `backupGraph`/`listBackups`/`restoreBackup`/`listHistory` 且 `loadGraph`/`saveGraph` 错误透传 `code`；`App.tsx` 新增 `saveErrorMessage`（锁定/版本冲突/数据损坏 → 具体提示）、`loadGraph` 区分 `workspace_corrupt`、侧边栏"备份数据"按钮、备份列表恢复入口与版本历史面板（vN→vN+1 + change_id 前缀）。
- 影响模块/接口/schema/migration/prompt：扩展 infrastructure/api/web；新增稳定错误码 `backup_invalid`/`backup_checksum_mismatch`；无 schema/migration/prompt。
- 兼容性：恢复走 checksum 校验；备份名守卫防路径逃逸；旧库无备份时列表为空。
- 验证与证据：`fb745bd`；后端 backup_api 3/3（round trip/路径遍历/缺失）；Web 新增冲突提示 + 备份按钮 2/2；全仓 pytest 246/246、Web 25/25、validator/Ruff/mypy/锁依赖/构建全绿。
- 性能/安全/运维影响：备份为 sqlite 在线备份 + sha256 sidecar；恢复替换 db 前校验和；无网络/Provider/真实用户数据。
- 回滚：回退 `fb745bd` 即回到无备份/恢复 UI 状态；不影响已验证提交门/锁定保护。
- 遗留风险与下一步：第 6 步产物基本齐全（锁定/撤销/冲突预览/崩溃恢复），普通编辑 patch 化保存（跨会话撤销覆盖所有编辑）与版本历史 UI 面板仍待；真实 Provider/Web 与 owner 接受保持禁用。

## 2026-08-14 — 普通编辑 patch 化保存与跨会话撤销（WORK-2026-022）

- 关联 ID：WORK-2026-022、REQ-2026-006/008、NFR-2026-001/003、ADR-0005、WORK-2026-005/019、TR-20260814-013。
- 实际变化：GraphPatch v1 契约新增 `delete_concept`/`delete_edge`（含 EdgeTarget，生成 TS/Python 产物）；领域 `_apply_delete_concept`（锁定概念删除拒绝 + 存活端点 relations 锁检查 + 级联）与 `_apply_delete_edge`；后端 `save_course_graph` 改为首次整图替换、后续 diff 生成有序 patch 走 `apply_graph_patch`（`_build_diff_patch`：删边→删概念→建概念→建边→update/lock/annotation→layout），普通编辑保留历史、跨会话撤销覆盖所有编辑；删除死代码 `_guard_locked_dimensions`/`_guard_revision_monotonic` 等（锁/revision 由提交门接管）。
- 影响模块/接口/schema/migration/prompt：扩展 GraphPatch v1 canonical schema（新增两个操作）、contracts-ts/py 生成产物、infrastructure；无 migration/prompt。
- 兼容性：锁语义收敛为提交门（锁降级=用户主动解锁）；noop 保存不递增 revision；前端零改动（继续整图 PUT）。
- 验证与证据：`ab50aa2` 实现；`7106621` QA 修复；QA attempt 001 FAIL（3 P1 + 2 P2）→ 复审 PASS；全仓 pytest 256/256、Web 27/27、contracts-ts drift、validator/Ruff/mypy/构建全绿；证据 `TR-20260814-013`。
- 性能/安全/运维影响：diff 为 O(V+E) 纯内存；删除为硬删除 + 历史可恢复（tombstone 软删除未引入）；错误仅含标识，不落正文/secret。
- 回滚：回退 `ab50aa2`/`7106621` 即回到整图替换保存；不回退已验证 GraphPatch 提交门/纯领域 history。
- 遗留风险与下一步：**第 6 步完成（100%）**，"不依赖 AI 也能使用"的手工 Alpha 形成；tombstone 软删除、真实 Provider/Web、owner 接受保持禁用，第 7 步 DeepSeek 适配待 owner 提供 API Key 与预算。

## 2026-08-14 — Markdown/TXT 文本查看器（WORK-2026-023）

- 关联 ID：WORK-2026-023、REQ-2026-010、WORK-2026-016。
- 实际变化：前端 `api.ts` 新增 `getResourceText(resourceId)`（经 `GET .../resources/{id}/file` 读取原文，复用 WORK-2026-018 的 file 端点）；`App.tsx` `openViewer` 按 mime 分流——PDF 走页文本/锚点，`text/*`（Markdown/TXT）读取原文进入文本查看器；资源列表对 `text/*` 资源开放"打开"按钮；查看器控件按 mime 显示（PDF 显示翻页/文本/渲染，MD/TXT 仅显示关闭）。填补第 5 步"MD/TXT 导入后无法查看内容"的缺口。
- 影响模块/接口/schema/migration/prompt：仅扩展 apps/web；后端复用既有 file 端点，无新端点/schema/migration/prompt。
- 兼容性：PDF 查看器行为不变；`text/*` 资源无翻页/渲染/锚点，仅纯文本查看。
- 验证与证据：`78c5264`；Web 新增 `opens a markdown resource in the text viewer`（getResourceText + 文本渲染）；全仓 pytest 256/256、Web 28/28、validator/Ruff/mypy/构建全绿。
- 性能/安全/运维影响：file 端点受控读取 + storage_key 越界守卫；错误不含正文；无网络/Provider/真实用户数据。
- 回滚：回退 `78c5264` 即回到 PDF-only 查看器；不影响持久化/导入/提交门证据。
- 遗留风险与下一步：Markdown 渲染为纯文本（无富文本渲染）；文本层与页面文本高亮联动、多页连续滚动仍为后续；真实 Provider/Web 与 owner 接受保持禁用。

## 2026-08-14 — Markdown 富文本渲染（WORK-2026-024）

- 关联 ID：WORK-2026-024、REQ-2026-010、WORK-2026-023。
- 实际变化：新增 `apps/web/src/markdown.ts` 的 XSS 安全 `renderMarkdown`——先 `escapeHtml`（& < > " '）再应用标题(1–3)/加粗/斜体/行内代码/无序列表/围栏代码块，输出仅含本模块生成的标签；`App.tsx` 对 `text/markdown` 资源经 `markdown-body` 渲染视图（`dangerouslySetInnerHTML`，因先转义故安全），`text/plain` 保持 `<pre>` 纯文本；`styles.css` 新增 markdown-body 基础排版。
- 影响模块/接口/schema/migration/prompt：仅扩展 apps/web；无后端/schema/migration/prompt 变化。
- 兼容性：TXT 仍纯文本；PDF 查看器行为不变；Markdown 从纯文本升级为富文本显示。
- 验证与证据：`0310061`；`markdown.test.ts` 3/3（格式渲染 + 注入转义 + 代码块）；全仓 pytest 256/256、Web 31/31、validator/Ruff/mypy/构建全绿。
- 性能/安全/运维影响：渲染为纯函数，先转义防 XSS（无第三方渲染依赖）；无网络/Provider/真实用户数据。
- 回滚：回退 `0310061` 即回到 Markdown 纯文本查看；不影响导入/查看器/提交门证据。
- 遗留风险与下一步：Markdown 富文本仅支持最小语法子集（无表格/链接/任务列表）；文本层与页面文本高亮联动、多页连续滚动、tombstone 软删除仍为后续；真实 Provider/Web 与 owner 接受保持禁用。

## 2026-08-14 — 知识树画布平移与缩放（WORK-2026-025）

- 关联 ID：WORK-2026-025、REQ-2026-006、WORK-2026-012。
- 实际变化：`App.tsx` 画布新增平移/缩放——滚轮缩放（0.5×–2.5×，步进 0.1）、拖动空白区域平移、节点拖动按 zoom 换算屏幕增量；`canvas-surface` 用 `transform: translate(pan) scale(zoom)`，`canvas-viewport` 由 scroll 改为 `overflow: hidden`；`centerOnNode`（pan 定位）取代原 scrollLeft 的选中/搜索定位；`styles.css` 加 `transform-origin:0 0`/`touch-action:none`/grab 光标。
- 影响模块/接口/schema/migration/prompt：仅扩展 apps/web；无后端/schema/migration/prompt 变化。
- 兼容性：节点世界坐标不变（仅渲染变换）；拖动/排布/锁定/撤销行为不变；现有移动节点测试经事件冒泡仍通过。
- 验证与证据：`8563fad`；Web 新增 `zooms the canvas with the wheel`（transform scale 断言）；全仓 pytest 256/256、Web 32/32、validator/Ruff/mypy/构建全绿。
- 性能/安全/运维影响：纯 CSS transform 渲染，无重排；`touch-action:none` 抑制浏览器默认手势；无网络/Provider/真实用户数据。
- 回滚：回退 `8563fad` 即回到 scroll-only 画布；不影响持久化/提交门/查看器证据。
- 遗留风险与下一步：缩放已支持鼠标位置为中心（`62e0b72`，zoom/pan 合并为 camera 状态原子更新）；文本层与页面文本高亮联动、多页连续滚动、tombstone 软删除仍为后续；真实 Provider/Web 与 owner 接受保持禁用。

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
