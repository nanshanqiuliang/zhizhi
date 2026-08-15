# WORK-2026-034：Windows 桌面壳（pywebview 原生窗口，第 10 步切片 2）

```yaml
status: ready
type: feature
owner: Codex (desktop shell + packaging role)
reviewers: [ai_qa_auditor, workspace_owner]
related_ids: [WORK-2026-033, REQ-2026-001, NFR-2026-001]
target_stage: "阶段 1 / 自然语言第 10 步（Windows 桌面封装）切片 2"
risk: medium
created_at: 2026-08-15T21:00:00+08:00
updated_at: 2026-08-15T21:00:00+08:00
```

## 问题与结果

- 用户/工程问题：切片 1 已把 sidecar 冻结为便携 exe 并自托管 UI，但默认用「系统浏览器」打开，
  体验是浏览器标签页而非桌面应用；关闭浏览器标签页不会触发 sidecar 优雅退出（需 Ctrl+C）。
- 期望结果：默认以 **pywebview 原生窗口**（WebView2，Win10/11 自带运行时）打开同源 UI；关闭窗口
  即优雅关闭 sidecar 并释放端口；保留 `--no-window`（无窗口，供 CI/e2e）与 `--browser`（回退系统
  浏览器）两种模式；冻结产物正确打包 pywebview/pythonnet/WebView2 程序集。
- 成功如何被观察：从失败测试启动；`open_window(url)` 调 `webview.create_window`/`webview.start`；
  窗口模式启动后 sidecar 健康、GUI 循环进入且不崩溃；关窗后端口释放；`--no-window` 仍 headless 可
  测；冻结产物窗口模式可启动；全仓门全绿。

## 范围

- In scope（切片 2）：
  - `apps/desktop/shell.py`：`open_window(url, title)` 用 pywebview 创建原生窗口并阻塞到关窗。
  - `apps/desktop/launcher.py`：三模式——默认原生窗口；`--no-window`（headless，sidecar 仅）；
    `--browser`（回退系统浏览器）；关窗后 `server.should_exit` 优雅退出并释放端口（关闭 P2-5）。
  - frozen 态写诊断日志（windowed 无控制台）：stdout/stderr 重定向到 `data_root/zhizhi.log`。
  - `apps/desktop/build.spec`：`console=False`（windowed）；hiddenimports 增
    `webview.platforms.winforms`/`webview.platforms.edgechromium`/`clr`/`clr_loader`（PyInstaller
    hook 会自动收集 `webview/lib` 与 pythonnet 运行时，hiddenimports 兜底动态平台导入）。
  - `pyproject.toml` build 组增 `pywebview>=5,<7`。
  - 测试：`tests/unit/test_desktop_shell.py`（mock webview 断言 create_window/start）；e2e 改用
    `--no-window` 并增「窗口模式启动不崩溃」冒烟。
- Out of scope（切片 2）：系统托盘/文件关联/单实例窗口激活（把已运行实例带到前台）；Inno Setup
  安装器/自动升级/代码签名（切片 3b）；日志轮转；多窗口。
- 受影响模块/接口/数据：新增 `apps/desktop/shell.py`；`launcher.py` CLI 模式变化（`--no-browser`
  改为 `--no-window`，新增 `--browser`）；`build.spec` console/hiddenimports；无 canonical
  contract/迁移/存储格式变化。
- 依赖和假设：WORK-2026-033（切片 1 已验证）；WebView2 运行时（本机 151.0.4129.86，Win10/11
  自带）；pywebview 6.2.1 + pythonnet 3.1.0（build 组已装）；PyInstaller hook-webview/hook-clr。

## 设计边界

- 领域/契约：无新 canonical contract/迁移。窗口只「呈现」同源 UI，不改 API 语义；sidecar 仍
  127.0.0.1。
- 生命周期：uvicorn 后台线程 + pywebview 主线程 GUI 循环；关窗 → `webview.start()` 返回 →
  `server.should_exit` → join → 删锁。这是真正的优雅退出（闭合 P2-5 硬杀证据）。
- 三模式：window（默认）/ browser（`--browser`）/ headless（`--no-window`）；headless 供 e2e 与
  CI，行为与切片 1 一致。
- 打包：windowed（`console=False`）无控制台；frozen 态 stdout/stderr 写 `data_root/zhizhi.log`
  以便诊断；源码运行保持控制台输出。

## 风险影响

- 数据/schema/migration：无迁移；数据目录不变。
- 安全/隐私：仍仅 127.0.0.1；pywebview 仅加载本地同源 URL；密钥仍 env-only。
- 并发/幂等/恢复：单实例逻辑不变（锁文件 + 健康探测）；关窗优雅退出释放端口；崩溃后陈旧锁接管。
- 性能/容量/成本：WebView2 常驻内存约几十 MB；零模型成本。
- 可观测性/诊断：frozen 窗口模式写 `zhizhi.log`；`--no-window` 走控制台/管道。
- 用户文档：`USER_MANUAL` 更新「双击 exe → 原生窗口，关窗即退」；路线第 10 步进度更新。

## 验收标准

- [ ] AC-1 (c1)：`open_window(url)` 调用 `webview.create_window(title, url)` 与 `webview.start()`。
- [ ] AC-2 (c2)：窗口模式启动：sidecar `/api/health` 200 且 GUI 循环进入（进程存活、无崩溃）。
- [ ] AC-3 (c3)：关窗 → sidecar 优雅退出、端口释放（无孤儿）。
- [ ] AC-4 (c4)：`--no-window`（headless）仍可跑 e2e（sidecar 仅，无窗口）；`--browser` 回退系统浏览器。
- [ ] AC-5 (c5)：冻结产物（windowed）窗口模式可启动；`webview/lib` + pythonnet 运行时被打包。
- [ ] AC-6 (c6)：repository 门：validator、Ruff、scripts + strict package mypy、全仓 pytest、Web 全绿。
- [ ] 错误和恢复路径：WebView2/pythonnet 加载失败时 fail-closed（明确错误、不挂起）；端口占用明确报错。
- [ ] 回滚/禁用方法：回退本工作项提交即回到「默认系统浏览器」；`--no-window` 保留 headless 路径。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-SHELL-001 | unit | `open_window` 调 create_window/start | mock webview 断言 | 待实现 |
| TC-SHELL-002 | e2e | 窗口模式启动不崩溃 + sidecar 健康 | 进程存活、health 200 | 待实现 |
| TC-SHELL-003 | e2e | 关窗 → 端口释放 | 优雅退出 | 待实现 |
| TC-SHELL-004 | e2e | `--no-window` headless + 冻结窗口模式 | 15 项冒烟 + 窗口冒烟 | 待实现 |
| TC-REPO-001 | repository | 全仓门 | validator/Ruff/mypy/pytest/Web | 待实现 |

## 交付物与关闭

- Commit/PR：分支 `feature/WORK-2026-034-pywebview-shell`；Ready → 红灯 → 实现 → QA。
- Contract/ADR/migration/prompt：无新 canonical contract/ADR/migration/prompt；build 组增 pywebview。
- Test Run：TC-SHELL-001..004 + 全仓门 + 冻结窗口冒烟。
- Release：`dist/zhizhi/zhizhi.exe`（windowed，双击即原生窗口）；便携 zip 由 `package_desktop.py` 产出。
- 观察结果：双击 exe → 原生窗口；关窗即退；第 10 步切片 2（桌面壳）达成。
- 未完成项的新 ID：切片 3b（Inno Setup 安装器/升级/签名）待 owner 决策后编号；向量检索（第 9 步遗留）。
