# WORK-2026-027：AI 草案来源锚点落库 + 点来源跳回原文（第 8 步切片 4）

```yaml
status: ready
type: feature
owner: Codex (ai-draft + persistence + web role)
reviewers: [ai_qa_auditor, workspace_owner]
related_ids: [WORK-2026-026, WORK-2026-009, WORK-2026-005, WORK-2026-017, WORK-2026-018, WORK-2026-019, WORK-2026-022, REQ-2026-006, NFR-2026-001, TR-20260814-015]
target_stage: "阶段 1 / 自然语言第 8 步切片 4（来源锚点落库 + 点来源跳回原文）"
risk: medium
created_at: 2026-08-15T03:55:00+08:00
updated_at: 2026-08-15T03:55:00+08:00
```

## 问题与结果

- 用户/工程问题：切片 3 已打通"导入 → 生成草案 → 预览 → 接受写入"，但草案的 `evidence_ids` 是合成 UUIDv7 来源引用，**不落 `anchor` 表**——接受后概念/边的来源无法持久化、无法查询，也无法"点来源跳回原文"。这留下了 `TR-20260814-015` 记录的原型边界。
- 期望结果：用户接受草案时，草案的来源引用**原子地**物化为真实 `anchor` 行（与提交门同一事务，失败则整体回滚）；接受后的概念/边 `evidence_ids` 指向真实锚点；草案预览面板对每个概念/关系提供"跳回原文"，打开对应资源查看器（资源级定位，明确不冒充精确页/bbox）。
- 成功如何被观察：从失败测试启动；接受原子性（锚点插入失败则图也不写入）；`accept_ai_draft` 与 `/ai-draft/accept` 端点通过提交门 + 锚点落库；`evidence_ids` 指向真实 anchor 行；Web 草案面板"跳回原文"打开资源查看器；全仓门全绿。

## 范围

- In scope：
  - `packages/infrastructure/.../workspace.py`：`accept_ai_draft(layout, patch, *, trusted_actor, anchors)`——重建历史、经 `GraphHistory.apply_patch` 应用确认 patch，并把 `anchors`（`[{id, resource_id, page, label}]`）与图/record/applied-count/搜索索引**单事务**提交（锚点插入失败则整体回滚）；`_atomic_commit_graph` 增 `anchors` 参数；导出 `accept_ai_draft`。
  - `apps/api/ai_draft.py`：`deterministic_uuidv7(seed)`（对 resource_id 派生的稳定 UUIDv7）；generator 改为对每个资源使用**单一确定性来源锚点 id**（所有概念/关系共享同一 `evidence_ids`），draft 响应增 `evidence: [{anchor_id, resource_id, label}]`（label = "AI 草案来源"）。
  - `apps/api/main.py`：`POST /api/workspaces/{id}/ai-draft/accept`（body `{patch, evidence}`）——校验 patch（本地 user 预览、`confirmed=true`、`ready_to_apply`），调 `accept_ai_draft` 原子落库；无 generator 或非法 body 失败关闭。
  - `apps/web/src/api.ts` + `App.tsx`：`acceptDraft(patch, evidence)`；草案预览面板每概念/关系显示来源，加"跳回原文"（按 evidence 的 `resource_id` 打开查看器）。
  - 测试：`tests/integration/test_ai_draft_accept.py`（`accept_ai_draft` 原子性 + 端点 + 证据指向真实锚点）+ Web `App.draft` 增跳回原文测试。
- Out of scope：精确页/bbox 级来源定位（草案按整资源文本分块，页边界已丢失，资源级定位如实披露）；接受后"点击树节点 → 跳原文"（需 evidence→resource 反查，后续切片）；PDF.js 渲染内高亮 AI 草案锚点；向量检索（第 9 步）。
- 受影响模块/接口/数据：扩展 `workspace.py`（`accept_ai_draft` + `_atomic_commit_graph` anchors）、`apps/api`（ai_draft generator evidence + accept 端点）、`apps/web`（api.ts/App）；无 canonical contract/migration/prompt 变更（anchor 表 schema v3 已存在）。
- 依赖和假设：WORK-2026-026（草案端点 + Web 接受/拒绝）、WORK-2026-005/019/022（提交门）、WORK-2026-016/017/018（资源/锚点/查看器）已验证；草案生成仍只读；仅"接受"写库（用户显式确认）。

## 设计边界

- 草案生成（`POST /ai-draft`）仍只读、不写库；"来源锚点落库"只发生在用户显式接受时。
- 锚点 id 用 `deterministic_uuidv7(resource_id)` 派生（对同一资源恒定），保证重复起草/重复接受幂等（`ON CONFLICT(id) DO UPDATE`），避免悬空引用。
- 草案锚点用 `page=0` 哨兵表示"资源级来源"（真实页锚点 `page>=1`，互不冲突；`UNIQUE(resource_id, page)` 对单资源单锚点不冲突）。
- 锚点 payload：`{topic_zh: "AI 草案来源", source: "ai_draft"}`；仅标识、不含正文。
- 原子性：`accept_ai_draft` 复用 `_atomic_commit_graph` 的单事务——锚点插入、图、record、initial、applied-count、FTS 索引同生共死；任何一步失败整体回滚。
- 接受仍走提交门：`base_revision_no` 冲突 → `patch_revision_conflict`；锁定项覆盖 → `target_locked`；确认门 `requires_confirmation=true` + `confirmed=true`。

## 风险影响

- 数据/schema/migration：无 migration；复用 anchor 表（schema v3 已存在）；仅新增插入路径。
- 安全/隐私：锚点 payload 仅标识 + `source="ai_draft"`；不接受正文；错误 details 仅标识。
- 并发/幂等/恢复：确定性锚点 id + `ON CONFLICT(id) DO UPDATE` 幂等；单事务原子；重复接受不产生重复/悬空锚点。
- 性能/容量/成本：单资源单锚点，O(1) 插入；无模型成本增量。
- 可观测性/诊断：稳定错误码复用 `patch_*`/`workspace_missing`；`accept_ai_draft` 锚点失败映射 `import_failed`/`save_failed`。
- 用户文档：用户手册补"接受草案 → 来源落库 → 跳回原文"；明确资源级定位边界。

## 验收标准

- [ ] AC-1 (c1)：`accept_ai_draft` 单事务——确认 patch 应用 + 锚点行 + 图/record/applied-count/索引同生共死；锚点插入失败整体回滚（图不变）。
- [ ] AC-2 (c2)：接受后概念/边 `evidence_ids` 指向真实 `anchor` 行（`list_anchors` 可见，id 匹配、`source="ai_draft"`）。
- [ ] AC-3 (c3)：`POST /ai-draft/accept` 校验失败关闭——非法 patch（未确认/actor 不符/revision 冲突）拒绝且不写锚点；无 generator 503；非法 body 422。
- [ ] AC-4 (c4)：确定性锚点 id——同一资源重复起草产生同一 `evidence_ids`；重复接受幂等（不产生重复锚点）。
- [ ] AC-5 (c5)：Web 草案面板"跳回原文"——按 evidence `resource_id` 打开资源查看器；`ai_not_available`/无证据时不误跳。
- [ ] AC-6 (c6)：repository 门：validator、Ruff、scripts + strict package mypy（含 apps/api）、全仓 pytest、Web 全绿。
- [ ] 错误和恢复路径：锚点插入失败/图提交失败整体回滚；接受非确认 patch 拒绝；生成仍只读。
- [ ] 回滚/禁用方法：回退本工作项提交即回到合成来源引用（切片 3 状态）；红灯与证据保留。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-ACCEPT-001 | integration | `accept_ai_draft` 原子性 | 确认 patch + 锚点 + 图同生共死；锚点失败回滚 | 待实现 |
| TC-ACCEPT-002 | integration | `/ai-draft/accept` 端点 | 接受后 evidence 指向真实锚点；失败关闭 | 待实现 |
| TC-ACCEPT-003 | integration | 确定性锚点 id | 同资源重复起草同 evidence；重复接受幂等 | 待实现 |
| TC-ACCEPT-004 | component | Web 跳回原文 | 草案面板跳回原文打开查看器 | 待实现 |
| TC-REPO-001 | repository | 全仓门 | validator/Ruff/mypy/pytest/Web | 待实现 |

## 交付物与关闭

- Commit/PR：分支 `feature/WORK-2026-009-ai-draft-pipeline`（切片 4 沿用）；Ready → 红灯 → 实现 → QA。
- Contract/ADR/migration/prompt：无新 canonical contract/ADR/migration/prompt；复用 GraphPatch v1、anchor 表 schema v3。
- Test Run：TC-ACCEPT-001..004 + 全仓门。
- Release：无托管发布；真实 DeepSeek 调用仍仅 `DEEPSEEK_API_KEY` opt-in。
- 观察结果：草案来源引用在接受时物化为真实锚点、单事务原子；Web 草案面板可跳回原文（资源级）。
- 未完成项的新 ID：接受后"点击树节点 → 跳原文"（evidence→resource 反查）、精确页/bbox 级定位（后续切片）。
