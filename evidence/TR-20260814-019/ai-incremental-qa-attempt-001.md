# AI QA attempt 001 — incremental rebuild pure-domain kernel (WORK-2026-030, Step 9 slice 3a)

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: ai_qa_auditor
decision: pass
reviewed_commit: da73951a560c67304826df196263a75e1981e38b
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

**PASS** — 0 P0 / 0 P1；2 个非阻塞 P2 + 2 个 P3。这是对冻结提交 `da73951`
（WORK-2026-030 切片 3a：`build_incremental_patch` 增量重建纯领域内核）的职责隔离
机器审查。

## Red/green chain

Ready（docs）→ 红灯（`ImportError: build_incremental_patch`）→ 实现 `da73951`。
红灯真值经实际运行确认（scratch worktree @红灯 `pytest --collect-only` 1 error）。

## Gates（本人执行，精确数字）

incremental 3/3；ai_draft 回归 20/20；全仓 424/424 + 5 skipped；ruff format/check
pass（92 文件）；strict mypy 33 文件；validator PASS（含 secret scan）。

## Adversarial mutation review（scratch worktree，已删除）

去重（既有 label→既有 id、零 create/layout；全角/大小写/尾随空格变体去重）、边解析
（既有→新 2/0、新→新 0/0、既有→既有 2/2）、证据失败关闭、全部校验失败关闭（DraftError）、
patch 契约（validate_contract OK、preview requires_confirmation、create 先于 layout、
actor=ai、confirmed=false、base_revision=2）、确定性 + 不可变性均通过。

## Findings

| Sev | Finding |
|-----|---------|
| P2 | 关系 label 与概念 label 规范化相等但文本不同（如概念 "极限 " 与关系 "极限"）时，`validate_draft` 通过但 `concept_ids[raw]` 抛裸 KeyError（`concept_ids` 以 raw label 为键）；AI 抽取变体可达，违反稳定错误码规则。 |
| P2 | 跨图先修环（既有 A→B + 草案 B→A）构建期不拒绝——builder 返回完整 patch，由提交门 `preview_graph_patch` 以 `graph_cycle_detected` 拒绝（门级失败关闭，builder 层 defense-in-depth 缺口）。 |
| P3 | 畸形既有概念缺 `revision_no` → 裸 KeyError（上游图契约使 pipeline 不可达）。 |
| P3/INFO | 内部空白折叠为单空格（"极 限"≠"极限"）——模块级稳定键契约，非验收违规。 |

## Post-review fix

`120e349`：F1 `concept_ids` 改按 `normalize_concept_label` 为键（+ 变体回归）；F3
用 `.get("revision_no", 0)`。F2/F4 记录为文档化边界。

## Superseding review

见 `ai-incremental-qa-attempt-002.md`：对 `120e349` 返回 PASS（0 P0/P1）。
