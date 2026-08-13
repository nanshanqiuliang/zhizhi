# AI QA Machine Attestation — Attempt 001

```yaml
attestation_type: machine_attestation
schema_version: ai-qa-report.v2
actor_type: ai_agent
role_id: ai_qa_auditor
decision: fail
reviewed_commit: db0831b0806d82e7bab95e2ad804bfe69e8d81cd
subject_artifact: evidence/TR-20260813-005/ai-subject-attempt-003.md
subject_artifact_sha256: 9905ca560d6776427db4d890f498fa7f8ab68601f21b187e91590a64ea6ec2b1
subject_hash_verified: true
subject_commit_binding_verified: true
workspace_modified: false
network_used: false
human_signature: false
owner_acceptance: false
correlation_classification: correlated_review
```

## Independent run

本次是新的只读 QA run，使用独立角色/context，不继承学科搜索摘要，不读取隐藏推理，不修改文件、不提交、不联网。因模型/Provider 独立性没有外部证明，保守披露为 `correlated_review`。

最终 subject artifact SHA-256 已重算并匹配预期，且其元数据绑定 `db0831b0806d82e7bab95e2ad804bfe69e8d81cd`。

## Findings

### P1 — Mock artifact 可重标为 controlled-live 并提升为 machine_verified

validator 信任调用者提供的 execution mode/evidence basis/subject evidence/product eligible 布尔值。把 mock artifact 改为 controlled-live/controlled-sources、两个资格布尔为 true、machine_verified、QA pass、failure null 后，validator 错误接受；实际 mock provenance/replay trace 未发生变化。

### P1 — Tool/evidence audit chain 完整性与 trace hash 未校验

validator 只检查 allowlist、数量上限和重复 call ID，不绑定 query/result hash/status 与 evidence/provider result。以下变异被错误接受：subject/QA `tool_trace=[]`；trace query hash/result hash 改为伪值且 status=denied。

### P1 — Owner risk acceptance 可被冒充且过期仍被接受

validator 只检查内容/policy/risk code 和 `expires_at > accepted_at`，不认证 owner，也不校验当前未过期。`owner_id=untrusted_ai_claiming_owner`、2000 年已过期时间仍被错误接受。

### P2 — Finding claim_id 未绑定 item identity

coverage 使用 item kind/id，而 evidence 使用调用方独立提供的 claim ID。把 finding 的 claim/evidence 换成另一合法 claim 但保留原 item identity 后被错误接受。

### P2 — Provenance tool-policy hash 未绑定有效策略

只验证 hash 等于调用方 `tool_policy.version` 的自哈希，不与 effective role policy/allowlist 比较；任意攻击者版本及配套自哈希被错误接受。

### P2 — Adjudicator 可与 subject 共享 mutable session

只要求 distinct agent run；把 adjudicator session 改为 subject session 后仍被错误接受。

## Confirmed controls

- 裁决 support 作为 counterevidence：拒绝。
- dataset drift：`review_input_drifted`。
- controlled-live `product_eligible=true` 且 subject evidence=false：拒绝。
- QA 错误 subject artifact binding：现有测试/validator 拒绝。
- 保持 mock label 的产品状态：拒绝。

## Independent recomputation

```yaml
schema_errors: 0
concepts_relations_anchors: 30/40/50
ids_unique: true
dag_nodes_visited: 30
dag_acyclic: true
relation_endpoint_errors: 0
anchor_reference_errors: 0
declared_and_observed_sections: [2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7]
anchor_page_range: 1..50
pdf_pages: 52
pdf_bytes: 736149
pdf_sha256: c6a89688e956bc83c75c073068e9be3e7e8317377bd34e2a9d905fcb1af119fb
review_coverage: 30/40/50
review_subject_sha256: 54021dcac42e5e5030aaa2109d09a8ca0393e51ca7d87f2ac3e76075178a4574
```

Subject attempts 001/002 的 dispute 与对应 revision 缺陷一致；003 正确说明其限定范围内的两个问题已修复，但不构成整体 QA ready。

## Gates

仓库规定的 uv/Python/ruff/mypy/pytest/pnpm peers/check/build 全部退出 0；pytest 为 77 passed。安全变异仍复现上述 P1/P2，因此门绿不改变 `fail`。

## Limitations

- 未运行真实 Provider、controlled-live 或新 52 页视觉复核。
- 这是 AI machine attestation，不是真人签字、发布批准或 workspace-owner 风险接受。
