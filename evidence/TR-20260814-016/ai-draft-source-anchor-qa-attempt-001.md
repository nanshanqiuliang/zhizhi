# AI QA attempt 001 — AI draft source-anchor persistence + jump to source (WORK-2026-027 slice 4)

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: ai_qa_auditor
decision: pass
reviewed_commit: 38df493d7513d5480f03ac80268f122285a641ab
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

**PASS** — 0 P0 / 0 P1；3 个非阻塞 P2。这是对冻结提交 `38df493`
（WORK-2026-027 切片 4：`deterministic_uuidv7` + `accept_ai_draft` 单事务
patch+锚点 + `POST /ai-draft/accept` + Web 跳回原文）的职责隔离机器审查。

## Red/green chain

Ready `b7094bc`（docs）→ 红灯 `2fcad41`（`test_ai_draft_accept.py` ImportError +
Web 跳回原文按钮缺失）→ 实现 `38df493`。红灯真值由 `2fcad41` 无
`deterministic_uuidv7`/`accept_ai_draft` 符号、api.ts 无 `acceptDraft`、App.tsx
无 `跳回原文` 确认。

## Gates（本人执行，精确数字）

pytest accept 5/5；回归 9/9；全仓 400/400 + 5 skipped；ruff format/check pass
（86 文件）；strict mypy 30 文件；validator PASS（含 secret scan，security 27）；
Web draft 4/4；`pnpm check` 36 tests + tsc + eslint 0 warnings；`pnpm build` ok。

## Adversarial mutation review（独立 scratch worktree @38df493，已删除）

- M1 原子性：把锚点插入移到图提交后的第二事务 → 回滚测试 FAIL（图已提交）⇒ 真单事务。
- M2 提交门：把锚点写提前到 `history.apply_patch` 前 → 4 个 no-write 测试 FAIL（残留锚点）⇒ 仅经提交门后写。
- M3 幂等：把 `deterministic_uuidv7` 随机化 → 稳定性测试 FAIL ⇒ sha256 稳定 v7。
- M4 provenance：改 payload `source` → 断言失败 ⇒ `source="ai_draft"`/page=0 保持。
- M5 evidence 校验：删除 422 守卫 → 5 个校验测试 FAIL（缺 patch 500、非 list 静默 200）⇒ 精确 422。
- 生成端点运行时验证只读；无硬编码密钥；`DEEPSEEK_API_KEY` env-only。

## Findings

| Sev | Finding |
|-----|---------|
| P2 | 空字符串 `anchor_id`/`resource_id` 通过 isinstance-str 检查；未交叉核对 evidence 锚点与 patch `evidence_ids`（loopback 信任客户端锚点；生产 1:1，影响最小）。 |
| P2 | `ON CONFLICT(id)` upsert 不更新 resource_id/page；复用锚点 id + 不同资源会保留首次绑定（生产 id↔resource 1:1，不可达）。 |
| P2 | 测试覆盖缺口：无"提交门拒绝时不写锚点"、精确 422 码、Web"无证据→无跳转按钮"的仓库级测试。 |

## Post-review fix

`3c3dfa0`：P2-1 用 `_is_uuidv7` 校验 anchor_id/resource_id（空/非 UUIDv7 → 422）；
P2-3 提升 3 个回归到仓库测试。P2-2 保持文档化边界。

## Superseding review

见 `ai-draft-source-anchor-qa-attempt-002.md`：对 `3c3dfa0` 返回 PASS（0 P0/P1）。
