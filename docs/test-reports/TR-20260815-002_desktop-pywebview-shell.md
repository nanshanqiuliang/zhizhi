# TR-20260815-002：pywebview 原生窗口验证（WORK-2026-034，第 10 步切片 2）

> 本报告密封 `cee4fe241d5c0ae8d7ed10f42c006c356c1f468d` 的 WORK-2026-034（第 10 步切片 2：
> pywebview WebView2 原生窗口壳 + launcher 三模式 + 关窗优雅退出 + `console=False` 打包）。
> 它证明冻结桌面产物双击即以原生窗口呈现同源 UI、关窗即优雅退出释放端口，且 `--no-window`
> headless 路径仍可用于 CI/e2e。超集修复 `dd86465` 关闭 3 项 P3（文档依赖位置、AC 证据、
> windowed 崩溃模态框）。

```yaml
status: passed
test_level: unit_integration_repository_e2e
owner: ai_qa_auditor
related_ids: [WORK-2026-034, WORK-2026-033, REQ-2026-001, NFR-2026-001]
build_id: cee4fe241d5c0ae8d7ed10f42c006c356c1f468d
started_at: 2026-08-15T21:15:00+08:00
finished_at: 2026-08-15T21:40:00+08:00
supersedes: null
```

## 目的与门槛

- 证明 `open_window(url)` 调 `webview.create_window`/`webview.start`。
- 证明窗口模式：sidecar `/api/health` 200 且 GUI 循环进入（进程存活、无崩溃）。
- 证明关窗 → sidecar 优雅退出、端口释放、锁删除（无孤儿）。
- 证明 `--no-window` headless 可跑 e2e；`--browser` 回退系统浏览器。
- 证明冻结 windowed 产物可启动且 `webview/lib` + pythonnet 运行时已打包。
- 证明全仓门全绿。

## 方法与结果

| Test ID | 场景 | Actual | Result |
|---|---|---|---|
| TC-SHELL-001 | `open_window` 调 create_window/start | mock webview 断言 create_window(title,url,1280,800)+start | PASS |
| TC-SHELL-002 | 窗口模式启动 + sidecar 健康 | window-health/process-alive（GUI 循环进入不崩溃） | PASS |
| TC-SHELL-003 | 关窗 → 优雅退出 | WM_CLOSE → exit 0、端口释放、锁删除、uvicorn 干净 shutdown | PASS |
| TC-SHELL-004 | `--no-window` headless + 冻结窗口模式 | e2e 18/18 | PASS |
| TC-REPO-001 | 完整门 | pytest 445/445 + 5 skipped；Ruff；strict mypy（39）；validator；sync | PASS |
| QA-001 | 职责隔离对抗审查 | 红灯真值 + 冻结 bundle + WM_CLOSE 复验 + 安全/锁泄漏静态追踪 | PASS（0 P0/P1/P2，3 P3） |

职责隔离 QA 对冻结 `cee4fe2` 返回 **PASS**（0 P0/P1/P2；3 个 informational P3 均由 `dd86465`
关闭）。QA 独立复验优雅关窗（WM_CLOSE → exit 0、端口释放、锁删除），确认 WebView2 窗口可证地
导航同源 UI，并静态追踪锁泄漏（`main()`/`_run()` finally 链无正常退出泄漏）、`_setup_frozen_logging`
源码运行 no-op、安全（127.0.0.1、`allowed_origins=[]`、仅本地同源 URL、AI 无 key 503）。

## 证据

- `evidence/TR-20260815-002/`：QA attempt 001、manifest、checksums、commands、environment、
  gate-summary。
- 本报告 `docs/test-reports/TR-20260815-002_desktop-pywebview-shell.md`。

职责隔离 QA 为 `correlated_review`（机器审查），非人类签名、非 owner 接受；最终残余风险接受属于
workspace owner。
