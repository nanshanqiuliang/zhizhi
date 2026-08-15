# WORK-2026-031：增量重建 LLM 接线（第 9 步切片 3b）

```yaml
status: ready
type: feature
owner: Codex (ai-draft + api role)
reviewers: [ai_qa_auditor, workspace_owner]
related_ids: [WORK-2026-030, WORK-2026-009, WORK-2026-026, WORK-2026-027, REQ-2026-006, NFR-2026-001, NFR-2026-006, NFR-2026-007, NFR-2026-008]
target_stage: "阶段 1 / 自然语言第 9 步切片 3b（增量重建 LLM 接线）"
risk: medium
created_at: 2026-08-15T07:45:00+08:00
updated_at: 2026-08-15T07:45:00+08:00
```

## 问题与结果

- 用户/工程问题：切片 3a 已实现 `build_incremental_patch` 纯领域内核，但草案生成仍用
  `build_ai_draft` + `build_draft_patch`（全量重建）——对非空图会重复创建既有概念（同 label
  新 id）。切片 3b 把增量内核接上真实 LLM 抽取器，使 `/ai-draft` 自动增量：既有概念去重、
  关系端点可指向既有概念、仅新概念创建。
- 期望结果：`build_incremental_ai_draft(existing_graph, text, ..., extractor, relation_provider)`
  ——抽取新概念、对既有概念去重、以"既有占位 + 新概念"并集让关系提供器跨图提议、过滤
  既有↔既有关系；generator 改用 `build_incremental_ai_draft` + `build_incremental_patch`，使
  `POST /ai-draft` 对非空图只产生新概念创建 + 跨图关系（经提交门确认后写入）。不写库、无新
  canonical contract/迁移/prompt。
- 成功如何被观察：从失败测试启动；`build_incremental_ai_draft` 离线确定性（去重、跨图关系、
  过滤既有↔既有）；generator 端到端（mock/fake）产出 `build_incremental_patch` 合法 patch；
  全仓门全绿。

## 范围

- In scope：
  - `packages/infrastructure/.../ai_draft.py`：`build_incremental_ai_draft(existing_graph, text, *, resource_id, extractor, relation_provider, chunk_id_factory, anchor_id_factory, chunk_size, overlap)`——复用 `chunk_text`/`merge_concept_candidates` 抽取新概念、按规范化 label 对既有图去重、构造"既有占位（empty evidence）+ 新概念"并集、调用关系提供器、过滤既有↔既有关系（保留 ≥1 新端点）。
  - `apps/api/ai_draft.py`：`build_deepseek_draft_generator` 改为增量路径——`build_incremental_ai_draft` + `build_incremental_patch`；返回的 `draft.concepts` 仅新概念（供展示），`evidence` 仍为确定性资源级锚点。
  - 测试：`tests/contract/test_ai_draft_incremental.py`（或新 `tests/integration/test_ai_draft_incremental.py`）——`build_incremental_ai_draft` 离线去重/跨图关系/过滤；端到端 fake/mock 产出合法增量 patch 且无重复 create。
- Out of scope：`update_concept`/`update_edge`（证据增强/既有概念更新，后续）；`POST /rebuild` 独立端点（复用既有 `/ai-draft`，不新增端点）；Web UI 变更（既有「生成草案」自动增量）；向量检索；AI 修改历史。
- 受影响模块/接口/数据：扩展 `knowledge_tree_infrastructure.ai_draft` 与 `apps/api/ai_draft.py`；无 canonical contract/migration/prompt 变更（复用 GraphPatch v1 + `build_incremental_patch`）。
- 依赖和假设：WORK-2026-030（`build_incremental_patch`）、WORK-2026-009 切片 1/2（抽取器/关系提供器）、WORK-2026-026/027（`/ai-draft` 端点 + accept）已验证；生成只读、仅确认后写库；真实 LLM 调用仅 `DEEPSEEK_API_KEY` opt-in。

## 设计边界

- 领域/契约不变：`build_incremental_patch` 输出 `origin=ai`/`proposed` patch；generator 沿用
  既有 re-authoring（origin→user/review_state→accepted/confidence→null，保留 evidence + reason）。
- 去重以 `normalize_concept_label` 为键：新候选命中既有 label → 丢弃（不重建）；新概念保留。
- 关系过滤：仅保留 ≥1 新端点的关系（既有↔既有关系丢弃，避免无证据 prerequisite_of 与冗余边）。
- 展示载荷：`draft.concepts` 仅新概念；`draft.relations` 为全部跨图关系；`evidence` 为确定性
  资源级锚点（同切片 4）。
- 生成只读、失败关闭；错误 details 仅标识不含正文。

## 风险影响

- 数据/schema/migration：无 migration；仅新增编排函数与 generator 改动。
- 安全/隐私：命令/文本仅进 user 消息、不落盘/日志；密钥仅 env。
- 并发/幂等/恢复：生成无副作用；接受走幂等提交门。
- 性能/容量/成本：O(V+E) + 单次 LLM 抽取/关系调用，受 task profile 预算约束。
- 可观测性/诊断：稳定错误码 `draft_invalid`/`draft_evidence_required`/`ai_not_available`。
- 用户文档：用户手册补"生成草案自动增量（既有概念不重复创建）"；路线第 9 步进度更新。

## 验收标准

- [ ] AC-1 (c1)：`build_incremental_ai_draft` 对既有图去重（新候选命中既有 label 不重复）；并集传给关系提供器；过滤既有↔既有关系。
- [ ] AC-2 (c2)：generator 用 `build_incremental_ai_draft` + `build_incremental_patch` 产出合法 patch；`draft.concepts` 仅新概念。
- [ ] AC-3 (c3)：端到端（fake/mock）对非空图无重复 `create_concept`；关系端点解析既有 id；`preview_graph_patch`(ai) `requires_confirmation`。
- [ ] AC-4 (c4)：空图退化为全量（与 `build_draft_patch` 等价，无回归）。
- [ ] AC-5 (c5)：repository 门：validator、Ruff、scripts + strict package mypy、全仓 pytest、Web 全绿。
- [ ] 错误和恢复路径：空文本/证据缺失/成环稳定失败关闭；不产出半成品 patch。
- [ ] 回滚/禁用方法：回退本工作项提交即回到全量草案生成；红灯与证据保留。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-INCRB-001 | unit | `build_incremental_ai_draft` 离线 | 去重 + 跨图关系 + 过滤既有↔既有 | 待实现 |
| TC-INCRB-002 | integration | generator 端到端 | 非空图无重复 create + 预览 requires_confirmation | 待实现 |
| TC-INCRB-003 | integration | 空图退化 | 与全量等价 | 待实现 |
| TC-REPO-001 | repository | 全仓门 | validator/Ruff/mypy/pytest/Web | 待实现 |

## 交付物与关闭

- Commit/PR：分支 `feature/WORK-2026-009-ai-draft-pipeline`；Ready → 红灯 → 实现 → QA。
- Contract/ADR/migration/prompt：无新 canonical contract/ADR/migration/prompt。
- Test Run：TC-INCRB-001..003 + 全仓门。
- Release：无托管发布；真实 DeepSeek 调用仅 `DEEPSEEK_API_KEY` opt-in。
- 观察结果：`/ai-draft` 对非空图增量（不重复创建既有概念），跨图关系可指向既有概念。
- 未完成项的新 ID：`update_concept`/`update_edge`（证据增强）、向量检索、AI 修改历史。
