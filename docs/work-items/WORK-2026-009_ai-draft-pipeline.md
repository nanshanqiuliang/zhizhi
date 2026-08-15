# WORK-2026-009：AI 从笔记/资料自动生成知识树草案（第 8 步）

```yaml
status: in_progress
type: feature
owner: Codex (ai-draft + persistence + web role)
reviewers: [ai_qa_auditor, workspace_owner]
related_ids: [WORK-2026-004, WORK-2026-005, WORK-2026-007, WORK-2026-008, WORK-2026-016, WORK-2026-017, WORK-2026-018, NFR-2026-006, NFR-2026-007, NFR-2026-008, REQ-2026-006]
target_stage: "阶段 1 / 自然语言第 8 步（AI 自动生成知识树草案）"
risk: high
created_at: 2026-08-15T01:30:00+08:00
updated_at: 2026-08-15T02:40:00+08:00
```

## 问题与结果

- 用户/工程问题：第 0–7 步已完成（DeepSeek adapter 经 owner 批准 `enabled: true`，GraphPatch v1 提交门与安全文件导入/PDF 解析均验证）。用户已可导入 Markdown/TXT/PDF 并手工编辑知识树，但 AI 尚不能从笔记/资料自动生成知识树草案；"导入微积分资料 → 看到『极限 → 连续 → 导数……』带来源草案 → 确认后写入"的闭环缺失。
- 期望结果：把已授权的笔记/资料文本分块、抽取概念、别名合并、推断树状关系，输出带置信度与来源绑定的**不可信草案**；草案转成 `origin=ai`、`review_state=proposed`、`requires_confirmation=true` 的 GraphPatch v1，经既有提交门预览/校验后才可能落库；草案绝不直接写数据库、绝不覆盖锁定项。
- 成功如何被观察：从失败测试启动；纯领域内核（分块/别名合并/DAG 校验/自动布局/patch 生成）确定性可测；生成的草案 patch 通过 `preview_graph_patch` 与 `validate_contract("graph_patch")` 校验（origin=ai、evidence 绑定、无环、布局合法）；离线编排把"文档文本 → AiDraft → GraphPatch"端到端串通；全仓门全绿。

## 范围

- In scope：
  - `packages/domain/src/knowledge_tree_domain/ai_draft.py`：纯领域草案内核——`chunk_text`（段落边界优先的稳定分块）、`normalize_concept_label`（别名合并基础）、`merge_concept_candidates`（去重/别名合并/evidence 并集）、关系去重与自环/端点校验、`detect_prerequisite_cycle`（DAG 环检测）、`assign_draft_layout`（树状分层自动布局）、`build_draft_patch`（AiDraft → GraphPatch v1 operations：create_concept + create_edge + set_layout_item，origin=ai/review_state=proposed/confidence/evidence_ids/requires_confirmation/confirmed=false）。
  - `packages/infrastructure/src/knowledge_tree_infrastructure/ai_draft.py`：离线编排——`ConceptExtractor`/`RelationCandidateProvider` Protocol（注入式，未来接 DeepSeek adapter 不侵入领域），确定性启发式抽取器（无网络），`build_ai_draft`（文档文本 → 分块 → 抽取 → 合并 → 关系候选 → 校验 → 布局 → AiDraft）。
  - `packages/infrastructure/src/knowledge_tree_infrastructure/ai_draft_llm.py`（切片 2）：LLM 概念抽取与关系候选——`LlmConceptExtractor`/`LlmRelationProvider` 实现同一 Protocol，经 canonical LLM port（`concept_extract`/`relation_validate` task profile）真实抽取；形状违规失败关闭（`DraftExtractionError`），内容噪声（未知端点/自环/重复边）丢弃，证据绑定 chunk anchor；`deepseek_concept_extractor`/`deepseek_relation_provider` 组合辅助。
  - `scripts/ai_draft_live_smoke.py`（切片 2）：live 冒烟（`RUN_LIVE_LLM_TESTS` + `DEEPSEEK_API_KEY` 双门控）——真实 DeepSeek 抽取 → 草案 → GraphPatch → 提交门 `requires_confirmation` + 用量/费用报告（密钥仅 env 不落盘）。
  - 契约/单元测试：`tests/unit/test_ai_draft.py` + `tests/contract/test_ai_draft_contract.py`（草案 patch 通过 `preview_graph_patch`/`validate_contract`，DAG 无环、evidence 非空、布局合法、幂等确定）+ `tests/contract/test_ai_draft_llm.py`（切片 2：LLM 抽取/关系候选离线契约 18/18，确定性 MockLlmAdapter，无网络）。
- Out of scope：草案 API 端点与 Web 批量接受/拒绝 UI（复用既有 `POST graph/patches` 提交门，UI 接入为切片 3）；向量检索（第 9 步）；PPTX/DOCX/OCR（第 11 步）。
- 受影响模块/接口/数据：扩展 `knowledge_tree_domain`（新增 `ai_draft` 子模块）与 `knowledge_tree_infrastructure`（新增 `ai_draft`、`ai_draft_llm` 子模块）与 `scripts`（live 冒烟）；新增三个测试文件；无 canonical contract/migration/prompt 变更；不改动 `config/llm` YAML 语义。
- 依赖和假设：WORK-2026-005（GraphPatch v1 + 环检测 + 锁定语义）、WORK-2026-007（canonical LLM contract）、WORK-2026-008（DeepSeek adapter，owner 已批准 `enabled: true`）、WORK-2026-016/017/018（安全导入/资源文本读取）已验证；切片 2 发起受控真实 LLM 调用（live 冒烟受双门控 + task profile 金额预算约束）；草案仅生成 `proposed` + `requires_confirmation` 的不可信 patch，确认/落库仍由既有提交门与用户控制。

## 设计边界

- 领域代码不 import FastAPI/存储/LLM SDK/parser 库；`ai_draft.py` 为纯函数 + 冻结数据类，确定性可重放。
- 别名合并以 `normalize_concept_label`（大小写/空白/全半角归一）为键，label 保留首个出现的原文，aliases 记录后续变体；evidence 取并集，confidence 取最大值。
- DAG 约束：`prerequisite_of` 边不得成环（含自环）；关系去重以 `(source, target, edge_type)` 为键；边端点必须存在于概念集。
- 自动布局：按 `prerequisite_of` 拓扑分层（`related_to`/`part_of`/`example_of` 不参与分层，作为同层或就近层摆放），每层水平等距排布；`view_id` 固定为课程视图。
- patch 生成：所有 AI 概念/`prerequisite_of` 边必须携带非空 `evidence_ids`（否则 `preview_graph_patch` 以 `evidence_required` 拒绝）；`create_concept` 先于 `set_layout_item`（新建概念 revision=0）；`requires_confirmation=true`、`confirmed=false`、`origin=ai`。
- 确定性：同一输入 + 同一抽取器 → 同一 AiDraft 与 patch（UUIDv7 由调用方注入/可注入 `id_factory`）。

## 风险影响

- 数据/schema/migration：无 schema/migration；纯新增 Python 模块与测试。
- 安全/隐私：草案不读真实用户数据之外的任何内容；错误仅含标识不含正文；不发起网络调用（本轮离线）。
- 并发/幂等/恢复：草案生成为纯函数幂等；落库仍走幂等 change_id 提交门，草案本身不写库。
- 性能/容量/成本：分块/合并/布局为 O(n)/O(V+E) 纯内存；本轮零模型成本。
- 可观测性/诊断：稳定错误码（`draft_invalid`、`draft_cycle_detected` 等）+ 标识化 details；不落正文。
- 用户文档：路线第 8 步进度更新；明确"草案流水线纯领域内核与离线编排已实现，真实 DeepSeek 抽取为后续切片，草案确认后经提交门写入"。

## 验收标准

- [x] AC-1 (c1)：`chunk_text` 稳定分块（段落边界优先、重叠可控、边界不切碎句子），同输入同输出。
- [x] AC-2 (c2)：`merge_concept_candidates` 按规范化标签去重合并（label 保留首现原文、aliases 并集、evidence 并集、confidence 取 max）。
- [x] AC-3 (c3)：关系去重 + 自环/端点缺失拒绝 + `detect_prerequisite_cycle` 检出环并返回环路径。
- [x] AC-4 (c4)：`assign_draft_layout` 按 prerequisite 拓扑分层，同层水平排布，view_id 固定，布局项与概念一一对应。
- [x] AC-5 (c5)：`build_draft_patch` 生成的 GraphPatch 通过 `preview_graph_patch`（trusted_actor=ai）与 `validate_contract("graph_patch")`；concept/edge 为 `origin=ai`、`review_state=proposed`、`confidence∈[0,1]`、AI 概念与 `prerequisite_of` 边 `evidence_ids` 非空、`requires_confirmation=true`、`confirmed=false`。
- [x] AC-6 (c6)：离线编排 `build_ai_draft` 端到端"文本 → AiDraft → 合法 patch"，确定性、无网络。
- [x] AC-7 (c7)：repository 门：validator、Ruff、scripts + strict package mypy、全仓 pytest、Web 全绿。
- [x] AC-8 (c8，切片 2)：`LlmConceptExtractor`/`LlmRelationProvider` 离线契约——mock adapter 无网络抽取/关系候选；形状违规（缺列表/缺 label/confidence 越界/aliases 非法/未知边类型）以 `draft_extraction_failed` 失败关闭；未知端点/自环/重复边丢弃；证据绑定 chunk anchor；抽取器失败不掩盖纯领域校验。
- [x] AC-9 (c9，切片 2)：live 冒烟（`RUN_LIVE_LLM_TESTS` + `DEEPSEEK_API_KEY`）——真实 DeepSeek 抽取概念与 `prerequisite_of` 候选，草案 patch 经提交门 `requires_confirmation`；报告仅含 label/用量/费用；密钥仅 env。
- [x] 错误和恢复路径：空文本/空概念/成环草案以稳定错误码拒绝，不产出半成品 patch；抽取器失败不掩盖纯领域校验结果；LLM 输出无 JSON/截断时失败关闭。
- [x] 回滚/禁用方法：回退本工作项提交即回到无 AI 草案能力；不触碰 `config/llm` 与真实 Provider 门控；红灯与证据保留。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-AIDRAFT-001 | unit | 文档分块（段落边界/重叠/确定性） | 稳定 chunk，不切碎句子 | 20/20（`136f7fa`） |
| TC-AIDRAFT-002 | unit | 别名合并（大小写/空白/全半角） | 去重合并、evidence 并集、confidence max | 20/20（`136f7fa`） |
| TC-AIDRAFT-003 | unit | 关系去重/自环/端点缺失/DAG 环检测 | 稳定拒绝、返回环路径 | 20/20（`136f7fa`） |
| TC-AIDRAFT-004 | unit | 自动布局（拓扑分层） | 分层正确、布局一一对应 | 20/20（`136f7fa`） |
| TC-AIDRAFT-005 | contract | 草案 → GraphPatch 通过提交门 | preview/validate 通过、origin=ai、evidence 非空 | 20/20（`136f7fa`） |
| TC-AIDRAFT-006 | integration | 离线编排端到端 | 文本→AiDraft→合法 patch，确定性无网络 | 20/20（`136f7fa`） |
| TC-AIDRAFT-007 | contract | LLM 抽取/关系候选离线契约（切片 2） | mock adapter 抽取/关系候选 + 失败关闭 + 噪声丢弃 + evidence 绑定 + 端到端 patch | 18/18（`1394a1e`） |
| TC-AIDRAFT-008 | e2e/live | live 冒烟（切片 2） | 真实 DeepSeek 抽取→草案→提交门 requires_confirmation，报告无正文无密钥 | AI-DRAFT-LIVE-SMOKE-001（`1394a1e`，~$0.004） |
| TC-REPO-001 | repository | 全仓门 | validator/Ruff/mypy/pytest/Web | 386/386 + 5 skipped、Web 32/32（`1394a1e`） |

## 交付物与关闭

- Commit/PR：分支 `feature/WORK-2026-009-ai-draft-pipeline`；Ready `c9f2875` → 红灯 `c9f2875`（3 collection error）→ 实现 `136f7fa`（切片 1）→ 无关历史文件 ruff format 修复 `cc23c91` → 切片 2 实现 `1394a1e`（过程披露：切片 2 红灯测试与实现合并为同一提交，红灯真值由父提交 `1407427` 无 `ai_draft_llm` 模块/测试文件确认）。
- Contract/ADR/migration/prompt：无新 canonical contract/ADR/migration/prompt；复用 `docs/contracts/knowledge-tree-graph.v1.schema.json`（GraphPatch v1）、`docs/contracts/llm.v1.schema.json` 与 `config/llm` v1。
- Test Run：TC-AIDRAFT-001..007 38/38；全仓 pytest 386/386 + 5 skipped；validator/Ruff/strict mypy（packages 26 + scripts 11）/Web 32/32/pnpm build 全绿；live 冒烟 `AI-DRAFT-LIVE-SMOKE-001` 通过。
- Release：无托管发布；真实 DeepSeek 抽取已 live 验证但仅限显式构造 adapter（live 双门控）；`config/llm` 与 Provider 门控不变。
- 观察结果：草案流水线纯领域内核确定性可测、无网络、零模型成本（切片 1）；LLM 抽取/关系候选离线契约可测、live 冒烟费用 < $0.01（切片 2）；草案 patch 经 `preview_graph_patch` 以 ai actor 预览通过，`requires_confirmation=true`，绝不直写库。
- 未完成项的新 ID：草案 API 端点与 Web 批量接受/拒绝（第 8 步切片 3，复用 `POST graph/patches` 提交门）。
