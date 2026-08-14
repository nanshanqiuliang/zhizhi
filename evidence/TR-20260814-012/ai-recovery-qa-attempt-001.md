# AI QA attempt 001 — conflict preview, backup/restore, version history (WORK-2026-021)

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: graph_qa_fresh
decision: fail
reviewed_commit: b962978d1de2e5635b6b7ec30ce457c36c6f6fb6
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

**FAIL**，含 1 个 P0、1 个 P1、5 个 P2。这是对冻结提交 `b962978`（WORK-2026-021 冲突预览 UI + 备份/恢复崩溃恢复 + 版本历史面板）的职责隔离只读机器审查，审查范围 `2742e71..b962978`。

后端三层路径守卫（`list_backups`/`restore_backup_by_name`：纯 basename + backups_dir 内 + 存在）与错误码映射本身干净，但前端四个新方法的 URL 全部拼错，导致备份/恢复/历史面板端到端 404 不可用。

## Findings

### P0

- **`apps/web/src/api.ts`** — `backupGraph`/`listBackups`/`restoreBackup`/`listHistory` 都以 `endpoint`（`…/api/workspaces/{id}/graph`）为前缀拼接，得到 `/graph/backup`、`/graph/backups`、`/graph/restore`、`/graph/history`；后端路由是 `/api/workspaces/{id}/backup|backups|restore|history`（无 `/graph` 段），全部 404。影响：Web 点"备份数据"报 `backup failed: 404`、恢复不可用、版本历史面板永不显示。

### P1

- **`workspace.py:restore_backup`** — `.sha256` 侧车文件缺失时静默跳过 checksum；`restore_backup_by_name` 只查文件存在不查 sidecar。任何落入 `backups_dir` 的裸 `.sqlite3` 都能未经校验覆盖在线库。

### P2

- `main.py:post_restore` 是 `async def` 却在事件循环内同步做 sha256 + copyfile（大备份阻塞服务）。
- `main.py:get_backups/post_restore` 经 `resolve_workspace` 在 `knowledge-tree.db` 缺失时抛 `workspace_missing`，恰无法处理"库文件丢失"这一崩溃场景。
- `App.tsx:handleRestore` 恢复成功后未刷新历史/资源列表。
- `test_backup_api.py` 缺 `backup_checksum_mismatch`/`restore_failed` 用例，无前端 URL↔路由契约测试（P0 因此漏网）。
- `App.tsx` 备份/恢复按钮嵌在"会话内演示…刷新恢复示例"提示内，api 存在（持久化模式）时文案矛盾。

## Post-review fix

- `2cd8270`：P0 改 `workspaceBase` 前缀 + `api.test.ts` URL 契约测试；P1 sidecar 缺失即 `backup_invalid(backup_checksum_missing)`；P2-2 加 `_recovery_layout`（仅 `database_file_absent` 降级 `create_workspace`，UUIDv7 守卫不变）；P2-3 `handleRestore` 补 `refreshHistory`；P2-4 补 checksum missing/mismatch 测试；P2-5 文案按 api 有无分流。
- `8562ee7`：补 `test_restore_recovers_after_database_lost`（复审指出 `_recovery_layout` 缺直接测试）。
- `2cfa883`：备份时间戳改毫秒（复审 nit：同秒两次备份会重名覆盖）。
- P2-1（post_restore 同步 IO）记为单用户本地边界。

## Superseding review

职责隔离复审（覆盖 2cd8270 → 8562ee7 → 2cfa883）三次均 **PASS**，无阻断性 finding；确认 P0/P1/P2 修复属实、`_recovery_layout` 路径守卫无回归、毫秒时间戳排序无回归。剩余 3 个非阻断 nit（毫秒非严格唯一、gmtime/time 两次调用跨秒、无专项同名测试）记录为边界。

修复后开发者实跑：pytest 249/249（backup_api 6/6）、Web 27/27（含 URL 契约）、ruff、strict mypy、repository validator、pnpm 锁依赖/check/build 全绿。
