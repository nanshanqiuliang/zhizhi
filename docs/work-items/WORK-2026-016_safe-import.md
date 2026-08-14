# WORK-2026-016：安全文件导入与资源注册（Markdown/TXT/PDF）

```yaml
status: verified_prototype
type: feature
owner: Codex (import + storage role)
reviewers: [ai_qa_auditor, workspace_owner]
related_ids: [REQ-2026-006, REQ-2026-010, NFR-2026-001, NFR-2026-002, ADR-0001, WORK-2026-004, WORK-2026-005, WORK-2026-013, WORK-2026-014, TR-20260814-005, TR-20260814-006, TR-20260814-008]
target_stage: "阶段 1 / 自然语言第 5 步"
risk: high
created_at: 2026-08-14T08:55:00+08:00
updated_at: 2026-08-14T09:15:00+08:00
```

## 问题与结果

- 用户/工程问题：第 4 步已交付持久化工作区（SQLite + API + Web 自动保存 + FTS5 搜索），但用户没有任何方式把本地 Markdown/TXT/PDF 资料导入 App；第 5 步"从节点点回原文"的前提是资料先被安全地收录进本地工作区。
- 期望结果：新增安全文件导入能力：把 Markdown/TXT/PDF 上传到本地 workspace 数据目录，校验文件类型/大小/哈希、注册 `resource` 与 `resource_version`（schema v2 migration）、提供 API 与 Web 导入入口；路径逃逸、伪造类型、超大文件、重复内容均以稳定错误失败关闭。
- 成功如何被观察：通过 API/Web 导入一个 Markdown 文件后，workspace 数据目录出现受控副本，`resource` 表出现记录（含 content_hash/mime/byte_size）；重复导入同一文件返回幂等结果；非法文件类型被拒绝且不落盘。

## 范围

- In scope：SQLite schema v2 migration（新增 `resource`/`resource_version` 表）；`packages/infrastructure` 新增资源导入逻辑（文件类型白名单 MD/TXT/PDF、大小上限、SHA-256 哈希、受控存储目录、去重）；`apps/api` 新增 `POST /api/workspaces/{id}/resources`（multipart upload）与 `GET /api/workspaces/{id}/resources`（列表）；Web 新增导入控件与资源列表；集成/组件/安全测试。
- Out of scope：PDF 解析为文本/页面（属后续工作项）、Markdown 渲染、PDF viewer、Anchor 生成与来源跳转（WORK-2026-005 Anchor 契约已冻结，落地在后续工作项）、url/note 类型资源、云同步、加密、真实 AI/Provider。
- 受影响模块/接口/数据：扩展 `packages/infrastructure`（migration v2 + 资源导入）、`apps/api`、`apps/web`；不修改既有 `knowledge-tree-graph.v1` canonical schema；`PRAGMA user_version` 从 1 升到 2（向前兼容，旧库可迁移）。
- 依赖和假设：文件内容只存受控数据目录（`resources/` 下按 resource_id 子目录），不写入仓库；MD/TXT 直接读文本，PDF 仅验证 magic bytes 与大小（解析在后续工作项）；哈希用 SHA-256。

## 安全边界

- 文件名/路径：客户端文件名只作为 display_name 记录，磁盘文件名用生成的 UUIDv7，杜绝路径逃逸；`../`、绝对路径、含分隔符的名称一律拒绝或规范化。
- 类型校验：按内容 magic bytes + 扩展名双校验（PDF `%PDF-`、TXT/MD 文本探测），不允许仅凭扩展名信任；白名单外 → 422 `import_type_rejected`。
- 大小上限：默认 ≤ 25 MiB，超限 → 422 `import_too_large`；错误 details 不含正文。
- 幂等去重：相同 content_hash 重复导入 → 返回既有 resource_version（200 + `already_exists`），不重复落盘。
- 只读查询端点不暴露文件内容，只返回元数据（id/display_name/mime/byte_size/hash/created_at）。

## 风险影响

- 数据/schema/migration：新增 schema v2；旧 v1 库启动时自动迁移；迁移失败回滚（沿用 `_connect` 事务语义）。
- 安全/隐私：受控存储 + 路径逃逸拒绝 + 类型/大小守卫；无网络出站；错误不含正文。
- 并发/幂等/恢复：单用户本地；同 hash 幂等；导入写事务原子；失败不留半文件。
- 性能/容量/成本：≤25 MiB 单文件，本地磁盘；无模型费用。
- 可观测性/诊断：稳定 `snake_case` 错误码（`import_type_rejected`/`import_too_large`/`resource_exists`）；不落正文。
- 用户文档：更新 USER_MANUAL 与路线第 5 步进度；明确"导入≠来源跳转"边界。

## 验收标准

- [x] AC-1：schema v2 migration 可把 v1 库升到 v2（新增 resource/resource_version 表），重复/乱序迁移稳定失败。
- [x] AC-2：导入合法 MD/TXT/PDF 后在受控目录生成副本、`resource` 表有记录（content_hash/mime/byte_size 正确）；重复导入同 hash 返回幂等结果不重复落盘。
- [x] AC-3：白名单外类型（如 .exe）、伪造扩展名、超大文件（>25 MiB）、路径逃逸文件名均以稳定错误拒绝且不落盘。
- [x] AC-4：`GET /api/workspaces/{id}/resources` 返回元数据列表（不含内容）；缺失 workspace 404。
- [x] AC-5：Web 提供导入控件与资源列表展示；错误提示可见。
- [x] AC-6：集成/安全/组件测试覆盖正/负路径；全仓门通过。
- [x] 错误和恢复路径：导入失败保留原数据不受影响；磁盘写入失败以稳定错误返回且不留孤儿记录。
- [x] 回滚/禁用方法：回退本工作项提交可回到 v1 库（迁移前备份）；不影响既有持久化证据。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-IMPORT-001 | integration | migration v1→v2 | 表存在、版本正确、冲突失败 | 15/15 PASS / TR-008 |
| TC-IMPORT-002 | integration | 导入 MD/TXT/PDF | 受控副本 + 元数据正确；重复幂等 | 15/15 PASS / TR-008 |
| TC-IMPORT-003 | security | 白名单外/伪造/超大/路径逃逸 | 稳定拒绝且不落盘；写失败无孤儿 | 15/15 PASS / TR-008 |
| TC-IMPORT-004 | integration | resources 列表 | 元数据不含内容；404 | 15/15 PASS / TR-008 |
| TC-IMPORT-005 | component | Web 导入控件与列表 | 导入成功/失败提示可见 | Web 15/15 PASS / TR-008 |
| TC-REPO-001 | repository | 全仓门 | validator/Ruff/mypy/pytest/Web | 208/208、15/15 PASS / TR-008 |

## 交付物与关闭

- Commit/PR：分支 `feature/WORK-2026-016-safe-import`；Ready `293c0ef`，红灯 `50b3245`，实现 `10e104f`，P2 修复 `eee15d0`。
- Contract/ADR/migration/prompt：schema v2（PRAGMA user_version=2 + resource/resource_version）；无新 canonical contract/prompt。
- Test Run：import 15/15、全仓 Python 208/208、Web 15/15、Ruff、strict mypy、repository validator、frozen installs/peers/check/build 全通过；职责隔离 QA attempt 001 PASS；真实 uvicorn e2e PASS；证据为 `TR-20260814-008`。
- Release：无托管发布；本地 API + Web 可演示导入。
- 观察结果：安全文件导入已验证，第 5 步首个工作项完成；PDF 解析/查看器与来源跳转属于后续。
- 未完成项的新 ID：PDF 文本解析与查看器、Anchor 生成与来源跳转、Markdown 渲染、url/note 资源分别后续建项。
