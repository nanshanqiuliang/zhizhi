# TR-20260815-001：Windows 桌面封装切片 1 验证（WORK-2026-033，第 10 步切片 1）

> 本报告密封 `fa8be626c72be4a3854ea98427cb11a4681c6cbe` 的 WORK-2026-033 切片 1
> （第 10 步 Windows 桌面封装：`create_app(web_dist)` 同源自托管 + frozen 感知
> `apps/api/_runtime.py` + `apps/desktop/launcher.py` 生命周期/单实例/数据目录 +
> PyInstaller onedir 冻结 `zhizhi.exe` + `desktop_e2e.py`）。它证明本地 sidecar 可被
> 冻结为便携可执行文件，同源自托管 UI、数据目录默认 `%LOCALAPPDATA%\知枝\data`、
> 单实例 fail-closed、退出释放端口，冻结产物 e2e 全流程（写笔记/导入/补丁+撤销/AI 无 key
> 安全降级）通过。超集修复提交 `0067aae` 关闭 3 项 P2（启动窗口竞态、自定义端口同源、
> 无 UI 警告），另加便携 zip 打包 `a0e60dc`。

```yaml
status: passed
test_level: unit_integration_repository_e2e
owner: ai_qa_auditor
related_ids: [WORK-2026-033, WORK-2026-013, WORK-2026-014, WORK-2026-021, WORK-2026-022, WORK-2026-026, WORK-2026-027, REQ-2026-001, NFR-2026-001]
build_id: fa8be626c72be4a3854ea98427cb11a4681c6cbe
started_at: 2026-08-15T20:30:00+08:00
finished_at: 2026-08-15T20:55:00+08:00
supersedes: null
```

## 目的与门槛

- 证明 `create_app(web_dist=...)` 同源自托管 UI，API 路由优先于静态挂载。
- 证明 frozen 感知 `runtime_root()` 使冻结进程内 `config/llm` 从 `_MEIPASS` 正确解析。
- 证明桌面启动器：数据目录默认 `%LOCALAPPDATA%\知枝\data` 自动创建；单实例（锁文件记端口
  + 健康探测）fail-closed；崩溃后陈旧锁接管；退出释放端口。
- 证明 PyInstaller onedir 冻结产物可启动并跑通端到端流程（AI 无 key 时安全降级 503）。
- 证明全仓门（validator/Ruff/mypy/pytest/Web/build）全绿。

## 方法与结果

| Test ID | 场景 | Actual | Result |
|---|---|---|---|
| TC-DSK-001 | `web_dist` 自托管 index/assets + API 优先 | `/`→index.html、`/assets/...` 200、`/api/health` 200 | PASS |
| TC-DSK-002 | `runtime_root()` 源码/frozen 分辨 | 冻结态伪 key 探针 422（非 503），证明 `_MEIPASS/config/llm` 被加载校验 | PASS |
| TC-DSK-003 | 启动器数据目录/单实例/端口释放 | e2e 数据目录+锁、第二实例 exit 1、首实例仍健康、端口释放 | PASS |
| TC-DSK-004 | 冻结产物全流程 | 健康/UI/图 PUT-GET/导入/补丁+撤销/AI 无 key 503 | PASS |
| TC-REPO-001 | 完整门 | pytest 442/442 + 5 skipped；Ruff；strict mypy（37）；validator；Web 41/41；build | PASS |
| QA-001 | 职责隔离对抗审查 | 红灯真值实际运行；冻结 config/llm 探针；单实例/静态托管/安全静态+执行探针 | PASS（0 P0/P1，5 P2） |

职责隔离 QA 对冻结 `fa8be62` 返回 **PASS**（0 P0/P1；5 个非阻塞 P2）。对抗审查覆盖红灯真值
（分离 worktree 运行 `8edf336` 得 2 failed）、冻结 `config/llm` 解析（伪 key 探针）、
`runtime_root()` 父级算术、Windows 单实例（无 `os.kill`，锁文件记端口 + 健康探测）、
StaticFiles 目录逃逸防护（Starlette 1.6.0）、路由优先级、spec `parents[1]` 算术、安全
（仅 127.0.0.1、无密钥落盘、AI fail-closed）。

5 项 P2 处置：P2-1（单实例启动窗口竞态）、P2-2（`--port ≠ 8000` 跨源被拦）、P2-4（无 UI
静默）由 `0067aae` 关闭；P2-3（文档漂移）随本轮文档同步修正；P2-5（优雅退出证据为硬杀）
记录为原型边界（Windows 自动化 Ctrl+C 不可靠）。

## 证据

- `evidence/TR-20260815-001/`：QA attempt 001、manifest、checksums、commands、
  environment、gate-summary。
- 本报告 `docs/test-reports/TR-20260815-001_desktop-packaging-slice1.md`。

职责隔离 QA 为 `correlated_review`（机器审查），非人类签名、非 owner 接受；最终残余风险接受
属于 workspace owner。
