# WORK-2026-030：增量重建纯领域内核（第 9 步切片 3a）

```yaml
status: ready
type: feature
owner: Codex (domain role)
reviewers: [ai_qa_auditor, workspace_owner]
related_ids: [WORK-2026-009, WORK-2026-005, WORK-2026-028, WORK-2026-029, REQ-2026-006, NFR-2026-001]
target_stage: "阶段 1 / 自然语言第 9 步切片 3a（增量重建纯领域内核）"
risk: medium
created_at: 2026-08-15T06:45:00+08:00
updated_at: 2026-08-15T06:45:00+08:00
```

## 问题与结果

- 用户/工程问题：第 9 步切片 1/2 已实现带来源问答与自然语言转 GraphPatch；但 AI 还不能"根据新笔记补充树"——即把新资料的概念/关系**增量地**并入既有知识树（不重建、不重复创建既有概念、关系端点可指向既有概念）。第 9 步"根据新笔记补充树"需要增量重建。
- 期望结果：纯领域函数 `build_incremental_patch(existing_graph, draft, ...)`——把一份 AiDraft（含既有+新概念）并入既有 CourseGraph，产出 `proposed` GraphPatch：**只**对全新概念 `create_concept` + `set_layout_item`，`create_edge` 的端点解析到既有或新概念 id（label 去重后映射）；既有概念不被重建；`prerequisite_of` 边/新 AI 概念必须携带 evidence；DAG/端点/证据校验失败关闭。无 LLM、无网络、无落库。
- 成功如何被观察：从失败测试启动；`build_incremental_patch` 确定性可测（去重、混合端点、布局仅新概念、证据、DAG、patch 经 `preview_graph_patch` 预览）；全仓门全绿。

## 范围

- In scope：
  - `packages/domain/.../ai_draft.py`：`build_incremental_patch(existing_graph, draft, *, workspace_id, course_id, base_revision_no, reason, actor_id, view_id, id_factory)`——label（规范化）去重映射到既有概念 id；仅新概念 `create_concept`（revision_no=0、origin=ai、review_state=proposed、confidence、evidence）+ `set_layout_item`；`create_edge` 端点解析既有/新 id（`expected_*_revision_no` 取对应概念当前 revision）；AI 概念与 `prerequisite_of` 边 evidence 非空（复用既有证据规则）；自环/重复边/DAG 由 `validate_draft` + 提交门拒绝。
  - 测试：`tests/unit/test_ai_draft.py`（或新 `tests/contract/test_ai_draft_incremental.py`）——去重、混合端点、布局仅新、证据缺失、cycle、patch 经 `preview_graph_patch` 预览。
- Out of scope：LLM 抽取器既有-label 注入（切片 3b）；`POST /rebuild` 端点与 Web（切片 3b）；`update_concept`/`update_edge`（后续）；向量检索；AI 修改历史。
- 受影响模块/接口/数据：扩展 `knowledge_tree_domain.ai_draft`；无 canonical contract/migration/prompt 变更（复用 GraphPatch v1）。
- 依赖和假设：WORK-2026-005（GraphPatch v1）、WORK-2026-009 切片 1（`AiDraft`/`validate_draft`/`build_draft_patch`）已验证；本轮纯领域、无网络、无 LLM。

## 设计边界

- 领域代码不 import FastAPI/存储/LLM SDK；纯函数 + 冻结数据类，确定性可重放。
- 去重以 `normalize_concept_label` 为键：draft 中 label 与既有概念同键 → 映射到既有 id（不 create、不 layout）；否则视为新概念（create + layout）。
- `create_edge` 端点解析：source/target 先查 draft 新概念 id，再查既有概念 id；二者都无 → `draft_invalid`（端点缺失）。
- `expected_*_revision_no`：新概念 = 0，既有概念 = 其当前 `revision_no`。
- 证据规则与 `build_draft_patch` 一致：AI 新概念与 `prerequisite_of` 边 evidence 非空，否则 `draft_evidence_required`。
- patch 恒 `origin=ai`（概念/边）+ `proposed` + `requires_confirmation=true` + `confirmed=false` + actor=ai。

## 风险影响

- 数据/schema/migration：无 schema/migration；纯新增函数与测试。
- 安全/隐私：错误仅标识不含正文；无网络。
- 并发/幂等/恢复：纯函数幂等；落库仍走提交门。
- 性能/容量/成本：O(V+E) 纯内存；零模型成本。
- 可观测性/诊断：稳定错误码 `draft_invalid`/`draft_evidence_required`/`draft_cycle_detected`；不落正文。
- 用户文档：路线第 9 步进度更新；明确"增量重建纯领域内核已实现，LLM 接线/端点/Web 为切片 3b"。

## 验收标准

- [ ] AC-1 (c1)：既有概念（label 去重命中）不重建——不产生 `create_concept`/`set_layout_item`。
- [ ] AC-2 (c2)：新概念产生 `create_concept` + `set_layout_item`；`create_edge` 端点正确解析既有/新 id 与 `expected_*_revision_no`。
- [ ] AC-3 (c3)：AI 新概念/`prerequisite_of` 边 evidence 缺失 → `draft_evidence_required`；成环/端点缺失/重复边 → 稳定拒绝。
- [ ] AC-4 (c4)：patch 经 `preview_graph_patch`（ai actor）预览 `requires_confirmation`；确定性（同输入同输出，注入 id_factory）。
- [ ] AC-5 (c5)：repository 门：validator、Ruff、scripts + strict package mypy、全仓 pytest、Web 全绿。
- [ ] 错误和恢复路径：空 draft/全既有/证据缺失/cycle 稳定失败关闭；不产出半成品 patch。
- [ ] 回滚/禁用方法：回退本工作项提交即回到无增量内核；红灯与证据保留。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-INCR-001 | unit | 去重 + 混合端点 | 既有不重建、新 create、边解析既有/新 id | 待实现 |
| TC-INCR-002 | unit | 证据/cycle/端点 | 缺失证据/成环/未知端点稳定拒绝 | 待实现 |
| TC-INCR-003 | contract | patch 预览 | `preview_graph_patch`(ai) `requires_confirmation` | 待实现 |
| TC-REPO-001 | repository | 全仓门 | validator/Ruff/mypy/pytest/Web | 待实现 |

## 交付物与关闭

- Commit/PR：分支 `feature/WORK-2026-009-ai-draft-pipeline`；Ready → 红灯 → 实现 → QA。
- Contract/ADR/migration/prompt：无新 canonical contract/ADR/migration/prompt；复用 GraphPatch v1。
- Test Run：TC-INCR-001..003 + 全仓门。
- Release：无托管发布；本轮无网络、无 LLM。
- 观察结果：增量重建纯领域内核确定性可测；仅新概念创建、关系端点可指向既有概念。
- 未完成项的新 ID：LLM 抽取器既有-label 注入 + `POST /rebuild` + Web（切片 3b）。
