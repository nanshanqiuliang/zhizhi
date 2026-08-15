# AI QA attempt 001 — pywebview 原生窗口（WORK-2026-034，第 10 步切片 2）

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: ai_qa_auditor
decision: pass
reviewed_commit: cee4fe241d5c0ae8d7ed10f42c006c356c1f468d
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

**PASS** — 0 P0 / 0 P1 / 0 P2；3 个 P3（文档/卫生，无功能影响）。这是对冻结提交
`cee4fe2`（WORK-2026-034 第 10 步切片 2：`apps/desktop/shell.py` pywebview WebView2
原生窗口 + launcher 三模式 + 关窗优雅退出 + `console=False` 打包 + pywebview 入
`[project] dependencies`）的职责隔离机器审查。

## Red/green chain

Ready `14a9ffc`（仅文档）→ 红灯 `4f47e5b` → 实现 `cee4fe2`。红灯真值经 `git ls-tree`
确认（`4f47e5b` 无 `apps/desktop/shell.py`），红测试 `import apps.desktop.shell` →
ModuleNotFoundError，与提交声明一致。

## Gates（本人执行，精确数字）

- 聚焦测试（shell/launcher/serve）：**11/11**。
- 全仓 pytest：**445 passed + 5 skipped**（live-LLM skip 需 key）。
- `ruff check .`：clean；`ruff format --check`：106 文件。
- `mypy scripts`：14 文件；`mypy --strict packages+apps/api+apps/desktop`：39 文件。
- `scripts.validate_repository`：**PASS**（含 secret scan）。
- `uv sync --locked --group dev`：clean；`import webview` 可解析且 `py.typed` 存在（顶层
  `import webview` 类型化）。
- 冻结 e2e `scripts/desktop_e2e.py`：**18/18 PASS**（`--no-window` headless + 窗口冒烟）。

## 附加执行探针

- **冻结 bundle（AC-5）**：`_internal/webview/lib/` 含 `Microsoft.Web.WebView2.Core.dll`、
  `Microsoft.Web.WebView2.WinForms.dll`、`runtimes/*/native/WebView2Loader.dll`（x64/x86/arm64）；
  `Python.Runtime.dll` 与 `clr_loader`/`pythonnet` 均打包。
- **优雅关窗（AC-3，独立复验）**：启动 windowed exe → health 200 → 进程存活（GUI 循环）→ 找
  到顶层窗口（标题「知枝」）→ 发 **WM_CLOSE** → **exit 0、端口释放、锁删除**；`zhizhi.log`
  显示 uvicorn 干净 shutdown；WebView2 窗口可证地导航了同源 UI。
- **冻结错误路径**：无效 `--data-root`（路径被文件占用）→ 干净中文报错、exit 1、不崩溃不挂起。

## Findings（P3，informational，已由 `dd86465` 修复）

| Sev | 位置 | Finding | 处置 |
|-----|------|---------|------|
| P3 | 工作项 doc:36,45 | 文档写 pywebview 入「build 组」，实际移入 `[project] dependencies` | `dd86465` 修正文档 |
| P3 | 工作项 doc AC/证据 | AC 未勾选、验证证据标「待实现」 | `dd86465` 勾选并填证据 |
| P3 | build.spec:70 | `disable_windowed_traceback=False`，窗口态崩溃弹模态框挂起 | `dd86465` 改为 True |

## 执行 vs 静态追踪

- **执行**：全部 9 项门、红灯真值、冻结 e2e 18/18、冻结 bundle 内容、WM_CLOSE 优雅关窗、冻结
  错误路径。未改仓库文件。
- **静态追踪**：`--browser` 回退（避免弹系统浏览器）、模式分发（`--no-window` 不调 window/
  browser）、锁泄漏分析（`main()`/`_run()` finally 链无正常退出泄漏）、`_setup_frozen_logging`
  源码运行 no-op、安全（127.0.0.1 绑定、`allowed_origins=[]`、仅本地同源 URL、AI 无 key 503）。

## Disclosure

本报告为独立 AI QA 子 Agent（与实现 Agent 角色分离、同模型相关性）进行的机器审查，是证据与
工程发现的证明，**不是**人类签名、非 owner 接受。最终残余风险接受属于 workspace owner。
