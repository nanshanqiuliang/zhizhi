# AI QA attempt 001 — persistent patch gate, cross-session undo/redo, lock guard (WORK-2026-019/020)

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: graph_qa_fresh
decision: fail
reviewed_commit: c70d339aea3d17993d77bc95d0860e2576cd411e
red_baseline_commit: db3cb26aa2d5ad024a8fef288cae68fa4031b303
ready_commit: 4f5fbd3a26aae5411cd6d1a15577cac618ccfb27
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

**FAIL**，含 2 个 P0、3 个 P1、3 个 P2 finding。这是对冻结提交 `c70d339`（WORK-2026-019 持久化 GraphPatch 提交门 + 跨会话撤销/重做，与 WORK-2026-020 锁定维度存储保护 + WebUI 锁定/撤销接入）的职责隔离只读机器审查。审查范围 `db3cb26..c70d339`（20 文件，+970/−75），核心生产文件为 `workspace.py`/`main.py`/`api.ts`/`App.tsx`。

提交链（Ready `4f5fbd3` → 红灯 `db3cb26` → 冻结 `c70d339`）经只读 git 命令实跑验证成立；红灯基线仅含 2 个测试文件（+409 行），符合"红灯仅测试"模式。核心 patch 门与 record digest 校验实现本身正确，但前后端两条持久化路径互相冲突，导致跨会话撤销在真实编辑流中失效，且锁定保护在 whole-graph 边界存在绕过。

## Findings

### P0

- **P0-1（`workspace.py:save_course_graph` + `App.tsx:commit/scheduleAutoSave/toggleLock`）**：`save_course_graph` 每次整图 PUT 都 `DELETE FROM history_records` 并重写 initial；前端每次编辑后 600ms 走自动保存 PUT、`toggleLock` 前也先 `saveGraph(present)`。后端 undo/redo 栈在正常编辑流里存活不过一次自动保存，普通编辑（增删改/拖动）的跨会话撤销/重做实际不可用。
- **P0-2（`App.tsx:undo/redo`）**：有 api 时，只要 `past/future` 非空，undo/redo 就只操作内存会话栈（不调后端、不触发自动保存），后端图保持旧值，刷新后撤销丢失；会话栈与后端历史两套撤销源完全割裂。

### P1

- **P1-1（`workspace.py:_dimension_value`）**：content 锁在 whole-graph 门只比较 `label`+`note`，不比较 `evidence_ids/origin/review_state/confidence` 等 concept 可写字段，与 domain 门 content 锁（保护整个 concept）不一致；PUT /graph 可改这些字段绕过 content 锁。
- **P1-2（`workspace.py:save_course_graph` + `main.py:put_graph`）**：PUT /graph 不校验 revision_no 单调性、无条件清空历史并重写 initial；客户端可传任意 `revision_no`（如 0）重置 revision 与历史，绕过 `base_revision` 冲突检查。
- **P1-3（`App.tsx:saveNode/addChild/deleteSelected/拖拽`）**：前端编辑入口不检查 `locks`；对锁定节点编辑会先 `commit` 更新内存并提示成功，随后自动保存的 PUT 被 guard 拒绝只 `setSaveState("failed")`，用户不知情且前后端状态分歧。

### P2

- **P2-1（`api.ts:graphToSnapshot`）**：`positionLocked` 改为读 `locks.position` 而非 `layout_items.pinned`；旧数据（`pinned=true` 且 `locks.position` 未设置）升级后会丢位置锁。
- **P2-2（`workspace.py:apply_graph_patch/undo_graph/redo_graph`）**：「重建历史 → 修改 → 提交」不在单一事务/锁内，并发请求会丢更新或产生重复 change_id（`history_records` 无 change_id 唯一约束）。
- **P2-3（`main.py:_read_json`）**：无 body 大小限制；错误 detail 透传 `cycle_path`/semantic hash/概念 id 到 HTTP 响应（不含 note 正文或 secret）。

## 已确认无问题

- record digest 校验（`record_from_json` + `_rebuild_history` 经 `replay`→`_validate_record` 二次校验）。
- redo 栈顺序（`reversed(records[applied:])` 使最早被撤销的记录位于栈顶，LIFO redo 语义正确）。
- `_workspace_root` 的 uuidv7 校验与 storage_key 路径逃逸守卫（本次 diff 未涉及 storage_key 路径）。

## Limitations

本次为静态只读审查，未实跑 pytest/集成测试/浏览器；并发 TOCTOU 为代码推演，未实测复现。所有 Python/TS 行为声明以逐行静态推演为主，提交 message 中的测试数字仅作自述引用，未被本审查独立复现。

## Post-review fix

- `a6a471ad8400467305e0d8461b579aaf0317b9f1`：修复 P0-2（undo/redo 会话内分支补 `scheduleAutoSave`）、P1-1（content 锁改护整个 concept 除 locks/revision_no）、P1-2（`_guard_revision_monotonic` 拒绝 revision 回退 + API 409 映射）、P1-3（saveNode/addChild/deleteSelected/startDrag 前检查锁）、P2-1（`positionLocked = locks.position || item.pinned`）、P2-3（`_read_json` body 上限 10 MiB）。
- 边界收敛（非代码缺陷，交付边界调整）：P0-1 的"普通编辑跨会话撤销"明确为 WORK-2026-021（前端 patch 化保存）范围，本工作项跨会话撤销覆盖 patch 门操作（锁定/解锁）；P2-2 单用户本地 loopback 场景无并发写，记录为原型边界。
- 修复后开发者实跑：pytest 243/243（新增 P1-1/P1-2 回归 2 项）、Web 23/23（新增 P1-3 回归 1 项）、ruff、strict mypy、repository validator、pnpm 锁依赖/check/build 全绿。
