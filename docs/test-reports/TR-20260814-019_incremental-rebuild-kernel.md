# TR-20260814-019：增量重建纯领域内核验证（WORK-2026-030，第 9 步切片 3a）

> 本报告密封 `120e34929683d4c5bee166f30a2028a96fd7de2f` 的
> WORK-2026-030（第 9 步切片 3a：`build_incremental_patch` 增量重建纯领域内核）。
> 它证明新资料草案可确定性并入既有知识树——既有概念去重不重建、仅新概念创建+布局、
> 关系端点解析既有/新 id、证据/DAG 失败关闭、产出 `proposed` patch 经提交门预览。

```yaml
status: passed
test_level: unit_contract_repository
owner: ai_qa_auditor
related_ids: [WORK-2026-030, WORK-2026-009, WORK-2026-005, REQ-2026-006, NFR-2026-001]
build_id: 120e34929683d4c5bee166f30a2028a96fd7de2f
started_at: 2026-08-15T06:45:00+08:00
finished_at: 2026-08-15T07:30:00+08:00
supersedes: null
```

## 目的与门槛

- 证明 `build_incremental_patch` 把新资料草案并入既有图：label 去重映射既有 id（不重建/
  不重排）、仅新概念 `create_concept`+`set_layout_item`、`create_edge` 端点解析既有/新 id
  且 `expected_*_revision_no` 正确、新 AI 概念与 `prerequisite_of` 边证据必需。
- 证明失败关闭：未知端点/证据缺失/草案内成环/空 reason/重复 label 稳定拒绝；label 变体
  （文本不同但规范化相同）不产生裸 KeyError。
- 证明产出 patch 经 `preview_graph_patch`（ai actor）`requires_confirmation`、确定性、不突变输入。

## 方法与结果

| Test ID | 场景 | Actual | Result |
|---|---|---|---|
| TC-INCR-001 | 去重 + 混合端点 | 既有不重建、新 create+layout、边解析既有/新 id | PASS |
| TC-INCR-002 | 证据/cycle/端点/label 变体 | 稳定拒绝；无裸 KeyError | PASS |
| TC-INCR-003 | patch 预览 | `preview_graph_patch`(ai) `requires_confirmation` | PASS |
| TC-REPO-001 | 完整门 | pytest 425/425 + 5 skipped；Ruff；strict mypy（33）；validator | PASS |
| QA-001/002 | 职责隔离对抗审查 | attempt001 PASS（0 P0/P1，2 P2+2 P3）→ 修复 `120e349` → attempt002 PASS（0 P0/P1） | PASS |

职责隔离 QA：attempt 001 对冻结 `da73951` 返回 **PASS**（0 P0/P1；2 P2 + 2 P3：label 变体
裸 KeyError、跨图先修环构建期缺口、缺 revision_no 裸 KeyError、空白折叠）；修复 `120e349`
（`concept_ids` 改按规范化键 + 变体回归、`.get("revision_no", 0)`）后 attempt 002 返回
**PASS**（0 P0/P1；F2 跨图环由提交门失败关闭、F4 为模块级稳定键契约，均文档化边界）。
QA 为只读机器审查；`correlated_review`，非 owner 接受。

## 证据

- `evidence/TR-20260814-019/`：attempt 001/002 报告、`manifest.json`、`checksums.sha256`、
  `commands.txt`、`environment.json`、`gate-summary.txt`。
- 全仓 pytest 425/425 + 5 skipped；validator PASS；Ruff/strict mypy 全绿。本轮纯领域、无网络。

## 遗留边界

- 跨图先修环在 builder 层不拒绝（由提交门 `preview_graph_patch` 以 `graph_cycle_detected`
  失败关闭）；`normalize_concept_label` 空白折叠为单空格为模块级稳定键契约。
- 切片 3b（LLM 抽取器既有-label 注入 + `POST /rebuild` + Web）为下一步；向量检索受
  Embedding provider 未决阻塞；AI 修改历史待后续。
- `correlated_review`：机器证明、同源披露；最终残余风险接受归 workspace owner。
