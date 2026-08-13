# 运维日志

> 用途：记录环境、发布、现存运行问题、临时缓解、恢复能力和接手提示。当前尚无运行系统。

## 当前运行状态

- 产品代码：仅最小 Web 工程状态页与开发工具骨架；无业务能力。
- 开发环境：本地 Python/Node 工具门已建立；test/staging/production 未建立。
- CI/CD：GitHub Actions workflow 已声明但无远端 run 证据；不是可用部署流水线。
- 监控与告警：未建立。
- 备份与恢复：未实现、未演练。
- 正式发布：无。
- 值守/支持渠道：未建立。

## 2026-08-13 — 建立运维规划

- 关联：WORK-2026-001。
- 已完成：定义日志、trace、metrics、诊断包、发布、灰度、回滚、事故、Runbook 和备份恢复要求。
- 未完成：没有工具或运行证据，不能宣称具备上述能力。
- 当前缓解：不发布、不处理真实用户数据。
- 下一门：建仓后先实现本地结构化日志、稳定错误码和诊断包格式。

## 现存问题

| ID | 严重度 | 问题 | 临时缓解 | Owner | 目标阶段 | 状态 |
|---|---|---|---|---|---|---|
| OPS-2026-001 | 高 | 尚无运行、备份、恢复和诊断能力 | 不进入真实运营 | 待定 | 阶段 1 | open |
| OPS-2026-002 | 高 | 尚无构建签名、SBOM 和来源证明 | 不分发安装包 | 待定 | 阶段 1/3 | open |
| OPS-2026-003 | 高 | DeepSeek 仅有配置/契约，尚无 API Key、live smoke、金标或运行遥测 | `enabled: false`，只使用 mock/fixture | 待定 | 阶段 0/2 | open |

## 2026-08-13 — DeepSeek 运维边界建立

- 关联：WORK-2026-007、RB-PROV-001。
- 环境/版本：仅文档与配置 v1；所有运行环境仍未创建。
- 变化：定义 Provider 错误、重试/回退、熔断、脱敏字段、配置 fingerprint 和排障顺序。
- 现状：DeepSeek deployment 明确关闭，尚不能处理真实流量。
- 启用前提：受控密钥、TC-LLM-001..009、EVAL-LLM-001、Runbook 演练和 QA 批准。
- 回滚：文档/配置回退；无运行状态和用户数据需要迁移。

## 2026-08-13 — 本地开发门与环境缺口登记

- 关联：WORK-2026-006、TR-20260813-002。
- 环境/版本：Windows x64；Python 3.12.6/uv 0.12.3；Node 24.14.1/pnpm 11.19.0；commit `bd66e8b`。
- 变化：新增锁定安装、配置/秘密校验、Python/TypeScript 门、Web build 和 CI workflow；`RUN_LIVE_LLM_TESTS` 在 CI 固定为 `0`。
- 验证：本地严格链与浏览器桌面/390px 验收通过；开发服务器已关闭，无常驻进程。
- 现状/影响：Rust/Cargo 缺失；无远端、托管 runner、制品、部署、监控或备份；workflow 存在不等于 CI 已运行。
- 缓解/回滚：`apps/desktop/Cargo.toml` 不存在时 CI 只允许显式 skip；manifest 出现却没有 Rust job 时失败。回退 `bd66e8b`。
- 遗留风险/Owner/期限：项目负责人确定远端/许可证；技术负责人批准 ADR-0014；运维补 Rust 与托管 CI；QA 独立复核。

## 2026-08-13 — 微积分 eval fixture 来源与恢复边界登记

- 关联：WORK-2026-004、TR-20260813-003。
- 环境/版本/build/config：Windows 11 x64；Python 3.12.6/uv 0.12.3；pypdf 6.15.0；commit `e918fdf`；dataset `1.0.0-draft.1` / `author_reviewed`。
- 操作者：Codex（数据集作者与分时验证；非独立 QA）。
- 变更或症状：新增 736149-byte、52-page MIT OCW 第 2 章 PDF 与固定 SHA-256；远端官方直链重下字节/hash 一致；无部署或运行服务变化。
- 影响：fixture 只允许非商业研发，不能进入商业分发；校验失败应阻断 parser/AI eval，禁止自动替换远端变化后的文件。
- 证据：`evidence/TR-20260813-003/` 含环境、命令、摘要、校验和与 7 张代表页截图；完整本地门通过。
- 缓解/回滚：远端摘要变化时保留 v1 文件和 hash，创建新 dataset version 再复核；回退 `e918fdf` 可禁用 fixture；不删除署名/许可来规避限制。
- 验证：来源/hash/页数/元数据/活动内容、schema、引用、DAG、许可、审批状态和视觉抽检通过。
- 遗留风险/Owner/期限：项目负责人待指派 independent_subject_reviewer 与 QA；签字前 dataset 不得标 `approved`，DeepSeek 保持禁用。

## 2026-08-13 20:28 — 独立复核门进入待签状态

- 关联 ID：WORK-2026-004、TR-20260813-004。
- 环境/版本/build/config：Windows 11 x64；Python 3.12.6/uv 0.12.3；Node 24.14.1/pnpm 11.19.0；commit `232d0cd`；review schema `independent-review.v1`。
- 操作者：Codex（门禁实现与分时验证；非独立学科复核者或 QA）。
- 变更或症状：新增待签复核执行包和完成硬门；当前 subject/QA 均为 `pending`，数据集保持 `author_reviewed`。
- 影响：无部署和常驻服务变化；普通仓库门为绿，关闭工作项所需的完成门按设计为红，稳定错误为 `calculus_review_invalid`。
- 证据：`evidence/TR-20260813-004/` 含环境、命令、门禁摘要、manifest 和校验和；完整本地门通过。
- 缓解/回滚：复核中可保存未完成包并运行普通门；不得关闭工作项。内容漂移时旧摘要失效，须重新逐条复核；回退实现不构成风险接受。
- 验证：30/40/50 精确覆盖、内容摘要、分歧裁决、双人身份及时序、许可确认和审批同步均有正/负向合同测试。
- 遗留风险/Owner/期限：项目负责人待指派两名不同人员；真实完成后由独立 QA 形成后续签字报告。DeepSeek 继续禁用。

## 2026-08-13 21:05 — AI 自动机器复核方向登记

- 关联 ID：CHG-2026-001、ADR-0015、WORK-2026-004、WORK-2026-010。
- 环境/版本/build/config：需求/治理变更；无新运行环境、deployment、secret 或 live flag。
- 操作者：workspace owner 提出需求；Codex 编排 AI 学科设计子 Agent与 AI QA 设计子 Agent完成只读方案审查。
- 变更或症状：真人双签不再作为个人产品的目标运行模式；后续采用 AI 学科/QA 子 Agent + 确定性 harness + 机器证明。v1 完成门仍保持红色且不被 AI 伪签。
- 影响：当前无网络、模型调用、部署、数据库或常驻进程变化；真实 DeepSeek 和 Web Search 继续关闭。
- 证据：`docs/PRODUCT_REQUIREMENTS.md`、CHG-2026-001、ADR-0015、`docs/ai-review/ROLE_CARDS.md`、WORK-2026-010。
- 缓解/回滚：v2 未实现前保持数据集 `author_reviewed`；如后续隔离/安全/eval 不达标，禁用 v2 policy 并返回 inconclusive。
- 验证：本轮只验证文档一致性和仓库门；不声称 harness 或自动审查已实现。
- 遗留风险/Owner/期限：同源模型偏差、搜索提示注入/漂移和 harness 共同缺陷已登记 RISK-2026-010..012；由后续 TC-AIREV 安全/变异/eval 门处理。

## 2026-08-13 22:15 — AI 机器复核 v2 离线原型进入本地门

- 关联 ID：WORK-2026-004、ADR-0015、TC-AIREV-001..010。
- 环境/版本/build/config：Windows 11 x64；Python 3.12.6/uv 0.12.3；Node 24.14.1/pnpm 11.19.0；harness `calculus-ai-review-harness.v2.mock.1`；实现提交待冻结。
- 操作者：Codex（实现与分时验证；正式隔离 AI 学科/QA 复核尚未执行）。
- 变更或症状：默认离线仓库门新增 30/40/50 subject/QA ReplaySearchProvider 复放；学科复核后收紧为无论同源/跨模型均输出 `inconclusive` + mock-only assurance，并以冻结 PDF 页文本 hash 而非待审 item 自身充当 replay 证据；不解析 secret、不访问网络、不启动常驻进程。
- 影响：无部署、数据库、真实 Provider、Web Search、用户数据或模型费用；不能用于声明产品自动复核已上线。
- 证据：初版工作树完整门 71/71 Python、1/1 Web 通过；隔离学科两轮复核分别发现证据链和状态组合绕过并触发失败测试/修复，当前增量测试 77/77 Python 通过；正式 `TR-20260813-005` 只会在最终修复提交、全门和 QA 完成后生成。
- 缓解/回滚：删除/回退 v2 policy、schema、harness 和默认门集成即可禁用；v1 历史 artifact 保留。任何输入/证据/policy hash 漂移必须重放，不允许沿用旧状态。
- 验证：同源披露、隔离、artifact 绑定、提示注入、越权、漂移、伪引用、timeout/budget、裁决和硬不变量风险豁免均有正/负向测试。
- 遗留风险/Owner/期限：正式 QA 尚未对冻结提交复核；真实搜索的 SSRF/allowlist/版权与 Provider 失败仍未验证，继续保持关闭。

## 2026-08-13 23:16 — AI 机器复核 v2 离线原型完成证据收口

- 关联 ID：WORK-2026-004、TR-20260813-005、RISK-2026-010..012。
- 环境/版本/build/config：Windows 11 x64 10.0.26200；Python 3.12.6/uv 0.12.3；Node 24.14.1/pnpm 11.19.0；commit `ae834d9051553aa02a079e72ce2bf6bd8955c081`；dataset `1.0.0-draft.2`；harness `calculus-ai-review-harness.v2.mock.1`。
- 操作者：Codex（实现）；职责隔离 `ai_subject_reviewer` 与 `ai_qa_auditor`（只读机器证明；非真人签字/owner 接受）。
- 变更或症状：QA attempt 001 在绿门下发现 3 P1/3 P2 语义绕过；全部先以 8 个失败测试复现，再在 `ae834d9` 失败关闭。QA attempt 002 绑定该提交并 PASS，明确 `correlation_classification=correlated_review`。
- 时间线：`73a74da` 初版 → `3f9b637`/`db0831b` 三轮学科复核收敛 → QA-001 FAIL → `ae834d9` 修复 → QA-002 PASS。
- 影响：无部署、数据库、真实 Provider/Web、用户数据、秘密或模型费用；mock 继续输出 `inconclusive`，不能声明产品能力上线。
- 证据：`docs/test-reports/TR-20260813-005_calculus-ai-review-v2.md` 与 `evidence/TR-20260813-005/`；targeted 39/39、pytest 84/84、Web 1/1，完整本地门全部通过。
- 缓解/回滚：`controlled_live` 和任意 owner acceptance artifact 在本原型中均被拒绝；回退 `ae834d9` 不得作为放行手段。若异常，禁用整个 v2 harness 并保留所有 attempt。
- 验证：trace/claim/policy/session/live/owner 变异以及原有注入、越权、漂移、伪引用、timeout/budget、裁决测试均通过；QA 未发现新 P0/P1/P2。
- 遗留风险/Owner/期限：真实搜索 SSRF/来源/版权、跨模型独立性、认证 owner 和产品状态机仍未验证；Owner 为 WORK-2026-007/008/010 对应角色，相关 gate 完成前保持关闭。

## 2026-08-14 00:23 — 个人 MVP 开发默认值通过离线 QA 门

- 关联 ID：WORK-2026-002、WORK-2026-005、TR-20260814-001。
- 环境/版本/build/config：Windows 11 x64；Python 3.12.6/uv 0.12.3；Node 24.14.1/pnpm 11.19.0；reviewed commit `10f249b3021da1577aa17eb114d3b44c20a2b0a2`。
- 操作者：Codex（文档修正）；职责隔离 `ai_qa_auditor`（只读机器证明，非人类签字或 owner 接受）。
- 变更或症状：首次 QA 的 1 P1/2 P2 治理缺陷由 superseding 提交修复；attempt 002 PASS 后仅开放 WORK-2026-005 的离线 schema/领域尖峰。
- 时间线：`8ff376d` 决策基线 → QA-001 FAIL → `10f249b` 修正 → QA-002 PASS → `TR-20260814-001` 收口。
- 影响：无部署、端口、进程、数据库、网络、Provider、用户数据、秘密或费用变化；当前网页仍只是工程状态页。
- 证据：`docs/test-reports/TR-20260814-001_mvp-scope-decisions.md` 与 `evidence/TR-20260814-001/`；84/84 Python、Web 1/1 和完整本地门通过。
- 缓解/回滚：回退 Ready/证据提交可停止 WORK-2026-005；禁止删除失败 attempt、伪造 owner 批准或借此开启 live 能力。
- 验证：10/10 决策映射；QA-002 0 P0/P1/P2、无新发现、`correlated_review`。
- 遗留风险/Owner/期限：Gate A、PRD/ADR 精确 owner 接受、仓库/许可证、预算、Embedding 和真实网络验收继续开放；不阻塞可回滚的离线 contract 测试。

## 2026-08-14 01:04 — Anchor/GraphPatch v1 prototype 进入 QA 前冻结门

- 关联 ID：WORK-2026-005、TC-GRAPH-001..005、TC-ANCH-001。
- 环境/版本/build/config：Windows 11 x64；Python 3.12.6/uv 0.12.3；Node 24.14.1/pnpm 11.19.0；graph contract v1；实现提交待冻结。
- 操作者：Codex（contract/domain 实现与分时验证；职责隔离 QA 尚未执行）。
- 变更或症状：红灯 `44b6233` 后建立 canonical schema、Python validator、生成/类型检查的 TypeScript enum 和纯 GraphPatch preview；trusted actor 从 payload 外注入并阻断身份自证。
- 时间线：WORK-005 Ready → `44b6233` 红灯 → 21/21 最小绿灯 → 专项 49/49 + 仓库集成 4/4 绿灯（当时误合记为目标 53/53）→ 完整门绿。
- 影响：无部署、端口、常驻进程、数据库、API、UI、网络、Provider、用户数据、秘密或费用；网页可见能力未变化。
- 证据：该冻结点专项 49/49、仓库集成 4/4；全仓 Python 135/135、Web 1/1；repository/schema/generation drift、Ruff、scripts/domain strict mypy、locked installs/peers 和 production build 全通过。QA 后续发现运行时文件读，故该记录不构成最终 GO。
- 缓解/回滚：回退待冻结实现提交可禁用未接产品的 v1 prototype；保留红灯测试；不得删除锁/DAG/actor/evidence 校验作为回滚。
- 验证：Anchor 四 selector、UUIDv7/hash、六 operation、确认门、端点/base revision、四维锁、任意长度 cycle path、AI evidence/origin/actor spoof、500 节点工程初值通过。
- 遗留风险/Owner/期限：职责隔离 QA、正式 ADR/owner 接受、operation log/inverse/undo、持久化/API/UI/resolver 和产品性能指标待后续门。

## 2026-08-14 01:26 — GraphPatch 冷启动文件 I/O 修复进入复审

- 关联 ID：WORK-2026-005、TR-20260814-002。
- 环境/版本/build/config：Windows 11 x64；Python 3.12.6/uv 0.12.3；Node 24.14.1/pnpm 11.19.0；红灯 `1278e79`；修复 `5ff02a4`。
- 操作者：Codex（实现）；职责隔离 `graph_qa_fresh` attempt 001（机器证明，非人类签字/owner 接受）。
- 变更或症状：QA 证明 `a25470c` 冷启动会从仓库 `docs/contracts` 读 schema，安装布局不可靠；现在运行时使用 canonical schema 的确定性 Python 派生产物，generator drift gate 同时约束 TS/Python。
- 时间线：`a25470c` → QA-001 FAIL → `1278e79` 单测预期失败 → `5ff02a4` 修复 → 完整门绿 → `b946855` → QA-002 PASS。
- 影响：无部署、端口、数据库、API、UI、网络、Provider、用户数据、秘密或费用；网页能力未变化。
- 证据：`TR-20260814-002`；专项 50/50、仓库集成 4/4、全仓 Python 136/136、Web 1/1；完整本地门全部通过；QA-002 为 0 P0/P1/P2、无新发现、`correlated_review`。
- 缓解/回滚：生成漂移立即失败关闭；不得手改生成物或恢复运行时仓库路径依赖。
- 遗留风险/Owner/期限：正式 ADR/owner 接受和下一工作项的回放/撤销仍待完成；机器 QA 不替代 owner 接受。

---

## 新条目模板

```markdown
## YYYY-MM-DD HH:mm — <环境/发布/运行事件>

- 关联 ID：
- 环境/版本/build/config：
- 操作者：
- 变更或症状：
- 时间线：
- 影响：
- 证据：
- 缓解/回滚：
- 验证：
- 遗留风险/Owner/期限：
```
