# TR-20260814-016：AI 草案来源锚点落库与点来源跳回原文验证（WORK-2026-027 切片 4）

> 本报告密封 `3c3dfa0782a8fde6c1c3dca6f84db4c1a45d1598` 的
> WORK-2026-027（第 8 步切片 4：`deterministic_uuidv7` + `accept_ai_draft` 单事务
> patch+锚点 + `POST /ai-draft/accept` + Web 跳回原文）。它证明用户接受草案时来源引用
> 原子地物化为真实锚点、`evidence_ids` 指向真实 anchor 行、草案面板可跳回原文，
> 从而兑现路线图第 8 步"每个节点/关系带来源，确认后才写入"。

```yaml
status: passed
test_level: integration_component_repository_e2e_live
owner: ai_qa_auditor
related_ids: [WORK-2026-027, WORK-2026-026, WORK-2026-009, WORK-2026-005, WORK-2026-017, WORK-2026-019, WORK-2026-022, REQ-2026-006, NFR-2026-001, TR-20260814-015]
build_id: 3c3dfa0782a8fde6c1c3dca6f84db4c1a45d1598
started_at: 2026-08-15T03:55:00+08:00
finished_at: 2026-08-15T04:30:00+08:00
supersedes: null
```

## 目的与门槛

- 证明 `accept_ai_draft` 把确认 patch 与草案来源锚点**单事务**提交（锚点失败整体回滚）。
- 证明接受后概念/边 `evidence_ids` 指向真实 `anchor` 行（`source="ai_draft"`、page=0）。
- 证明 `POST /ai-draft/accept` 校验失败关闭（未确认/非法 evidence 拒绝且不写锚点/图）。
- 证明确定性资源级锚点 id 幂等（重复起草/接受不产生重复/悬空锚点）。
- 证明 Web 草案面板"跳回原文"打开来源资料查看器；无证据时不显示。

## 方法与结果

| Test ID | 场景 | Actual | Result |
|---|---|---|---|
| TC-ACCEPT-001 | `accept_ai_draft` 原子性 | 确认 patch + 锚点 + 图同生共死；锚点失败回滚 | PASS |
| TC-ACCEPT-002 | `/ai-draft/accept` 端点 | 接受后 evidence 指向真实锚点；失败关闭（422/409） | PASS |
| TC-ACCEPT-003 | 确定性锚点 id | 同资源重复起草同 evidence；重复接受幂等 | PASS |
| TC-ACCEPT-004 | Web 跳回原文 | 草案面板跳回原文打开查看器；无证据不显示 | PASS |
| TC-REPO-001 | 完整门 | pytest 402/402 + 5 skipped；Ruff；strict mypy（30）；validator | PASS |
| TC-REPO-002 | Web/构建门 | Web 37/37；pnpm check/build | PASS |
| QA-001/002 | 职责隔离对抗审查 | attempt001 PASS（0 P0/P1，3 P2）→ 修复 `3c3dfa0` → attempt002 PASS（0 P0/P1） | PASS |

职责隔离 QA：attempt 001 对冻结 `38df493` 返回 **PASS**（0 P0/P1；3 个非阻塞 P2：
空字符串 evidence 信任、跨资源 id 复用边界、回归覆盖缺口）；修复 `3c3dfa0`（UUIDv7
evidence 校验 + 提升 3 个回归）后 attempt 002 返回 **PASS**（0 P0/P1；P2-2 保持文档化
边界）。QA 为只读机器审查；`correlated_review`，非 owner 接受。

## 证据

- `evidence/TR-20260814-016/`：attempt 001/002 报告、`manifest.json`、`checksums.sha256`、
  `commands.txt`、`environment.json`、`gate-summary.txt`。
- live e2e（orchestrator，owner key env-only）：导入 calculus.md → 生成（确定性锚点 id）→
  接受 applied；接受后概念 `evidence_ids` == 持久化锚点 id（`source=ai_draft`、page=0）。
- 全仓 pytest 402/402 + 5 skipped；validator PASS；Ruff/strict mypy 全绿；Web 37/37。

## 遗留边界

- P2：`ON CONFLICT(id)` upsert 不更新 resource_id/page；锚点 id 由 `deterministic_uuidv7`
  对资源 1:1 派生，跨资源复用需 SHA-256 碰撞，生产不可达（文档化边界）。
- "接受后点击树节点 → 跳原文"（evidence→resource 反查）与精确页/bbox 级定位为后续增强；
  草案锚点为资源级（page=0 哨兵）。
- `correlated_review`：机器证明、同源披露；最终残余风险接受归 workspace owner。
