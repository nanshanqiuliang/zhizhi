# TR-20260814-011：持久化提交门、跨会话撤销/重做与锁定维度保护验证

> 本报告冻结 `a6a471ad8400467305e0d8461b579aaf0317b9f1` 的
> WORK-2026-019（持久化 GraphPatch 提交门 + 跨会话撤销/重做）与
> WORK-2026-020（锁定维度存储保护 + WebUI 锁定/撤销接入）。它证明已确认
> GraphPatch 经锁定/revision/确认门落盘并可跨会话撤销/重做、整图保存不能
> 覆盖锁定维度、Web 可锁定/撤销；第 6 步"人工编辑安全感"的核心完成标志
> （锁定项不被覆盖、失败/重启不重复写入）兑现。

```yaml
status: passed
test_level: integration_security_component_repository
owner: graph_qa_fresh
related_ids: [WORK-2026-019, WORK-2026-020, REQ-2026-006, REQ-2026-008, NFR-2026-001, NFR-2026-003, ADR-0005, WORK-2026-005, WORK-2026-011, WORK-2026-013, WORK-2026-014, TR-20260814-002, TR-20260814-003, TR-20260814-005, TR-20260814-006]
build_id: a6a471ad8400467305e0d8461b579aaf0317b9f1
started_at: 2026-08-14T16:20:00+08:00
finished_at: 2026-08-14T18:15:00+08:00
supersedes: null
```

## 目的与门槛

- 证明已确认 user GraphPatch 经确认门 + 四维锁 + revision 冲突 + 重复 change_id 检查后原子落盘（图/记录/初始图/栈指针单事务）。
- 证明跨会话 LIFO undo/redo（持久化栈指针，revision 单调）、重复 change_id 幂等拒绝、篡改 record digest 失败关闭。
- 证明整图保存不能覆盖锁定维度：锁降级 / 锁定内容变化 / 锁定概念删除均 `target_locked` 拒绝，content 锁保护整个 concept，revision_no 不可回退。
- 证明 Web 内容/位置锁定走 patch 门、撤销回退后端历史、前端编辑前检查锁。

## 方法与结果

| Test ID | 场景 | Actual | Result |
|---|---|---|---|
| TC-GATE-001 | apply → 落盘 → 重开重放 | 语义一致、revision 单调 | PASS |
| TC-GATE-002 | 跨会话 undo/redo | 恢复前/后语义、栈空 `history_empty` | PASS |
| TC-GATE-003 | 锁定维度修改 / 非 user / 未确认 / revision 冲突 | `target_locked`/`permission_denied`/`patch_revision_conflict` | PASS |
| TC-GATE-004 | 重复 change_id / 篡改 | 幂等拒绝 / `record_tampered` | PASS |
| TC-GATE-005 | 截断/垃圾字节/中断写入 | 稳定错误、无部分状态 | PASS |
| TC-GATE-006 | patches/undo/redo/history 端点 | 正/负路径、404、错误码 | PASS |
| TC-LOCK-001..006 | 锁定维度保护 + revision 回退拒绝 | content 锁护整个 concept、锁降级/删除/内容变化拒绝、revision 回退 409 | PASS |
| TC-LOCK-Web | Web 锁定/撤销/锁检查 | 锁定走 patch 门、撤销回退后端、编辑锁定项被拒 | PASS |
| TC-REPO-001 | 完整 Python/仓库门 | 全仓 243/243、Ruff/mypy/validator | PASS |
| TC-REPO-002 | TS/Web/依赖/构建门 | frozen install、peers、Web 23/23、check、build | PASS |

职责隔离 QA 对冻结 `c70d339` 返回 **FAIL（2 P0、3 P1、3 P2）**——核心是前后端两条持久化路径冲突（整图 PUT 清空历史，致普通编辑流中跨会话撤销失效）与锁定边界绕过。修复 `a6a471a` 关闭 P0-2（撤销后自动保存）、P1-1（content 锁护整个 concept）、P1-2（revision 回退拒绝）、P1-3（前端编辑前查锁）、P2-1（positionLocked 兼容旧 pinned）、P2-3（body 上限）；P0-1（普通编辑跨会话撤销）与 P2-2（单用户并发 TOCTOU）记录为交付边界（分别归 WORK-2026-021 与单用户本地场景）。QA 为静态只读推演（如实披露未实跑）；本会话实跑全门（243/243、Web 23/23）与锁定回归。角色独立性无外部 Provider 证明，保守记录 `correlated_review`。

## 证据与结论

- Evidence manifest：`evidence/TR-20260814-011/manifest.json`。
- Decision：GO，仅限 WORK-2026-019/020 的持久化提交门、跨会话撤销/重做（覆盖 patch 门操作）与锁定维度保护 prototype verification。第 6 步核心完成标志（锁定项不被覆盖、失败/重启不重复写入）兑现；第 6 步标记约 60%（普通编辑跨会话撤销、冲突预览/崩溃恢复 UI 归 WORK-2026-021）。
- 未完成/未授权：普通编辑的跨会话撤销（需前端 patch 化 + GraphPatch delete/tombstone 语义）、冲突预览 UI、崩溃恢复 UI、真实 Provider/Web、用户数据和发布。
