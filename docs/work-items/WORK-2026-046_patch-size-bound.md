# WORK-2026-046：放宽 GraphPatch 单补丁操作数上限（maxitems 修复）

```yaml
status: ready
type: bugfix
owner: api + ai-draft + QA
reviewers: [project_owner, qa]
related_ids: [WORK-2026-043, WORK-2026-044, REQ-2026-001, NFR-2026-001]
target_stage: 第 10 步后反馈修复
risk: low
created_at: 2026-08-16T00:00:00Z
updated_at: 2026-08-16T00:00:00Z
```

## 问题与结果

- 用户/工程问题：用户用全库思维导图 agent（WORK-2026-043）对 88 页长论文
  （`paper.pdf`，约 27.9 万字符）生成草案时，重装后的 exe 报错 `maxitems`。
  根因：canonical 契约 `GraphPatch.operations` 的 `maxItems` 为 100（
  `docs/contracts/knowledge-tree-graph.v1.schema.json`），而一次全库生成
  （40 块上限、每块可能抽出多概念）产生的操作数为 `create_concept +
  set_layout_item（+create_edge）`，轻松超过 100；`preview_graph_patch` 的
  schema 校验（`validate_contract("graph_patch", ...)`）拒绝该草案，端点在
  WORK-2026-044 后把 `rule: "maxItems"` 透出给 UI。
- 期望结果：一次全库思维导图生成（受 `max_chunks=40` 与 task profile 预算约束）
  的草案可以通过预览与确认，不再被 100 操作上限误伤。
- 成功如何被观察：① 契约级：150 操作补丁通过 `validate_contract("graph_patch")`；
  ② API 级：注入的大型全库生成器（240 操作）`POST /ai-draft` 返回 200；
  ③ 越界仍 fail-closed：超过新上限（5000）的补丁仍被拒（rule `maxItems`）；
  ④ 用户复测 `paper.pdf` 不再报 `maxitems`。

## 范围

- In scope：`GraphPatch.operations.maxItems` 100 → 5000（含描述注释）；重新生成
  Python/TS 契约产物；契约红灯/绿灯测试；API 集成回归测试；全部门禁 + 桌面重建 +
  职责隔离 QA + 证据封存。
- Out of scope：分块应用补丁（多事务接受）；改变 `max_chunks`（保持 40）与 task
  profile 预算；`CourseGraph` 顶层容量（concepts 10000 / edges 50000 /
  layout_items 10000，均远大于单补丁上限，无需改动）；每概念 `evidence_ids`
  maxItems=100（全库模式每资源 1 个确定性锚点、增量模式每块 1 个，40 块上限内
  不会触顶）。
- 受影响模块/接口/数据：canonical 契约（文档 + 生成产物）、契约测试、
  `/api/workspaces/{id}/ai-draft` 行为（错误路径收窄）。无迁移。
- 依赖和假设：一次生成的操作数上界 = 概念数×2 + 关系数；DeepSeek 概念抽取
  max_output_tokens=4096、关系候选 8192（thinking 关闭）实际每块产出有限；5000
  约为现实最坏情况（40 块 × ~25 概念/块 × 2 操作 + 关系）的 2 倍余量，同时保持
  单事务提交有界。

## 风险影响

- 数据/schema/migration：仅放宽数组长度上限（向后兼容：≤100 操作的旧补丁仍合法）；
  `schema_version` 仍为 1，无需迁移。
- 安全/隐私：无变化（草案仍不可信、预览→确认→提交门、fail-closed 不变）。
- 并发/幂等/恢复：单事务补丁变大（5000 操作 ~ 数 MB JSON）；SQLite 顺序应用，
  本地单用户可接受；失败路径不变（原子回滚）。
- 性能/容量/成本：生成成本仍由 `max_chunks=40` + 预算约束；校验/应用为线性。
- 可观测性/诊断：错误码不变；UI 继续显示精确 `code/rule`。
- 用户文档：无行为变化，无需改 `USER_MANUAL`；harness 文档补充上限说明。

## 验收标准

- [ ] AC-1：`validate_contract("graph_patch", patch)` 接受 150 操作补丁（回归用户场景）。
- [ ] AC-2：契约按 canonical 上限 +1 操作仍被拒，`rule == "maxItems"`（上限未移除）。
- [ ] AC-3：API 级：全库模式注入 240 操作生成器 → 200 + `requires_confirmation`。
- [ ] 错误和恢复路径：越界补丁返回既有 `draft_invalid/maxItems`，不吞错。
- [ ] 回滚/禁用方法：回退契约提交即回旧上限；生成器端 `max_chunks` 不变可独立回退。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-PATCH-BOUND-001 | contract | 150 操作补丁 | 通过 | `test_graph_patch_accepts_large_operation_set` |
| TC-PATCH-BOUND-002 | contract | 上限+1 操作补丁 | 拒绝 `maxItems` | `test_graph_patch_enforces_operation_bound` |
| TC-PATCH-BOUND-003 | integration | 全库 240 操作草案 | 200 + proposed patch | `test_ai_draft_large_workspace_patch_exceeds_old_cap` |
| TC-PATCH-BOUND-004 | 全部门禁 | 既有回归不破坏 | 全绿 | pytest/ruff/mypy/validator/pnpm |
| TC-PATCH-BOUND-005 | desktop e2e | 冻结产物冒烟 | 18/18 | `scripts/desktop_e2e.py` |

## 交付物与关闭

- Commit/PR：契约 + 测试 + 文档提交；证据封存提交。
- Contract/ADR/migration/prompt：canonical `knowledge-tree-graph.v1.schema.json`
  `GraphPatch.operations.maxItems=5000` + 生成产物（Python/TS）。
- Test Run：pytest 全量 + Web + mypy + ruff + validator + e2e。
- Release：桌面 exe/安装器/zip 重建。
- 观察结果：QA 封存 `TR-20260815-007`。
- 未完成项的新 ID：无（画布无限延伸仍为 WORK-2026-045）。
