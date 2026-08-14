# AI QA attempt 001 — diff-based ordinary-edit save (WORK-2026-022)

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: graph_qa_fresh
decision: fail
reviewed_commit: ab50aa280558dd4bd08738c0b83da88c84bfadee
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

**FAIL**，含 3 个 P1、2 个 P2。这是对冻结提交 `ab50aa2`（WORK-2026-022 GraphPatch v1 契约扩展 delete 操作 + 后端 diff 生成 patch，实现普通编辑 patch 化保存）的职责隔离只读机器审查。

契约扩展本身正确（oneOf/EdgeTarget/required 无冲突），但 diff 生成与 delete 应用存在锁绕过与覆盖缺口。

## Findings

### P1

- **`graph_patch.py:_apply_delete_concept`** — 级联移除 edges 时只对被删概念做四维锁检查，未对仍存活的另一端概念做 `relations` 锁检查。若 B 锁 relations，删除相邻 A 会静默移除 A-B 边，绕过 B 的 relations 锁。
- **`workspace.py:_build_diff_patch` 第 5 步** — 把 label 变化与 review_state/confidence/evidence_ids 变化拆成两个 `update_concept`，`_operation_target_key` 对 update_concept 只返回 `(update_concept, concept_id)`，同概念两个 op 被判 `duplicate_operation_target` 拒绝。
- **`workspace.py:_build_diff_patch` 第 6 步** — layout diff 只遍历 cur∩inc，新增概念的 layout_item 不生成 `set_layout_item`（新概念位置丢失）。

### P2

- edge 的同 id 字段修改不产出 op，`operations` 空时落到整图替换（清空历史 + 无锁保护）。
- 锁降级语义：diff 自动生成 `set_lock false` 视作用户主动解锁（设计权衡，建议前端加锁保真回归断言）。

## Post-review fix

- `7106621`：P1-1 在级联删边前对存活端点 `_ensure_unlocked(..., "relations")`；P1-2 合并 label+review 字段到一个 `update_concept` changes；P1-3 改为遍历 `inc_layout`（含新增概念 layout）；补 `test_delete_concept_rejects_surviving_relations_lock` 与 `test_new_concept_layout_is_preserved` 回归。P2-1（前端 edge id 由端点决定，同 id 字段修改不发生）与 P2-2（锁保真已有往返）记为边界。

## Superseding review

职责隔离复审（覆盖 7106621）返回 **PASS**，确认 P1-1/P1-2/P1-3 修复正确、无新增阻断；3 条 low nits（仅边界）记录。

修复后开发者实跑：pytest 256/256（diff_save_undo 4/4）、Web 27/27、ruff、strict mypy、repository validator、contracts-ts drift、pnpm 锁依赖/check/build 全绿。
