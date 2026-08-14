# TR-20260814-006：本地持久化 API sidecar 与 Web 自动保存验证

> 本报告冻结 `e0a4c7212aa8be2aae1b2319968b3f75159bfba1`
> 的本地持久化 API sidecar 与 Web 自动保存接入。它证明浏览器可通过
> loopback FastAPI 保存/加载 CourseGraph、自动保存与保存状态可见、API
> 不可达降级；不代表 Tauri 打包、认证/token、FTS5 搜索、导入、加密、
> 多进程或云同步已经完成。

```yaml
status: passed
test_level: integration_component_repository
owner: graph_qa_fresh
related_ids: [WORK-2026-014, REQ-2026-006, REQ-2026-008, NFR-2026-001, ADR-0005, ADR-0011, WORK-2026-013, TR-20260814-005]
build_id: e0a4c7212aa8be2aae1b2319968b3f75159bfba1
started_at: 2026-08-14T07:55:00+08:00
finished_at: 2026-08-14T08:05:00+08:00
supersedes: null
```

## 目的与门槛

- 证明 `apps/api` FastAPI sidecar 只监听 loopback、CORS 白名单精确、路径遍历被拒。
- 证明 PUT 保存合法 CourseGraph 后 GET 可回同一图（语义等价、revision 保留）；非法图 422 且不覆盖。
- 证明 Web 挂载加载已保存图、编辑后 debounce 自动保存、保存状态在 已保存/保存中/失败 间切换、API 不可达降级且草稿保留。
- 证明备份生成校验和；对未保存 workspace 的备份请求返回 404（不静默建库）。

## 方法与结果

| Test ID | 场景 | Actual | Result |
|---|---|---|---|
| TC-API-001 | health/loopback/CORS | 白名单外无 allow-origin 头；白名单内精确回显 | PASS |
| TC-API-002 | PUT 合法图 → GET | 语义等价、revision 保留 | PASS |
| TC-API-003 | PUT 非法图/非 JSON | 422 graph_invalid，原图保持 | PASS |
| TC-API-004 | backup/缺失 workspace | 校验和 sidecar；缺失 404 workspace_missing | PASS |
| TC-API-005 | Web 加载/自动保存/状态 | 状态正确切换，无丢数据 | PASS |
| TC-API-006 | API 不可达降级 | 提示未连接，草稿保留 | PASS |
| TC-REPO-001 | 完整 Python/仓库门 | API 8/8、全仓 183/183、Ruff/mypy/validator | PASS |
| TC-REPO-002 | TS/Web/依赖/构建门 | frozen install、peers、Web 10/10、check、build | PASS |

职责隔离 QA 两轮：attempt 001 审冻结 `6c0c33c` 返回 PASS（0 P0/P1，3 个
非阻塞 P2），其中 P2-1（对缺失 workspace 备份会静默建库返回 200）由修复
提交 `e0a4c72` 关闭并新增回归测试；attempt 002 复核修复返回 PASS（无新增
finding），P2-2（挂载加载竞态）与 P2-3（600ms debounce 关闭前不 flush）
确认属于原型已知边界、不影响本轮关闭。两份 QA 均因只读环境无法实跑，
变异为静态推演并如实披露；本会话随后实跑全门（183/183、Web 10/10）并做
真实 uvicorn e2e smoke（PUT→GET 往返、非法图 422、backup 校验和、CORS
拒绝恶意 Origin）全部通过。角色独立性无外部 Provider 证明，保守记录
`correlated_review`。

## 证据与结论

- Evidence manifest：`evidence/TR-20260814-006/manifest.json`。
- Decision：GO，仅限 WORK-2026-014 的本地持久化 API/Web 接入 prototype
  verification；允许下一工作项推进第 4 步剩余能力。
- 未完成/未授权：Tauri 打包、认证/token（ADR-0011/SPK-009）、FTS5 搜索、
  文件导入/PDF viewer、加密、多进程并发、云端同步、真实 Provider/Web、
  用户数据和发布。
