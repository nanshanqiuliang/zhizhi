# TR-20260814-013：普通编辑 patch 化保存与跨会话撤销验证

> 本报告冻结 `71066219935528da4e5e3ebbbadfd624b3e661e5` 的
> WORK-2026-022（GraphPatch v1 契约扩展 delete 操作 + 后端 diff 生成 patch）。
> 它证明普通编辑（新增/修改/删除概念与边、拖动布局）在保存时被 diff 成
> GraphPatch 并经受保护提交门落盘，因此**所有编辑**都可跨会话撤销/重做；
> 第 6 步「人工编辑安全感」的最后一环完成。

```yaml
status: passed
test_level: contract_unit_integration_component_repository
owner: graph_qa_fresh
related_ids: [WORK-2026-022, REQ-2026-006, REQ-2026-008, NFR-2026-001, NFR-2026-003, ADR-0005, WORK-2026-005, WORK-2026-011, WORK-2026-019, TR-20260814-002, TR-20260814-011]
build_id: 71066219935528da4e5e3ebbbadfd624b3e661e5
started_at: 2026-08-14T19:40:00+08:00
finished_at: 2026-08-14T20:15:00+08:00
supersedes: null
```

## 目的与门槛

- 证明 GraphPatch v1 新增 `delete_concept`/`delete_edge` 操作（契约 + 领域语义）。
- 证明后端 `save_course_graph` 在后续保存时 diff 当前图与传入图并生成有序 patch，
  经确认门 + 四维锁 + revision 检查落盘，普通编辑保留历史。
- 证明普通编辑（增/改/删概念、删边、拖布局）可跨会话 undo/redo。
- 证明锁定不被绕过：锁定内容被改、锁定概念被删、级联删边触碰存活端点 relations 锁均 `target_locked`。

## 方法与结果

| Test ID | 场景 | Actual | Result |
|---|---|---|---|
| TC-DIFF-001 | 契约 delete 操作 | delete_concept/delete_edge schema + 领域应用 | PASS |
| TC-DIFF-002 | delete 单元语义 | 删除概念/锁拒绝/删除边 | PASS |
| TC-DIFF-003 | 普通编辑跨会话撤销 | 增/改/删 + undo 恢复 | PASS |
| TC-DIFF-004 | noop 保存 | 不递增 revision、不追加历史 | PASS |
| TC-DIFF-005 | 存活端点 relations 锁 | 删除相邻概念拒绝 | PASS |
| TC-DIFF-006 | 新概念布局保留 | create + set_layout_item | PASS |
| TC-LOCK-001..006 | 锁定维度保护（patch 门） | 锁内容/锁删除/锁降级=解锁/revision 业务驱动 | PASS |
| TC-REPO-001 | 完整 Python/仓库门 | 全仓 256/256、Ruff/mypy/validator | PASS |
| TC-REPO-002 | TS/Web/依赖/构建门 | contracts-ts drift、Web 27/27、check、build | PASS |

职责隔离 QA 对冻结 `ab50aa2` 返回 **FAIL（3 P1、2 P2）**——P1 为 delete 级联未查存活端点 relations 锁、diff 拆分 label/review 触发重复 op、新概念 layout 丢失。修复 `7106621`（级联锁检查 + 合并 update_concept + 遍历 inc_layout）并补回归后，职责隔离复审 PASS。QA 为静态只读推演（如实披露未实跑）；本会话实跑全门（256/256、Web 27/27）。角色独立性无外部 Provider 证明，保守记录 `correlated_review`。

## 证据与结论

- Evidence manifest：`evidence/TR-20260814-013/manifest.json`。
- Decision：GO，仅限 WORK-2026-022 的普通编辑 patch 化保存与跨会话撤销 prototype verification。**第 6 步全部产物完成并验证**：锁定、撤销/重做（覆盖所有编辑）、冲突预览、崩溃恢复、重复任务保护、版本历史。
- 未完成/未授权：tombstone 软删除（当前为硬删除 + 历史可恢复）、真实 Provider/Web、用户数据和发布。
