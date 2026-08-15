# AI QA attempt 002 — AI draft source-anchor fix (superseding, WORK-2026-027 slice 4)

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: ai_qa_auditor
decision: pass
reviewed_commit: 3c3dfa0782a8fde6c1c3dca6f84db4c1a45d1598
supersedes: attempt 001 (38df493, PASS with 3 P2)
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

**PASS** — 0 P0 / 0 P1。这是对修复提交 `3c3dfa0` 的超越审查（attempt 001 对 `38df493`
已 PASS，含 3 个非阻塞 P2；本轮闭合 P2-1/P2-3，P2-2 保持文档化边界）。

## Closure proof

- **P2-1（evidence 校验）— CLOSED**：`post_ai_draft_accept` 对每个 evidence item 要求
  `anchor_id`/`resource_id` 为字符串且 `_is_uuidv7`（version==7 + RFC 4122 变体），否则
  422 `evidence_item_invalid`；校验先于 `accept_ai_draft`，无写可能。独立验证：空 anchor_id、
  非 UUIDv7 resource_id、UUIDv4 anchor_id、非 list evidence 均 422，且拒绝后
  `list_anchors==[]`、图 concepts `==[]`（无任何写）。
- **P2-3（仓库回归）— CLOSED**：`test_accept_ai_draft_accept_writes_no_anchors_on_gate_rejection`
  （未确认 patch → 非 200，锚点空 + 图 concepts 空）、`test_ai_draft_accept_endpoint_validation_codes`
  （缺 patch 422 / 非 list evidence 422 / 空 anchor_id 422）、Web
  `omits jump-to-source when the draft has no evidence` 均存在且通过。
- **P2-2（跨资源 id 复用）— 文档化边界，确认准确**：`anchor_id = deterministic_uuidv7(resource_id)`
  （SHA-256 派生 v7，资源 1:1 幂等）；跨资源复用需 SHA-256 碰撞，生产不可达。

## Gates（本人执行，精确数字）

pytest accept 7/7；全仓 402/402 + 5 skipped；ruff format/check pass（86 文件）；
strict mypy 30 文件；validator PASS（含 secret scan）；Web draft 5/5；`pnpm check`
37 tests（9 files）+ tsc + eslint 0 warnings。

## Core properties — no regression

原子性（单事务图+历史+锚点，回滚测试通过）；仅提交门写（门拒绝回归证明无锚点/图残留）；
生成只读；确定性锚点 id；`evidence_ids` → 真实锚点行；无密钥（validator scan + diff 检查）。

## Conclusion

PASS。`correlated_review`（机器证明、同源披露），非 owner 接受。
