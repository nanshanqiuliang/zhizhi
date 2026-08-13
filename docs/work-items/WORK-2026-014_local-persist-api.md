# WORK-2026-014：本地持久化 API sidecar 与 Web 自动保存接入

```yaml
status: ready
type: feature
owner: Codex (api + web integration role)
reviewers: [ai_qa_auditor, workspace_owner]
related_ids: [REQ-2026-006, REQ-2026-008, NFR-2026-001, ADR-0005, ADR-0011, WORK-2026-005, WORK-2026-011, WORK-2026-012, WORK-2026-013]
target_stage: "阶段 1 / 自然语言第 4 步"
risk: high
created_at: 2026-08-14T07:55:00+08:00
updated_at: 2026-08-14T07:55:00+08:00
```

## 问题与结果

- 用户/工程问题：WORK-2026-013 已证明本地 SQLite 持久化内核可保存/加载 CourseGraph、备份/导出/删除，但浏览器（WORK-2026-012 的"知枝"工作台）仍在会话内存中运行，两者之间没有任何桥接；用户关闭页面内容即丢失，第 4 步"关闭并重新打开后内容仍在"的完成标志未兑现。
- 期望结果：新增本地 FastAPI sidecar（`apps/api`）暴露受控 persistence 端点（save/load CourseGraph、备份），Web 前端接入 API：加载已保存图、编辑后自动保存、保存状态可见（已保存/保存中/失败）、刷新/重开后恢复同一图。
- 成功如何被观察：启动本地 API 后，在浏览器编辑"知枝"工作台并保存，关闭页面重开仍显示同一图；状态栏显示真实保存结果而非仅"会话内"；API 不可达时前端明确提示"本地服务未连接"，不伪造成功。

## 范围

- In scope：`apps/api` FastAPI 应用（loopback 绑定、CORS 白名单、`/api/health`、CourseGraph GET/PUT、备份 POST 端点）；Web 接入（加载已保存图、自动保存 debounce、保存状态指示、API 不可达降级提示）；API 集成测试与 Web 组件测试（mock fetch）。
- Out of scope：Tauri 打包、token/Origin 之外的认证机制、多用户、云端同步、FTS5 搜索、文件导入、PDF viewer、真实 AI/Provider、数据加密、多进程并发、浏览器端直接读写 SQLite。
- 受影响模块/接口/数据：新增 `apps/api` composition root（复用 `knowledge_tree_infrastructure.workspace` 与 domain 契约）；修改 `apps/web` 增加 API client 与保存状态；不改 canonical graph schema、domain、infrastructure 公共 API 语义。
- 依赖和假设：新增 `fastapi`、`uvicorn[standard]` 运行依赖与 `httpx2` 测试依赖（已锁定）；API 只监听 `127.0.0.1` 随机/固定空闲端口；CORS 白名单默认 `http://localhost:5173`（Vite dev）可配置；Web 端保存时仍以 GraphPatch 语义为准（AI/导入不可绕过校验）。

## 安全边界

- API 只绑定 loopback（`127.0.0.1`），不对外网卡暴露。
- CORS 使用精确 Origin 白名单，不返回 `*`；预检与简单请求都校验 Origin。
- 保存端点只接受符合 canonical graph contract 的 CourseGraph（复用 `validate_course_graph`），非法载荷以稳定错误拒绝。
- 不做身份认证（单用户本地）；token/Origin 之外的认证归 ADR-0011/SPK-009，不在本工作项范围。
- 错误响应不包含笔记 label/正文；日志不记录正文。

## 风险影响

- 数据/schema/migration：复用 WORK-2026-013 的 migration v1；API 不新增 schema。
- 安全/隐私：loopback + CORS 白名单；无 secret；无网络出站。
- 并发/幂等/恢复：单进程单用户；保存请求串行；失败时前端保留草稿并提示重试，不静默丢数据。
- 性能/容量/成本：单课程数百节点规模；无模型费用。
- 可观测性/诊断：稳定 `snake_case` 错误码透传；健康检查端点。
- 用户文档：更新 USER_MANUAL 与路线第 4 步进度；明确"本地 API 未启动时不能保存"。

## 验收标准

- [ ] AC-1：`apps/api` 可启动，监听 loopback；`GET /api/health` 返回 ok；CORS 白名单外 Origin 被拒。
- [ ] AC-2：PUT 保存合法 CourseGraph 后可 GET 回同一图（语义等价、revision 保留）；非法图被拒且不覆盖已有数据。
- [ ] AC-3：Web 启动时从 API 加载已保存图；编辑后自动保存（debounce）；保存状态在 已保存/保存中/失败 间正确切换。
- [ ] AC-4：API 不可达时前端显示"本地服务未连接"，不伪造成功、不清空当前编辑内容。
- [ ] AC-5：API 集成测试与 Web 组件测试（mock fetch）覆盖正/负路径；全仓门通过。
- [ ] 错误和恢复路径：保存失败保留草稿并可重试；API 中途关闭后重开仍可恢复。
- [ ] 回滚/禁用方法：回退本工作项提交可回到纯内存 Demo；不影响已验证的持久化内核与证据。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-API-001 | integration | health/loopback/CORS | ok；白名单外拒绝 | 红灯→绿灯 |
| TC-API-002 | integration | PUT 合法图 → GET | 语义等价、revision 保留 | 红灯→绿灯 |
| TC-API-003 | integration | PUT 非法图 | 稳定拒绝，原数据保持 | 红灯→绿灯 |
| TC-API-004 | component | Web 加载/自动保存/状态 | 状态正确切换，无丢数据 | 红灯→绿灯 |
| TC-API-005 | component | API 不可达降级 | 提示未连接，草稿保留 | 红灯→绿灯 |
| TC-REPO-001 | repository | 全仓门 | validator/Ruff/mypy/pytest/Web | 绿灯 |

## 交付物与关闭

- Commit/PR：分支 `feature/WORK-2026-014-local-persist-api`；先提交失败 API/Web 测试，再实现最小 sidecar 与前端接入。
- Contract/ADR/migration/prompt：无新 canonical contract；新增 `apps/api` composition root；无 prompt 变化。
- Test Run：API 集成 + Web 组件 + 全仓门按 DoD 执行；职责隔离 QA 对冻结 SHA 复核。
- Release：无托管发布；本地 `uv run uvicorn` + `pnpm dev` 可演示。
- 观察结果：本轮交付浏览器↔本地 API 的持久化闭环 prototype；Tauri 打包、认证、加密仍后置。
- 未完成项的新 ID：Tauri sidecar 打包、token/Origin 认证、FTS5 搜索、文件导入、加密与多进程分别后续建项。
