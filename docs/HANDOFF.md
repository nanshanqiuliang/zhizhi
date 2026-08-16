# 知枝（知识树 Agent）交接文档

> **交接基线**：2026-08-16 · main = `af754a3`（与远端同步）· 工作分支 `feature/WORK-2026-049-empty-graph-crash`（链式包含全部工作，main 已 fast-forward 追平）· 桌面产物 0.1.0（含全部 55 个工作项能力）。
> 仓库：<https://github.com/nanshanqiuliang/zhizhi>（**公开**，MIT）· CI `quality-gates` 三 job 全绿。
> 质量基线：pytest **524 passed + 6 skipped**、Web **22 文件 / 84 测试**、`mypy --strict` 45 文件、ruff/validator/contracts/peers 全绿。

---

## 1. 这是什么项目

**本地优先的个人 AI 知识管理工具**：把资料（Markdown/TXT/PDF）或网络主题变成一棵可编辑的"知识树"（思维导图），每个知识点可追溯来源（文档锚点/网页链接）。

一条不可妥协的核心理念贯穿全部代码：**AI 输出永远是不授信草案**。AI 只能读图与提议（草案/补丁/搜索结果都是素材），一切写库都经过应用内人工确认 + GraphPatch 提交门（锁/修订号/历史/可撤销）。外部 AI（MCP 客户端）同样**没有任何写图库或自确认工具**。

## 2. 十分钟上手

```powershell
# 环境：Windows + Python 3.12 + uv + Node 24 + pnpm 11（版本需与 CI 声明一致：
# uv 0.12.3 / node 24.14.1 / pnpm 11.19.0，见 .github/workflows/ci.yml）
uv sync --locked --group dev          # Python 依赖（构建再加 --group build）
pnpm install --frozen-lockfile        # 前端依赖

# 源码运行（两个终端；数据目录放仓库外）
uv run python -m apps.api --data-root C:\Users\<你>\knowledge-tree-data
pnpm --filter @knowledge-tree/web dev

# 全量门禁（提交前必跑，CI 同口径）
uv run python -m scripts.validate_repository
uv run ruff format --check packages scripts tests apps
uv run ruff check .
uv run mypy scripts
uv run python -m mypy --strict packages/contracts-py/src packages/domain/src packages/infrastructure/src apps/api apps/desktop
uv run python -m pytest
pnpm peers check && pnpm check && pnpm build
pnpm --filter @knowledge-tree/contracts-ts check
```

桌面体验：安装 `dist\zhizhi-0.1.0-setup.exe`（或解压 portable.zip）。数据在 `%LOCALAPPDATA%\知枝\data`，**安装/升级/卸载都不动它**。

## 3. 代码地图

```
apps/
  api/       FastAPI sidecar（组合根 create_app）
    main.py        全部端点（工作区/图/补丁/资源/锚点/AI 草案/问答/指令/
                   提议确认/Web 搜索/PNG 导出/设置）
    mcp_server.py  内置 MCP server（--mcp-stdio，8 个工具）
    ai_config.py / web_search_config.py   key 的文件+环境双通道（镜像模式）
  web/       React+TS 前端
    App.tsx        单文件主应用（画布/详情面板/草案/外部提议/来源链接）
    api.ts         PersistApi 接口 + 快照↔canonical 图转换（保真往返）
  desktop/   pywebview 壳（launcher.py 四模式：窗口/无窗口/浏览器/--mcp-stdio）
             build.spec（PyInstaller；注意 PIL 已不可加入 excludes）
  worker/    预留的进程边界
packages/
  contracts-py / contracts-ts   契约即代码：docs/contracts/*.schema.json 生成，
                                pnpm contracts:generate + drift 门（勿手改产物）
  domain/    纯领域内核（零框架依赖）
    graph_patch.py / graph_history.py   提交门/撤销重放（upsert_annotation
                                        按 kind 替换——多链接用 link_N 编号）
    ai_draft.py   草案内核：分块/合并/DAG + assign_draft_layout（垂直 tidy-tree）
  infrastructure/
    workspace.py   SQLite 工作区（图/历史/资源/锚点/FTS5/备份）
    proposals.py   外部提议文件存储（MCP↔sidecar 跨进程信道）
    png_export.py  PNG 导出（PIL + 层次布局）
    web_search.py  Tavily/Brave 搜索适配器（stdlib urllib、可注入 opener）
    llm/           LLM 端口与 DeepSeek adapter（urllib、SSE、预算/回退）
docs/
  ENGINEERING_PLAN.md 工作项总表（状态/证据/提交号）
  work-items/WORK-2026-*.md  每项的 Ready 文档（范围/AC/验证计划）
  test-reports/ 与 evidence/TR-*  QA 报告与证据（含 checksums/manifest）
  ai-mindmap-agent-harness.md  AI 约束总纲（MCP 门/Web 搜索门等）
  USER_MANUAL.md / OPS_LOG.md / DEVELOPMENT_LOG.md / TRACEABILITY_MATRIX.md
checkpoint.md  最新的进度恢复点（新会话从这里接）
```

**进程拓扑**（桌面模式）：pywebview 窗口 → 内嵌 sidecar API（loopback）→ SQLite/文件。MCP server 是独立进程（`zhizhi.exe --mcp-stdio --data-root <目录>`，不占单实例锁），与 sidecar 通过 `proposals/*.json` 文件信道交互。

**密钥**（永不入库）：`数据目录\ai.json`（DeepSeek）、`数据目录\web-search.json`（搜索 provider+key）；环境变量兜底 `DEEPSEEK_API_KEY` / `TAVILY_API_KEY` / `BRAVE_API_KEY`。live 测试双门：`RUN_LIVE_LLM_TESTS=1` / `RUN_LIVE_WEB_SEARCH_TESTS=1` + key，默认 skip。

## 4. 开发工作流（一个工作项的生命周期）

仓库铁律见 `AGENTS.md`。实际操作步骤（本仓库 55 个工作项都是这么做的）：

1. **Ready 文档**：`docs/work-items/WORK-2026-0NN_*.md`，写清问题/范围/AC/验证计划/回滚。
2. **红灯**：先写测试（真实运行、存档失败输出到 `evidence/TR-*/logs/red-run-*.log`）。
3. **实现**：最小范围。Python 改动过 `ruff format` + `ruff check --fix` 后再跑门禁（格式化会改文件，注意重新 Read）。
4. **全量门禁**：上面第 2 节的命令全绿。
5. **QA 封存**：`docs/test-reports/TR-YYYYMMDD-NNN_*.md` + `evidence/TR-*/`（commands.txt、manifest.json、gates 日志、checksums.sha256）；报告头部按惯例披露 `correlated_review`、`human_signature=false`、`owner_acceptance=false`。
6. **文档同步**：ENGINEERING_PLAN 加行、DEVELOPMENT_LOG 加条目、TRACEABILITY_MATRIX 加行、USER_MANUAL（用户可见变化）、checkpoint.md 更新"Exact next action"。
7. **提交**：Conventional Commits，正文带 `Refs:` 和实际执行的测试。
8. **产物**（涉及桌面能力时）：见第 5 节。
9. **推送**：main fast-forward 自工作分支后 `git push origin main`，等 CI 绿。注意本机到 GitHub 的 HTTPS 偶发中断——静默重试即可（历史多次 2-5 次内成功）。

## 5. 发布（桌面产物）流程

```powershell
# 前置：关闭正在运行的 zhizhi.exe（否则 PyInstaller 清理 dist 报 PermissionError，
# 这是历史上最常见的构建失败原因，已三次记录在 OPS_LOG）
pnpm build
uv run --group dev --group build python scripts/build_desktop.py      # 冻结 onedir
uv run --group dev --group build python scripts/build_installer.py    # Inno Setup
uv run --group dev --group build python scripts/package_desktop.py    # portable zip
```

冒烟（建议每次重建后跑，探针已存档可复用）：

```powershell
uv run --group dev --group build python evidence/TR-20260816-004/probes/frozen_search_smoke.py
# 验证：8 工具枚举 + search_draft 无 key fail-closed（2/2 PASS）
```

## 6. 当前系统能力清单（用户视角）

- 多课程知识树画布：编辑/自由建块/连线断线（4 种边类型）/拖拽缩放（无限画布）/
  锁定（内容/关系/位置）/撤销重做/版本历史（区分 AI 来源）/备份恢复/FTS5 搜索/
  安全导入（MD/TXT/PDF）/PDF 查看器 + 锚点跳转与漂移保护
- AI：DeepSeek 草案（单资源/全库，40 块上限 fail-soft 可诊断）→ 预览确认 → 写入；
  带来源问答；自然语言指令；**网络主题搜索草案**（Tavily/Brave，默认零网络出口）
- 排版：垂直树形自动排布（父居中/间距宽松/孤立底行/锁定保持），AI 草案同规则落位
- 来源跳转：节点详情面板「来源与链接」——文档锚点跳 PDF 对应页、网页链接开浏览器、
  手动添加链接（提交门写入）；搜索草案来源自动持久化；🔗 画布角标
- MCP（8 工具，外部 AI 客户端如 Cursor 可用）：list_workspaces / read_workspace /
  preview_draft / validate_patch / **propose_patch（入队待确认提议）** /
  proposal_status（只读观察）/ export_png / search_draft——无任何写图库动词
- 应用内确认：「外部提议（MCP）」面板逐条接受（走提交门，source=mcp_proposal）/拒绝
- PNG 导出：Web 按钮 / GET /graph/image / MCP export_png 三入口

## 7. 治理红线（接手必读）

1. **AI 永不直写库**：任何新 AI 能力只能产出草案/提议；写库必须走应用内确认 +
   `apply_graph_patch`。外部 AI 不得自确认（会话级自动确认开关若要做，须独立过
   harness 评审，目前有意未实现）。
2. **provider 门**：真实网络调用必须文档化门 + 显式 opt-in 环境变量 + 受控密钥引用
   （mirror DeepSeek/Tavily/Brave 模式）；无 key = 结构化 fail-closed 零网络出口。
3. **契约单一事实源**：改 schema 只改 `docs/contracts/*.json`，跑 `pnpm contracts:generate`
   （含 drift 门）；不要手改生成产物，不要在两处维护同义枚举。
4. **领域纯净**：domain 不 import FastAPI/SQLAlchemy/LLM SDK/存储实现。
5. **秘密不入库**：secret scan 是门禁一部分；数据目录/产物/大文件不入 git。
6. **稳定标识**：snake_case 错误码、UTC 时间戳、UUIDv7 业务 id、可演进 JSON 带
   schema_version。
7. **证据文化**：计划不是证据；implemented 要有 commit，verified 要有可重复 Test Run。
   不改写已封存报告——出补充就写 addendum（已有先例）。

## 8. 关键设计决策（为什么是这样）

| 决策 | 理由 |
|---|---|
| MCP 有 propose 无 apply | 外部提议落 `proposals/*.json`（跨进程文件信道），确认只存在于应用内本地 API——单用户本地场景下最简单且守住"不自确认"红线 |
| upsert_annotation 按 kind 替换 | 契约既有语义；多链接用 `link_1..N` 编号天然幂等 |
| 搜索 provider 用 stdlib urllib | 与 LLM 传输层一致，零新依赖、可注入 opener 离线测试、冻结体积不涨 |
| 快照往返保真（055 修复） | 整图自动保存曾清空 evidence_ids/丢注解——保真测试锁定，改 `api.ts` 快照转换时务必保持 |
| 提议排序 (created_at, proposal_id) 双键 | CI 抓到的同毫秒并列 flake；任何"按时间排序"的列表都应有确定性第二键 |
| 垂直 tidy-tree 布局在 domain（草案）与 web（排布）各一份 | 两端坐标语义不同（槽位 vs 像素），统一是可选重构不是缺陷 |
| 分支模型：链式 feature + main ff | 个人项目最小摩擦；main 与远端始终同步，CI 每次 push 验证 |
| 公开 + MIT（2026-08-16 定） | owner 决策；公开前确认 secret scan 全绿、无个人数据入库 |

## 9. 已知问题 / 遗留 / 环境缺口

- **BUG-2026-001**：已修复（WORK-2026-049），状态 ready_for_release，随 0.1.0 产物
  安装验证后可在 BUG_REGISTER 转 closed。
- 观察项（P3，不阻塞）：vite chunk >500KB 警告（既有）；exe 体积随依赖缓慢增长；
  构建时 zhizhi.exe 运行会锁文件（流程已写明）；GitHub 推送偶发网络重试。
- 功能遗留：链接删除/编辑（同序号 upsert 可覆盖，完整删除走 update_concept）；
  MD/TXT 来源只能打开无法页内定位；PNG 导出布局未映射画布自由拖拽坐标；
  会话级自动确认开关（需 harness 评审）；B-lite agentic 绘图编排（机制已就绪未做）；
  提议 TTL/清理；问答接搜索；向量检索（Embedding provider 长期未决）；代码签名
  （无证书，SmartScreen 会提示）；分支保护规则未在 GitHub 设置（建议 owner 补）。
- 真实链路复测：live DeepSeek 全库生成与真实搜索全链路需 owner 配 key 实测
  （自动化只覆盖注入链路与 fail-closed）。

## 10. 建议的下一步（按价值排序）

1. **分支保护**（5 分钟）：GitHub Settings → Branches → main 要求
   `Python contracts and tests` + `TypeScript checks and build` 必须通过。
2. **B-lite agentic 绘图**（10–16h）：外部 AI 循环 `read_workspace → propose_patch →
   proposal_status`，应用内受权确认——050 的机制已全部就绪，只差编排与评审。
3. **链接管理增强**（2–4h）：删除/编辑/标题（update_concept 全量或扩 Annotation）。
4. **hardening 批次**：OCR/PPTX/DOCX 导入、大图性能、安全红队、代码签名与更新通道。
5. **向量检索**（第 9 步遗留）：定 Embedding provider 后走 provider 门模式接入。

## 11. 常见任务速查

| 任务 | 入口 |
|---|---|
| 加 API 端点 | `apps/api/main.py`（错误统一 `_http_error`/HTTPException code 形状） |
| 加 MCP 工具 | `apps/api/mcp_server.py` 的 `tool_*` 纯函数 + 注册；同步更新 `test_mcp_bridge.py` 两处工具集断言与 stdio 冒烟、冻结冒烟探针 |
| 改布局 | domain `ai_draft.py::assign_draft_layout`（草案落位）+ `App.tsx` 顶部 `LAYOUT_*` 与 `layoutWorkspace`（画布排布） |
| 改契约 | `docs/contracts/*.schema.json` → `pnpm contracts:generate` → 两端产物更新 + drift 门 |
| 加搜索 provider | `web_search.py`（适配器+白名单）+ `web_search_config.py`（env 变量）+ live 冒烟门 |
| 数据恢复 | 工作区 `backups/` + 应用内恢复；`exports/` 是导出产物可删 |
| 查历史决策 | `docs/DEVELOPMENT_LOG.md`（技术）/ `docs/OPS_LOG.md`（运维）/ `docs/work-items/`（单项）/ `checkpoint.md`（最新快照） |

## 12. 联系与凭据

- 仓库 owner：GitHub `nanshanqiuliang`（gh CLI 已在本机认证，scopes：repo/workflow）。
- 一切密钥在用户本机数据目录与应用内设置，仓库与本文档均不含任何凭据。
- 交接时建议当面验证：源码跑起来、门禁全绿、装一次 setup.exe 走一遍
  「导入 PDF → 生成草案 → 确认 → 点节点跳来源」。
