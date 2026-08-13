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
- 遗留风险与下一步：职责隔离 QA 复审通过后生成 TR-20260814-002，并把 WORK-005 移入 verification；operation log/inverse/undo 仍属于下一独立工作项。

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
