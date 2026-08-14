# TR-20260814-012：冲突预览、备份/恢复与版本历史验证

> 本报告冻结 `2cfa88372cd9244753c0b5e50216ce70d22d98b8` 的
> WORK-2026-021（冲突预览 UI + 备份/恢复崩溃恢复 + 版本历史面板）。它证明
> 保存遇到锁定/版本冲突时给出具体提示、本地数据可带校验和备份并一键恢复、
> 库文件丢失后可从备份恢复、侧边栏展示版本历史；第 6 步"人工编辑安全感"
> 的可见表面基本补齐。

```yaml
status: passed
test_level: integration_component_repository
owner: graph_qa_fresh
related_ids: [WORK-2026-021, REQ-2026-006, REQ-2026-008, NFR-2026-001, WORK-2026-019, WORK-2026-020, TR-20260814-011]
build_id: 2cfa88372cd9244753c0b5e50216ce70d22d98b8
started_at: 2026-08-14T18:50:00+08:00
finished_at: 2026-08-14T19:35:00+08:00
supersedes: null
```

## 目的与门槛

- 证明保存错误码映射为具体提示（`target_locked`/`revision_conflict`/`workspace_corrupt`）。
- 证明 `list_backups`/`restore_backup_by_name` 的三重路径守卫与 checksum 校验（sidecar 缺失/不匹配均拒绝）。
- 证明库文件丢失后 `GET /backups` 与 `POST /restore` 仍可达并恢复（`_recovery_layout`）。
- 证明前端备份/恢复/历史使用正确的 workspace 级 URL（契约测试防回归）。
- 证明版本历史面板展示 `vN → vN+1` 与 `change_id` 前缀。

## 方法与结果

| Test ID | 场景 | Actual | Result |
|---|---|---|---|
| TC-BACKUP-001 | 备份列表与恢复 round trip | 备份→列表→改图→恢复→原值 | PASS |
| TC-BACKUP-002 | 路径遍历/缺失备份拒绝 | `backup_invalid` 422 | PASS |
| TC-BACKUP-003 | checksum sidecar 缺失/不匹配拒绝 | `backup_invalid`/`backup_checksum_mismatch` | PASS |
| TC-BACKUP-004 | 库文件丢失后恢复 | `_recovery_layout` 降级、restore 重建 db | PASS |
| TC-UI-001 | 冲突预览提示 | 保存 target_locked 显示"保存被拒：该内容已锁定" | PASS |
| TC-UI-002 | 备份/恢复/历史面板 | 侧边栏按钮 + 列表 + 版本历史 | PASS |
| TC-API-URL | 前端 URL 契约 | backup/backups/restore/history 命中 workspace 级路由 | PASS |
| TC-REPO-001 | 完整 Python/仓库门 | 全仓 249/249、Ruff/mypy/validator | PASS |
| TC-REPO-002 | TS/Web/依赖/构建门 | frozen install、peers、Web 27/27、check、build | PASS |

职责隔离 QA 对冻结 `b962978` 返回 **FAIL（1 P0、1 P1、5 P2）**——P0 为前端备份/恢复/历史 URL 用 `/graph` 前缀拼错致 404；P1 为 checksum sidecar 缺失时静默跳过。修复 `2cd8270`（URL 修正 + checksum 必需 + `_recovery_layout` + 文案分流 + 契约测试）、`8562ee7`（db-lost 恢复用例）、`2cfa883`（毫秒备份时间戳）后，职责隔离复审三次 PASS，无阻断性 finding。QA 为静态只读推演（如实披露未实跑）；本会话实跑全门（249/249、Web 27/27）。角色独立性无外部 Provider 证明，保守记录 `correlated_review`。

## 证据与结论

- Evidence manifest：`evidence/TR-20260814-012/manifest.json`。
- Decision：GO，仅限 WORK-2026-021 的冲突预览、备份/恢复与版本历史 prototype verification。第 6 步产物（锁定、撤销/重做、冲突预览、崩溃恢复、重复任务保护、版本历史）全部验证。
- 未完成/未授权：普通编辑的 patch 化保存（跨会话撤销覆盖所有编辑，需 GraphPatch delete/tombstone 语义）、真实 Provider/Web、用户数据和发布。
