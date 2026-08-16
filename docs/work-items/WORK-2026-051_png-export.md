# WORK-2026-051：知识树 PNG 导出（第 11 步切片 3）

```yaml
status: ready
type: feature
owner: api + infrastructure + web + QA
reviewers: [project_owner, qa]
related_ids: [WORK-2026-048, WORK-2026-050, REQ-2026-001]
target_stage: 第 11 步 Beta 加固与扩展
risk: low
created_at: 2026-08-16T00:00:00Z
updated_at: 2026-08-16T00:00:00Z
```

## 问题与结果

- 用户/工程问题：知识树只能截图分享；外部 AI 客户端（MCP）也无法让知枝产出
  可嵌入文档的静态思维导图图（048 工作项 out-of-scope 已预告
  「generate_mindmap PNG 导出」切片；借鉴 mind-map-mcp 的渲染思路、自研实现）。
- 期望结果：任意工作区的知识树可一键导出为 PNG（确定性树布局、中文字体回退、
  tone 配色），入口三处一致：Web「导出 PNG」按钮、`GET /graph/image` 端点、
  MCP `export_png` 工具（写 exports 目录，不触图库）。
- 成功如何被观察：① 渲染产物为合法 PNG（magic bytes）且非空；② 空图导出占位
  图不崩；③ 中文标签正常回退不崩；④ 层次布局确定性可测；⑤ 全部门禁 + QA 封存。

## 范围

- In scope：
  - 依赖：`pillow>=10,<12` 加入运行时依赖（uv add）。
  - `packages/infrastructure/.../png_export.py`（新）：`layout_tree(concepts, edges)`
    纯函数（BFS 层次布局：根=无入边者，同层横排，孤立节点归底部层）+
    `render_graph_png(graph, out_path)`（PIL：白底、tone 三色圆角节点、边直线、
    中文字体回退 msyh → simhei → simsun → PIL default；原子写）。
  - `apps/api/main.py`：`GET /api/workspaces/{id}/graph/image` → 渲染到
    `layout.exports_dir/"mindmap.png"`（覆盖式）+ FileResponse(image/png)。
  - `apps/api/mcp_server.py`：`export_png(workspace_id)` 工具（渲染到 exports，
    返回 `{ok, path}`；无图库写路径）；工具集 6→7。
  - `apps/web`：工具栏「导出 PNG」按钮 + `getGraphImageDownloadUrl?()`（打开下载）。
  - 测试：`tests/integration/test_png_export.py`（渲染/布局/端点）、
    `test_mcp_bridge.py` 工具集 7 + export_png、`App.export.test.tsx`。
- Out of scope：忠实复刻画布自由拖拽布局（layout_items 坐标映射，后续增强）；
  SVG/PDF 格式；主题/样式定制；mind-map-mcp 的 markdown 渲染语法（我们不引入
  其无 LICENSE 的代码，仅借鉴"服务端渲染 PNG"思路）。
- 受影响模块/接口/数据：新增渲染模块 + 1 端点 + 1 MCP 工具 + Web 按钮；
  无契约/迁移/图库变化；`exports/` 目录新增 PNG 文件。
- 依赖和假设：Pillow 加入运行时依赖后冻结产物体积略增（已在 build 组验证过
  PyInstaller 可打包）；Windows 系统字体存在（缺失时回退 PIL 默认字体）。

## 风险影响

- 数据/schema/migration：无（只读图 → 写 exports 文件）。
- 安全/隐私：渲染输入为本地图数据 + 标签文本（PIL 绘制，无 HTML/JS 注入面）；
  MCP 工具只写 exports 目录，不触图库。
- 并发/幂等/恢复：导出文件覆盖式（同名单文件），并发导出后者覆盖前者，可接受。
- 性能/容量/成本：单图毫秒-秒级；无网络。
- 可观测性：错误码 `export_failed`（含 rule）；MCP 返回结构化错误。
- 用户文档：USER_MANUAL「导出 PNG」说明。

## 验收标准

- [ ] AC-1：2 节点图导出合法非空 PNG（magic bytes + 尺寸>0）。
- [ ] AC-2：空图导出占位 PNG 不崩。
- [ ] AC-3：中文标签渲染不因字体缺失崩溃（回退链）。
- [ ] AC-4：`layout_tree` 确定性（同输入同输出）且同层不重叠。
- [ ] AC-5：`GET /graph/image` 返回 200 + image/png；MCP `export_png` 返回
  path 且图库 revision 不变；Web 按钮触发下载 URL。
- [ ] 回滚：回退本切片提交 + `uv remove pillow` 即回到无导出形态。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-PNG-001 | integration | 渲染小图 | PNG magic + 非空 | `test_png_export.py` |
| TC-PNG-002 | integration | 空图/中文字体 | 占位图不崩 | 同上 |
| TC-PNG-003 | unit | layout_tree 确定性 | 同输入同输出、无重叠 | 同上 |
| TC-PNG-004 | integration | API 端点 | 200 + image/png | 同上 |
| TC-PNG-005 | integration | MCP export_png | ok+path、图库不变、工具集 7 | `test_mcp_bridge.py` |
| TC-PNG-006 | web | 导出按钮 | 触发下载 URL | `App.export.test.tsx` |
| TC-PNG-007 | 全部门禁 | 回归 | pytest + Web + 构建绿 | 门禁输出 |

## 交付物与关闭

- Commit/PR：红灯测试 → 实现 → 文档 → 证据封存。
- Contract/ADR/migration/prompt：无契约变化；运行时依赖 +pillow。
- Test Run：`TR-20260816-003`。
- Release：桌面产物重建 + 冻结 export_png 冒烟。
- 未完成项的新 ID：layout_items 忠实布局映射；SVG/PDF 格式；主题定制。
