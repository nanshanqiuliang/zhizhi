# 运维日志

> 用途：记录环境、发布、现存运行问题、临时缓解、恢复能力和接手提示。当前尚无运行系统。

## 当前运行状态

- 产品代码：本地知识树 Web 界面 + FastAPI loopback sidecar + SQLite 持久化原型；LLM port 契约层、mock/DeepSeek adapter 已冻结；AI 草案流水线（切片 1–4，`/ai-draft` 现为增量式）、带来源问答（第 9 步切片 1）、自然语言转 GraphPatch（切片 2）、增量重建纯领域内核 + LLM 接线（切片 3a/3b）已实现。真实调用仅显式构造 adapter（live 双门控 + `DEEPSEEK_API_KEY` opt-in）；草案/指令只经提交门落库；问答/草案生成/指令解释/增量内核只读。
- 开发环境：本地 Python/Node 工具门已建立；test/staging/production 未建立。
- CI/CD：GitHub Actions workflow 已声明但无远端 run 证据；不是可用部署流水线。
- 监控与告警：未建立。
- 备份与恢复：工作区 sqlite 在线备份 + checksum 恢复已实现（WORK-2026-021）；无托管环境演练。
- 正式发布：无。
- 值守/支持渠道：未建立。

## 2026-08-15 — 第 9 步切片 3b：增量重建 LLM 接线（WORK-2026-031）运维记录

- 关联 ID：WORK-2026-031、WORK-2026-030、WORK-2026-009、WORK-2026-008。
- 环境/版本/build/config：commit `d012660`（feature/WORK-2026-009-ai-draft-pipeline）；local-dev Windows x64。
- 变更或症状：新增 `build_incremental_ai_draft` + generator 改增量路径；`/ai-draft` 对非空图不重复创建既有概念；无部署/常驻服务变化；真实调用仅 `DEEPSEEK_API_KEY` opt-in。
- 影响：无部署或常驻服务变化；仅扩展 Python 模块；`config/llm` 与 Provider 门控不变。
- 证据：pytest 427/427 + 5 skipped；validator（含 secret scan）/Ruff/mypy（scripts 11 + strict packages/api 33）全绿；live e2e（owner key env-only）非空图增量（极限 未重建）。
- 缓解/回滚：回退 `d012660` 即回全量草案生成；密钥仅 env。
- 遗留风险/Owner/期限：切片 3b 职责隔离 QA 待执行；向量检索（Embedding provider 未决）、AI 修改历史为后续。

## 2026-08-15 — 第 9 步切片 3a：增量重建纯领域内核（WORK-2026-030）运维记录

- 关联 ID：WORK-2026-030、WORK-2026-009、WORK-2026-005。
- 环境/版本/build/config：commit `da73951`（feature/WORK-2026-009-ai-draft-pipeline）；local-dev Windows x64。
- 变更或症状：新增 `build_incremental_patch`（纯领域增量并入：去重/混合端点/证据/DAG）；无 LLM、无网络、无落库、无部署/常驻服务变化。
- 影响：无部署或常驻服务变化；仅新增纯领域函数与测试；`config/llm` 与 Provider 门控不变。
- 证据：pytest 424/424 + 5 skipped；validator（含 secret scan）/Ruff/mypy（scripts 11 + strict packages/api 33）全绿。
- 缓解/回滚：回退 `da73951` 即回无增量内核；本轮无真实 LLM 调用。
- 遗留风险/Owner/期限：切片 3a 职责隔离 QA 已封存（TR-20260814-019，attempt 001 PASS + 修复 `120e349` + attempt 002 PASS，correlated_review）；切片 3b（LLM 接线 + 端点 + Web）待做。

## 2026-08-15 — 第 9 步切片 2：自然语言转 GraphPatch（WORK-2026-029）运维记录

- 关联 ID：WORK-2026-029、WORK-2026-008、WORK-2026-028。
- 环境/版本/build/config：commit `b4fde38`（feature/WORK-2026-009-ai-draft-pipeline）；local-dev Windows x64。
- 变更或症状：新增 `build_command_patch`（label→概念 id 严格映射 + set_lock/create_edge）、`POST /api/workspaces/{id}/interpret`（注入式 generator，无 Key 503）、`apps/api/command.py`（DeepSeek `command_interpret` 组合根，env-only）、Web 指令输入 + 预览/接受/拒绝面板；解释只读、接受经提交门；无部署/常驻服务变化。
- 影响：无部署或常驻服务变化；仅新增/扩展 Python 模块、端点与 Web UI；`config/llm` 与 Provider 门控不变。
- 证据：pytest 415/415 + 5 skipped；validator（含 secret scan）/Ruff/mypy（scripts 11 + strict packages/api 33）全绿；Web 39/39、pnpm build 通过；live e2e（owner key env-only）指令→create_edge+set_lock→接受落库。
- 缓解/回滚：回退 `b4fde38` 即回无自然语言图修改能力；不设 `DEEPSEEK_API_KEY` 则端点 503；密钥仅 env。
- 遗留风险/Owner/期限：切片 2 职责隔离 QA 已封存（TR-20260814-018，attempt 001 PASS + 修复 `9a255d2`/`9abd339` + attempt 002 PASS，correlated_review）；向量检索、增量重建、AI 修改历史为后续切片。

## 2026-08-15 — 第 9 步切片 1：带来源问答（WORK-2026-028）运维记录

- 关联 ID：WORK-2026-028、WORK-2026-008、WORK-2026-015。
- 环境/版本/build/config：commit `47d6c6f`（feature/WORK-2026-009-ai-draft-pipeline）；local-dev Windows x64。
- 变更或症状：新增 `build_answer_context`（FTS5 + 反向子串回退）、`POST /api/workspaces/{id}/answer`（注入式 generator，无 Key 503）、`apps/api/answer.py`（DeepSeek `answer_with_sources` 组合根，env-only）、Web 提问框 + 带来源回答面板；回答只读、不写库；无部署/常驻服务变化。
- 影响：无部署或常驻服务变化；仅新增/扩展 Python 模块、端点与 Web UI；`config/llm` 与 Provider 门控不变。
- 证据：pytest 408/408 + 5 skipped；validator（含 secret scan）/Ruff/mypy（scripts 11 + strict packages/api 31）全绿；Web 38/38、pnpm build 通过；live e2e（owner key env-only）「什么是极限」→ 回答引用 `[1] 极限`。
- 缓解/回滚：回退 `47d6c6f` 即回无问答能力；不设 `DEEPSEEK_API_KEY` 则端点 503、UI「AI 未连接」；密钥仅 env。
- 遗留风险/Owner/期限：切片 1 职责隔离 QA 已封存（TR-20260814-017，attempt 001 PASS + 修复 `9e06ebf` + attempt 002 PASS，correlated_review）；向量检索、自然语言转 GraphPatch、增量重建、AI 修改历史为后续切片。

## 2026-08-15 — 第 8 步切片 4：AI 草案来源锚点落库（WORK-2026-027）运维记录

- 关联 ID：WORK-2026-027、WORK-2026-026、WORK-2026-009、WORK-2026-007/008。
- 环境/版本/build/config：commit `38df493`（feature/WORK-2026-009-ai-draft-pipeline）；local-dev Windows x64。
- 变更或症状：新增 `deterministic_uuidv7`、`accept_ai_draft`（单事务：确认 patch + 锚点行 + 图/record/applied/索引）、`POST /ai-draft/accept` 端点、generator 确定性资源级锚点 + `evidence`、Web 草案面板"跳回原文"；接受仍只经提交门；无部署/常驻服务变化。
- 影响：无部署或常驻服务变化；仅扩展 Python 模块/端点与 Web UI；`config/llm` 与 Provider 门控不变。
- 证据：pytest 400/400 + 5 skipped；validator（含 secret scan）/Ruff/mypy（scripts 11 + strict packages/api 30）全绿；Web 36/36、pnpm build 通过；live e2e（owner key env-only）生成→接受 applied，证据指向真实锚点。
- 缓解/回滚：回退 `38df493` 即回合成来源引用；生成只读；密钥仅 env。
- 遗留风险/Owner/期限：切片 4 职责隔离 QA 已封存（TR-20260814-016，attempt 001 PASS + 修复 `3c3dfa0` + attempt 002 PASS，correlated_review）；"接受后点击树节点跳原文"与精确页/bbox 定位为后续增强；`relation_validate` 思考模式延迟较高为原型边界。

## 2026-08-15 — 第 8 步切片 3：AI 草案 API/Web 接入（WORK-2026-026）运维记录

- 关联 ID：WORK-2026-026、WORK-2026-009、WORK-2026-007/008、OPS-2026-003。
- 环境/版本/build/config：commit `dfbcc30`（feature/WORK-2026-009-ai-draft-pipeline）；local-dev Windows x64。
- 变更或症状：新增 `read_resource_text`、`POST /api/workspaces/{id}/ai-draft`（注入式 generator，无 Key 503 `ai_not_available`）、`apps/api/ai_draft.py`（DeepSeek 组合根，`DEEPSEEK_API_KEY` env-only）与 Web 生成/预览/接受/拒绝 UI；接受仍只经既有 `POST graph/patches` 提交门（锁定/revision/确认门）；无部署/常驻服务变化（沿用 `python -m apps.api` 启动，仅新增可选 generator 接线）。
- 影响：无部署或常驻服务变化；仅新增/扩展 Python 模块、端点、Web UI 与测试；`config/llm` 与 Provider 门控不变。
- 证据：pytest 394/394 + 5 skipped；validator（含 secret scan）/Ruff/mypy（scripts 11 + strict packages/api 30）全绿；Web 35/35、pnpm build 通过；live e2e（owner key env-only）导入→生成→接受闭环通过。
- 缓解/回滚：回退 `dfbcc30` 即回无 AI 草案 UI；不设 `DEEPSEEK_API_KEY` 则端点 503、UI「AI 未连接」；密钥仅 env。
- 遗留风险/Owner/期限：切片 3 职责隔离 QA 已封存（TR-20260814-015，attempt 001 FAIL → 修复 `d47ce88` → attempt 002 PASS，correlated_review）；来源锚点真实落库 + 点来源跳回原文为后续切片；`relation_validate` 思考模式延迟较高为原型边界。

## 2026-08-15 — 第 8 步切片 2：LLM 概念抽取/关系候选 live 冒烟（WORK-2026-009）运维记录

- 关联 ID：WORK-2026-009、WORK-2026-007/008、OPS-2026-003。
- 环境/版本/build/config：commit `1394a1e`（feature/WORK-2026-009-ai-draft-pipeline）；local-dev Windows x64。
- 变更或症状：新增 `knowledge_tree_infrastructure/ai_draft_llm.py`（`LlmConceptExtractor`/`LlmRelationProvider`）与 `scripts/ai_draft_live_smoke.py`；真实 DeepSeek 概念抽取（deepseek-v4-flash，thinking disabled）与关系判定（deepseek-v4-pro，thinking enabled）；草案仍只经提交门以 `requires_confirmation` 落库；无部署/常驻服务变化。
- 影响：无部署或常驻服务变化；仅新增 Python 模块/脚本/测试与证据报告；`config/llm` 与 Provider 门控不变。
- 证据：pytest 386/386 + 5 skipped；repository validator（含 secret scan）/Ruff/strict mypy 全绿；live 冒烟 `AI-DRAFT-LIVE-SMOKE-001`（极限/连续/导数/可导 + 4 条 prerequisite_of，preview=requires_confirmation，427/3435 tokens，~$0.004 USD，~57.5s）；报告 `evals/calculus-v1/ai-draft-live-smoke.json`；密钥仅 env，从未写入任何文件。
- 缓解/回滚：回退 `1394a1e` 即回启发式抽取；live 冒烟受 `RUN_LIVE_LLM_TESTS` + `DEEPSEEK_API_KEY` 双门控。
- 遗留风险/Owner/期限：切片 2 职责隔离 QA 已封存（TR-20260814-014，PASS，correlated_review）；切片 3（草案 API/Web 批量接受拒绝）待做；`relation_validate` 思考模式延迟较高（~57s）记录为原型边界。

## 2026-08-15 — 第 8 步切片 1：AI 草案流水线离线内核（WORK-2026-009）运维记录

- 关联 ID：WORK-2026-009、REQ-2026-006、NFR-2026-006。
- 环境/版本/build/config：commit `136f7fa`（feature/WORK-2026-009-ai-draft-pipeline）；本地 local-dev Windows x64；ruff 0.16.2。
- 变更或症状：新增纯领域 AI 草案内核与离线编排（分块/别名合并/DAG 校验/自动布局/patch 生成 + 确定性启发式抽取器）；草案仅产出 `proposed` + `requires_confirmation` 的 GraphPatch，经既有提交门才可能落库；本轮无真实 LLM 调用、无网络、无部署/常驻服务变化。
- 影响：无部署或常驻服务变化；仅新增两个 Python 模块与三个测试文件；`config/llm` 与真实 Provider 门控不变。
- 证据：pytest 368/368 + 5 skipped（新增 TC-AIDRAFT 20 个）；ruff format/check、strict mypy、validator、Web 32/32、pnpm build 全绿。
- 缓解/回滚：回退 `136f7fa` 即回到无 AI 草案能力；真实 DeepSeek 抽取为后续切片。
- 遗留风险/Owner/期限：真实 LLM 概念抽取（切片 2）与草案 API/Web 接入（切片 3）未做；本轮启发式抽取不冒充真实 AI 质量。

## 2026-08-14 — DeepSeek deployment 正式启用（owner 批准）

- 关联：WORK-2026-008、OPS-2026-003、LLM-COMPAT-BASELINE-001。
- 已完成：owner 批准后将 `config/llm/providers.yaml` 的 `deepseek.enabled` 置为 `true`；路由验证 concept_extract→deepseek/fast、relation_validate→deepseek/quality；OPS-2026-003 关闭（剩余生产遥测归后续可观测性）。
- 未完成：AI 草案流水线接入（第 8 步 WORK-2026-009）未开始；生产运行遥测/监控未建立。
- 当前缓解：真实调用仍仅显式构造 adapter（live 门控）；金额/attempt/回退预算约束生效；密钥仅 env 不落盘。
- 下一门：第 8 步 Ready 工作项 + 红灯测试；随后按需建立 Provider 运行遥测。

## 2026-08-14 — 交付检查：环境清单、费用风险与 Runbook 部分演练登记

- 关联：WORK-2026-007/008、RISK-2026-015、RB-PROV-001。
- 已完成：ENVIRONMENT_INVENTORY 记录 local-dev 的 DeepSeek provider snapshot 与 secret 引用状态（`env://DEEPSEEK_API_KEY`，present，不落盘）；新增 RISK-2026-015（LLM 费用失控，`max_cost_usd` 金额预算缺口）；RB-PROV-001 标记 adapter + live smoke 部分演练（5/5，金标与完整演练待后续）。
- 未完成：`max_cost_usd` 金额预算实现、EVAL-LLM-001 金标、RB-PROV-001 完整演练、职责隔离 QA 封存。
- 当前缓解：除 `mock` 外所有 provider `enabled: false`；live 仅 env 门控；max_tokens/attempt 约束（本轮 817 token 远低于 3 元）。
- 下一门：实现金额预算 + 金标评测，再 QA 批准 deployment。

## 2026-08-14 — 实现 DeepSeek adapter 与受控 live smoke（WORK-2026-008）

- 关联：WORK-2026-008、OPS-2026-003、LLM-COMPAT-BASELINE-001。
- 已完成：DeepSeek OpenAI Chat Completions 协议适配器 + vendor profile + stdlib 传输 + resilience 接线；离线契约测试 TC-DS-001..005 21/21；真实 live smoke 5/5（text/JSON/thinking/tool/stream，约 817 token，费用远低于 3 元预算）。
- 未完成：微积分金标评测 `EVAL-LLM-001`、`RB-PROV-001` 演练、DeepSeek deployment 正式批准（`enabled: true`）。
- 当前缓解：除 `mock` 外所有 provider `enabled: false`；live 仅 `RUN_LIVE_LLM_TESTS=1` + `DEEPSEEK_API_KEY` 门控；密钥只经环境变量，绝不落盘/日志/git。
- 下一门：金标评测与 RB-PROV-001 演练，再由 QA 批准 model policy 与 capability snapshot。

## 2026-08-14 — 冻结 LLM port 契约层与 mock adapter（WORK-2026-007，第 7 步离线第 1 期）

- 关联：WORK-2026-007、OPS-2026-003、LLM-COMPAT-BASELINE-001。
- 已完成：canonical LLM contract v1（`docs/contracts/llm.v1.schema.json`）与生成 artifact；`knowledge_tree_infrastructure/llm/`（canonical DTO/errors/capabilities/resilience/router/mock）；TC-LLM-001..009 mock 契约测试 56/56；全仓 314/314、validator/Ruff/mypy/Web 32/32/build 全绿。
- 未完成：OpenAI Chat Completions 协议适配器与 DeepSeek vendor profile（实施顺序 3–6）；DeepSeek live smoke、金标评测、RB-PROV-001 演练（顺序 7–8，WORK-2026-008）。
- 当前缓解：除 `mock` 外所有 provider `enabled: false`；无网络、无密钥解析、无费用；错误 details 与 fixture 脱敏。
- 下一门：实现协议适配器与 vendor profile（离线 fixture 契约测试），再按 owner 决策（受控 API Key/预算）进入 live smoke 门。

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
| OPS-2026-003 | 高 | DeepSeek 已配置/契约/adapter/金标/演练齐全并经 owner 批准 `enabled: true`；剩余为生产运行遥测未建立 | `enabled: true`（2026-08-14 owner 批准）；金额/attempt/回退三重预算约束，密钥仅 env 不落盘 | 待定 | 阶段 0/2 | closed（遥测归后续可观测性工作项） |

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

## 2026-08-14 01:55 — 内存回放/撤销 prototype 通过 QA

- 关联 ID：WORK-2026-011、TR-20260814-003。
- 环境/版本/build/config：Windows 11 x64；Python 3.12.6/uv 0.12.3；Node 24.14.1/pnpm 11.19.0；Ready `9d9f569`；红灯 `2425718`；实现 `4fc8e60`。
- 操作者：Codex（实现）；职责隔离 `graph_qa_fresh`（只读机器 QA，非人类签字/owner 接受）。
- 变更或症状：纯内存 history 支持最小 delta、顺序 replay、LIFO undo/redo、redo 分支清空和 tamper/hash/revision 冲突检测；无持久日志或运行服务变化。
- 时间线：Ready → 2 个预期 ImportError → 18/18 目标绿灯 → 154/154 全门绿 → QA attempt 001 PASS。
- 影响：无部署、端口、常驻进程、数据库、API、UI、网络、Provider、用户数据、秘密或费用；当前网页仍只是工程状态页。
- 证据：`TR-20260814-003`；history 18/18、graph 50/50、全仓 154/154、Web 1/1、完整门 PASS；QA 0 P0/P1/P2。
- 缓解/回滚：prototype 可整体禁用；不得把内存证明写成跨进程恢复/数据已持久化。记录未来落盘前需版本化 schema、迁移、隐私和损坏恢复门。
- 遗留风险/Owner/期限：ADR-0005/owner、SQLite operation log、periodic snapshot、crash recovery 和 UI 未完成；由后续工作项承接。

## 2026-08-14 03:04 — 本地知识树 Web Demo 验证

- 关联 ID：WORK-2026-012、TR-20260814-004。
- 环境/版本/build/config：Windows 11 x64；Python 3.12.6/uv 0.12.3；Node 24.14.1/pnpm 11.19.0；实现 `5aab0e3`；Vite 本地开发服务仅绑定 `127.0.0.1:4173` 用于浏览器验收。
- 操作者：Codex（实现、自动门与浏览器验证）；职责隔离 QA 正在只读审查冻结提交。
- 变更或症状：没有部署/发布；只启动短期本地预览。1440×900 document 为 1440×900，390×844 document client width 375/scroll width 375；画布自身承担 1000px 内部滚动。
- 时间线：Ready `87fb402` → 红灯 `4caa76a` → 实现 `5aab0e3` → QA-001 P1 → `c8c6bf9` 红灯 → `fff1ce6` 修复 → QA-002 PASS → 证据收口。
- 影响：无数据库、文件/浏览器持久化、网络模型、secret、真实用户数据或费用；不应输入需要保留的内容。
- 证据：`evidence/TR-20260814-004/`；Web 6/6、Python 154/154、完整门 PASS；桌面/手机截图及交互 metrics；浏览器 warning/error 0；职责隔离 QA PASS。
- 缓解/回滚：异常时停止本地 Vite 进程并回退 `5aab0e3`；因无持久状态，不存在数据 migration 或回滚数据。
- 验证：编辑/undo/redo、drag、lock-preserving layout、add/delete、reset、无 page-level 横溢、selection-only 不创建 history。
- 遗留风险/Owner/期限：没有托管可用性或安装包；持久化、备份/恢复和桌面生命周期由第 4/10 步承接。

## 2026-08-14 07:45 — 本地 SQLite 持久化 prototype 验证

- 关联 ID：WORK-2026-013、TR-20260814-005。
- 环境/版本/build/config：Windows 11 x64；Python 3.12.6/uv 0.12.3；Node 24.14.1/pnpm 11.19.0；sqlite3 3.45.3（stdlib）；commit `8e34a40`。
- 操作者：Codex（实现与 live 变异重放）；职责隔离 `graph_qa_fresh`（只读机器证明，非真人签字/owner 接受）。
- 变更或症状：新增本地 SQLite workspace prototype（数据目录、migration v1、save/load、backup/restore/export/purge、history records 落盘）；无部署或常驻服务变化。
- 时间线：`ec8005e` Ready → `1420b68` 红灯（2 个预期 ImportError）→ `8e34a40` 实现 → QA attempt 001 PASS → live 变异重放 8/8 PASS。
- 影响：无部署、端口、进程、网络、Provider、真实用户数据、秘密或费用；仅测试目录写 SQLite。
- 证据：`evidence/TR-20260814-005/` 与 `docs/test-reports/TR-20260814-005_local-sqlite-workspace.md`；目标 21/21、全仓 175/175、Web 6/6、完整本地门 PASS。
- 缓解/回滚：回退 `8e34a40` 禁用 prototype；不得复用内存 Demo 冒充保存。
- 验证：目录/重启存活/migration/备份导出删除/故障注入（截断、垃圾字节、非法图、重复 replay、digest 篡改、checksum 篡改、purge）全部失败关闭。
- 遗留风险/Owner/期限：浏览器自动保存/API/UI 接入、FTS5 搜索、导入、加密、多进程、云端与真实 Provider 保持关闭，由后续工作项承接。

## 2026-08-14 08:05 — 本地持久化 API sidecar 验证

- 关联 ID：WORK-2026-014、TR-20260814-006。
- 环境/版本/build/config：Windows 11 x64；Python 3.12.6/uv 0.12.3；Node 24.14.1/pnpm 11.19.0；fastapi 0.141.1/uvicorn 0.52.3；commit `e0a4c72`。
- 操作者：Codex（实现与 e2e smoke）；职责隔离 `graph_qa_fresh`（只读机器证明，非真人签字/owner 接受）。
- 变更或症状：新增本地 FastAPI sidecar（loopback/CORS/health/graph GET-PUT/backup）与 Web 自动保存接入；无部署或常驻服务变化。
- 时间线：`31ce814` Ready → `4fe918b` 红灯（API 1 ImportError + Web 4 失败）→ `6c0c33c` 实现 → QA-001 PASS（3 P2）→ `e0a4c72` P2-1 修复 → QA-002 PASS。
- 影响：无部署、端口常驻、网络出站、Provider、真实用户数据、秘密或费用；API 仅测试期临时监听 127.0.0.1:8123，已关闭。
- 证据：`evidence/TR-20260814-006/` 与 `docs/test-reports/TR-20260814-006_local-persist-api.md`；API 8/8、全仓 183/183、Web 10/10、完整本地门 PASS、e2e smoke PASS。
- 缓解/回滚：回退 `e0a4c72` 回到纯内存 Demo；不得把 prototype 冒充浏览器已保存。
- 验证：CORS/路径遍历/非法图 422/往返/备份校验和/缺失 backup 404/Web 加载/自动保存/降级全部失败关闭。
- 遗留风险/Owner/期限：Tauri 打包、认证/token（ADR-0011/SPK-009）、FTS5、导入、加密、多进程、云端与真实 Provider 保持关闭；P2-2/P2-3 前端已知边界记录在 QA 报告。

## 2026-08-14 08:40 — FTS5 基础搜索验证

- 关联 ID：WORK-2026-015、TR-20260814-007。
- 环境/版本/build/config：Windows 11 x64；Python 3.12.6/uv 0.12.3；Node 24.14.1/pnpm 11.19.0；sqlite3 3.45.3 FTS5；commit `d6c8e01`。
- 操作者：Codex（实现与 e2e smoke）；职责隔离 `graph_qa_fresh`（只读机器证明，非真人签字/owner 接受）。
- 变更或症状：新增 FTS5 派生索引与只读 search 端点、Web 搜索框；无部署或常驻服务变化。
- 时间线：`e451057` Ready → `eeba073` 实现（红灯与实现合并，偏差已披露）→ QA-001 PASS（3 P2）→ `d6c8e01` P2-2 修复。
- 影响：无部署、端口常驻、网络出站、Provider、真实用户数据、秘密或费用；API 仅测试期临时监听 127.0.0.1:8124，已关闭。
- 证据：`evidence/TR-20260814-007/` 与 `docs/test-reports/TR-20260814-007_fts5-search.md`；搜索 10/10、全仓 193/193、Web 12/12、完整本地门 PASS、e2e smoke PASS。
- 缓解/回滚：回退 `d6c8e01` 移除搜索；不影响持久化内核与证据。
- 验证：中文 label/note 子串命中、空/超长/非法查询 422、无匹配 200 空、缺失 404、snippet 截断、索引原子重建全部通过。
- 遗留风险/Owner/期限：中文分词、模糊/纠错、文件内容检索（第 5 步）保持关闭；P2-1/P2-3 前端已知边界记录在 QA 报告。第 4 步完成（100%）。

## 2026-08-14 09:15 — 安全文件导入验证

- 关联 ID：WORK-2026-016、TR-20260814-008。
- 环境/版本/build/config：Windows 11 x64；Python 3.12.6/uv 0.12.3；Node 24.14.1/pnpm 11.19.0；python-multipart 0.0.32；commit `eee15d0`。
- 操作者：Codex（实现与 e2e smoke）；职责隔离 `graph_qa_fresh`（只读机器证明，非真人签字/owner 接受）。
- 变更或症状：新增 schema v2 与安全文件导入（MD/TXT/PDF → 受控资源）；无部署或常驻服务变化。
- 时间线：`293c0ef` Ready → `50b3245` 红灯 → `10e104f` 实现 → QA-001 PASS（5 P2）→ `eee15d0` P2-1/P2-3 修复。
- 影响：无部署、端口常驻、网络出站、Provider、真实用户数据、秘密或费用；API 仅测试期临时监听 127.0.0.1:8125，已关闭。
- 证据：`evidence/TR-20260814-008/` 与 `docs/test-reports/TR-20260814-008_safe-import.md`；import 15/15、全仓 208/208、Web 15/15、完整本地门 PASS、e2e smoke PASS。
- 缓解/回滚：回退 `eee15d0` 回到 v1 库（迁移前数据保留）；不影响既有持久化证据。
- 验证：migration v1→v2、类型/伪造/超大/路径守卫、去重幂等、写失败无孤儿、列表元数据全部通过。
- 遗留风险/Owner/期限：PDF 解析/查看器、Markdown 渲染、Anchor 来源跳转、url/note 资源保持关闭；P2-2/P2-4/P2-5 已知边界记录在 QA 报告。

## 2026-08-14 09:45 — PDF 文本解析与 Anchor 来源跳转验证

- 关联 ID：WORK-2026-017、TR-20260814-009。
- 环境/版本/build/config：Windows 11 x64；Python 3.12.6/uv 0.12.3；Node 24.14.1/pnpm 11.19.0；pypdf 6.15.0；commit `267fb7e`。
- 操作者：Codex（实现与 e2e smoke）；职责隔离 `graph_qa_fresh`（只读机器证明，非真人签字/owner 接受）。
- 变更或症状：新增 schema v3 与 PDF 页文本解析/查看器/锚点端点；无部署或常驻服务变化。
- 时间线：`2829ff2` Ready → `53eb2cd` 红灯 → `8c3c620` 实现 → QA-001 PASS（6 P2）→ `267fb7e` P2-1/3/4/6 修复。
- 影响：无部署、端口常驻、网络出站、Provider、真实用户数据、秘密或费用；API 仅测试期临时监听 127.0.0.1:8126，已关闭。
- 证据：`evidence/TR-20260814-009/` 与 `docs/test-reports/TR-20260814-009_pdf-viewer-anchor.md`；viewer 10/10、全仓 218/218、Web 18/18、完整本地门 PASS、e2e smoke PASS。
- 缓解/回滚：回退 `267fb7e` 回到导入-only；不影响既有持久化与导入证据。
- 验证：解析幂等、页文本/越界/未解析/404、锚点 UPSERT/排序/缺失 404、漂移 source_changed 全部通过。
- 遗留风险/Owner/期限：PDF.js 渲染、bbox 高亮、Markdown/TXT 查看器、OCR、中文分词保持关闭；P2-2/P2-5 已知边界记录在 QA 报告。

## 2026-08-14 11:40 — PDF.js 可视化渲染与 bbox 高亮验证

- 关联 ID：WORK-2026-018、TR-20260814-010。
- 环境/版本/build/config：Windows 11 x64；Python 3.12.6/uv 0.12.3；Node 24.14.1/pnpm 11.19.0；pdfjs-dist 6.2.108；commit `d56e7ef`。
- 操作者：Codex（实现与浏览器 e2e）；职责隔离 `graph_qa_fresh`（只读机器证明，非真人签字/owner 接受）。
- 变更或症状：新增 PDF.js canvas 渲染与 bbox 高亮、file/anchors 端点；无部署或常驻服务变化。
- 时间线：`54a108b` Ready → `275d7c6` 红灯 → `2601215` 实现 → QA-001 FAIL（1 P1 + 7 P2）→ `d56e7ef` P1/P2-1/P2-4 修复。
- 影响：无部署、端口常驻、网络出站、Provider、真实用户数据、秘密或费用；API 仅测试期临时监听 127.0.0.1:8127，已关闭。
- 证据：`evidence/TR-20260814-010/` 与 `docs/test-reports/TR-20260814-010_pdfjs-render.md`；viewer 12/12、file 4/4、全仓 224/224、Web 20/20、完整本地门 PASS、浏览器 e2e（CDP 完整渲染/高亮/窄视口对齐）PASS。
- 缓解/回滚：回退 `d56e7ef` 回到页文本查看器；不影响既有持久化/导入/跳转证据。
- 验证：file 二进制/404/越界/文件缺失、anchors 注册/无效 422、bbox 百分比映射、窄视口对齐（aligned: true）、worker dev/build 一致性全部通过。
- 遗留风险/Owner/期限：文本层联动、多页连续滚动、Markdown/TXT 可视化、OCR、中文分词保持关闭；其余 P2 记录在 QA 报告。第 5 步完成（100%）。

## 2026-08-14 11:55 — 新增人工验证启动入口

- 关联 ID：WORK-2026-014/018。
- 环境/版本/build/config：commit `ff02c3e`。
- 变更或症状：新增 `uv run python -m apps.api --data-root <dir> [--port N] [--origin URL]` 启动入口（loopback + Vite dev origins 默认允许）；`apps/__init__.py`/`apps/api/__init__.py` 修正 mypy 包识别（此前 main.py 被匹配为 "main" 与 "apps.api.main" 两处）。
- 影响：无部署或常驻服务变化；纯开发者/人工验证便利。
- 证据：health 200、allowed origin 200、evil origin 无 ACAO 头；224/224 pytest、mypy 11 源文件、ruff 全绿。
- 缓解/回滚：回退 `ff02c3e` 即恢复无启动入口状态（临时脚本仍可用）。
- 遗留风险/Owner/期限：无新增风险；数据目录默认在用户主目录 `knowledge-tree-data`，用户应自行选择位置。

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

## 2026-08-14 12:10 — Windows 下 `uv run pytest` 的 venv 重定位环境缺口

- 关联 ID：WORK-2026-014..018。
- 环境/版本/build/config：Windows x64 本地；`uv run pytest` 解析到 `E:\知识树\.venv`（旧副本）而 `uv run python -m pytest` 正确解析到 `E:\知识树 - 副本\.venv`，导致 `uv run pytest` 下 `ModuleNotFoundError: No module named 'fastapi'`。
- 变更或症状：无代码缺陷；纯环境解析歧义。CI 已在干净 ubuntu 上改 `uv run python -m pytest`，本地门/README/AGENTS 同步。
- 影响：本地必须用 `uv run python -m pytest`；`uv run pytest` 不可信。
- 证据：`uv run python -m pytest` 224/224；`uv run pytest` 在 fastapi 上 ImportError。
- 缓解/回滚：无；为环境事实记录，不视为代码问题。
- 遗留风险/Owner/期限：若未来重装/迁移环境需复核 pytest 可执行文件指向；CI 与本地门统一命令后无行为分叉。

## 2026-08-14 12:20 — 交付检查两轮与第 5 步完成状态

- 关联 ID：WORK-2026-013..018、TR-20260814-005..010。
- 环境/版本/build/config：commit `bf35b18` + `f56c99e`。
- 变更或症状：交付检查关闭 DoD 缺口——本地门命令同步、README 能力状态、ERROR_CODE_CATALOG 已验证错误码表、RISK-2026-013/014、test-reports 索引补 TR-004..010、ENVIRONMENT_INVENTORY local-dev 更新、CI pytest 统一 `uv run python -m pytest`、OPS_LOG pytest 环境缺口登记；13 个 TR 证据 checksums 全量核验无漂移。
- 影响：无部署或常驻服务变化；CI 命令与本地门一致后无行为分叉。
- 证据：`bf35b18`/`f56c99e`；validator、Ruff、pytest 224/224、Web 20/20、diff-check 全绿；13 个 TR checksums 逐字节匹配。
- 缓解/回滚：回退两个提交仅撤销文档/CI 命令修正；不影响实现与证据。
- 验证：全量证据校验和核验（含截图/QA 报告/manifest）；早期 TR 校验此前误报为 mismatch 系校验脚本路径/格式问题，非内容漂移。
- 遗留风险/Owner/期限：人工验收按 `docs/USER_MANUAL.md` 清单执行；第 5 步完成（100%），下一主项第 6 步 WORK-2026-019；真实 Provider/Web 与 owner 接受保持禁用。

## 2026-08-14 12:30 — 交付检查发现：主分支滞后与 CI 未执行

- 关联 ID：WORK-2026-003、WORK-2026-006。
- 环境/版本/build/config：git main 停在 `9e15cb4`；HEAD（feature/WORK-2026-018）领先 main 64 个提交；CI workflow 仅触发 push main/PR。
- 变更或症状：非缺陷、非代码问题——交付检查发现的仓库治理缺口：
  1. main 停留在 WORK-2026-006 骨架基线，WORK-2026-002/004/005/011..018 的全部工作仅在 feature 分支，从未并入 main；
  2. 分支为线性继承链（每个新 feature 从上一分支切出），但未定义"何时合并 main"的明确门；
  3. 因所有工作都在 feature 分支，CI（仅 push main/PR 触发）从未实际运行，与 ENVIRONMENT_INVENTORY 的 `declared_not_executed` 一致；
  4. WORK-2026-003（确定仓库、许可证与分支保护）未开始，合并策略归属其范围。
- 影响：无运行影响；影响证据可追溯性与 CI 有效性声明。
- 证据：`git log --oneline main..HEAD | wc -l` = 64；`git branch -a` 列出 12 个 feature 分支；CI 触发条件 `on: push branches [main] / pull_request`。
- 缓解/回滚：无需回滚；不擅自合并 main（仓库治理属项目负责人决策，归 WORK-2026-003）。本地交付完整性不受影响（证据/日志/测试均在 feature 分支）。
- 遗留风险/Owner/期限：项目负责人决定 main 合并策略与远端仓库/许可证（WORK-2026-003）；在此之前 main 不作为当前状态的权威指针，以 feature/WORK-2026-018 与 checkpoint 为准。

## 2026-08-14 17:25 — 交付检查：第 6 步能力文档同步与运维记录

- 关联 ID：WORK-2026-019/020、REQ-2026-006/008、NFR-2026-001/003。
- 环境/版本/build/config：commit `3547cbb`（feature/WORK-2026-019-patch-gate）；本地 local-dev Windows x64。
- 变更或症状：交付检查关闭第 6 步（WORK-2026-019/020）的 DoD 文档缺口——CHANGELOG 补第 4–6 步用户可见变化（持久化/搜索/导入/PDF/锁定/撤销）；README 当前状态更新到第 6 步（约 60%、MVP 约 72%）；USER_MANUAL 增补内容/位置锁定与撤销能力、锁定被拒失败恢复与第 7 项人工验收清单、验证范围改为 Python 241/Web 22；OPS_LOG 登记本条目；work-items README、ENVIRONMENT_INVENTORY、RISK_REGISTER 同步。
- 影响：无部署或常驻服务变化；仅文档与运维事实同步。
- 证据：repository validator PASS；pytest 241/241、Web 22/22、CDP 浏览器端到端（锁定→409→撤销）PASS。
- 缓解/回滚：回退本次文档提交仅撤销文档修正；不影响实现与证据。
- 遗留风险/Owner/期限：职责隔离 QA（WORK-2026-019/020）仍待执行；普通编辑跨会话撤销、冲突预览/崩溃恢复 UI 归 WORK-2026-021；真实 Provider/Web 与 owner 接受保持禁用。

## 2026-08-14 20:30 — 第 6 步完成与 MD/TXT 查看器（WORK-2026-022/023）运维记录

- 关联 ID：WORK-2026-022/023、TR-20260814-013、REQ-2026-006/008/010、NFR-2026-001/003。
- 环境/版本/build/config：commit `962d165`（第 6 步完成）+ `78c5264`（MD/TXT 查看器），feature/WORK-2026-019-patch-gate；本地 local-dev Windows x64。
- 变更或症状：第 6 步人工编辑安全感完成（100%）——GraphPatch v1 新增 delete 契约，`save_course_graph` 改为 diff 生成 patch 走提交门，普通编辑跨会话撤销覆盖所有编辑；随后新增 Markdown/TXT 文本查看器（复用 file 端点，前端按 mime 分流）。职责隔离 QA（TR-013）FAIL（3 P1+2 P2）→ 修复 → 复审 PASS。
- 影响：无部署或常驻服务变化；后端写入路径从"整图替换"改为"diff + 提交门"（历史保留），删除了整图锁/revision 守卫（由提交门接管）；前端新增 `getResourceText` 方法。
- 证据：pytest 256/256、Web 28/28、ruff、strict mypy、validator、contracts-ts drift、pnpm 锁依赖/check/build 全绿；TR-013 evidence checksums OK。
- 缓解/回滚：回退 `78c5264` 回到 PDF-only 查看器；回退 `ab50aa2`/`7106621` 回到整图替换保存；不回退已验证 GraphPatch 提交门/纯领域 history。
- 遗留风险/Owner/期限：第 6 步 100%、MVP 约 75%；tombstone 软删除未引入（硬删除 + 历史可恢复）；真实 Provider/Web、owner 接受保持禁用，第 7 步 DeepSeek 适配待 owner 提供 API Key 与预算。

## 2026-08-14 20:55 — Markdown 富文本渲染（WORK-2026-024）运维记录

- 关联 ID：WORK-2026-024、REQ-2026-010、WORK-2026-023。
- 环境/版本/build/config：commit `0310061`（feature/WORK-2026-019-patch-gate）；本地 local-dev Windows x64。
- 变更或症状：Markdown 笔记从纯文本升级为富文本显示——新增 XSS 安全的 `renderMarkdown`（先 HTML 转义再应用最小 Markdown 语法），`text/markdown` 走 `markdown-body` 渲染视图，`text/plain` 保持纯文本；无第三方渲染依赖。
- 影响：无部署或常驻服务变化；仅前端查看器增强，无后端/schema 变化。
- 证据：`markdown.test.ts` 3/3（含注入转义）；pytest 256/256、Web 31/31、ruff、validator、build 全绿。
- 缓解/回滚：回退 `0310061` 即回到 Markdown 纯文本查看。
- 遗留风险/Owner/期限：Markdown 仅最小语法子集（无表格/链接）；真实 Provider/Web、owner 接受保持禁用。

## 2026-08-14 21:05 — 知识树画布平移与缩放（WORK-2026-025）运维记录

- 关联 ID：WORK-2026-025、REQ-2026-006、WORK-2026-012。
- 环境/版本/build/config：commit `8563fad`（feature/WORK-2026-019-patch-gate）；本地 local-dev Windows x64。
- 变更或症状：画布从 scroll-only 升级为 transform 平移/缩放——滚轮缩放（0.5–2.5×）、拖动空白平移、节点拖动按 zoom 换算；`canvas-viewport` 改为 `overflow:hidden`、`touch-action:none`；选中/搜索定位由 scrollLeft 改为 `centerOnNode` pan 定位。
- 影响：无部署或常驻服务变化；仅前端画布交互，无后端/schema 变化。
- 证据：Web 新增 wheel 缩放测试（transform scale 断言）；pytest 256/256、Web 32/32、ruff、validator、build 全绿。
- 缓解/回滚：回退 `8563fad` 即回到 scroll-only 画布。
- 遗留风险/Owner/期限：缩放已支持鼠标位置为中心（`62e0b72`）；真实 Provider/Web、owner 接受保持禁用。
