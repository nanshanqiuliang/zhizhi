# AI QA attempt 002 — incremental rebuild kernel fix (superseding, WORK-2026-030)

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: ai_qa_auditor
decision: pass
reviewed_commit: 120e34929683d4c5bee166f30a2028a96fd7de2f
supersedes: attempt 001 (da73951, PASS with 2 P2 + 2 P3)
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

**PASS** — 0 P0 / 0 P1。这是对修复提交 `120e349` 的超越审查（attempt 001 对 `da73951`
已 PASS，含 2 个非阻塞 P2 + 2 个 P3；本轮闭合 F1/F3，F2/F4 保持文档化边界）。

## Closure proofs

- **F1（label 变体裸 KeyError）— CLOSED**：`concept_ids` 改按 `normalize_concept_label`
  为键，边端点经规范化键解析；新回归 `test_incremental_patch_resolves_label_variants_in_relations`
  （概念 "导数 " + 关系 "导数"→"极限"）通过；独立脚本确认无 KeyError、`validate_contract`
  通过、`preview_graph_patch` → `requires_confirmation`（2 概念）。
- **F3（缺 revision_no 裸 KeyError）— CLOSED**：既有端点 revision 读用 `.get("revision_no", 0)`。
- **F2（跨图先修环）— 文档化边界，已验证**：builder 仅校验草案内部 DAG；跨图环由提交门
  `_apply_create_edge` 以 `graph_cycle_detected` 失败关闭。
- **F4（空白折叠）— 文档化边界，已验证**：`normalize_concept_label` = NFKC + casefold +
  空白折叠为单空格，模块级稳定键契约。

## Gates（本人执行，精确数字）

incremental 4/4；ai_draft 回归 20/20；全仓 425/425 + 5 skipped；ruff format/check pass
（92 文件）；strict mypy 33 文件；validator PASS（含 secret scan）。

## Behavioral checks

label 变体 → 合法 patch、契约有效、预览正确；跨图环 → 预览失败关闭；确定性（两次构建
相同 id_factory → 字节一致）；不可变性（输入图/草案不变）。

## Conclusion

PASS。`correlated_review`（机器证明、同源披露），非 owner 接受。
