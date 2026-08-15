# WORK-2026-033：Windows 桌面封装（第 10 步切片 1：sidecar 冻结 + 自托管 UI + 生命周期 + 数据目录）

```yaml
status: ready
type: feature
owner: Codex (desktop composition + api + packaging role)
reviewers: [ai_qa_auditor, workspace_owner]
related_ids: [WORK-2026-013, WORK-2026-014, WORK-2026-021, WORK-2026-022, WORK-2026-026, WORK-2026-027, WORK-2026-032, REQ-2026-001, NFR-2026-001]
target_stage: "阶段 1 / 自然语言第 10 步（Windows 桌面封装）切片 1"
risk: medium
created_at: 2026-08-15T20:13:00+08:00
updated_at: 2026-08-15T20:13:00+08:00
```

## 问题与结果

- 用户/工程问题：第 0–9 步已交付并 QA 封存，个人 MVP 约 90%。但当前只能以
  `uv run python -m apps.api` + Vite dev server（或手动 dist）在本机跑，新机器无法安装：
  没有冻结产物、没有自托管 UI、没有桌面生命周期与数据目录策略。第 10 步完成标志是
  「新机器可安装，从写笔记/导入资料到人工编辑、AI 草案、来源回跳、撤销恢复的完整流程通过」。
- 期望结果：本地 sidecar 被 PyInstaller 冻结为可执行文件，启动时同时托管 UI 与 API（同源、
  免 CORS）、健康后打开 UI、数据目录默认落在 `%LOCALAPPDATA%\知枝\data`（升级/替换不丢数据）、
  单实例、退出后无孤儿进程；完整流程在冻结产物上冒烟通过。
- 成功如何被观察：从失败测试启动；`create_app(web_dist=...)` 自托管 index.html/assets；冻结产物
  启动后 `/api/health` 200、`/` 返回 index.html；数据目录自动创建且可写；单实例 fail-closed；
  退出后端口释放；全流程 e2e 冒烟（写笔记→保存→重载仍在；导入 MD→AI 草案→接受→来源回跳→撤销）通过；
  全仓门全绿。

## 范围

- In scope（切片 1）：
  - `apps/api/_runtime.py`：`runtime_root()`（frozen 感知：`sys._MEIPASS` 优先，否则仓库根）+
    `ensure_source_paths()`（仅源码运行注入 packages/*/src 与仓库根；冻结时 no-op）。
  - `apps/api/{ai_draft,answer,command}.py` + `apps/api/__main__.py`：改用 `_runtime` 做
    source path 注入与 `runtime_root()`，使 `load_and_validate_llm_config(root)` 在冻结态
    定位到打包进 `_MEIPASS` 的 `config/llm`。
  - `apps/api/main.py`：`create_app(..., web_dist: Path | None = None)`；`web_dist` 存在时在
    所有 API 路由之后 `mount("/", StaticFiles(directory=web_dist, html=True))`（同源自托管）。
  - `apps/desktop/launcher.py`（`python -m apps.desktop.launcher` / PyInstaller 入口）：
    `--data-root`（默认 `%LOCALAPPDATA%\知枝\data`）、`--port`（默认 8000）、`--no-browser`、
    `--web-dist`（默认 `runtime_root()/web_dist`）；`uvicorn` 以 `loop="asyncio", http="h11"`
    运行在 `127.0.0.1`，健康轮询后打开系统默认浏览器到 `http://127.0.0.1:<port>/`；单实例
    （端口占用即 fail-closed 退出）；Ctrl+C / 窗口关闭后优雅退出（server.should_exit）。
  - `apps/desktop/build.spec`（PyInstaller onedir）+ `scripts/build_desktop.py`：构建 Web
    （`pnpm build`）→ PyInstaller 冻结，`datas` 打包 `config/llm/**` 与 `apps/web/dist/**`
    （落到 `_MEIPASS`）；`hiddenimports` 覆盖 knowledge_tree_* 与 uvicorn 子模块。
  - `pyproject.toml`：新增 `[dependency-groups] build = ["pyinstaller>=6,<7"]`。
  - 测试：`tests/integration/test_desktop_serve.py`——`web_dist` 自托管 index.html/assets、
    SPA 回退、API 优先于静态挂载；`apps.desktop.launcher` 导入存在。
- Out of scope（切片 1）：pywebview 原生窗口（owner 决策，切片 2）；Inno Setup 安装器/开始菜单/
  自动升级/代码签名（owner 决策，切片 3）；AI Key 配置 UI（仍读 `DEEPSEEK_API_KEY` env，无 Key
  显示「AI 未连接」）；向量检索（Embedding provider 未决，第 9 步遗留 owner 决策）。
- 受影响模块/接口/数据：`create_app` 新增可选 `web_dist`（无 canonical contract/迁移）；三个
  generator 组合根与 `__main__` 的路径引导改为共享 `_runtime`；新增 `apps/desktop/`；数据目录
  沿用 WORK-2026-013 的 workspace 布局与 WORK-2026-021 的备份/恢复，不改变存储格式。
- 依赖和假设：WORK-2026-013（workspace 布局/迁移）、WORK-2026-014（sidecar + CORS）、
  WORK-2026-021/022（备份/恢复/版本历史）、WORK-2026-026/027/029/032（AI 草案/来源/指令/历史）
  已验证；`config/llm` 与 `apps/web/dist` 是运行时必需数据；PyInstaller 为 owner 指定打包方案。

## 设计边界

- 领域/契约：无新 canonical contract/迁移。自托管只改变「UI 从哪来」，不改 API 语义；同源后
  Web 仍按 `VITE_LOCAL_API`（默认 `http://127.0.0.1:8000`）访问，恰好同源、无 CORS。
- frozen 感知：`runtime_root()` 用 `getattr(sys, "_MEIPASS", None)` 定位打包数据目录；源码运行
  回退到仓库根。source path 注入仅在非 frozen 时执行，避免冻结态把 `_MEIPASS` 当仓库根。
- 生命周期：uvicorn 用纯 Python `asyncio`+`h11`（PyInstaller 友好，规避 uvloop/httptools 隐藏
  导入）；端口占用即单实例冲突、fail-closed 退出；优雅退出释放端口。
- 数据目录：默认 `%LOCALAPPDATA%\知枝\data`，`--data-root` 可覆盖；程序目录与数据目录分离，
  替换/升级程序不触碰用户数据。

## 风险影响

- 数据/schema/migration：无迁移；数据目录位置改变只影响「默认值」，已有工作区可由 `--data-root`
  指向（`Path.home()/knowledge-tree-data` 兼容迁移提示写入用户文档）。
- 安全/隐私：仍仅绑定 `127.0.0.1`；静态托管仅 serve `web_dist` 目录内文件（StaticFiles 无目录
  逃逸）；密钥仍仅 env；无网络开放。
- 并发/幂等/恢复：单实例 fail-closed 防双写/抢端口；uvicorn 线程 + should_exit 优雅退出；
  崩溃后备份/恢复能力不变（WORK-2026-021）。
- 性能/容量/成本：自托管静态文件开销可忽略；零模型成本（AI 仍 env-gated）。
- 可观测性/诊断：启动/健康/端口占用打印明确日志；稳定错误码复用现有。
- 用户文档：`docs/USER_MANUAL.md` 增「桌面打包版」章节（解压即用、数据目录、升级、备份恢复、
  AI Key 配置）；路线第 10 步进度更新。

## 验收标准

- [ ] AC-1 (c1)：`create_app(web_dist=<含 index.html/assets 的目录>)` 时，`GET /` 返回 index.html、
  `GET /assets/...` 返回静态资源；`/api/health` 仍 200（API 路由优先于静态挂载）。
- [ ] AC-2 (c2)：`apps.desktop.launcher` 可导入；`--data-root` 缺省为 `%LOCALAPPDATA%\知枝\data`
  且自动创建、可写；`--data-root` 覆盖生效。
- [ ] AC-3 (c3)：单实例：端口被占时第二实例 fail-closed 退出（不双写、不抢端口）。
- [ ] AC-4 (c4)：优雅退出释放端口（无孤儿 uvicorn）。
- [ ] AC-5 (c5)：冻结产物 e2e 冒烟：启动→`/api/health` 200→`/` 返回 UI→写笔记保存重载仍在→导入
  MD→AI 草案（mock 或 env key）→接受→来源回跳→撤销恢复。
- [ ] AC-6 (c6)：repository 门：validator、Ruff、scripts + strict package mypy（含 apps/api）、
  全仓 pytest、Web 全绿；PyInstaller 构建可重复且产物可启动。
- [ ] 错误和恢复路径：`web_dist` 不存在/非法时不挂载且 API 仍可用；端口占用明确报错退出；
  数据目录不可写时明确报错。
- [ ] 回滚/禁用方法：回退本工作项提交即回到「`python -m apps.api` + 外部 Vite」；无数据格式变更，
  旧数据不受影响；红灯与证据保留。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-DSK-001 | integration | `web_dist` 自托管 index/assets/回退 + API 优先 | 200 且内容正确 | 待实现 |
| TC-DSK-002 | unit | `runtime_root()` 源码/frozen 分辨 + source path 注入 | 源码→仓库根；frozen→`_MEIPASS` | 待实现 |
| TC-DSK-003 | e2e | 冻结产物启动/健康/UI/数据目录/单实例/优雅退出 | AC-2..4 | 待实现 |
| TC-DSK-004 | e2e | 全流程冒烟（写笔记/导入/草案/接受/来源/撤销） | AC-5 | 待实现 |
| TC-REPO-001 | repository | 全仓门 | validator/Ruff/mypy/pytest/Web/build | 待实现 |

## 交付物与关闭

- Commit/PR：分支 `feature/WORK-2026-033-desktop-packaging`；Ready → 红灯 → 实现 → QA。
- Contract/ADR/migration/prompt：无新 canonical contract/ADR/migration/prompt；新增 PyInstaller
  打包 spec 与构建脚本。
- Test Run：TC-DSK-001..004 + 全仓门 + 冻结产物 e2e 冒烟。
- Release：冻结 onedir 产物（便携解压即用）；安装器/升级属切片 3（owner 决策）。
- 观察结果：新机器解压即用，完整流程在冻结产物上通过；第 10 步完成标志达成（切片 1）。
- 未完成项的新 ID：切片 2（pywebview 原生窗口）、切片 3（Inno Setup 安装器/升级/签名）待 owner
  决策后编号；向量检索（第 9 步遗留）。
