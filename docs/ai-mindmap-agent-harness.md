# 思维导图 Agent 约束（harness）说明

> 关联：WORK-2026-043（全库思维导图生成 agent）。本文件定义「自动规划思维导图」agent 的
> 行为边界。agent 的每一次运行都必须满足以下全部约束；任何一条被绕过即视为缺陷（P0/P1）。

## 目标

用户在应用内导入资料（PDF / Markdown / TXT）后，agent 自行**阅读全部资料**并**规划一张
知识树（思维导图）草案**：抽取概念、合并别名去重、推断树状/先修关系、绑定来源证据、自动
布局，最终以**可预览、可接受/拒绝**的 GraphPatch 草案呈现；接受后才经提交门写入数据库。

## 硬约束（harness，不可绕过）

1. **AI 输出永远是不可信草案**：agent 不直接写数据库；唯一写入路径是用户在界面上确认
   「接受并写入」后由既有提交门（`apply_graph_patch`/`accept_ai_draft`）执行。
2. **预览→确认→锁定→历史→校验，五关全过才落库**：草案在预览层通过 `preview_graph_patch`
   （`requires_confirmation`）防御性校验；接受路径仍受锁定维度、修订号冲突、确认位、
   DAG 环检测、schema 校验约束；写入后进入版本历史、可撤销。
3. **来源证据强绑定**：每个新概念/关系必须携带 `evidence_ids`，指向真实导入资料的锚点
   （按资源 `deterministic_uuidv7(resource_id)` 确定性生成）；接受时锚点与图修改**同一
   事务**物化；无证据的 AI 概念/先修关系 fail-closed 拒绝。
4. **结构确定性校验**：分块（段落对齐、重叠受限）、标签规范化、别名合并（证据并集、最高
   置信度）、去重（既有概念永不重建）、DAG/环拒绝、自动布局——全部纯领域内核、离线可重放。
5. **fail-closed**：无 Key → 503 `ai_not_available`；模型输出畸形 → 422
   `draft_extraction_failed`（不回显推理文本）；配置损坏 → 降级 503；无资料 → 422
   `no_resources`；PDF 未解析由端点自动解析后读取（幂等）。
6. **预算上限**：按 task profile 的 `max_attempts`/`max_output_tokens`/`max_cost_usd` 执行；
   全库模式总块数上限 `max_chunks`（40），超出截断（防爆预算）。单补丁操作数上限由契约
   `GraphPatch.operations.maxItems`（**5000**，WORK-2026-046）约束：一次生成（≤40 块）的
   现实最坏约 2.5k 操作（概念×2 + 关系），留 2 倍余量；越界草案仍 fail-closed
   `draft_invalid/maxItems`，上限不因放宽而移除。
7. **成本与安全**：仅调用已批准 provider（DeepSeek，`enabled: true`）；Key 只存本机
   `data_root/ai.json`、不回显、不入库不入日志。

## 使用的开源组件

| 组件 | 用途 |
|---|---|
| pypdf | PDF 页文本抽取（幂等、绑定 content_hash） |
| PDF.js | 前端 PDF 渲染与 bbox 高亮 |
| FastAPI / uvicorn | 本地 loopback sidecar |
| pywebview + WebView2 | 桌面原生窗口 |
| PyInstaller / Inno Setup | 冻结与安装器 |
| DeepSeek API（OpenAI Chat Completions 兼容） | 概念抽取 / 关系校验 / 问答 / 指令解释（自研 stdlib urllib 传输，无厂商 SDK） |

分块、抽取协议、合并、DAG 校验、补丁构建与提交门均为仓库自研纯 Python 内核
（`packages/domain` / `packages/infrastructure`），不引入 LangChain 等编排框架——编排本身
保持可审计、确定性、可重放。

## MCP 桥（WORK-2026-048 切片 1 + WORK-2026-050 切片 2）

桌面程序内置 MCP server（`--mcp-stdio`），供外部 AI 客户端调用。**约束**：

1. **外部 AI 永远不能写图库**：工具集为 `list_workspaces`/`read_workspace`/
   `preview_draft`/`validate_patch`/`propose_patch`/`proposal_status`/`export_png`，
   没有任何 apply/commit/save/accept 类图库写工具。`propose_patch` 只把经
   `preview_graph_patch` 防御性校验的**未确认**补丁（`requires_confirmation=true /
   confirmed=false`，预确认补丁 fail-closed 拒绝）落为工作区 `proposals/` 目录下的
   pending 提议文件（跨进程信道，非图库）；`proposal_status` 只读观察结果；
   `export_png`（WORK-2026-051）只把图渲染为 `exports/mindmap.png`（PIL 服务端
   渲染，读图不写图）。
2. **应用内确认机制（WORK-2026-050）**：提议仅在应用内 UI「外部提议」面板由用户逐条
   接受/拒绝。接受 = sidecar API 把存储的提议补丁副本置 `confirmed=true` 后走
   `apply_graph_patch` 提交门（锁/修订冲突/历史/可撤销，source=`mcp_proposal`），
   成功才 settle accepted（附 change_id）；提交门拒绝时提议保持 pending（fail-closed）。
   仅 pending→accepted/rejected 单向迁移。**外部 AI 不得自确认**——确认动作只存在于
   应用内本地回环 API，MCP 无对应工具；会话级自动确认开关（默认关）为后续独立评审项。
3. `preview_draft` 返回的补丁必须是 `requires_confirmation=true / confirmed=false` 的
   不可信草案，经 `preview_graph_patch` 防御性校验后才返回；无 key 时结构化
   `ai_not_available`，不崩溃、不吞错。
4. `validate_patch` 只做预检（dry-run），不落库；错误保持稳定 `code/rule`。
5. stdio 信道纯净（stdout 不重定向日志）；提议文件为原子写 JSON
   （`schema_version: 1`）；proposal_id 严格 UUID 校验防路径穿越；note 截断 500 字符。
6. stdio server 不占应用单实例锁；数据根与 key 沿用应用配置（`--data-root` /
   `data_root/ai.json`）。

## Web 搜索 provider 门（WORK-2026-053）

「主题 → 搜网 → 思维导图」链路的搜索侧约束（镜像 DeepSeek 门）：

1. **显式 opt-in**：仅在用户于设置对话框保存 Provider Key（`data_root/web-search.json`）
   或设置 `TAVILY_API_KEY`/`BRAVE_API_KEY` 环境变量后启用；无 key 时 API/MCP 一致
   结构化 `web_search_not_available`，**不发出任何网络请求**。
2. **受控密钥**：key 仅存本机数据目录（明文边界已文档化）、仅经 HTTPS 发往对应
   provider 域名（Tavily/Brave 二选一，白名单）、任何端点/错误/日志不回显。
3. **不可信输入**：搜索结果（标题/摘要）是外部不可信文本，只作为草案生成素材；
   产出仍是 `requires_confirmation` 草案，经应用内确认 + GraphPatch 提交门写入。
   prompt 注入面延续 fail-closed 处理（搜索文本不执行指令）。
4. query 上限 200 字符；结果仅保留 HTTPS 链接、摘要截断 1000 字符；15s 超时；
   错误稳定 `web_search_invalid_query`/`web_search_failed`（+rule）。
5. live 测试双门：`RUN_LIVE_WEB_SEARCH_TESTS=1` + provider key，默认 skip。

## 可观测与回滚

- 每次生成的前端状态（生成中/就绪/失败）可见；失败显示稳定错误码。
- 草案可拒绝丢弃；接受后的写入可撤销/重做（跨会话）；版本历史区分 AI 来源
  （`ai_draft`/`ai_command`）。
- 回滚：删除已接受概念即可（撤销）；或从备份恢复。
