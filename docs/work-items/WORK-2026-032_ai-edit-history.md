# WORK-2026-032：AI 修改历史（历史记录来源标记，第 9 步收尾）

```yaml
status: ready
type: feature
owner: Codex (history + api + web role)
reviewers: [ai_qa_auditor, workspace_owner]
related_ids: [WORK-2026-011, WORK-2026-019, WORK-2026-022, WORK-2026-026, WORK-2026-027, WORK-2026-029, REQ-2026-006, NFR-2026-001]
target_stage: "阶段 1 / 自然语言第 9 步收尾（AI 修改历史）"
risk: medium
created_at: 2026-08-15T08:45:00+08:00
updated_at: 2026-08-15T08:45:00+08:00
```

## 问题与结果

- 用户/工程问题：第 9 步已实现带来源问答、自然语言转 GraphPatch、增量重建，但版本历史面板
  无法区分哪些修改来自 AI（草案接受/指令接受）还是手动编辑——AI 修改历史缺失。这是第 9 步
  剩余可做项（向量检索受 Embedding provider 未决阻塞，属 owner 决策）。
- 期望结果：历史记录携带 `source`（`manual`|`ai_draft`|`ai_command`）；`accept_ai_draft` 标记
  `ai_draft`、指令接受标记 `ai_command`、其余 `manual`；`GET /history` 返回 `source`；Web 版本
  历史面板对 AI 来源显示标记。向后兼容：旧记录无 `source` 视为 `manual`，digest 不变。
- 成功如何被观察：从失败测试启动；record 序列化/反序列化往返保留 source；AI 接受路径落库
  source 正确；`GET /history` 返回 source；旧记录（无 source）反序列化为 manual 且 digest 一致；
  全仓门全绿。

## 范围

- In scope：
  - `packages/domain/.../graph_history.py`：`GraphChangeRecord` 增 `source: str = "manual"`；
    `_record_payload` 仅在 `source != "manual"` 时写入 `source`（保持旧记录 digest 不变）；
    `_build_record`/`_validate_record`/`GraphHistory.apply_patch` 增 `source` 参数。
  - `packages/infrastructure/.../workspace.py`：`record_to_json`/`record_from_json` 往返 `source`
    （仅非 manual 序列化 + digest；反序列化缺省 manual）；`apply_graph_patch` 增
    `source: str = "manual"`；`accept_ai_draft` 默认 `source="ai_draft"`。
  - `apps/api/main.py`：`POST /ai-draft/accept` 用 `source="ai_draft"`；新增
    `POST /interpret/accept`（body `{patch}`）用 `source="ai_command"` 经提交门写入；
    `GET /history` 返回 `source`。
  - `apps/web/src/api.ts` + `App.tsx`：`HistoryRecord` 增 `source`；`acceptCommand` 改走
    `/interpret/accept`；版本历史面板对 `ai_draft`/`ai_command` 显示「AI」标记。
  - 测试：`tests/integration/test_ai_edit_history.py`——record source 往返、AI 接受标记、
    `GET /history` source、旧记录向后兼容。
- Out of scope：向量检索（Embedding provider 未决，owner 决策）；逐条 AI 修改的差异预览（已有
  版本历史 + 撤销）；流式/多轮对话。
- 受影响模块/接口/数据：扩展 GraphChangeRecord（向后兼容，digest 仅当 source≠manual 时变化）、
  `apply_graph_patch`/`accept_ai_draft`、`/interpret/accept`、`/history`、Web；无 canonical
  contract/迁移（历史记录 payload 向后兼容，旧记录 digest 不变）。
- 依赖和假设：WORK-2026-011/019/022（历史记录 + 提交门）、WORK-2026-026/027（草案 accept）、
  WORK-2026-029（指令解释）已验证；向量检索非本轮。

## 设计边界

- 领域/契约：历史记录 `source` 仅非 `manual` 时进入 payload 与 digest，旧记录（无 source）
  反序列化为 `manual` 且 digest 校验不变——严格向后兼容。
- 来源枚举：`manual`（默认）、`ai_draft`（草案接受）、`ai_command`（指令接受）；仅标识。
- 原子性：`accept_ai_draft`/`apply_graph_patch(source=...)` 在图 + record + source 同一事务提交。
- 错误 details 仅标识；不落正文/密钥。

## 风险影响

- 数据/schema/migration：无迁移；历史记录 payload 向后兼容（source 仅追加、digest 条件变化）。
- 安全/隐私：source 仅标识；密钥仅 env。
- 并发/幂等/恢复：source 与图同事务；undo/redo 不改变 source（记录保留）。
- 性能/容量/成本：O(1) 字段；零模型成本。
- 可观测性/诊断：稳定错误码复用 `record_invalid`/`record_tampered`。
- 用户文档：用户手册补「版本历史面板标记 AI 来源」；路线第 9 步进度更新。

## 验收标准

- [ ] AC-1 (c1)：`GraphChangeRecord.source` 缺省 `manual`；`record_to_json`/`record_from_json` 往返保留 source。
- [ ] AC-2 (c2)：旧记录（无 source 字段）反序列化为 `manual` 且 digest 校验一致（向后兼容）。
- [ ] AC-3 (c3)：`accept_ai_draft` 落库 `source="ai_draft"`；`/interpret/accept` 落库 `source="ai_command"`；`apply_graph_patch` 缺省 `manual`。
- [ ] AC-4 (c4)：`GET /history` 返回每条的 `source`。
- [ ] AC-5 (c5)：Web 版本历史面板对 `ai_draft`/`ai_command` 显示「AI」标记。
- [ ] AC-6 (c6)：repository 门：validator、Ruff、scripts + strict package mypy（含 apps/api）、全仓 pytest、Web 全绿。
- [ ] 错误和恢复路径：record 篡改/缺字段稳定拒绝；source 非法值稳定拒绝。
- [ ] 回滚/禁用方法：回退本工作项提交即回到无 AI 来源标记；旧数据不受影响；红灯与证据保留。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-AIH-001 | integration | record source 往返 | source 保留；旧记录→manual + digest 一致 | 待实现 |
| TC-AIH-002 | integration | AI 接受标记 | accept_ai_draft→ai_draft；/interpret/accept→ai_command | 待实现 |
| TC-AIH-003 | integration | `/history` 返回 source | 每条含 source | 待实现 |
| TC-AIH-004 | component | Web 版本历史 AI 标记 | ai_draft/ai_command 显示「AI」 | 待实现 |
| TC-REPO-001 | repository | 全仓门 | validator/Ruff/mypy/pytest/Web | 待实现 |

## 交付物与关闭

- Commit/PR：分支 `feature/WORK-2026-009-ai-draft-pipeline`；Ready → 红灯 → 实现 → QA。
- Contract/ADR/migration/prompt：无新 canonical contract/ADR/migration/prompt；历史记录 payload 向后兼容扩展。
- Test Run：TC-AIH-001..004 + 全仓门。
- Release：无托管发布；本轮无网络。
- 观察结果：版本历史面板可区分 AI 来源；第 9 步收尾（向量检索为唯一 owner 未决项）。
- 未完成项的新 ID：向量检索（Embedding provider 未决，owner 决策）。
