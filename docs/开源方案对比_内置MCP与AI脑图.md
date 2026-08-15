# 开源方案架构对比与复用可行性报告

> 目标：评估 GitHub 上是否已有与「知枝 / 知识树 Agent」近似（手动笔记编辑 + AI 自动生成思维导图 + 应用**自带 MCP**）的现成程序，并明确**哪些模块能直接复用 / 借鉴 / 不可复用**。
> 调研日期：2026-08-16 ｜ 项目现状：`GraphPatch.operations.maxItems` 已从 100 放宽到 5000（`WORK-2026-046` 已落地），MCP 层仍为空白。

---

## 0. 一句话结论

- **不存在「三合一」现成替代品**：手动笔记编辑 + AI 自动成图 + 应用内置 MCP 的组合目前 GitHub 上没有成品。
- **`mind-map-mcp`**：是纯 MCP server（被外部 AI 调用的「工具提供方」），与你们「应用自带 MCP」的方向**最对口**，但它的代码**无 LICENSE（默认保留所有权利）**，**只能当架构参考，不能直接 copy**；其 markdown→PNG 的渲染层可借鉴自研「导出脑图图片」功能。
- **`SparkNoteAI`**：最接近你们的完整愿景（笔记 + AI → 知识图谱 + 脑图页），但技术栈很重（Neo4j / Redis / PostgreSQL），且是 **AGPL-3.0**（强传染性），**不建议搬代码，只借鉴架构模式**。
- **你们已有基础**（见 §3）已经覆盖了大部分难点：FastAPI sidecar + pywebview 桌面 + DeepSeek 草案管线 + 严格的 `GraphPatch` 契约。真正缺的只是「把已有能力通过 MCP 暴露出去」这一层，正好可以用 `mind-map-mcp` 的传输骨架思路来补。

---

## 1. `mind-map-mcp`（sawyer-shi）剖析

**定位**：一个**纯 MCP server**，把 Markdown 文本渲染成思维导图 PNG，供 Cursor / Claude Desktop 等外部 AI 客户端调用。**不是应用、没有 UI、不做笔记编辑、不做 AI 抽取**。

### 技术栈
| 项 | 内容 |
|---|---|
| MCP 框架 | 低层 `mcp.server.Server`（非 FastMCP） |
| HTTP 传输 | `fastapi` + `uvicorn` + `starlette` |
| 渲染 | `matplotlib`（Agg 后端画曲线）+ `PIL/Pillow`（画中文圆角矩形）+ `numpy` |
| 依赖总数 | 仅 6 个：`mcp, fastapi, uvicorn, pillow, matplotlib, numpy` |
| 传输模式 | stdio（本地）/ SSE（已弃用）/ streamable-http（推荐） |
| **许可证** | ⚠️ **仓库无 LICENSE 文件 → 默认 all rights reserved，不可直接复制使用** |

### 暴露的 Tools（核心）
- `create_center_mindmap`：放射状布局（适合核心概念 / 头脑风暴）
- `create_horizontal_mindmap`：从左到右布局（适合时间线 / 流程）
- `create_free_mindmap`：按内容复杂度自动选布局
- 三者输入均为单个 `markdown_content: string`，输出为 `ImageContent`（base64 PNG）+ 元数据 JSON。

### Markdown → 图片 渲染管线（可借鉴部分）
1. `_parse_markdown_to_tree`：正则 + 栈，把 `#` 标题和 `-`/`1.` 列表解析成层级树。
2. `_generate_png_mindmap`：`matplotlib` 算径向布局、贝塞尔曲线分支、碰撞避让；`PIL` 在底图上画带圆角矩形的中文标签。
3. 中文处理：`_setup_pil_chinese_font` 优先用自带 `fonts/chinese_font.ttc`，否则回退系统字体（Windows 微软雅黑/黑体、macOS 苹方、Linux 文泉驿/Noto CJK）。
4. `_invoke(params)` 是生成器，分批 yield `blob`（PNG）/ `text` / `json` 三类消息——这是典型的「Dify tool」封装模式。

### ✅ 对你们的复用价值
| 模块 | 复用方式 | 说明 |
|---|---|---|
| MCP 传输骨架（stdio/sse/http、tool 注册、JSON Schema、Windows UTF-8 处理、HTTP 懒加载 import） | **参考自研** | 你们是 FastAPI 技术栈，建议改用 `FastMCP`（更简洁），但传输/工具注册/懒加载思路可直接套 |
| `markdown → tree` 解析 + `matplotlib+PIL` 渲染 | **借鉴自研**（约 200 行，自研成本低） | 可做成你们「把 `GraphPatch`/笔记导出为脑图 PNG」的 tool，而非依赖外部库 |
| 3 个现成 tool 本身 | ❌ 不可直接复用 | 输入是 markdown 大纲，承载不了你们 concept/edge/evidence 的富语义 |

---

## 2. `SparkNoteAI`（spark-ai-boy）剖析

**定位**：完整的 AI 笔记应用（RN/Expo + Electron 桌面 + FastAPI 后端），笔记 → AI 抽取概念关系 → Neo4j 知识图谱 → 力导向图 / 独立脑图页。**是你们完整愿景最接近的成品**。

### 技术栈
| 层 | 技术 |
|---|---|
| 前端/桌面 | React Native + Expo；Electron 封装 Windows/macOS；Zustand；`md-editor-rt`（Markdown 编辑器）；`react-force-graph`（力导向图） |
| 后端 | FastAPI + Uvicorn + SQLAlchemy + Pydantic；JWT + bcrypt |
| 存储 | PostgreSQL + Redis（任务队列/缓存）+ **Neo4j**（图数据库） |
| AI | 多 LLM（OpenAI / Anthropic / Azure / 阿里云），可切换、可测连 |
| 部署 | Docker Compose + Nginx + GitHub Actions |
| **许可证** | ⚠️ **AGPL-3.0**（强 Copyleft，分发即须开源全部衍生代码） |

### 数据流（笔记 → 知识图谱）
1. 用户在 Markdown 编辑器保存笔记 → PostgreSQL；
2. 触发图谱构建任务 → 进 Redis 队列；
3. 后端 worker 调 LLM 抽取概念/关系；
4. 结果写入 Neo4j（节点=概念，边=关系）；
5. 前端轮询状态，用 `react-force-graph` 渲染。

### ✅ 对你们的借鉴价值（**仅模式，不搬代码**）
- **异步队列解耦**：把「AI 抽取」放进后台任务、前端轮询状态——你们已有类似草案管线，可继续沿用此模式。
- **多 LLM 配置系统**：你们已有 `deepseek` vendor adapter + `load_and_validate_llm_config`，架构领先，无需引入其重量级实现。
- **力导向图可视化**：`react-force-graph` 可作为你们前端可视化「知识树」的参考（注意 AGPL 组件若用于闭源产品有传染风险，建议选 MIT 替代品如 `reactflow` / `cytoscape`）。

### ❌ 不建议复用的部分
- **Neo4j / Redis / PostgreSQL 三库架构**：对你们「本地单用户、JSON 图 + `GraphPatch` 契约」的定位属于过度工程。你们的本地 JSON 图 + 确定性校验（`graph_patch.py`）更轻、更可控。
- **整套代码**：AGPL-3.0 下，若你们产品未来分发/商业化，会被强制开源。仅作架构参考。

---

## 3. 你们项目（知枝 / 知识树 Agent）现状

> 信息来自 `apps/desktop/launcher.py`、`apps/api/ai_draft.py`、`packages/domain/.../graph_patch.py` 等。

### 已有能力（强项）
- **桌面壳**：`apps/desktop` 用 **pywebview** 原生窗口 + **FastAPI sidecar**（loopback `127.0.0.1:8000`）+ **单实例锁** + **PyInstaller 冻结**。已有「重装 exe 才生效」的构建闭环。
- **AI 草案管线**：`ai_draft.py` 把资料文本经 DeepSeek 抽取 → 生成**未授信草案** + 用户可确认的 `GraphPatch`；严格遵循「草案永不直写库、须预览确认、带 evidence_ids 溯源」。
- **契约优先**：`GraphPatch` / `CourseGraph` 有 canonical JSON Schema + Python 生成产物 + 确定性语义校验（DAG/去重/循环拒绝），`maxItems` 上限 bug 已修复为 5000。
- **多 LLM vendor 适配**：基础设施层已有 `deepseek` adapter + 预算/弹性/计费。

### 缺口（空白）
- **MCP server**：`apps/` 内**没有任何 MCP 代码**，这是「自带 MCP」目标真正要补的部分。
- **脑图图片导出**：目前没有把图谱渲染成 PNG 的能力（`mind-map-mcp` 的渲染层正好可补这块）。

---

## 4. 复用映射矩阵

| 能力 | `mind-map-mcp` | `SparkNoteAI` | 你们现状 | 复用建议 |
|---|---|---|---|---|
| 桌面 UI（手动笔记编辑） | ❌ | ✅ RN+Electron | ✅ pywebview+FastAPI | 已具备，无需动 |
| AI 抽取概念/关系 | ❌ | ✅ LLM+Neo4j | ✅ DeepSeek 草案 | 已具备，无需动 |
| 知识图谱/脑图数据模型 | ❌（仅 markdown 树） | ✅ Neo4j | ✅ `GraphPatch`+JSON 图 | 已具备，更轻量 |
| **应用内置 MCP server** | ✅ 传输骨架 | ❌ | ❌ **空白** | **重点补：参考 mind-map-mcp 传输层，自研基于 GraphPatch 的 tools** |
| 脑图 PNG 导出 | ✅ matplotlib+PIL | ❌ | ❌ 空白 | 借鉴 mind-map-mcp 渲染层自研 |
| 力导向可视化 | ❌ | ✅ react-force-graph(AGPL) | ❌ | 参考，选 MIT 库（reactflow/cytoscape） |
| 异步任务队列 | ❌ | ✅ Redis | 部分（草案管线） | 沿用现有模式即可 |

---

## 5. 推荐的内置 MCP 最小接口（衔接现有 `GraphPatch`）

「自带 MCP」的正确形态：**让应用内部启动一个 MCP server，把已有的知识树能力暴露给外部 AI 客户端（Cursor/Claude）或内部调用**。建议 tools（替代 mind-map-mcp 那 3 个 markdown 工具）：

| Tool | 输入 | 输出 | 对接你们现有能力 |
|---|---|---|---|
| `generate_mindmap` | `workspace_id` / `note_id`（或概念树） | PNG 脑图（base64）+ 元数据 | 复用 mind-map-mcp 渲染层（自研），输入从 markdown 改为你们的 concept/edge 树 |
| `read_note` | `note_id` | 笔记 Markdown 文本 | 读 `apps/api` 已有笔记接口 |
| `apply_patch` | 一个 `GraphPatch`（operations 数组） | 校验结果（预览/确认） | 直接复用 `graph_patch.py` 的确定性校验 + 你们 commit gate |
| `preview_draft` | 资料文本 | 未授信草案 + `GraphPatch`（即现有 `/ai-draft`） | 直接复用 `ai_draft.py` |
| `list_workspaces` | — | 工作区列表 | 复用 workspace 基础设施 |

实现要点：
- 用 **FastMCP**（与 FastAPI 同源、心智负担低），stdio 模式随桌面启动一个子进程；远程模式用 streamable-http（参考 mind-map-mcp 的懒加载 import 写法，避免冻结包隐式依赖问题）。
- **所有写操作必须经 `GraphPatch` 校验 + 用户确认**，延续你们「AI 输出永不直写库」的硬性约束（见 `ai_draft.py` 顶部 harness 约束）。

---

## 6. 风险与下一步

### 风险
1. **`mind-map-mcp` 无 LICENSE**：不能直接复制其代码到你们仓库/产品。只能「阅读 → 自研等价实现」。其渲染逻辑约 200 行、依赖仅有 matplotlib+PIL，**自研成本极低**，建议直接重写而非 fork。
2. **`SparkNoteAI` AGPL-3.0**：任何代码/AGPL 组件（如 `react-force-graph`）用于闭源分发都会触发传染。可视化请改用 MIT/Apache 库。
3. **MCP 暴露面**：内置 MCP server 若开放 http 端口，需做鉴权/仅绑定 loopback，避免本地端口被任意进程调用改图。

### 建议下一步（按优先级）
1. **确认产品许可证意图**：若计划闭源分发，则 `mind-map-mcp` 仅供学习、`SparkNoteAI` 完全排除；若开源，则可更开放地参考。
2. **自研 MCP server 骨架**（参考 mind-map-mcp 传输层 + 你们 `GraphPatch`）：先实现 `preview_draft` + `apply_patch` 两个 tool，打通「外部 AI → 草案 → 确认 → 入库」闭环。
3. **自研脑图 PNG 导出**：把 `mind-map-mcp` 的 `matplotlib+PIL` 渲染改写成接受 concept/edge 树（而非 markdown）的 tool，作为 `generate_mindmap`。
4. 补 `WORK-2026-046` 的 240-operation 全库集成测试与桌面 e2e（见上一轮结论），复测 `paper.pdf` 与短文件。

---

*附录：本报告基于 GitHub 仓库 `sawyer-shi/mind-map-mcp`（master, 2025-12-15）、`spark-ai-boy/SparkNoteAI` 的 README/源码，以及本项目 `apps/`、`packages/` 现状梳理，未克隆完整代码库。*
