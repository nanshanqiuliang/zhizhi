# WORK-2026-048：内置 MCP server（第 11 步切片 1：读 + AI 提议，零写工具）

```yaml
status: ready
type: feature
owner: api + desktop + QA
reviewers: [project_owner, qa]
related_ids: [WORK-2026-043/046/047, REQ-2026-001, NFR-2026-001]
target_stage: 第 11 步 Beta 加固与扩展
risk: medium
created_at: 2026-08-16T00:00:00Z
updated_at: 2026-08-16T00:00:00Z
```

## 问题与结果

- 用户/工程问题：知枝的能力（读知识树、AI 生成草案、提交门校验）只对应用内 UI 开放，
  无法被外部 AI 客户端（Cursor、Claude Desktop 等）以标准方式调用；MCP 方向分析文档
  （`docs/开源方案对比_内置MCP与AI脑图.md`、`docs/程序可用性实测与开源借鉴分析.md`）已
  确认「应用内置 MCP server」为最大缺口（全库零 MCP 实现）。
- 期望结果：桌面程序内置一个 MCP server（stdio），暴露**读 + AI 提议**工具，外部 MCP
  客户端可枚举工作区、读取知识树、请求 AI 草案、预检补丁；**本切片不暴露任何写库工具**
  ——AI 输出仍是不授信草案，确认与写库仍只在应用内（延续 harness 硬约束）。
- 成功如何被观察：① `zhizhi.exe --mcp-stdio --data-root <目录>` 以 MCP stdio 协议运行，
  标准客户端可 initialize/tools/list/tools/call；② 工具集精确为
  `list_workspaces`/`read_workspace`/`preview_draft`/`validate_patch`（无写工具）；
  ③ `preview_draft` 返回 `requires_confirmation=true / confirmed=false` 的草案补丁、
  不写库；无 key 时结构化 fail-closed；④ 协议级测试 + 全部门禁 + QA 封存。

## 范围

- In scope：
  - 依赖：`mcp` SDK（官方，MIT；1.x FastMCP；2.x 结构重构无 FastMCP，故锁 `<2`）。
  - `apps/api/mcp_server.py`：`build_mcp_server(data_root, *, draft_generator=None,
    workspace_draft_generator=None)`（注入式，镜像 `create_app`）；四个工具：
    `list_workspaces`（枚举 UUIDv7 工作区）、`read_workspace(workspace_id)`（canonical
    图 JSON）、`preview_draft(workspace_id, resource_id=None)`（单资源/全库，复用
    `/ai-draft` 语义：PDF 自动解析、40 块上限、fail-soft、`preview_graph_patch` 防御性
    校验；**不写库**）、`validate_patch(workspace_id, patch)`（`preview_graph_patch`
    预检，返回 status/snapshot 或错误，**不写库**）；`python -m apps.api.mcp_server
    --data-root <dir>` stdio 入口；所有工具返回结构化 `{ok, ...}`/`{ok:false, code, rule}`，
    不抛协议级异常。
  - `apps/desktop/launcher.py`：`--mcp-stdio` 模式（不占单实例锁、不改 stdout 日志——
    stdio 信道必须保持纯净），冻结产物可启动。
  - `apps/desktop/build.spec`：`mcp` 相关 hiddenimports。
  - 测试：`tests/integration/test_mcp_bridge.py`（工具集精确断言、读/提议/预检、
    fail-closed、真实 stdio 子进程协议冒烟）。
- Out of scope（后续切片）：写工具（`apply_patch`/确认队列——需设计"外部提议 → 应用内
  确认"机制）；`generate_mindmap` PNG 导出（matplotlib+PIL 渲染层）；streamable-http
  远程模式；MCP 客户端能力（调外部搜索 server 属第 11 步后续）。
- 受影响模块/接口/数据：新增 `apps/api/mcp_server.py` + 依赖 + launcher 模式；无契约/
  迁移/既有端点变化。
- 依赖和假设：`mcp<2`（FastMCP）可经 PyInstaller 冻结（hiddenimports 补齐并冒烟验证）；
  数据根为 `--data-root`（默认 `%LOCALAPPDATA%\知枝\data`）；DeepSeek key 复用
  `data_root/ai.json`/环境（`apps.api.ai_config`）。

## 风险影响

- 数据/schema/migration：无写路径，无数据影响；`validate_patch`/`preview_draft` 只读。
- 安全/隐私：**本切片无写工具** → 外部 AI 无法经 MCP 改图；读图/草案与既有权限一致
  （本地数据根、无网络出口）；stdio 仅本机进程管道。文档明确信任边界（后续切片加写工具
  必须重新过 harness 评审 + 应用内确认机制）。
- 并发/幂等/恢复：只读并发安全（SQLite WAL）；不占单实例锁，可与应用并行。
- 性能/容量/成本：草案生成沿用 `max_chunks=40` + 预算；无新增成本面。
- 可观测性/诊断：工具返回结构化 `code/rule`；日志走 stderr（不污染 stdio）。
- 用户文档：`USER_MANUAL` 增加"MCP 接入"说明；harness 文档补充 MCP 桥约束。

## 验收标准

- [ ] AC-1：`--mcp-stdio` 启动后标准 MCP 客户端完成 initialize + tools/list + tools/call。
- [ ] AC-2：工具集精确等于 4 个（无 write/apply/commit/save 类工具）。
- [ ] AC-3：`preview_draft` 返回 `requires_confirmation` 草案且不落库；无 key → 结构化
  `ai_not_available`。
- [ ] AC-4：`validate_patch` 对越权补丁（版本冲突/actor 不符）返回稳定错误、不写库。
- [ ] 错误和恢复路径：坏数据根/未知工作区返回结构化错误而非崩溃。
- [ ] 回滚/禁用方法：回退提交即移除 MCP 能力与依赖；`--mcp-stdio` 不启用不影响应用。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-MCP-001 | integration | 工具集精确断言 | 4 个工具、无写工具 | `test_mcp_bridge.py` |
| TC-MCP-002 | integration | list_workspaces/read_workspace | 枚举/读取正确 | 同上 |
| TC-MCP-003 | integration | preview_draft（注入生成器） | requires_confirmation/confirmed=false、不落库 | 同上 |
| TC-MCP-004 | integration | preview_draft 无 key | 结构化 ai_not_available | 同上 |
| TC-MCP-005 | integration | validate_patch 合法/非法 | status / 稳定错误、不落库 | 同上 |
| TC-MCP-006 | integration | stdio 子进程协议冒烟 | initialize/tools/list/call 成功 | 同上 |
| TC-MCP-007 | 全部门禁 | 既有回归不破坏 | pytest + Web + 构建绿 | 门禁输出 |
| TC-MCP-008 | desktop | 冻结 exe --mcp-stdio | 启动 + tools/list | e2e/冒烟脚本 |

## 交付物与关闭

- Commit/PR：红灯测试 → 实现 → 文档 → 证据封存。
- Contract/ADR/migration/prompt：无 canonical 契约变化；新增 `mcp<2` 依赖。
- Test Run：pytest 全量 + Web + ruff/mypy/validator/pnpm。
- Release：桌面 exe/安装器/zip 重建。
- 观察结果：QA 封存 `TR-20260815-010`。
- 未完成项的新 ID：写工具 + 应用内确认机制（切片 2）；`generate_mindmap` PNG（切片 3）。
