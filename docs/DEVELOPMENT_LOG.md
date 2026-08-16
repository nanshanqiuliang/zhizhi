# 开发日志

> 用途：按时间记录已发生的技术变化、验证和遗留风险。计划项请写入 `ENGINEERING_PLAN.md`。

## 2026-08-16 — 内置 MCP server（WORK-2026-048，第 11 步切片 1）

- 关联 ID：WORK-2026-048、第 11 步、WORK-2026-043/046；QA `TR-20260815-010`。
- 实际变化：
  ① 新增 `apps/api/mcp_server.py`：FastMCP（官方 SDK，`mcp<2`，MIT；2.x 重构无 FastMCP
     故锁 1.x）stdio server，暴露**恰好四个工具** `list_workspaces` / `read_workspace` /
     `preview_draft` / `validate_patch`——**本切片零写工具**（harness 硬约束：外部 AI 只能
     读与提议，确认与写库仅在应用内；后续加写工具须重过 harness 评审 + 应用内确认机制）。
  ② `preview_draft` 复用 `/ai-draft` 语义：单资源/全库、PDF 自动解析、40 块上限、
     fail-soft、`preview_graph_patch` 防御性校验；返回 `requires_confirmation=true /
     confirmed=false` 不写库；无 key 结构化 `ai_not_available`。`validate_patch` 只做
     dry-run 预检。错误统一 `{ok:false, code, rule, ...}`（镜像端点稳定码）。
  ③ `apps/desktop/launcher.py` 增 `--mcp-stdio`（不重定向 stdout、不占单实例锁）；
     `build.spec` 补 mcp hiddenimports（冻结 exe 11.5MB，`--mcp-stdio` 实测通过）；
     源码模式 `python -m apps.api.mcp_server` 自举 `packages/*/src` sys.path（与 pytest
     pythonpath 对齐）。
- 影响模块/接口/schema/migration/prompt：新增模块 + 依赖（`mcp<2`）+ launcher 模式；
  无 canonical 契约/迁移/既有端点变化。
- 兼容性：`--mcp-stdio` 不启用不影响应用；只读并发安全（可与 sidecar 同数据根并行）。
- 验证与证据：红灯真值（worktree 改名模块 → collection error；还原 7/7 passed）；实现
  `0f5b1c2`（feat）+ `944a996`（ruff/mypy 清理，含 ruff 排除 `evidence/` 封存产物）；
  pytest 476/476 + 5 skipped；Web 64/64；ruff/mypy（41 files）/validator/pnpm 全绿；
  QA `TR-20260815-010` PASS（0 P0/P1/P2；4 P3：actor 错误码命名差异、mcp SDK 上游
  lifespan 警告、真实 LLM 未启用、sidecar 日志为空）；冻结 exe MCP stdio + 并发探针
  15/15。
- 性能/安全/运维影响：MCP 只读/提议、无写路径 → 无数据风险；stdio 仅本机进程管道；
  依赖面 +3MB（exe 8.6→11.5MB）。
- 回滚：回退实现提交即移除 MCP 能力与依赖。
- 遗留风险与下一步：写工具 + 应用内确认机制（切片 2，须 harness 评审）；受控 Web 搜索
  （需定 provider）；`generate_mindmap` PNG 导出；PPTX/DOCX/OCR；大图性能与安全加固。

## 2026-08-16 — 完整编辑工具箱 + 拖拽跳变修复（WORK-2026-047）

- 关联 ID：WORK-2026-047、WORK-2026-040/045、REQ-2026-001、NFR-2026-001；QA `TR-20260815-009`。
- 实际变化：
  ① **拖拽跳变修复**：根因是真实浏览器 pointerup 后补发 `click`，节点 `onClick=selectNode`
     调 `centerOnNode` 重定心相机；`suppressRecentOnClick` ref（`endDrag` 有位移时置位、
     `selectNode` 消费并跳过重定心）修复；普通点击仍居中。WORK-2026-040 只修了拖拽起点，
     未修拖拽后的 click。
  ② **编辑工具箱**：工具栏新增「添加概念」（自由块：视口中心放置、无父连线、无上界钳制）、
     「添加总纲」（root 块）、「连线」模式（先点起点再点终点建立连线，边类型选择 相关/先修/
     包含/举例，Esc 退出，起点 `connect-source` 高亮）；详情面板新增「关联关系」列表
     （指向/来自 + 类型标签 + 删除=断线），两端 `relations` 锁任一为真则拒绝连线/断线；
     边 `<path>` 增 `aria-label`（可测/可定位）。
  ③ **边类型往返修复**：`api.ts` `ConceptEdge.edge_type`（`EdgeKind`）经
     `snapshotToGraph`/`graphToSnapshot` 保留（此前保存时硬编码改写为 `related_to`，AI 草案
     的 `prerequisite_of` 等类型会丢失）；默认 `related_to` 向后兼容。
- 影响模块/接口/schema/migration/prompt：仅 `apps/web`（App.tsx、api.ts、styles.css、新增
  测试）。无契约/迁移；后端 diff 保存路径不变（自动生成 create/delete_edge）。
- 兼容性：旧数据无边类型按 `related_to`；快照边字段为可选增量（既有 fixture 不受影响）。
- 验证与证据：红灯真值（worktree @`8a67656`：6 failed 与预期一一对应；HEAD 11/11 passed）
  → 实现 `8a67656`/`c878c44`；Web 64/64；pytest 469/469 + 5 skipped；ruff/mypy/validator/pnpm
  全绿；后端 TestClient 闭环 6/6（prerequisite_of/part_of 经提交门保留 + 历史记录）；e2e
  18/18；QA `TR-20260815-009` PASS（0 P0/P1；1 P2 既有 BUG-2026-001；3 P3）。
- 性能/安全/运维影响：无显著变化；连线/断线入历史可撤销。
- 回滚：回退 `c878c44` 即回旧行为（含边类型改写缺陷）。
- 遗留风险与下一步：空工作区空态兜底（BUG-2026-001，待立工作项）；拖拽橡皮筋预览、边类型
  编辑（可选）；MCP 内置 server（第 11 步方向文档已入库）。

## 2026-08-16 — 画布无限延伸（WORK-2026-045）

- 关联 ID：WORK-2026-045、WORK-2026-043/046、REQ-2026-001；QA `TR-20260815-008`。
- 实际变化：① `moveDrag` 去掉 835/555 上界钳制（保留 ≥8 下限防节点不可达）；
  ② 新增 `apps/web/src/canvas.ts` 纯函数 `canvasSurfaceSize(nodes)`（内容包围盒 +
  节点 150×68 + 边距 48，下限 1000×650），应用于 `.canvas-surface` 内联宽高与
  `edge-layer` SVG viewBox/宽高，画布随内容无限生长；③ `.canvas-legend` 移出变换
  画布、锚定视口角落（巨大画布下图例不漂移）；④ `USER_MANUAL` 画布说明补充。
- 影响模块/接口/schema/migration/prompt：仅 `apps/web`（`App.tsx`、新增 `canvas.ts`、
  新增测试；`styles.css` 无需改动）。无契约/迁移。
- 兼容性：1000×650 下限保留，示例图/既有拖拽/缩放/平移行为不变（既有测试全绿）。
- 验证与证据：红灯真值（隔离 worktree @`16e72c4`：3 failed——拖拽被钳 835/835、
  surface 固定 1000×650、helper 缺失；HEAD 3 passed）→ 实现 `16e72c4`/`6277db7`/
  `ce80bd2`；Web 56/56（新增 3 用例）；pytest 469/469 + 5 skipped；ruff/mypy/validator/
  pnpm 全绿；e2e 18/18；QA `TR-20260815-008` PASS（0 P0/P1；1 P2 既有缺陷——空工作区
  崩溃，登记 BUG-2026-001；5 P3 含冻结 JS 哈希差异=桌面构建 `VITE_LOCAL_API=""` 既定
  配置，已实证字节一致）。
- 性能/安全/运维影响：超大画布（数万像素）grid/SVG 渲染线性开销，可接受；无安全变化。
- 回滚：回退 `6277db7` 即回固定画布。
- 遗留风险与下一步：空工作区空态兜底（BUG-2026-001，另立工作项）；负坐标裁剪与视口
  自动居中（可选）。

## 2026-08-16 — GraphPatch 单补丁操作数上限放宽（WORK-2026-046，maxitems 修复）

- 关联 ID：WORK-2026-046、WORK-2026-043/044、REQ-2026-001、NFR-2026-001；QA `TR-20260815-007`。
- 实际变化：① canonical `GraphPatch.operations.maxItems` 100→5000（
  `docs/contracts/knowledge-tree-graph.v1.schema.json` L514）+ 重新生成
  `_generated_graph_v1_schema.py`（`pnpm contracts:generate`，drift 门验证无漂移）；
  schema_version 仍为 1，向后兼容（≤100 操作旧补丁/历史不变）；② 新增回归测试：契约
  150 操作接受 / 上限+1 拒绝（rule=maxItems，上限未移除）/ API 全库模式 240 操作草案
  200（复现用户 `paper.pdf` 的 `maxitems` 场景）；③ `docs/ai-mindmap-agent-harness.md`
  约束 6 补充单补丁操作数上限说明；④ 桌面产物（exe/安装器/zip）重建，冻结 exe 实测
  **120 操作补丁接受并落库**（revision_no=1）、**5001 操作补丁 422
  `patch_invalid/maxItems`**（上限仍强制）。
- 影响模块/接口/schema/migration/prompt：canonical 契约 + 生成产物；无迁移；无 UI/API
  契约变化（仅大草案错误路径收窄）；生成器端 `max_chunks=40` 不变。
- 兼容性：≤100 操作的既有补丁/历史/备份不受影响。
- 验证与证据：红灯真值（隔离 worktree 还原 100 后，150 操作契约测试与 240 操作 API
  测试均以 rule=maxItems 失败，与用户 exe 报错一致）→ 实现 `87f9c1a`（红灯）/
  `f8d673c`（修复）；pytest 469/469 + 5 skipped；Web 53/53；ruff/mypy/validator/pnpm
  （含契约 drift）全绿；e2e 18/18；QA `TR-20260815-007` PASS（0 P0/P1/P2；5 个 P3：
  上限测试读 canonical 由 drift 门兜底、no_resources 断言补强已关闭、DoD 文档提交、
  exe 8.2MB 实测、5000 操作单事务基准可选）。
- 性能/安全/运维影响：单事务补丁上限 5000（数 MB JSON，本地 SQLite 顺序应用可接受）；
  安全语义不变（草案仍不可信、预览→确认→提交门、fail-closed 不变）。
- 回滚：回退 `f8d673c` 即回旧上限；或回退 `87f9c1a` 移除回归测试。
- 遗留风险与下一步：5000 操作单事务基准可选（P3-5）；画布无限延伸 WORK-2026-045；
  内置 MCP server / 受控 Web 搜索（第 11 步）已产出两份可行性文档
  （`docs/开源方案对比_内置MCP与AI脑图.md`、`docs/程序可用性实测与开源借鉴分析.md`），
  待 owner 定方向后立项。

## 2026-08-16 — 草案生成可诊断化与鲁棒性（WORK-2026-044）

- 关联 ID：WORK-2026-044、WORK-2026-009/026/043、NFR-2026-001、REQ-2026-001。
- 实际变化：① `apps/web/src/api.ts` 的 `readError` 携带 `rule`，`formatCode` 组装 `code/rule`
  （14 处抛错位全部接入），草案/回答/指令失败提示显示精确子错误码；② `build_incremental_ai_draft`
  增 `max_chunks`（单资源与全库均 40 块上限，长资料截断防爆成本/耗时）；③
  `fail_soft_extractor`/`fail_soft_relation_provider`（apps/api/ai_draft.py）仅捕获
  `DraftExtractionError`（单块坏内容跳过、其余保留；关系坏响应返回空），`LLMProviderError`
  （传输/鉴权）不吞、仍 502。
- 影响模块/接口/schema/migration/prompt：无 canonical contract/迁移；错误消息新增 rule。
- 兼容性：单资源/全库生成语义不变；`max_chunks=None` 保持旧行为（测试/确定性路径）。
- 验证与证据：红灯（rule 缺失 + TypeError max_chunks）→ 实现 `0abe9e9`；pytest 466/466 + 5
  skipped（robustness 3/3：块数截断、坏块跳过、LLMProviderError 不吞）；Web 52/52；
  ruff/mypy/validator 全绿；桌面 e2e 18/18；桌面产物重建。
- 性能/安全/运维影响：40 块上限约束成本；错误消息只含 code/rule（无文本/推理泄露）。
- 回滚：回退 `0abe9e9` 即回旧行为。
- 遗留风险与下一步：职责隔离 QA 待封存（`TR-20260815-006`）；画布无限延伸（WORK-2026-045）；
  扫描件提示/OCR、PPTX、受控 Web 搜索（第 11 步）；向量检索仍为第 9 步 owner 未决项。

## 2026-08-15 — 第 10 步后第二轮修复 QA 封存（WORK-2026-040..043，TR-20260815-005）

- 关联 ID：WORK-2026-040..043、TR-20260815-005、NFR-2026-001、REQ-2026-001。
- 实际变化：职责隔离 QA 对四项修复返回 **PASS**（0 P0/P1/P2；3 个 P3）。QA 执行全部门
  （pytest 461/461 + 5 skipped、ruff、mypy 40、validator、Web 51/51）、28 断言对抗探针与冻结
  exe 探针，并在隔离 worktree 重跑 040/041 红灯真值。
- 影响模块/接口/schema/migration/prompt：无新代码（封存证据）；`cf1bdad` 关闭 3 个 P3
  （`deepseek_relation_provider` 陈旧 helper 改 thinking=disabled、`resource_id` 类型 422、
  零新概念 422 `no_new_concepts`）。
- 兼容性：无行为变化（除错误码更清晰）。
- 验证与证据：`evidence/TR-20260815-005/`；桌面产物（exe/安装器/zip）重建含全部修复；期间
  修复了本机 node_modules 内容丢失（tsc/vite 等包内容被清空）→ 清理重装 `pnpm install
  --frozen-lockfile` 恢复。
- 性能/安全/运维影响：无新增。
- 回滚：无新增代码可回滚；回退 `cf1bdad` 即回 P3 修复前。
- 遗留风险与下一步：两轮共 10 项反馈全部修复并 QA 封存（TR-20260815-004/005）；全库模式 live
  验证需 owner key；课程重命名/删除、key 加密（第 11 步）；向量检索仍为第 9 步 owner 未决项。

## 2026-08-15 — 第 10 步后第二轮使用反馈修复（WORK-2026-040..043）

- 关联 ID：WORK-2026-040（拖拽背景稳定）、041（文件名保留）、042（AI 内容右移 + 边栏可调/
  隐藏）、043（思维导图 agent）、NFR-2026-001、REQ-2026-001。
- 实际变化：
  1. 拖拽起点不再居中视图（`selectNodeKeepCamera`），背景保持稳定（040）。
  2. 导入文件按原文件名+扩展名存盘：`_safe_storage_name`（Windows 非法字符中性化、保留
     stem/suffix、保留字防护）+ `_unique_storage_path`（冲突 `-1/-2` 后缀）（041）。
  3. 布局：草案/回答/指令预览移入右侧栏（`right-column`）；左侧栏右缘拖拽调宽（170–480px）、
     「«」隐藏、「显示边栏」恢复（042）。
  4. 思维导图 agent（043）：`build_workspace_ai_draft` 全库合并内核（按资源锚点、既有概念不
     重建、跨语料关系、40 块上限）；`/ai-draft` 不带 resource_id 即全库模式（503/422
     fail-closed，PDF 自动解析）；relation_validate thinking=disabled + max_tokens 8192（修
     「每次生成失败」：reasoning 耗尽令牌导致空内容/JSON 解析失败）；Web「从全部资料生成思维
     导图」按钮；harness 约束文档 `docs/ai-mindmap-agent-harness.md`（不可信草案/预览确认/
     证据绑定/确定性校验/fail-closed/预算）。
- 影响模块/接口/schema/migration/prompt：新增 `WorkspaceDraftGenerator` 与全库端点语义（
  resource_id 可选）；导入存储命名变化（旧数据 UUID 名不变，向前兼容）；无 canonical
  contract/迁移。
- 兼容性：单资源生成路径不变；旧资源仍按 UUID 文件名工作；`api` prop 与既有测试兼容。
- 验证与证据：pytest 461/461 + 5 skipped；Web 51/51（新增布局/背景稳定/全库内核用例）；
  ruff/mypy/validator 全绿；桌面 e2e 18/18；桌面产物重建。
- 性能/安全/运维影响：全库模式有块数上限防爆预算；relation 非思考模式更快更稳；文件名安全化
  无目录逃逸。
- 回滚：逐项回退 WORK-2026-040..043 提交。
- 遗留风险与下一步：职责隔离 QA 待封存（`TR-20260815-005`）；全库模式 live 验证需 owner key；
  向量检索仍为第 9 步 owner 未决项。

## 2026-08-15 — 第 10 步后修复 QA 封存（WORK-2026-036..039，TR-20260815-004）

- 关联 ID：WORK-2026-036..039、TR-20260815-004、NFR-2026-001、REQ-2026-001。
- 实际变化：职责隔离 QA 对四项修复返回 **PASS**（0 P0/P1；1 P2 + 3 P3）。QA 执行全部门
  （pytest 454/454 + 5 skipped、ruff、mypy 40、validator、Web 47/47）、45 个对抗 API 探针与
  冻结 exe 探针（12/12，证明四项修复均在重建产物中），并重跑 037/038/039 红灯真值。
- 影响模块/接口/schema/migration/prompt：无新代码（封存证据）；`c577928` 关闭 P2（ruff 格式）
  与 P3（`startDrag/startPan` 过滤 `event.button !== 0`）。
- 兼容性：无行为变化（除右键不再启动拖拽）。
- 验证与证据：`evidence/TR-20260815-004/`；报告
  `docs/test-reports/TR-20260815-004_desktop-fixes.md`；桌面产物（exe/安装器/zip）已重建含修复。
- 性能/安全/运维影响：无新增。
- 回滚：无新增代码可回滚；回退 `c577928` 即回 P2/P3 修复前。
- 遗留风险与下一步：P2*（图内部 workspace id 默认值）与 P3（env key 于 DELETE 后仍 configured）
  记录为 MVP 边界；课程重命名/删除、key 加密（第 11 步）；建议合并 `main` + 跑一次 CI；向量
  检索仍为第 9 步 owner 未决项。

## 2026-08-15 — 第 10 步后 5 项使用反馈修复（WORK-2026-036..039）

- 关联 ID：WORK-2026-036（拖拽）、037（打开本地目录）、038（AI 设置）、039（多课程）、
  NFR-2026-001、REQ-2026-001。
- 实际变化：
  1. **拖拽**（App.tsx）：`moveDrag` 增加 `(event.buttons & 1) === 0 → endDrag`（仅左键按住
     拖拽；missed pointerup 不再粘滞）；`startDrag/startPan` 加 `setPointerCapture`；
     canvas 加 `onPointerCancel`。
  2. **打开本地目录**（main.py + api.ts + App.tsx）：`POST /resources/open-dir` 与
     `/{rid}/reveal`（`explorer` 子进程，`_storage_key_within`/`get_resource_file_path` 守卫，
     非 Windows no-op）；Web「打开资料目录」「在文件夹中显示」。
  3. **AI 设置**：新 `apps/api/ai_config.py`（`data_root/ai.json` 存 key，env 兜底）；
     generator 构建器加 `api_key` 参数；`create_app` 用 `load_api_key(root)` 建未注入 generator
     并持可变 `ai_state`；`GET/PUT/DELETE /api/settings/ai`（保存/清除后重建/清空 generator）；
     Web「AI 设置」对话框 + 动态徽标。
  4. **多课程**：`GET/POST /api/workspaces`（枚举 UUIDv7 目录 + 根概念命名；新建 = 新 id +
     初始图）；`httpPersistApi(baseUrl, workspaceId)`；App `apiFactory`/`workspaceId`；
     侧边栏课程列表 + 新建/切换；非默认课程隐藏示例笔记。
- 影响模块/接口/schema/migration/prompt：新增 `ai_config.py` 与 4 类端点（settings/workspaces/
  resources reveal）；`create_app` 路由改读 `ai_state`；无 canonical contract/迁移。
- 兼容性：`api` prop 兼容既有测试（单工作区）；`apiFactory` 供生产；AI key 配置优先级
  `ai.json` → env；图内部 workspace/course id 与 URL 不必一致（MVP 边界）。
- 验证与证据：全仓 pytest 454/454 + 5 skipped；Web 47/47；ruff/mypy（40）/validator 全绿；
  桌面 e2e 18/18；桌面产物（exe/安装器/zip）重建。
- 性能/安全/运维影响：key 明文存本机 `ai.json`（边界，不回显）；reveal 仅限工作区内资源路径；
  多工作区每课独立数据。
- 回滚：逐项回退 WORK-2026-036..039 提交。
- 遗留风险与下一步：职责隔离 QA 待封存（`TR-20260815-004`）；课程重命名/删除、跨课程迁移、
  key 加密（第 11 步）；向量检索仍为第 9 步 owner 未决项。

## 2026-08-15 — 第 10 步切片 3b QA 封存（WORK-2026-035，TR-20260815-003）

- 关联 ID：WORK-2026-035、WORK-2026-033/034、TR-20260815-003、NFR-2026-001、REQ-2026-001。
- 实际变化：职责隔离 QA 对冻结 `c0cd6a9` 返回 **PASS**（0 P0/P1；1 P2 + 3 P3 非阻塞）。QA
  执行全部门（pytest 448/448 + 5 skipped、ruff、strict mypy 39、validator、Web 42/42）与完整
  静默安装/升级/卸载循环（HKCU 注册表 + 数据标记，零残留）。
- 影响模块/接口/schema/migration/prompt：无新代码（封存证据）；后续 `cb46909` 关闭 P2-1（`.iss`
  纳入 validator secret scan）、P2-2（签名文档修正）、P3-1（注释修正）、P3-2（桌面快捷方式
  `unchecked` 改为按需）；并瘦身冻结产物（pillow 移回 build 组 + spec `excludes` PIL/mypy/
  hypothesis/pytest/ruff，安装器 22.6→18.4 MB）。
- 兼容性：无行为变化；数据目录 `%LOCALAPPDATA%\知枝\data` 安装/升级/卸载均不触碰。
- 验证与证据：`evidence/TR-20260815-003/`；报告 `docs/test-reports/TR-20260815-003_desktop-inno-setup.md`；
  修复后 e2e 18/18、安装器静默冒烟（桌面快捷方式默认关闭）。
- 性能/安全/运维影响：安装器 18.4 MB；免管理员按用户安装；代码签名缺省不签名（SmartScreen 可能提示）。
- 回滚：无新增代码可回滚；回退 `cb46909` 即回 P2/P3 修复前。
- 遗留风险与下一步：**第 10 步完成（约 100%）**；代码签名证书（owner 可选）、自动更新、向量
  检索（第 9 步 owner 未决项）为剩余项；治理上建议把已验证链合并 `main` 并跑一次 CI。

## 2026-08-15 — 第 10 步切片 3b：Inno Setup 安装器（WORK-2026-035）

- 关联 ID：WORK-2026-035、WORK-2026-033/034、NFR-2026-001、REQ-2026-001。
- 实际变化：新增 `apps/desktop/installer.iss`（固定 AppId `{8F2B3C1E-...}`、按用户安装
  `{localappdata}\Programs\知枝\`、开始菜单 + 可选桌面快捷方式、卸载器注册、`ignoreversion
  recursesubdirs` 覆盖安装升级、`PrivilegesRequired=lowest` 免管理员）；`scripts/build_installer.py`
  （定位 `ISCC.exe` 后编译 `dist/zhizhi-<version>-setup.exe`）；`scripts/generate_icon.py` +
  `apps/desktop/icon.{ico,png}`（Pillow 树状图图标）；`build.spec` 嵌入图标；pillow 入
  `[project] dependencies`，`[[tool.mypy.overrides]] PIL ignore_missing_imports`。
- 影响模块/接口/schema/migration/prompt：新增 installer.iss/build_installer/generate_icon/icon；
  build.spec 增 icon；无 canonical contract/迁移/存储格式变化。
- 兼容性：数据目录 `%LOCALAPPDATA%\知枝\data` 在安装目录之外，安装/升级/卸载均不触碰；同 AppId
  覆盖安装幂等升级。
- 验证与证据：红灯（installer.iss 缺失 + build_installer ModuleNotFoundError）→ 实现
  `c0cd6a9`；安装器 22.58 MB 编译成功；静默安装→exe/开始菜单/卸载器/注册表正确→覆盖安装升级
  数据保留→静默卸载干净且数据保留；e2e 18/18；pytest 448/448 + 5 skipped、validator/Ruff/strict
  mypy（39）全绿。
- 性能/安全/运维影响：安装器 ~22.6 MB；无管理员权限；代码签名 env 门控缺省跳过（未签名，
  SmartScreen 可能提示）。
- 回滚：回退本工作项提交即回到「便携 zip 手动解压」；安装器不影响数据目录。
- 遗留风险与下一步：职责隔离 QA 待封存（`TR-20260815-003`）；代码签名证书（owner 未提供，可选）；
  向量检索仍为第 9 步 owner 未决项。

## 2026-08-15 — 第 10 步切片 2 QA 封存（WORK-2026-034，TR-20260815-002）

- 关联 ID：WORK-2026-034、WORK-2026-033、TR-20260815-002、NFR-2026-001、REQ-2026-001。
- 实际变化：职责隔离 QA 对冻结 `cee4fe2` 返回 **PASS**（0 P0/P1/P2；3 个 informational P3）。
  QA 执行全部门（pytest 445/445 + 5 skipped、ruff、strict mypy 39、validator、locked sync）与
  冻结 e2e 18/18；独立复验 WM_CLOSE 优雅关窗（exit 0、端口释放、锁删除、uvicorn 干净 shutdown）
  并确认 WebView2 窗口导航同源 UI。
- 影响模块/接口/schema/migration/prompt：无新代码（封存证据）；后续 `dd86465` 关闭 P3-1（文档
  依赖位置）、P3-2（AC 证据）、P3-3（`disable_windowed_traceback=True`，窗口态崩溃改写入日志而
  非弹模态框挂起）。
- 兼容性：无行为变化；`--no-window` headless 与默认原生窗口行为不变。
- 验证与证据：`evidence/TR-20260815-002/`；报告 `docs/test-reports/TR-20260815-002_desktop-pywebview-shell.md`；
  修复后重建 + e2e 18/18。
- 性能/安全/运维影响：无新增；仍仅 127.0.0.1；窗口态崩溃不再挂起（利于 CI/无人值守）。
- 回滚：无新增代码可回滚；回退 `dd86465` 即回 P3 修复前。
- 遗留风险与下一步：切片 3b（Inno Setup 安装器/升级/签名）待 owner 决策；向量检索仍为第 9 步
  owner 未决项。

## 2026-08-15 — 第 10 步切片 2：pywebview 原生窗口（WORK-2026-034）

- 关联 ID：WORK-2026-034、WORK-2026-033、NFR-2026-001、REQ-2026-001。
- 实际变化：新增 `apps/desktop/shell.py`（`open_window` 用 pywebview WebView2 原生窗口，关窗即返回）；launcher 改三模式——默认原生窗口 / `--browser`（系统浏览器）/ `--no-window`（headless，供 CI/e2e）；关窗 → `server.should_exit` 优雅退出释放端口删锁（闭合切片 1 P2-5 硬杀证据）；frozen windowed 无控制台，stdout/stderr 重定向到 `data_root/zhizhi.log`；`build.spec` 改 `console=False` + hiddenimports（clr/clr_loader/webview.platforms.winforms/edgechromium，hook-webview/hook-clr 收集 `webview/lib` 与 `Python.Runtime.dll`）；pywebview 移入 `[project] dependencies`（运行时依赖）；e2e 增窗口冒烟（18 项）。
- 影响模块/接口/schema/migration/prompt：新增 `apps/desktop/shell.py`；launcher CLI（`--no-browser`→`--no-window`，新增 `--browser`）；`build.spec` console/hiddenimports；无 canonical contract/迁移/存储格式变化。
- 兼容性：`--no-window` 保持切片 1 headless 行为（e2e/CI）；默认从系统浏览器改为原生窗口。
- 验证与证据：红灯（`apps.desktop.shell` ModuleNotFoundError）→ 实现 `cee4fe2`；冻结 e2e 18/18（含窗口冒烟）；冻结 `zhizhi.log` 显示 WebView2 窗口加载 UI（GET / + assets）；WM_CLOSE 优雅退出 exit 0 + 端口释放 + 锁删除；pytest 445/445 + 5 skipped、validator/Ruff/strict mypy（39）全绿。
- 性能/安全/运维影响：WebView2 常驻内存；仍仅 127.0.0.1；pywebview 仅加载本地同源 URL；密钥 env-only。
- 回滚：回退 `cee4fe2` 即回到「默认系统浏览器」；`--no-window` headless 路径保留。
- 遗留风险与下一步：职责隔离 QA 待封存（`TR-20260815-002`）；切片 3b（Inno Setup 安装器/升级/签名）待 owner 决策；向量检索仍为第 9 步 owner 未决项。

## 2026-08-15 — 第 10 步切片 1 QA 封存（WORK-2026-033，TR-20260815-001）

- 关联 ID：WORK-2026-033、WORK-2026-013/014/021/022/026/027、TR-20260815-001、NFR-2026-001、REQ-2026-001。
- 实际变化：职责隔离 QA 对冻结 `fa8be62` 返回 **PASS**（0 P0/P1；5 个非阻塞 P2）。QA 执行全部门（pytest 442/442 + 5 skipped、ruff、strict mypy 37 文件、validator 含 secret scan、Web 41/41、pnpm build）与冻结 e2e 15/15；另在分离 worktree 实际重跑红灯 `8edf336`（2 failed 与声明一致）并以伪 key 探针证明冻结 `config/llm` 从 `_MEIPASS` 解析（422 而非 503，零网络）。
- 影响模块/接口/schema/migration/prompt：无新代码（封存证据）；后续 `0067aae` 关闭 P2-1（单实例启动窗口竞态，健康探测重试）、P2-2（桌面构建 `VITE_LOCAL_API=""` 同源相对基址）、P2-4（无 UI 警告）；`a0e60dc` 增便携 zip（`package_desktop.py`，版本 0.1.0）。
- 兼容性：数据目录默认 `%LOCALAPPDATA%\知枝\data`；`--data-root` 可指向旧 `knowledge-tree-data`；冻结与源码运行行为一致。
- 验证与证据：`evidence/TR-20260815-001/`；报告 `docs/test-reports/TR-20260815-001_desktop-packaging-slice1.md`；修复后 e2e 15/15、Web 42/42、全仓门全绿。
- 性能/安全/运维影响：仅 127.0.0.1；单实例 fail-closed；密钥 env-only；无网络开放。
- 回滚：回退 `39117a1`..`0067aae` 即回到「python -m apps.api + 外部 Vite」；无数据格式变更。
- 遗留风险与下一步：P2-5（优雅退出证据为硬杀）记录为原型边界；切片 2（pywebview 原生窗口）与切片 3b（Inno Setup 安装器）待 owner 决策；向量检索仍为第 9 步 owner 未决项。

## 2026-08-15 — 第 10 步切片 1：桌面封装（PyInstaller 冻结 + 自托管 UI + 生命周期，WORK-2026-033）

- 关联 ID：WORK-2026-033、WORK-2026-013/014/021/022/026/027、NFR-2026-001、REQ-2026-001。
- 实际变化：`create_app(web_dist=...)` 同源自托管 Web UI（API 路由优先，`StaticFiles(html=True)` 挂在最后）；新增 `apps/api/_runtime.py`（frozen 感知 `runtime_root()`/`ensure_source_paths()`），ai_draft/answer/command/__main__ 共用同一路径引导；新增 `apps/desktop/launcher.py`（数据目录默认 `%LOCALAPPDATA%\知枝\data`、`uvicorn` 以 asyncio+h11 运行、健康轮询后打开系统浏览器、锁文件记录端口 + 健康探测做单实例、优雅退出释放端口）；`apps/desktop/build.spec` + `scripts/build_desktop.py`（PyInstaller onedir 冻结 `zhizhi.exe`，打包 `config/llm` 与 `apps/web/dist` 到 `_MEIPASS`）；`pyproject.toml` 新增 `build` 依赖组（pyinstaller）；`scripts/desktop_e2e.py` 15 项冻结冒烟。
- 影响模块/接口/schema/migration/prompt：`create_app` 增可选 `web_dist`（无 canonical contract/迁移）；三个 generator 组合根的路径引导改为共享 `_runtime`；新增 `apps/desktop/`；无存储格式/迁移变化。
- 兼容性：数据目录默认值变化（`%LOCALAPPDATA%\知枝\data`），旧 `Path.home()/knowledge-tree-data` 可由 `--data-root` 指向；冻结产物与源码运行行为一致；`python -m apps.api` 与 `python -m apps.desktop` 均可源码运行。
- 验证与证据：红灯 `8edf336`（web_dist TypeError + launcher ModuleNotFoundError）→ 核心实现 `39117a1` → 打包+单实例修复 `545b404`；e2e 15/15；全仓 pytest 436/436 + 5 skipped；validator/Ruff/strict mypy（scripts 13 + packages/api 37）/Web 41/41/pnpm build 全绿；冻结产物健康/UI/数据目录/图 PUT-GET/导入/补丁+撤销/AI 无 key 503/单实例/崩溃后陈旧锁接管/端口释放全通过。
- 性能/安全/运维影响：仅绑定 127.0.0.1；自托管免 CORS；密钥仍 env-only；单实例 fail-closed 防双写/抢端口；无网络开放。
- 回滚：回退 `39117a1`/`545b404` 即回到「python -m apps.api + 外部 Vite」；无数据格式变更。
- 遗留风险与下一步：切片 2（pywebview 原生窗口）与切片 3（Inno Setup 安装器/升级/签名）待 owner 决策后编号；向量检索仍为第 9 步 owner 未决项。

## 2026-08-15 — 第 9 步收尾 QA 封存（WORK-2026-032，TR-20260814-021）

- 关联 ID：WORK-2026-032、WORK-2026-011/019/022/026/027/029、TR-20260814-021、NFR-2026-001、REQ-2026-006。
- 实际变化：职责隔离 QA 对冻结 `954a7c8` 返回 **PASS**（0 P0/P1；4 个 informational P2 均 Accept，无需修复）。对抗审查 32 探针全通过：向后兼容（红灯代码写的 DB 在绿灯载入为 manual、digest 有效）、digest 完整性（篡改 source 稳定拒绝）、提交门/原子性、重放/撤销/重做、端点矩阵。
- 影响模块/接口/schema/migration/prompt：无代码变更（本条目为证据/文档封存）；历史记录 payload 向后兼容扩展（无迁移）。
- 兼容性：无行为变化；旧数据不受影响（digest 向后兼容）。
- 验证与证据：报告与证据存 `evidence/TR-20260814-021/`；报告 `docs/test-reports/TR-20260814-021_ai-edit-history.md`；全仓 pytest 434/434 + 5 skipped、Ruff/strict mypy/validator/Web 41/41 全绿。
- 性能/安全/运维影响：无新增。
- 回滚：无新增代码可回滚；回退 `954a7c8` 即回无 AI 来源标记。
- 遗留风险与下一步：**第 9 步收尾完成**——向量检索为唯一 owner 未决项（Embedding provider）；下一主里程碑为第 10 步（Windows 桌面封装，经 owner 指引）。

## 2026-08-15 — 第 9 步收尾：AI 修改历史（WORK-2026-032）

- 关联 ID：WORK-2026-032、WORK-2026-011/019/022/026/027/029、REQ-2026-006、NFR-2026-001。
- 实际变化：`GraphChangeRecord` 增 `source: str = "manual"`（向后兼容：`_record_payload` 仅当 source≠manual 时写入 source，旧记录 digest 不变）；`apply_graph_patch(source=...)`、`accept_ai_draft(source="ai_draft")`；新增 `POST /interpret/accept`（source="ai_command"）；`GET /history` 返回 source；Web 版本历史面板对非 manual 来源显示「AI」标记；`acceptCommand` 改走 `/interpret/accept`。
- 影响模块/接口/schema/migration/prompt：扩展 GraphChangeRecord 与历史序列化（向后兼容，无迁移）；`apply_graph_patch`/`accept_ai_draft`/`/interpret/accept`/`/history`/Web；无 canonical contract/ADR/prompt 变更。
- 兼容性：旧记录（无 source）反序列化为 manual 且 digest 校验不变；undo/redo 不改变 source。
- 验证与证据：红灯（source 缺失 + /interpret/accept 404）；实现 `954a7c8`；ai_edit_history 4/4；全仓 pytest 434/434 + 5 skipped；validator（含 secret scan）/Ruff/mypy（scripts 11 + strict packages/api 33）/Web 41/41 全绿。
- 性能/安全/运维影响：O(1) 字段；source 仅标识；密钥仅 env；本轮无网络。
- 回滚：回退 `954a7c8` 即回到无 AI 来源标记；旧数据不受影响；红灯与证据保留。
- 遗留风险与下一步：职责隔离 QA 已封存（TR-20260814-021，PASS 0 P0/P1）；**第 9 步收尾**——向量检索为唯一 owner 未决项（Embedding provider）；下一主里程碑为第 10 步（桌面封装）。

## 2026-08-15 — 第 9 步切片 3b QA 封存（WORK-2026-031，TR-20260814-020）

- 关联 ID：WORK-2026-031、WORK-2026-030、WORK-2026-009、TR-20260814-020、NFR-2026-001/006/007/008、REQ-2026-006。
- 实际变化：职责隔离 QA 对冻结 `d012660` 返回 **PASS**（0 P0/P1；4 个非阻塞 P2 覆盖缺口）；修复 `f0459f4`（测试强化：冲突 heading 文本 + 2 既有概念图 + generator fail-closed + 空图等价，无生产代码变更）后超越审查 attempt 002 返回 **PASS**（0 P0/P1）。
- 影响模块/接口/schema/migration/prompt：仅测试文件；无 canonical contract/ADR/migration/prompt 变更。
- 兼容性：无行为变化；核心性质（增量去重、跨图关系、空图退化、确定性、密钥 env-only）保持。
- 验证与证据：attempt 001/002 报告与证据存 `evidence/TR-20260814-020/`；报告 `docs/test-reports/TR-20260814-020_incremental-rebuild-llm.md`；全仓 pytest 430/430 + 5 skipped、Ruff/strict mypy/validator 全绿。
- 性能/安全/运维影响：无新增。
- 回滚：无新增代码可回滚（修复为测试强化）；回退 `f0459f4` 即回 attempt 001 状态。
- 遗留风险与下一步：**第 9 步切片 1+2+3a+3b 完成（约 80%）**；剩余第 9 步项为向量检索（Embedding provider 未决）与 AI 修改历史；下一主里程碑为第 10 步（桌面封装）。

## 2026-08-15 — 第 9 步切片 3b：增量重建 LLM 接线（WORK-2026-031）

- 关联 ID：WORK-2026-031、WORK-2026-030、WORK-2026-009、WORK-2026-026、REQ-2026-006、NFR-2026-001/006/007/008。
- 实际变化：新增 `knowledge_tree_infrastructure.ai_draft.build_incremental_ai_draft(existing_graph, text, ...)`（分块→抽取→合并→对既有 label 去重→"既有占位 + 新概念"并集→关系提供器→过滤既有↔既有关系）；`apps/api/ai_draft.build_deepseek_draft_generator` 改用 `build_incremental_ai_draft` + `build_incremental_patch`，且 `draft.concepts` 仅返回新概念。`POST /ai-draft` 自此对非空图增量：不重复创建既有概念、跨图关系端点指向既有 id。
- 影响模块/接口/schema/migration/prompt：扩展 infrastructure `ai_draft` 与 apps/api `ai_draft`；无 canonical contract/ADR/migration/prompt 变更（复用 GraphPatch v1 + `build_incremental_patch`）。
- 兼容性：空图退化为全量（等价原行为）；既有「生成草案」UI 自动增量；生成仍只读、仅确认后写库。
- 验证与证据：红灯（ImportError）；实现 `d012660`；incremental LLM 2/2 + incremental kernel 4/4；全仓 pytest 427/427 + 5 skipped；validator（含 secret scan）/Ruff/mypy（scripts 11 + strict packages/api 33）全绿；live e2e（owner key env-only）非空图 → 新概念 [导数, 连续]、极限 未重建。
- 性能/安全/运维影响：O(V+E) + 单次 LLM 抽取/关系调用受 task profile 预算约束；文本仅进 user 消息；密钥仅 env。
- 回滚：回退 `d012660` 即回到全量草案生成；红灯与证据保留。
- 遗留风险与下一步：职责隔离 QA 已封存（TR-20260814-020，attempt 001 PASS + 修复 `f0459f4` + attempt 002 PASS）；向量检索（Embedding provider 未决）、AI 修改历史为第 9 步剩余项。

## 2026-08-15 — 第 9 步切片 3a QA 封存（WORK-2026-030，TR-20260814-019）

- 关联 ID：WORK-2026-030、WORK-2026-009、TR-20260814-019、NFR-2026-001、REQ-2026-006。
- 实际变化：职责隔离 QA 对冻结 `da73951` 返回 **PASS**（0 P0/P1；2 P2 + 2 P3）；修复 `120e349` 闭合 F1（`concept_ids` 改按 `normalize_concept_label` 为键 + 变体回归）与 F3（`.get("revision_no", 0)`），F2（跨图先修环由提交门失败关闭）与 F4（空白折叠为模块级稳定键契约）记录为文档化边界；超越审查 attempt 002 返回 **PASS**（0 P0/P1）。
- 影响模块/接口/schema/migration/prompt：仅 `knowledge_tree_domain.ai_draft` 与测试；无 canonical contract/ADR/migration/prompt 变更。
- 兼容性：无行为变化；核心性质（去重、混合端点、证据/DAG 失败关闭、确定性、不突变输入）保持。
- 验证与证据：attempt 001/002 报告与证据存 `evidence/TR-20260814-019/`；报告 `docs/test-reports/TR-20260814-019_incremental-rebuild-kernel.md`；全仓 pytest 425/425 + 5 skipped、Ruff/strict mypy/validator 全绿。
- 性能/安全/运维影响：无新增；本轮纯领域、无网络。
- 回滚：无新增代码可回滚（修复为正向变更）；回退 `120e349` 即回 attempt 001 状态。
- 遗留风险与下一步：**第 9 步切片 1+2+3a 完成（约 60%）**；下一动作为切片 3b（LLM 抽取器既有-label 注入 + `POST /rebuild` + Web）。

## 2026-08-15 — 第 9 步切片 3a：增量重建纯领域内核（WORK-2026-030）

- 关联 ID：WORK-2026-030、WORK-2026-009、WORK-2026-005、REQ-2026-006、NFR-2026-001。
- 实际变化：新增 `knowledge_tree_domain.ai_draft.build_incremental_patch(existing_graph, draft, ...)`——把新资料草案并入既有图的纯领域函数：label（规范化）去重映射到既有概念 id（不重建/不重排），仅新概念 `create_concept` + `set_layout_item`，`create_edge` 端点解析既有/新 id（`expected_*_revision_no` 取对应 revision），新 AI 概念与 `prerequisite_of` 边证据必需；DAG/端点/证据失败关闭。纯函数、离线、确定性，无 LLM/网络/落库。
- 影响模块/接口/schema/migration/prompt：扩展 `knowledge_tree_domain.ai_draft`；无 canonical contract/ADR/migration/prompt 变更（复用 GraphPatch v1）。
- 兼容性：仅新增纯领域函数；不改变既有 `build_draft_patch`/`AiDraft`/提交门行为。
- 验证与证据：红灯（ImportError）；实现 `da73951`；incremental 3/3；全仓 pytest 424/424 + 5 skipped；validator（含 secret scan）/Ruff/mypy（scripts 11 + strict packages/api 33）全绿。
- 性能/安全/运维影响：O(V+E) 纯内存；零模型成本；无网络。
- 回滚：回退 `da73951` 即回到无增量内核；红灯与证据保留。
- 遗留风险与下一步：职责隔离 QA 已封存（TR-20260814-019，attempt 001 PASS + 修复 `120e349` + attempt 002 PASS）；切片 3b（LLM 抽取器既有-label 注入 + `POST /rebuild` + Web）为下一步。

## 2026-08-15 — 第 9 步切片 2 QA 封存（WORK-2026-029，TR-20260814-018）

- 关联 ID：WORK-2026-029、WORK-2026-008/005/019/022/028、TR-20260814-018、NFR-2026-001/006/007/008、REQ-2026-006。
- 实际变化：职责隔离 QA 对冻结 `b4fde38` 返回 **PASS**（0 P0/P1；3 个非阻塞 P2）；修复 `9a255d2` 闭合 P2-1（label/dimension/edge_type 改发 `*_hash`）+ P2-2（补 6 个 Python 回归）+ P2-3（补 3 个 Web 回归），`9abd339` 使 `op_unknown` 发 `op_hash` 一致性；超越审查 attempt 002 返回 **PASS**（0 P0/P1）。
- 影响模块/接口/schema/migration/prompt：仅 `command.py` 与两个测试文件；无 canonical contract/ADR/migration/prompt 变更。
- 兼容性：无行为变化；核心性质（label→id 失败关闭、精确 revision 绑定、proposal-only、提交门接受、解释只读、密钥 env-only）保持。
- 验证与证据：attempt 001/002 报告与证据存 `evidence/TR-20260814-018/`；报告 `docs/test-reports/TR-20260814-018_nl-to-graphpatch.md`；全仓 pytest 421/421 + 5 skipped、Ruff/strict mypy/validator/Web 41/41 全绿。
- 性能/安全/运维影响：无新增。
- 回滚：无新增代码可回滚（修复为正向变更）；回退 `9abd339` 即回 attempt 001 状态。
- 遗留风险与下一步：**第 9 步切片 1+2 完成（约 50%）**；下一动作为切片 3（向量检索 / 增量重建 / AI 修改历史，取最小者）。

## 2026-08-15 — 第 9 步切片 2：自然语言转 GraphPatch（WORK-2026-029）

- 关联 ID：WORK-2026-029、WORK-2026-008/005/019/022/028、REQ-2026-006、NFR-2026-001/006/007/008。
- 实际变化：新增 `knowledge_tree_infrastructure.command`（`CommandError` + `build_command_patch`：label→概念 id 严格映射，支持 `set_lock`（content/position）与 `create_edge`（四类），生成 `proposed` GraphPatch（actor=user、requires_confirmation、confirmed=false、revision 绑定））；新增 `apps/api/command.py`（`build_deepseek_command_generator()`，`command_interpret` profile，config 失败关闭）；`apps/api/main.py` `POST /api/workspaces/{id}/interpret`（注入式 generator，503，空/超长/未知 label/畸形输出 422，预览必须 `requires_confirmation`）；Web `interpretCommand` + 指令输入 + 预览/接受/拒绝面板。
- 影响模块/接口/schema/migration/prompt：新增 infrastructure `command` 与 apps/api `command` 模块；扩展 apps/api/main、apps/web；无 canonical contract/ADR/migration/prompt 变更（复用 GraphPatch v1 + `command_interpret` profile）。
- 兼容性：解释只读、不改图；未知概念/操作/维度失败关闭；接受复用既有 `POST graph/patches` 提交门（锁定/revision/确认门）；密钥仅 env。
- 验证与证据：红灯（ModuleNotFoundError + Web 指令输入缺失）；实现 `b4fde38`；command 6/6；全仓 pytest 415/415 + 5 skipped；validator（含 secret scan）/Ruff/mypy（scripts 11 + strict packages/api 33）/Web 39/39/pnpm build 全绿；live e2e（owner key env-only）「连续以极限为前提，并锁定极限的内容」→ create_edge + set_lock，接受后边 + 内容锁落库。
- 性能/安全/运维影响：单次 LLM 调用受 `command_interpret` 预算约束；命令/概念列表仅进 user 消息、不落盘/日志；错误 details 仅标识。
- 回滚：回退 `b4fde38` 即回到无自然语言图修改能力；不设 `DEEPSEEK_API_KEY` 则端点 503；红灯与证据保留。
- 遗留风险与下一步：职责隔离 QA 已封存（TR-20260814-018，attempt 001 PASS + 修复 `9a255d2`/`9abd339` + attempt 002 PASS）；向量检索、增量重建、AI 修改历史为第 9 步后续切片。

## 2026-08-15 — 第 9 步切片 1 QA 封存（WORK-2026-028，TR-20260814-017）

- 关联 ID：WORK-2026-028、WORK-2026-008/015、TR-20260814-017、NFR-2026-006/007/008、REQ-2026-006。
- 实际变化：职责隔离 QA 对冻结 `47d6c6f` 返回 **PASS**（0 P0/P1；3 个非阻塞 P2）；修复 `9e06ebf` 闭合 A2（问题上限对齐 100 + 150 字符回归）与 A3（`handleAsk` asking 守卫），A1（搜索路径 DDL 只读破例）记录为文档化既有边界；超越审查 attempt 002 返回 **PASS**（0 P0/P1）。
- 影响模块/接口/schema/migration/prompt：仅 `apps/api/main.py`、`apps/web/src/App.tsx`、`tests/integration/test_answer_api.py`（含 docstring 修正）；无 canonical contract/ADR/migration/prompt 变更。
- 兼容性：无行为变化；核心性质（回答只读、失败关闭、密钥仅 env、来源为检索命中）保持。
- 验证与证据：attempt 001/002 报告与证据存 `evidence/TR-20260814-017/`；报告 `docs/test-reports/TR-20260814-017_answer-with-sources.md`；全仓 pytest 409/409 + 5 skipped、Ruff/strict mypy/validator/Web 38/38 全绿。
- 性能/安全/运维影响：无新增。
- 回滚：无新增代码可回滚（修复为正向变更）；回退 `9e06ebf` 即回 attempt 001 状态。
- 遗留风险与下一步：**第 9 步切片 1 完成（约 25%）**；下一动作为切片 2（向量检索 / 自然语言转 GraphPatch / 增量重建，取最小者）。

## 2026-08-15 — 第 9 步切片 1：带来源问答（WORK-2026-028）

- 关联 ID：WORK-2026-028、WORK-2026-008、WORK-2026-015、REQ-2026-006、NFR-2026-006/007/008。
- 实际变化：新增 `workspace.AnswerContext` + `build_answer_context`（FTS5 正向命中 + `_reverse_match_concepts` 反向子串回退，使自然语言问题如「什么是极限」能命中「极限」概念；产出 `[n] label：snippet` 引用上下文 + 概念来源）；新增 `apps/api/answer.py` `build_deepseek_answer_generator()`（仅 `DEEPSEEK_API_KEY` env 存在时构造，`answer_with_sources` profile thinking enabled，config 失败关闭返回 None）；`apps/api/main.py` `POST /api/workspaces/{id}/answer`（注入式 `answer_generator`，无 generator 503 `ai_not_available`，空/超长 question 422，无命中 200 `{note:"no_matches"}`）；Web `askQuestion` + 提问框 + 带来源回答面板（来源可点回概念节点）。
- 影响模块/接口/schema/migration/prompt：扩展 workspace（`AnswerContext`/`build_answer_context`）、apps/api（answer 组合根 + 端点）、apps/web；无 canonical contract/ADR/migration/prompt 变更（复用 `answer_with_sources` profile）。
- 兼容性：回答只读、不改图、不写库；来源为 FTS5 检索命中（明确不冒充逐句 grounding）；密钥仅 env。
- 验证与证据：红灯（ImportError + Web 提问框缺失）；实现 `47d6c6f`；answer 6/6；全仓 pytest 408/408 + 5 skipped；validator（含 secret scan）/Ruff/mypy（scripts 11 + strict packages/api 31）/Web 38/38/pnpm build 全绿；live e2e（owner key env-only）「什么是极限」→ 回答并引用 `[1] 极限`。
- 性能/安全/运维影响：FTS5 O(命中) + 单次 LLM 调用受 `answer_with_sources` 预算约束；问题/上下文仅进 user 消息、不落盘/日志；错误 details 仅标识。
- 回滚：回退 `47d6c6f` 即回到无问答能力；不设 `DEEPSEEK_API_KEY` 则端点 503；红灯与证据保留。
- 遗留风险与下一步：职责隔离 QA 已封存（TR-20260814-017，attempt 001 PASS + 修复 `9e06ebf` + attempt 002 PASS）；向量检索、自然语言转 GraphPatch、增量重建、AI 修改历史为第 9 步后续切片。

## 2026-08-15 — 第 8 步切片 4 QA 封存（WORK-2026-027，TR-20260814-016）

- 关联 ID：WORK-2026-027、WORK-2026-026、WORK-2026-009、TR-20260814-016、NFR-2026-001、REQ-2026-006。
- 实际变化：职责隔离 QA 对冻结 `38df493` 返回 **PASS**（0 P0/P1；3 个非阻塞 P2）；修复 `3c3dfa0` 闭合 P2-1（evidence 用 `_is_uuidv7` 校验空/非 UUIDv7 → 422）与 P2-3（提升 3 个回归：门拒绝不写锚点、精确 422 码、Web 无证据不显示跳转按钮），P2-2（跨资源 id 复用）记录为文档化边界；超越审查 attempt 002 返回 **PASS**（0 P0/P1）。
- 影响模块/接口/schema/migration/prompt：仅 `apps/api/main.py` 与两个测试文件；无 canonical contract/ADR/migration/prompt 变更。
- 兼容性：无行为变化；核心性质（原子性、仅提交门写、生成只读、确定性锚点 id、evidence 指向真实锚点、无密钥）保持。
- 验证与证据：attempt 001/002 报告与证据存 `evidence/TR-20260814-016/`；报告 `docs/test-reports/TR-20260814-016_ai-draft-source-anchor.md`；全仓 pytest 402/402 + 5 skipped、Ruff/strict mypy/validator/Web 37/37 全绿。
- 性能/安全/运维影响：无新增。
- 回滚：无新增代码可回滚（修复为正向变更）；回退 `3c3dfa0` 即回 attempt 001 状态。
- 遗留风险与下一步：**第 8 步切片 1+2+3+4 完成（约 95%）**；下一动作为"接受后点击树节点跳原文 + 精确页/bbox 定位"增强，或进入第 9 步（对话/检索）。

## 2026-08-15 — 第 8 步切片 4：AI 草案来源锚点落库 + 点来源跳回原文（WORK-2026-027）

- 关联 ID：WORK-2026-027、WORK-2026-026、WORK-2026-009、WORK-2026-005/017/019/022、REQ-2026-006、NFR-2026-001、TR-20260814-015。
- 实际变化：新增 `knowledge_tree_domain.ai_draft.deterministic_uuidv7(seed)`（sha256 派生的稳定 UUIDv7）；`workspace.accept_ai_draft(layout, patch, *, trusted_actor, anchors)`——经 `GraphHistory.apply_patch` 应用确认 patch，并把 `anchors`（`{id, resource_id, page, label}`，page=0 哨兵表示资源级来源）与图/record/applied-count/FTS 索引**单事务**提交（`_atomic_commit_graph` 增 `anchors` 参数，锚点失败整体回滚）；`POST /api/workspaces/{id}/ai-draft/accept`（body `{patch, evidence}`）校验证据结构后调 `accept_ai_draft`；generator 改用确定性资源级锚点 id（`anchor_id_factory=lambda: deterministic_uuidv7(resource_id)`）并返回 `evidence`；Web `acceptDraft(patch, evidence)` + 草案面板"跳回原文"（按 evidence `resource_id` 打开查看器）。
- 影响模块/接口/schema/migration/prompt：扩展 domain（`deterministic_uuidv7`）、workspace（`accept_ai_draft` + `_atomic_commit_graph` anchors）、apps/api（accept 端点 + generator evidence）、apps/web（api.ts/App）；无 canonical contract/ADR/migration/prompt 变更（复用 anchor 表 schema v3）。
- 兼容性：草案生成仍只读；仅用户显式接受写库；接受仍走提交门（锁定/revision/确认门）；确定性锚点 id + `ON CONFLICT(id) DO UPDATE` 幂等，重复起草/接受不产生悬空/重复锚点。
- 验证与证据：红灯 `2fcad41`（ImportError + Web 按钮缺失）；实现 `38df493`；accept 5/5；全仓 pytest 400/400 + 5 skipped；validator（含 secret scan）/Ruff/mypy（scripts 11 + strict packages/api 30）/Web 36/36/pnpm build 全绿；live e2e（owner key env-only）生成→接受 applied，接受后概念 `evidence_ids` 指向真实 `anchor` 行（`source=ai_draft`、page=0）。
- 性能/安全/运维影响：单资源单锚点 O(1) 插入；锚点 payload 仅标识 + `source="ai_draft"`，无正文；错误 details 仅标识。
- 回滚：回退 `38df493` 即回合成来源引用（切片 3 状态）；红灯与证据保留。
- 遗留风险与下一步：职责隔离 QA 已封存（TR-20260814-016，attempt 001 PASS + 修复 `3c3dfa0` + attempt 002 PASS）；"接受后点击树节点 → 跳原文"（evidence→resource 反查）与精确页/bbox 级定位为后续增强；第 8 步完成后进入第 9 步（对话/检索）。

## 2026-08-15 — 第 8 步切片 3 QA 封存（WORK-2026-026，TR-20260814-015）

- 关联 ID：WORK-2026-026、WORK-2026-009、TR-20260814-015、NFR-2026-001/006/007/008、REQ-2026-006。
- 实际变化：职责隔离 QA 对冻结 `dfbcc30` 返回 **FAIL**（1 P1：`read_resource_text` PDF 漂移守卫恒真，`source_changed` 不可达 + 3 P2）；修复 `d47ce88`（取 segment parse-time `content_hash` 漂移校验 + 镜像 TC-VIEW-004 回归、`build_deepseek_draft_generator` config 加载失败关闭返回 None、过期 docstring 修正）后超越审查返回 **PASS**（0 P0/P1；P2-2 evidence 信任注记记录为无代码变更边界）。
- 影响模块/接口/schema/migration/prompt：仅 `workspace.py`/`ai_draft.py`/两个测试文件；无 canonical contract/ADR/migration/prompt 变更。
- 兼容性：无行为变化；核心闭环（生成只读、接受仅经提交门、503 失败关闭、密钥 env-only）保持不变。
- 验证与证据：attempt 001/002 报告与证据存 `evidence/TR-20260814-015/`；报告 `docs/test-reports/TR-20260814-015_ai-draft-api-web.md`；全仓 pytest 395/395 + 5 skipped、Ruff/strict mypy/validator/Web 35/35 全绿。
- 性能/安全/运维影响：无新增。
- 回滚：无新增代码可回滚（修复为正向变更）；回退 `d47ce88` 即回 attempt 001 状态。
- 遗留风险与下一步：第 8 步切片 1+2+3 完成（约 90%）；下一动作为来源锚点真实落库 + 「点来源跳回原文」，或进入第 9 步（对话/检索）；`relation_validate` 思考模式延迟 ~57s 为原型边界。

## 2026-08-15 — 第 8 步切片 3：AI 草案 API 端点与 Web 接受/拒绝（WORK-2026-026）

- 关联 ID：WORK-2026-026、WORK-2026-009、WORK-2026-005/008/014/016/017/019/022、REQ-2026-006、NFR-2026-001/006/007/008、TR-20260814-014。
- 实际变化：新增 `workspace.read_resource_text`（MD/TXT 读原文、PDF 已解析按页拼接、未知 mime `draft_unsupported_resource`）；`apps/api/main.py` 新增 `POST /api/workspaces/{id}/ai-draft`（注入式 `draft_generator`，无 generator 503 `ai_not_available`，返回前以本地 user `preview_graph_patch` 校验必须为 `requires_confirmation` 失败关闭）；新增 `apps/api/ai_draft.py` `build_deepseek_draft_generator()`（仅 `DEEPSEEK_API_KEY` env 存在时构造，读 `config/llm` + task profile 预算，`build_ai_draft` + `build_draft_patch` 后把概念/边重新作者化为 `origin=user`/`review_state=accepted`/`confidence=null`，保留 evidence + reason，patch actor=user/confirmed=false）；`apps/api/__main__.py` 启动注入 generator；Web `api.ts` `generateDraft` + `App.tsx`「生成草案」按钮、草案预览面板（概念/关系/置信度/来源）、接受（confirmed=true → 提交门）/拒绝、`ai_not_available` →「AI 未连接」。
- 影响模块/接口/schema/migration/prompt：扩展 workspace（`read_resource_text`）、apps/api（端点 + ai_draft 组合根）、apps/web（api.ts/App/styles）；无 canonical contract/ADR/migration/prompt 变更；`config/llm` 语义不变。
- 兼容性：草案绝不直写库；接受仅经既有 `POST graph/patches` 提交门（锁定/revision/确认门）；无 Key 时端点 503、UI「AI 未连接」。
- 验证与证据：红灯 `b5a38e1`（ImportError/TypeError/404 + Web 按钮缺失）；实现 `dfbcc30`；ai-draft API 6/6 + read_resource_text 3/3；全仓 pytest 394/394 + 5 skipped；validator（含 secret scan）/Ruff/mypy（scripts 11 + strict packages/api 30）/Web 35/35/pnpm build 全绿；live e2e（owner key env-only）：导入 calculus.md → 抽取 极限/连续/导数 + 3 prerequisite_of → 接受经提交门写入（user/accepted/evidence 保留）。
- 性能/安全/运维影响：生成受 task profile 金额/attempt/回退预算约束；密钥仅 env；错误 details 仅标识；live 调用仅显式构造 generator（`DEEPSEEK_API_KEY` 存在时）。
- 回滚：回退 `dfbcc30` 即回到无 AI 草案 UI；不设置 `DEEPSEEK_API_KEY` 则端点 503；红灯与证据保留。
- 遗留风险与下一步：职责隔离 QA 已封存（TR-20260814-015，attempt 001 FAIL → 修复 `d47ce88` → attempt 002 PASS）；来源锚点真实落库与「点来源跳回原文」为后续切片（草案 evidence 现为合成 UUIDv7 来源引用）；第 8 步完成后进入第 9 步（对话/检索）或来源跳转增强。

## 2026-08-15 — 第 8 步切片 2 QA 封存（WORK-2026-009，TR-20260814-014）

- 关联 ID：WORK-2026-009、WORK-2026-007/008、TR-20260814-014、NFR-2026-006/007/008、REQ-2026-006。
- 实际变化：职责隔离 QA（`ai_qa_auditor`）对冻结 `1394a1e` 返回 **PASS**（0 P0/P1；3 个 P2 记录为 prototype 边界：模型提供 label 进入异常 details、单条 user 消息的固有注入面、live 门控在 CI 静默跳过）。QA 独立复核红绿链（父提交 `1407427` 无 `ai_draft_llm` 模块/测试文件，过程披露红灯与实现合并为同一提交）、18/18 + 20/20 定向测试、Ruff/mypy/validator（含 secret scan）、全仓 386/386 + 5 skipped；对抗变异（25+ 畸形答案形状绕过、evidence/contract 绕过、噪声处理、不可变性、注入面、错误卫生、冒烟失败关闭）全部通过。
- 影响模块/接口/schema/migration/prompt：无代码变化；新增证据封存（`evidence/TR-20260814-014/`）与测试报告（`docs/test-reports/TR-20260814-014_ai-draft-llm-extraction.md`）。
- 兼容性：无行为变化；`config/llm` 与 Provider 门控不变。
- 验证与证据：QA PASS（correlated_review，机器证明非 owner 接受）；live 冒烟 `AI-DRAFT-LIVE-SMOKE-001` 报告存 `evals/calculus-v1/ai-draft-live-smoke.json`。
- 性能/安全/运维影响：无新增。
- 回滚：无代码变更可回滚；证据为新增只读记录。
- 遗留风险与下一步：第 8 步切片 1+2 完成（约 60%）；下一动作为切片 3——草案 API 端点 + Web 批量接受/拒绝，复用 `POST graph/patches` 提交门；`relation_validate` 思考模式延迟 ~57s 为原型边界。

## 2026-08-15 — 第 8 步切片 2：LLM 概念抽取与关系候选 + live 冒烟（WORK-2026-009）

- 关联 ID：WORK-2026-009、WORK-2026-007、WORK-2026-008、NFR-2026-006/007/008、REQ-2026-006。
- 实际变化：新增 `knowledge_tree_infrastructure/ai_draft_llm.py`——`LlmConceptExtractor`/`LlmRelationProvider` 实现草案流水线的 `ConceptExtractor`/`RelationCandidateProvider` Protocol，经 canonical LLM port（`concept_extract`/`relation_validate` task profile）从真实 DeepSeek 抽取概念与先修关系候选；`DraftExtractionError` 稳定错误；模型答案形状违规失败关闭（缺 concepts/relations 列表、item 非对象、缺/空 label、confidence 越界、aliases 非法、未知边类型），内容噪声（未知端点、自环、重复边）丢弃；证据绑定 chunk anchor（无 anchor 则无 evidence，提交门按契约拒绝）；新增 `deepseek_concept_extractor`/`deepseek_relation_provider` 组合辅助。新增 `scripts/ai_draft_live_smoke.py`（`RUN_LIVE_LLM_TESTS` + `DEEPSEEK_API_KEY` 双门控 live 冒烟：真实 DeepSeek 抽取 → 草案 → GraphPatch → 提交门 `requires_confirmation` + 用量/费用报告）。
- 影响模块/接口/schema/migration/prompt：扩展 infrastructure 包新增 `ai_draft_llm` 子模块，scripts 新增 live 冒烟脚本，tests 新增离线契约测试文件；无 canonical contract/ADR/migration/prompt 变更；`config/llm` 语义不变。
- 兼容性：草案仍只产出 `proposed` + `requires_confirmation` 的不可信 patch；AI 概念/`prerequisite_of` 边必须携带非空 evidence 否则提交门拒绝；live 冒烟仅显式构造 adapter 时发生，密钥仅 env 不落盘。
- 验证与证据：新契约测试 18/18（确定性 MockLlmAdapter 离线、无网络）；全仓 pytest 386/386 + 5 skipped；repository validator（含 secret scan）/Ruff/strict mypy（packages 26 + scripts 11）全绿；live 冒烟 `AI-DRAFT-LIVE-SMOKE-001`：真实 DeepSeek 抽取 极限/连续/导数/可导，4 条 `prerequisite_of` 候选，preview=requires_confirmation、patch 12 ops，427 in / 3435 out tokens、~$0.004 USD、~57.5s；报告 `evals/calculus-v1/ai-draft-live-smoke.json`（仅 label/用量/费用，无正文、无密钥）；密钥从未写入任何文件（secret scan PASS）。
- 性能/安全/运维影响：抽取/关系判定为真实 LLM 调用（费用受 task profile 金额预算约束）；`relation_validate` 思考模式先耗 reasoning_content，`max_tokens` 过小会得到 `finish_reason=length` 与空 content——live 冒烟以 4096 max_tokens 留足余量；错误 details 仅含标识不含正文/推理内容。
- 回滚：回退 `1394a1e` 即回到启发式抽取（切片 1 状态）；不触碰 `config/llm` 与 Provider 门控；红灯与证据保留。
- 遗留风险与下一步：切片 2 职责隔离 QA 已封存（TR-20260814-014，PASS）；切片 3（草案 API 端点 + Web 批量接受/拒绝）复用 `POST graph/patches` 提交门；`relation_validate` 思考模式延迟较高（~57s）记录为原型边界，后续可评估降级/异步策略。

## 2026-08-15 — 第 8 步切片 1：AI 草案流水线纯领域内核与离线编排（WORK-2026-009）

- 关联 ID：WORK-2026-009、WORK-2026-005、WORK-2026-007、WORK-2026-008、REQ-2026-006。
- 实际变化：新增 `knowledge_tree_domain/ai_draft.py` 纯领域草案内核——`chunk_text`（段落对齐分块+可控重叠）、`normalize_concept_label`/`merge_concept_candidates`（别名合并/evidence 并集/confidence 取 max）、`validate_draft`/`detect_prerequisite_cycle`（关系去重/自环/端点/DAG 环检测）、`assign_draft_layout`（prerequisite 拓扑分层自动布局）、`build_draft_patch`（AiDraft → GraphPatch v1：create_concept+create_edge+set_layout_item，origin=ai/review_state=proposed/confidence/evidence 绑定/requires_confirmation=true/confirmed=false）、`uuid7`。新增 `knowledge_tree_infrastructure/ai_draft.py` 离线编排——`ConceptExtractor`/`RelationCandidateProvider` Protocol（注入式，未来接 DeepSeek 不侵入领域）+ 确定性启发式抽取器 + `build_ai_draft`（文本→分块→抽取→合并→关系→AiDraft）。
- 影响模块/接口/schema/migration/prompt：扩展 domain/infrastructure 两包各新增 `ai_draft` 子模块；无 canonical contract/ADR/migration/prompt 变更；复用 GraphPatch v1 提交门，`config/llm` 语义不变。
- 兼容性：草案仅产出 `proposed` + `requires_confirmation` 的不可信 patch，确认/落库仍由既有提交门与用户控制；不写库、不覆盖锁定项；本轮无真实 LLM 调用、无网络。
- 验证与证据：红灯 `c9f2875`（3 collection error）→ 实现 `136f7fa`；TC-AIDRAFT-001..006 20/20；全仓 pytest 368/368 + 5 skipped；validator/Ruff/strict mypy（28 文件）/Web 32/32/pnpm build 全绿；`136f7fa` 后另有无关历史文件的 ruff format 修复 `cc23c91`。
- 性能/安全/运维影响：分块/合并/布局为 O(n)/O(V+E) 纯内存，零模型成本；错误仅含标识不含正文；不发起网络调用；密钥无涉及。
- 回滚：回退 `136f7fa` 即回到无 AI 草案能力；不触碰 `config/llm` 与真实 Provider 门控；红灯与证据保留。
- 遗留风险与下一步：真实 DeepSeek 概念抽取/关系候选为第 8 步切片 2（复用 concept_extract/relation_validate task profile）；草案 API 端点与 Web 批量接受/拒绝为切片 3；本轮确定性启发式抽取仅作骨架，不冒充真实 AI 质量。

## 2026-08-14 — owner 批准 DeepSeek deployment，第 7 步正式完成（100%）

- 关联 ID：WORK-2026-008、LLM-COMPAT-BASELINE-001、OPS-2026-003、NFR-2026-008。
- 实际变化：workspace owner 批准 DeepSeek deployment 正式启用——`config/llm/providers.yaml` 的 `deepseek.enabled` 由 `false` 改为 `true`；路由行为验证：`select_deployment` 对 concept_extract→deepseek/fast、relation_validate/answer_with_sources→deepseek/quality（批准前为 mock/deterministic）；多 LLM 基线签字检查表最后一项勾选。
- 影响模块/接口/schema/migration/prompt：仅 config 声明变化；无代码/schema/migration/prompt 变化；`model-policies.yaml` 的 `production_preference` 已指向 deepseek，无需改动。
- 兼容性：`enabled: true` 仅使 deployment 可被路由选中；无产品代码自动调用（AI 草案流水线属第 8 步）；live 测试仍受 `RUN_LIVE_LLM_TESTS` 门控；金额/attempt/回退预算约束保持生效。
- 验证与证据：repository validator PASS（config schema/语义）；全仓 pytest 348/348 + 5 skipped；`select_deployment` 真实 config 验证 deepseek 路由；secret scan 无命中。
- 性能/安全/运维影响：真实调用仍仅显式构造 adapter 时发生（评测/live smoke 门控）；密钥仅 env、不落盘；费用约束已接线。
- 回滚：将 `deepseek.enabled` 改回 `false` 即恢复 mock-only 路由；不影响已验证 adapter/契约/评测证据。
- 遗留风险与下一步：第 7 步 100% 完成；下一主项为第 8 步 WORK-2026-009（AI 自动生成知识树草案），复用 DeepSeek adapter 与 GraphPatch 提交门从失败测试启动。

## 2026-08-14 — 第七步收口：金额预算、受控回退、金标评测、RB-PROV-001 演练与隔离审查

- 关联 ID：WORK-2026-007/008、EVAL-LLM-001、RB-PROV-001、NFR-2026-006/007/008、RISK-2026-015、LLM-COMPAT-BASELINE-001。
- 实际变化：实现金额预算（`Pricing`/`CostBudget`/`estimate_cost_usd` + DeepSeek adapter 接线，config 定价与 `max_cost_usd` 上限，providers schema 增 pricing）；实现受控回退（`ModelRunner`，仅瞬态错误码回退、`max_fallbacks` 上限）；新增 `scripts/eval_llm_001.py` 金标评测（概念抽取/关系候选/命令解释/带引用回答 4 子任务）；`RB-PROV-001` 演练报告（10 定位步骤 + 错误处置表核对，状态 draft→drilled）。
- 隔离审查（review subagent，`correlated_review`）发现 2 blocking + 4 should-fix + 4 nits，已全部修复：金额预算缺 pricing 失败关闭、重试次数受 request `max_attempts` 约束、ModelRunner 受 `max_fallbacks` 约束、usage 非法值/finish_reason 缺失抛稳定码、reasoning_continuation 附加到 tool call 消息、stream URLError 映射 + 熔断、HTTP base_url 强制 HTTPS。
- 影响模块/接口/schema/migration/prompt：扩展 `llm/`（resilience/runner/vendors/protocols/http_client）、`scripts/eval_llm_001.py`、config pricing/max_cost_usd；无 migration/prompt；canonical contract 不变（LlmErrorCode 上轮已对齐 17 码）。
- 兼容性：金额预算缺定价失败关闭；回退有界；协议解析失败关闭。
- 验证与证据：全仓 pytest 348/348 + 5 skipped；validator/Ruff/strict mypy（scripts 10 + packages 26）/contracts-ts drift 全绿；live smoke 5/5（~817 token）；EVAL-LLM-001 基线（concept recall 0.133、relation accuracy 0.667、answer 通过；369 in/969 out，~$0.0012）；review 修复 `dd49599`。
- 性能/安全/运维影响：密钥仅 env、不落盘；HTTPS 强制；金额/attempt/fallback 三重预算约束；费用 < $0.002 远低于 3 元。
- 回滚：回退 `042f937`/`dd49599` 即回到 mock-only；DeepSeek deployment 保持 `enabled: false`；红灯与证据保留。
- 遗留风险与下一步：DeepSeek deployment `enabled: true` 的最终批准为唯一待 owner 决定的残余项（`correlated_review` 已通过并修复 blocking）；金标质量阈值（recall/accuracy 目标）待 owner 批准；随后进入第 8 步 AI 草案流水线。

## 2026-08-14 — 交付检查第三轮：同步第 7 步状态、环境清单、风险与 Runbook

- 关联 ID：WORK-2026-007/008、RB-PROV-001、OPS-2026-003、RISK-2026-015。
- 实际变化：README 当前状态更新到第 6 步 100%/第 7 步约 45%/MVP 约 77% 并补充 live gate 说明；CHANGELOG 补第 7 步 Added 条目并修正 Security 段（LLM live 门控）；USER_MANUAL status 更新到第 4–6 步完成/第 7 步后端进行中并补 AI 状态说明；ENVIRONMENT_INVENTORY 更新 local-dev/ci 行并新增"Provider 与密钥状态"表（deepseek `enabled:false`、secret 仅 env）；RISK_REGISTER 更新 RISK-007/009 预防证据并新增 RISK-015（LLM 费用失控，`max_cost_usd` 金额预算缺口）；test-reports 索引补 WORK-2026-007/008 待 QA 封存说明；RB-PROV-001 维护记录 + runbooks 索引补部分演练。
- 影响模块/接口/schema/migration/prompt：仅文档；无代码/schema/migration/prompt 变化。
- 兼容性：无行为变化。
- 验证与证据：见本轮收口提交；全仓 pytest 335/335 + 5 skipped、validator/Ruff/mypy 全绿（无代码改动，回归确认）。
- 性能/安全/运维影响：无；明确记录 `max_cost_usd` 金额预算为未实现缺口，不冒充已具备费用上限。
- 回滚：回退本轮文档提交即恢复上一版描述；不影响实现与证据。
- 遗留风险与下一步：`max_cost_usd` 金额预算、EVAL-LLM-001 金标评测、RB-PROV-001 完整演练与职责隔离 QA（TR 封存）仍待后续。

## 2026-08-14 — 实现 DeepSeek OpenAI Chat Completions adapter 与受控 live smoke（WORK-2026-008，第 7 步真实接入第 1 期）

- 关联 ID：WORK-2026-008、LLM-COMPAT-BASELINE-001、NFR-2026-006/007/008、WORK-2026-007、OPS-2026-003、TC-DS-001..005、TC-DS-LIVE-001..005。
- 实际变化：`knowledge_tree_infrastructure/llm/protocols/openai_chat.py` 实现 canonical↔OpenAI Chat Completions 双向映射（消息/角色/内容、tool_calls、`response_format=json_object`、显式 `thinking.type`、reasoning_content 工具轮回传、usage/finish_reason、SSE 流解析容忍空行/keep-alive/`[DONE]`）；`vendors/deepseek.py` 实现 DeepSeek vendor profile（endpoint、模型 ID 快照、HTTP 错误映射按基线 4.6）+ `DeepSeekLlmAdapter`（有界重试/退避/熔断接线，auth/balance 立即熔断不重试）；`http_client.py` 用 stdlib `urllib` 传输（POST JSON + SSE 逐行，单 read 超时；Python 3.12 socket 不接受 timeout tuple）；`tests/e2e/test_deepseek_live_smoke.py` 在 `RUN_LIVE_LLM_TESTS=1` + `DEEPSEEK_API_KEY` 双重门控下跑真实 smoke。
- 影响模块/接口/schema/migration/prompt：扩展 `knowledge_tree_infrastructure/llm/`（新增 protocols/vendors/http_client 子模块 + 两个测试文件）；无 canonical contract/migration/prompt 变更；config/llm YAML 语义不变（模型 ID 快照与真实 `/models` 探测一致）。
- 兼容性：传输不依赖厂商 SDK；thinking 模式禁发 sampling 参数；reasoning_content 只临时回传不展示/不落盘；SSE 断流返回 `provider_stream_incomplete` 不续写中间 delta。
- 验证与证据：红灯 `d6a7444`（1 collection error）；实现 `d81c574` + 修复 `a80f43d`；离线契约 21/21（TC-DS-001..005）；live smoke 5/5（真实 DeepSeek：text/JSON/thinking/tool/stream，约 817 token，费用远低于 3 元）；全仓 pytest 335/335 + 5 skipped；validator/Ruff/strict mypy（25 文件）/contracts-ts drift/pnpm build 全绿。
- 性能/安全/运维影响：live 仅 env 门控运行；密钥只经环境变量进入 composition root，绝不落盘/日志/git；错误 details 与 fixture 脱敏；退避 500→1000→2000ms；预算受 max_tokens/attempt 约束。
- 回滚：回退 `d81c574`/`a80f43d` 即回到 mock-only；DeepSeek deployment 保持 `enabled: false`；红灯与 evidence 保留。
- 遗留风险与下一步：微积分金标评测 `EVAL-LLM-001` 与质量/成本/延迟门、`RB-PROV-001` 演练、DeepSeek deployment 正式批准（`enabled: true`）未做；AI 草案流水线接入（第 8 步）未开始；职责隔离 QA 待执行。

## 2026-08-14 — 冻结 canonical LLM contract 与 mock adapter（WORK-2026-007，第 7 步离线第 1 期）

- 关联 ID：WORK-2026-007、LLM-COMPAT-BASELINE-001、REQ-2026-006、NFR-2026-001、TC-LLM-001..009、WORK-2026-006。
- 实际变化：新增 `docs/contracts/llm.v1.schema.json` 作为 canonical LLM contract 唯一手写来源（ProviderId/ProtocolId/MessageRole/ContentPartKind/FinishReason/CapabilityName/LlmErrorCode 15 码/ContentPart/CanonicalMessage/ToolDefinition/CanonicalToolCall/CanonicalUsage/Budget/TraceContext/GenerationRequest/GenerationResult/CapabilitySet）；`packages/contracts-ts/scripts/generate.mjs` 扩展为同时生成 `_generated_llm_v1_schema.py` 并在 `--check` 检测漂移（TS 侧待第 8 步 Web 消费时生成）；contracts-py 新增 `llm_v1.py`（schema-backed 校验器，冷启动无 repo I/O）；`knowledge_tree_infrastructure/llm/` 新增 canonical（frozen DTO 无厂商 SDK 类型）/errors（稳定错误码）/capabilities（能力校验 + sha256 fingerprint）/resilience（确定性退避 + AttemptBudget + CircuitBreaker）/router（deployment 解析，纯 dict 输入）/mock（确定性 MockLlmAdapter：文本/JSON/流式/tool/thinking/失败注入）。
- 影响模块/接口/schema/migration/prompt：新增 LLM canonical contract v1 与生成 artifact、infrastructure llm 子包；扩展 repository 门（`load_llm_contract_schema` + REQUIRED_PATHS）；无 migration/prompt；graph v1 contract 不变；config/llm YAML 语义不变。
- 兼容性：enum 全部从 schema 派生（无第二份手写 enum）；`["string","null"]` + format 陷阱以 `anyOf` 规避；运行时 DTO 往返经 canonical 校验。
- 验证与证据：红灯 `b5747ec`（2 collection errors）；实现 `b2e215b`；契约/安全定向 56/56（TC-LLM-001..009 mock 必须部分）；全仓 pytest 314/314；repository validator、Ruff、scripts + strict package mypy、contracts-ts drift/tsc、Web 32/32、pnpm build 全绿。
- 性能/安全/运维影响：无网络、无密钥解析、无真实费用；错误 details 与 fixture 脱敏（无正文/密钥/reasoning）；401/402 不重试、auth/balance 立即熔断、退避 500→1000→2000ms full jitter 确定性。
- 回滚：回退 `b2e215b` 即回到无 LLM port 状态；不影响 graph contract、持久化、导入、查看器与第 6 步全部已验证能力；红灯保留。
- 遗留风险与下一步：协议适配器（openai_chat_completions）与 DeepSeek vendor profile 的 HTTP 实现（实施顺序 3–6）未开始；DeepSeek live smoke 与金标（实施顺序 7）待 owner 提供受控 API Key 与预算（WORK-2026-008）；TS enum 与 Web 接入属第 8 步；mock 不是真实 DeepSeek 支持。

## 2026-08-13 — 建立流程基线

- 状态：已形成文档，未开始实现。
- 关联：WORK-2026-001。
- 变化：新增全生命周期开发/测试/发布/运维总纲和治理模板。
- 接口/数据库/Prompt 版本：尚未建立。
- 验证：仅进行 Markdown 静态复核；没有代码或运行测试。
- 遗留风险：仓库、负责人、金标数据、CI 和遥测尚未落地。

## 2026-08-13 — 建立本地仓库与最小质量门

- 关联 ID：WORK-2026-006、NFR-2026-005、NFR-2026-006、RISK-2026-004。
- 实际变化：初始化本地 Git；建立 `main` 基线和工作分支；新增 `AGENTS.md`、模块目录、uv/pnpm 锁文件、离线仓库/LLM 配置/秘密校验、最小 React 状态页和声明式 CI workflow。
- 影响模块/接口/schema/migration/prompt：只建立组合入口和包边界；复用 `config/llm/schema`，没有业务 API、数据库 migration、GraphPatch/Anchor 或 prompt 版本。
- 兼容性：Python 3.12、Node 24、pnpm 11 本地通过；TypeScript 固定到 6.0.2 以匹配 typescript-eslint；Rust/Tauri 未安装且未宣称通过。
- 验证与证据：提交 `bd66e8b`；`TR-20260813-002`；Python 10/10、Web 1/1、schema/秘密/type/lint/peer/build 与桌面/390px 浏览器检查通过。
- 性能/安全/运维影响：普通门禁禁止 live LLM；秘密扫描只报告位置和规则；无真实用户数据或网络模型费用。
- 回滚：回退 `bd66e8b` 可恢复到文档基线 `0a2a64d`；不删除用户原始文档。
- 遗留风险与下一步：远端治理、独立 QA、Rust/Tauri、许可证、SBOM/provenance、金标许可和核心 contract 尚未完成。

## 2026-08-13 — 建立多 LLM 兼容基线（DeepSeek 优先）

- 状态：兼容架构、非敏感配置和运维契约已形成；没有产品代码或真实 API 联调。
- 关联：WORK-2026-007、NFR-2026-006、ADR-0013（待正式建仓拆分）。
- 实际变化：新增根目录多 LLM 特殊基线；首家真实 LLM Provider 决策为 DeepSeek；预留 OpenAI Responses、Kimi Chat Completions 和 Anthropic Messages。
- 配置：新增 `config/llm/providers.yaml` 与 `config/llm/model-policies.yaml` v1；DeepSeek 保持 `enabled: false`，mock 为唯一已配置可用项。
- 兼容性：定义 canonical DTO、protocol adapter、vendor profile、capability snapshot、错误映射、有界重试、回退和熔断边界。
- 验证：官方文档核对和 Markdown/YAML 静态校验；没有 API Key、live smoke、金标或运行测试。
- 安全/运维：API Key 仅通过 secret reference；禁止记录 prompt/response/reasoning 正文；新增 `RB-PROV-001` 草案。
- 回滚：删除新增配置/基线并恢复原文档引用即可；尚无运行数据或 migration。
- 遗留风险：Embedding Provider、金额预算、live smoke、微积分金标、Provider adapter 和 QA 批准均未完成。

## 2026-08-13 — 建立微积分金标 fixture 并完成作者验证

- 关联 ID：WORK-2026-004、NFR-2026-002、NFR-2026-008、RISK-2026-001、RISK-2026-005。
- 实际变化：新增 MIT OCW RES.18-001 第 2 章 hash-pinned PDF、dataset card、NOTICE、作者/独立复核记录、`calculus-gold.v1` schema、30 个概念、40 条先修关系、50 个页级锚点，以及来源/许可/语义/DAG 校验 CLI。
- 影响模块/接口/schema/migration/prompt：仅新增 `evals/calculus-v1` 的 eval fixture contract；不创建产品 Anchor/GraphPatch contract、数据库 migration、API 或 prompt。
- 兼容性：新增锁定依赖 pypdf 6.15.0；数据集版本 `1.0.0-draft.1`，状态 `author_reviewed`，独立复核前禁止 `approved`。
- 验证与证据：实现提交 `e918fdf`；`TR-20260813-003` CONDITIONAL GO；金标合同/变异 14/14、仓库 Python 24/24、Web 1/1、完整本地门通过；官方 PDF 重下字节/hash 一致；7 页 144 DPI 渲染抽检清晰。
- 性能/安全/运维影响：无 LLM、数据库或用户数据；validator 拒绝路径逃逸、hash/许可漂移、加密 PDF、活动文档动作、嵌入文件、无证据边、环和伪批准状态；许可限制为 CC BY-NC-SA 4.0 非商业/署名/ShareAlike。
- 回滚：回退 `e918fdf` 可移除数据集和校验器；不得通过删除 NOTICE/来源记录绕过上游限制。
- 遗留风险与下一步：独立学科复核者和 QA 尚未指派；不得关闭 WORK-2026-004、进入产品代码或运行真实 DeepSeek。页级 fixture 也不证明 bbox/区域指标。

## 2026-08-13 — 建立微积分金标独立复核硬门

- 关联 ID：WORK-2026-004、NFR-2026-002、NFR-2026-008、RISK-2026-001、RISK-2026-005。
- 实际变化：新增 `independent-review.v1` schema、30/40/50 全量待签复核包、复核指南、领域校验器和 CLI；仓库默认门开始验证复核包，并在出现完成态时自动强制完整双签校验。
- 影响模块/接口/schema/migration/prompt：仅扩展 `evals/calculus-v1` 的 eval/review contract 和 CI 本地门；没有产品 API、数据库 migration、GraphPatch/Anchor 或 prompt 变化。
- 兼容性：复核包以排除可变审批元数据后的内容 SHA-256 绑定数据集；真实内容漂移会强制重新复核，最终签字元数据更新不会产生循环摘要。
- 验证与证据：实现提交 `232d0cd`；`TR-20260813-004` CONDITIONAL GO；43/43 Python、1/1 Web 和完整本地门通过；待签普通门通过，完成门按预期以 `calculus_review_invalid`/退出 1 阻断。
- 性能/安全/运维影响：无网络、LLM、数据库或用户数据；防止缺项、重复、摘要漂移、自签、自行裁决、未解决分歧、签字逆序和审批状态不同步。
- 回滚：回退 `232d0cd` 可移除复核门；这会重新暴露误批准风险，因此不得据此绕过 WORK-2026-004 关闭条件。
- 遗留风险与下一步：自动门不提供学科判断。项目负责人仍需指派两名不同人员完成学科复核与 QA；真实签字后创建新的增量报告，不改写已冻结报告。

## 2026-08-13 — 产品需求改为 AI Harness 自动机器复核

- 关联 ID：CHG-2026-001、ADR-0015、REQ-2026-001..005、NFR-2026-009、WORK-2026-004、WORK-2026-010。
- 实际变化：用户明确首版为个人、本地优先 AI Agent App；后续学科复核和 QA 由 harness 编排的职责隔离 AI 子 Agent执行，可调用受控本地检索/Web Search，必要时启动第三个裁决 Agent。
- 影响模块/接口/schema/migration/prompt：新增 PRD v0.2、AI review 角色卡、v2 machine-attestation 架构提案和 harness 工作项；v1 真人签字 contract 与已冻结 TR-003/004 原样保留，不用 AI 名称伪签。
- 兼容性：v2 将使用新 schema/version 和 content-addressed artifact；机器审查状态不映射为无修饰真人 `approved`，owner risk acceptance 单独建模。
- 验证与证据：本轮由 AI 学科设计子 Agent和 AI QA 设计子 Agent分别只读审查；共同要求 run/prompt/context 隔离、QA 绑定冻结学科 artifact、同源降级、证据 ledger、失败关闭和硬不变量不可豁免。实现测试尚未执行。
- 性能/安全/运维影响：未来每次自动复核至少两个模型运行，需要预算/超时/搜索轮次上限；Agent 只读最小权限，网页/PDF 指令不可信，不保存隐藏推理或全文镜像。
- 回滚：关闭 v2 review policy，保留所有 v1/v2 artifact 和失败 attempt，回到 `inconclusive`/用户手工检查；不得删除失败证据或回写伪批准。
- 遗留风险与下一步：当前继续 WORK-2026-004，先以失败测试实现 v2 contract、mock harness 和注入/越权/漂移 fixture；真实 Provider/Web 仍受 WORK-2026-007/008 gate 阻断。

## 2026-08-13 — 实现微积分 AI 机器复核 v2 离线原型

- 关联 ID：WORK-2026-004、ADR-0015、REQ-2026-002..005、NFR-2026-009、RISK-2026-010..012。
- 实际变化：以失败测试起步新增 `calculus-machine-review.v2` JSON Schema、版本化角色 prompt/context/tool policy、content-addressed subject/QA/裁决 artifact、证据 ledger、只读 ReplaySearchProvider 和稳定 CLI；默认仓库门开始复放同源 mock 双角色审查。
- 影响模块/接口/schema/migration/prompt：仅扩展 `evals/calculus-v1` prototype contract 和 `scripts` 离线工具；三角色 prompt/context 版本为 `*.v2.mock.1`；无产品 API、数据库 migration、GraphPatch/Anchor 或真实 LLM SDK。
- 兼容性：v1 真人签字 contract/历史证据原样保留；mock/replay 无论模型相关性均固定为 `inconclusive`/非产品可用，不能进入 `machine_reviewed`/`machine_verified` 或由 owner 风险接受提升；真实状态转换留给后续受控实现。
- 验证与证据：初版 TC-AIREV 原型测试 28/28、完整本地门 71/71 Python/1 Web；学科子 Agent随后提出证据自证、claim 绑定、范围和裁决 ledger 缺陷，修复后当前 75/75 Python 通过，完整增量门与正式 TR 待完成。
- 性能/安全/运维影响：无网络、模型费用、秘密、数据库或用户内容；提示注入、工具越权、输入漂移、伪引用、低置信 accept、共享 run/session/prompt/context、未裁决分歧、超时和预算失败均失败关闭或转 inconclusive。
- 回滚：回退本轮实现提交可禁用 v2 prototype；保留 v1 数据、历史 TR 和所有失败证据，不得据此启用真人 `approved` 或真实 Provider。
- 遗留风险与下一步：冻结实现提交和不可变 TR，执行隔离 AI 学科/QA 复核；随后再决定 WORK-2026-004 是否可关闭。真实联网与产品化状态机仍归 WORK-2026-007/008/010。

## 2026-08-13 — 修复 AI 学科子 Agent首轮复核争议

- 关联 ID：WORK-2026-004、RISK-2026-010..012、TC-AIREV-001..010。
- 实际变化：根据冻结提交 `73a74da` 的隔离 AI 学科 machine attestation，将 replay evidence 改为绑定冻结 PDF 页文本 hash；新增不可误读的 mock-only assurance 并强制 `inconclusive`；校验 finding/evidence 同 claim 与支持/反证立场；允许每个 claim 多证据；为裁决增加 evidence ledger/tool trace/confidence/uncertainty；修正数据集 2.1..2.7 范围与 a036 措辞。
- 影响模块/接口/schema/migration/prompt：`calculus-machine-review.v2` 原型 schema 向前演进；数据集升为 `1.0.0-draft.2` 并刷新 v1 pending review content hash；无产品 migration 或 live prompt。
- 兼容性：`1.0.0-draft.1` 的 TR-003/004 保持不可变历史证据；新的待签 review packet 绑定 draft.2，不改写旧报告。
- 验证与证据：新增失败测试先复现全部争议；第一次修复后 75/75 Python 通过。隔离学科 resumed audit 又发现 controlled-live assurance 组合和裁决 position 两个绕过；第二轮失败测试复现后已修复，当前 77/77 Python 通过，完整本地门、修复提交和复核重跑待执行。
- 性能/安全/运维影响：首次进程内建 PDF 页文本索引，随后按 PDF/hash 缓存；不联网，不保存全文到 artifact，只保存页 locator 与 hash。
- 回滚：回退本轮修复提交恢复初版原型，但会重新暴露误读/错绑风险，因此不得用于放行。
- 遗留风险与下一步：冻结修复提交，要求同一学科角色复核争议是否解决；再将冻结学科 attestation hash 交给隔离 QA。

## 2026-08-13 — 完成 AI 机器复核 v2 离线原型与隔离 QA 收口

- 关联 ID：WORK-2026-004、ADR-0015、REQ-2026-002..005、NFR-2026-009、RISK-2026-010..012、TR-20260813-005。
- 实际变化：隔离学科 attempt 003 接受 `db0831b` 后，独立 QA attempt 001 对冻结提交发现 3 P1/3 P2；以 8 个红灯回归修复 live 重标、trace 缺失/篡改、伪 owner、claim 替换、tool-policy 自证和裁决 session 复用，形成 `ae834d9`。QA attempt 002 复放全部缺陷及额外组合后 PASS，未发现新 P0/P1/P2。
- 影响模块/接口/schema/migration/prompt：subject/QA trace contract 固定为每个 120 claims 精确覆盖；validator 把 trace 绑定到 claim/query/result/tool/status，把 provenance 绑定到有效 role policy/harness，并要求三角色 session 隔离。当前 prototype 显式拒绝 `controlled_live` 和任何 owner acceptance artifact；无数据库 migration 或 live prompt。
- 兼容性：v1 `TR-20260813-003/004` 和 QA FAIL attempt 001 原样保留；attempt 002 通过 `supersedes` 追加而非改写。mock 仍为 `inconclusive`/`product_eligible=false`，不映射为人类 `approved`。
- 验证与证据：`TR-20260813-005`；targeted 39/39，完整 pytest 84/84、Web 1/1；repository validator、Ruff format/lint、mypy、pnpm frozen install/peers/check/build 全通过。学科/QA 同源独立性无外部证明，保守披露 `correlated_review`。
- 性能/安全/运维影响：无网络、模型费用、秘密、数据库、真实用户内容或常驻进程；120-claim trace 只做本地确定性 replay。任何真实 Provider、Web Search 或 owner 身份使用继续失败关闭。
- 回滚：回退 `ae834d9` 会重新暴露 QA 已证明的状态/证据绕过，不得用于放行；如需禁用，整体关闭 v2 policy/harness 并保留所有失败/通过 artifact。
- 遗留风险与下一步：WORK-2026-004 的离线 prototype 已完成；真实 Provider/live eval 归 WORK-2026-007/008，认证 owner/产品状态机/通用 harness 归 WORK-2026-010，Anchor/GraphPatch 产品 contract 归 WORK-2026-005。RISK-2026-010..012 保持 open。

## 2026-08-13 — 建立面向用户的自然语言开发路线与进度口径

- 关联 ID：PLAN-ROOT、WORK-2026-002、WORK-2026-005、WORK-2026-007、WORK-2026-010。
- 实际变化：将 Proposal/架构中的技术阶段转换为第 0–11 步用户路线，分别描述产品目标、完成标志、当前状态和可见里程碑；约定用户说“继续推进”时固定报告当前自然语言步骤、本步进度、MVP 粗略进度、本轮成果、验证和下一动作。
- 影响模块/接口/schema/migration/prompt：仅新增 `docs/USER_FACING_DEVELOPMENT_ROADMAP.md` 并链接工程计划、README 与恢复检查点；无产品代码、schema、migration 或 prompt 变化。
- 兼容性：技术事实仍以工程计划、工作项、提交和测试报告为准；百分比只依据已提交且可验证的产品能力，不把文档/测试数量误算为 App 功能。
- 验证与证据：路线与 Proposal 的 2 周尖峰、8–12 周个人 MVP、16–24 周 Beta，以及架构阶段 0–3/实现顺序逐项对齐；仓库文档链接和默认门复验。
- 性能/安全/运维影响：无运行时影响；真实 Provider/Web 与未认证 owner acceptance 保持关闭。
- 回滚：回退本条文档提交即可；不影响已冻结的 WORK-2026-004 证据。
- 遗留风险与下一步：当前为自然语言第 1 步（约 40%），MVP 粗略 10%–15%；下一次“继续推进”先完成 WORK-2026-002 的首版决策记录，再进入第 2 步 Anchor/GraphPatch contract。

## 2026-08-14 — 冻结个人笔记 App 首版产品边界

- 关联 ID：WORK-2026-002、ADR-0016、REQ-2026-006..010。
- 实际变化：把架构第 21 节十项待决问题逐项映射为首版决定或失败关闭边界；PRD 升为 v0.3，冻结 Windows 单用户、本地核心可离线、Markdown/TXT/PDF 首发、AI 持久修改默认预览确认、四维锁定、标准概念粒度和 workspace 备份/逻辑删除承诺。
- 影响模块/接口/schema/migration/prompt：只更新产品/架构/计划事实源；为后续 Anchor/GraphPatch contract 提供输入，不创建产品 schema、migration 或 prompt。
- 兼容性：不改变 WORK-2026-004 历史 evidence；PPTX/DOCX/OCR、多平台、云端多人和完整 Obsidian 导入明确后置。
- 验证与证据：TC-PLAN-001..003 的静态映射、仓库门和独立一致性复核待执行；当前自然语言第 1 步推进到约 90%。
- 性能/安全/运维影响：核心功能目标为无 Docker 本地运行；金额预算、Embedding、真实 Provider/Web、远端仓库/许可证仍未批准并保持禁用/未发布。
- 回滚：范围改变必须新建 superseding ADR/CHG，不原位把已接受默认值改成另一含义。
- 遗留风险与下一步：完成独立一致性复核并提交 WORK-2026-002；随后进入自然语言第 2 步，创建 Ready 的 WORK-2026-005 并从失败契约测试开始。

## 2026-08-14 — 修正首版边界的 owner 批准与证据状态

- 关联 ID：WORK-2026-002、ADR-0016、REQ-2026-001、REQ-2026-006..010。
- 实际变化：隔离 QA 对冻结提交 `8ff376d` 返回 FAIL（1 P1/2 P2）；产品边界本身 10/10 完整，但 PRD/ADR 把 workspace owner 的正式批准写得过早，提交中的工作项/计划/追踪状态仍写“待提交/待验证”，且 correlated-review 描述与当前失败关闭策略不一致。
- 影响模块/接口/schema/migration/prompt：将 PRD v0.3 恢复为 `in_review`、ADR-0016 恢复为 `proposed`，明确安全默认值只授权可回滚离线 prototype；同步工作项、工程计划、路线图、追踪矩阵、checkpoint 和 QA 证据。不修改运行 contract、migration 或 prompt。
- 兼容性：保留 `8ff376d` 作为不可变决策基线和首次 FAIL，不改写历史证明；后续通过 superseding 提交与 QA attempt 002 收口。
- 验证与证据：`evidence/TR-20260814-001/ai-product-qa-attempt-001.md`；修正后的 repository validator、Ruff、mypy、84/84 Python、pnpm frozen install/peers、Web 1/1 和生产构建通过，复审待执行。
- 性能/安全/运维影响：无运行时影响；真实 Provider/Web、用户数据、数据库与 owner 风险接受继续关闭。
- 回滚：不得回到伪造 owner 批准语义；若默认边界改变，应创建 superseding ADR/CHG。
- 遗留风险与下一步：要求同一 QA 角色审查本 superseding 提交的完整 SHA；通过后将 WORK-2026-005 改为 Ready 并以失败契约测试启动第 2 步。

## 2026-08-14 — 首版开发默认值 QA 通过并开放离线 GraphPatch 尖峰

- 关联 ID：WORK-2026-002、WORK-2026-005、ADR-0016、TR-20260814-001。
- 实际变化：职责隔离 QA attempt 002 对 `10f249b3021da1577aa17eb114d3b44c20a2b0a2` 给出 PASS，attempt 001 的 1 P1/2 P2 全部关闭且原始失败证据保留；WORK-2026-005 由 `proposed` 提升为 `ready`，自然语言开发进入第 2 步。
- 影响模块/接口/schema/migration/prompt：本阶段仅固化验证报告和 Ready 状态，尚未新增 Anchor/GraphPatch schema、validator、migration 或 prompt。
- 兼容性：PRD v0.3 继续 `in_review`、ADR-0016 继续 `proposed`；QA PASS 不冒充 workspace-owner 精确批准、阶段出口或发布授权。
- 验证与证据：`TR-20260814-001`；10/10 决策映射、84/84 Python、Web 1/1 和完整本地门通过；QA attempt 002 为 0 P0/P1/P2、无新发现、`correlated_review`。
- 性能/安全/运维影响：无运行时影响；无网络、Provider、用户数据、数据库或费用。
- 回滚：回退 Ready/证据收口提交即可停止尖峰；不得删除失败 attempt 或回退到伪 owner 批准表述。
- 遗留风险与下一步：切换 `feature/WORK-2026-005-anchor-graphpatch-v1`，从失败 Anchor/GraphPatch schema 契约测试开始；Gate A 和精确 owner 验收仍开放。

## 2026-08-14 — 建立 Anchor/GraphPatch v1 红灯契约基线

- 关联 ID：WORK-2026-005、TC-GRAPH-001..005、TC-ANCH-001。
- 实际变化：新增 Anchor、CourseGraph、GraphPatch 正/负契约测试，以及 preview/确认、revision、DAG、跨课程端点、四维锁和 AI evidence 安全测试；测试路径加入 contracts/domain 源目录。
- 影响模块/接口/schema/migration/prompt：只新增测试和测试导入路径；尚未创建 schema、领域实现、migration 或 prompt。
- 兼容性：既有 84 个 Python 测试未被改写；本红灯目标套件在收集阶段因两个预期公共 API 缺失而失败。
- 验证与证据：`uv run pytest tests/contract/test_graph_contracts.py tests/unit/test_graph_patch.py tests/security/test_graph_patch_security.py -q`，exit 1，3 个收集错误；`ContractValidationError`、`GraphPatchError` 尚不存在。
- 性能/安全/运维影响：无运行时、网络、数据库、Provider、用户数据或费用。
- 回滚：回退本红灯提交即可移除未实现测试；不得以删除测试替代实现关键不变量。
- 遗留风险与下一步：实现 JSON Schema 单一事实源、schema-backed Python contract API 和纯领域 preview；再补全六类 operation 与属性/容量测试。

## 2026-08-14 — 实现 Anchor/GraphPatch v1 纯领域 prototype

- 关联 ID：WORK-2026-005、ADR-0001、ADR-0004、ADR-0006、ADR-0012、TC-GRAPH-001..005、TC-ANCH-001。
- 实际变化：新增 canonical Draft 2020-12 schema、schema-backed Python contract API、schema 生成的 TypeScript enum、纯 GraphPatch preview，以及六类 operation、确认、revision、四维锁、DAG/cycle path、AI evidence/origin 防伪和输入不可变验证。
- 影响模块/接口/schema/migration/prompt：新增 `knowledge-tree-graph.v1.schema.json` 和 GraphPatch/Anchor/CourseGraph v1 prototype；新增 Hypothesis 开发依赖与 CI schema/type drift 门；无 migration、API 或 prompt。
- 兼容性：旧 placeholder TS contract 被生成入口替换；前端/存储尚未消费该 contract。新增边必须绑定 source/target revision；AI update 携带 operation evidence IDs。
- 验证与证据：红灯 `44b6233`；该冻结点实际为专项 49/49 加仓库集成 4/4，曾误写为“目标 53/53”，由后续 QA 指出并更正；Ruff、严格 mypy、schema self-check、repository validator 和 TypeScript generation drift/tsc 通过。
- 性能/安全/运维影响：无网络/文件写/数据库/Provider/用户数据；错误 details 只含 rule/ID/revision/cycle path，不含正文。首轮实现仍有冷启动 schema 文件读，已在后续 superseding 修复中移除；500 节点容量初值仍待产品基准测试。
- 回滚：回退实现提交和 schema/generator 即可禁用未接入产品的 prototype；不得回退红灯测试来规避不变量。
- 遗留风险与下一步：完整门、500 节点线性验证、冻结实现 SHA 和 QA；真正 persistence/operation log/inverse/undo/API/UI/resolver 仍后置。

## 2026-08-14 — 修复 GraphPatch 运行时 schema I/O 并重交 QA

- 关联 ID：WORK-2026-005、TR-20260814-002、TC-GRAPH-001。
- 实际变化：职责隔离 QA attempt 001 对 `a25470c` 返回 FAIL（1 P1/1 P2）：合同冷启动间接读取仓库 JSON Schema，且三文件专项测试 49 项被误记为 53 项。`1278e79` 先以拦截 `Path.read_text` 的失败测试复现；`5ff02a4` 令现有 generator 从 canonical JSON Schema 生成 Python runtime artifact，并把它纳入 drift check。
- 影响模块/接口/schema/migration/prompt：canonical JSON Schema 仍是唯一手工事实源；新增的是确定性派生产物，不新增/手写第二套 enum。Python 合同公共 API 和 GraphPatch 语义不变；无 migration/API/prompt。
- 兼容性：安装后运行不再依赖仓库 `docs/` 布局；TypeScript 与 Python 生成物必须同时与 canonical schema 一致。
- 验证与证据：失败 attempt 保存在 `evidence/TR-20260814-002/ai-graph-qa-attempt-001.md`；修复后专项 50/50、仓库集成 4/4、全仓 Python 136/136、Web 1/1，repository validator、Ruff、两层 mypy、生成漂移/tsc、locked installs/peers 和 build 全通过。
- 性能/安全/运维影响：GraphPatch/contract 冷启动不再文件 I/O；仍无网络、数据库、Provider、用户数据或常驻进程。
- 回滚：不得回退到运行时读取仓库 schema 的实现；若生成链异常，应让 drift gate 失败并停止交付，不得手改派生 schema。
- 遗留风险与下一步：职责隔离 QA attempt 002 已对 `b946855` PASS，0 P0/P1/P2、无新发现；`TR-20260814-002` 已生成并把 WORK-005 移入 verification。正式 ADR/owner 接受仍待阶段出口；operation log/inverse/undo 属于下一独立工作项。

## 2026-08-14 — 完成纯领域修改回放与 LIFO 撤销/重做 prototype

- 关联 ID：WORK-2026-011、ADR-0005、REQ-2026-008、TR-20260814-003。
- 实际变化：在 `2425718` 两组预期 ImportError 红灯后，`4fc8e60` 新增不可变 GraphHistory/GraphChangeRecord/EntityDelta、语义 hash、两条记录顺序 replay 和 LIFO undo/redo；undo 后新 apply 清空 redo。history 只接受 confirmed user GraphPatch，内部 inverse 不扩展 AI/导入器公共删除权限。
- 影响模块/接口/schema/migration/prompt：新增纯领域 `graph_history.py` 和 `validate_course_graph()` 复用入口；不改 GraphPatch canonical schema、数据库或 prompt。record 只保存变化实体 before/after canonical JSON、index、revision、hash 和 digest，不保存整图、patch reason 或 actor credential。
- 兼容性：既有 GraphPatch preview 公共语义不变；history snapshot 对调用方返回副本；revision 在 apply/undo/redo 中单调递增，语义 hash 排除 revision。
- 验证与证据：history/security/property 18/18、既有 graph 50/50、全仓 Python 154/154、Web 1/1 和完整门通过；`TR-20260814-003` 的职责隔离 QA attempt 001 PASS，0 P0/P1/P2、无新发现，并主动变异 delta/digest/hash/revision/order/duplicate/LIFO/no-I/O。
- 性能/安全/运维影响：O(V+E) 内存 prototype；无文件/网络/数据库/Provider/用户数据；错误 details 不含 label/annotation 正文。
- 回滚：回退独立 history 模块/export 即可禁用，不能回退 GraphPatch 锁/DAG/确认门；失败红灯和 QA 证据保留。
- 遗留风险与下一步：ADR-0005 owner 接受、持久 operation log/周期快照、崩溃恢复和 UI history 面板未完成。自然语言第 2 步底层 prototype 收口，下一主项进入第 3 步示例数据知识树网页。

## 2026-08-14 — 实现会话内可操作知识树 Web Demo

- 关联 ID：WORK-2026-012、REQ-2026-001、REQ-2026-006、REQ-2026-008、TR-20260814-004。
- 实际变化：在 `4caa76a` 的 5/5 红灯后，`5aab0e3` 把工程状态页替换为“知枝”三栏工作台；提供 8 节点示例树、节点/笔记编辑、添加子概念、叶节点删除、pointer 拖动、自动排布、位置锁、重置和会话内 undo/redo。
- 影响模块/接口/schema/migration/prompt：仅修改 `apps/web` 和用户/工程文档；不改 canonical graph schema、Python domain、API、migration 或 prompt。Web 内存历史不冒充 WORK-2026-011 持久产品集成。
- 兼容性：桌面保持三栏，窄屏按课程→画布→详情堆叠；画布内部可横向滚动但 document 不横溢；首次移动视图居中当前节点。
- 验证与证据：Web 6/6、全仓 Python 154/154、repository validator/Ruff/mypy/locked dependencies/peers/contracts generation/check/build 全通过；浏览器 1440×900 和 390×844 的编辑/历史/拖动/锁/layout/增删/重置、溢出和 console 验证 PASS。QA attempt 001 的移动端能力边界 P1 由 `c8c6bf9`/`fff1ce6` 关闭；attempt 002 PASS，见 `TR-20260814-004`。
- 性能/安全/运维影响：仅 8–12 节点演示规模；无网络、Provider、secret、真实用户数据、浏览器存储、文件或数据库写。界面明确“示例数据 / 仅本次会话 / AI 未连接”。
- 回滚：回退 `5aab0e3` 恢复状态页；不影响 contracts/domain 或历史证据。
- 遗留风险与下一步：刷新/关闭会丢失修改；无导入、来源跳转、AI 或安装包。QA 通过后关闭本项，并以独立 Ready 工作项从持久化/restart 红灯进入自然语言第 4 步。

## 2026-08-14 — 实现本地 SQLite 持久化工作区 prototype

- 关联 ID：WORK-2026-013、ADR-0005、REQ-2026-006、REQ-2026-008、TR-20260814-005。
- 实际变化：新增 `packages/infrastructure` 的 stdlib `sqlite3` workspace adapter：数据目录布局/校验、版本化 migration v1（`PRAGMA user_version`）、CourseGraph 原子保存/加载（复用 `validate_course_graph`）、备份（在线备份 + sha256 sidecar）、恢复（校验和 + WAL 侧车清理）、导出 JSON、purge manifest 删除、history records 落盘与 digest 防篡改 JSON 往返；CI mypy 覆盖 infrastructure。
- 影响模块/接口/schema/migration/prompt：新增 workspace adapter 与 `tests/integration|unit` 持久化测试；复用 `knowledge-tree-graph.v1` canonical schema 与 `GraphHistory` 记录语义；不修改既有 domain/contract 公共 API 语义；无 prompt 变化。
- 兼容性：Python 3.12 标准库 sqlite3 3.45.3；`_connect` 上下文管理器确保提交并关闭句柄，避免 Windows 文件锁；WAL 侧车在 restore/purge 时清理。
- 验证与证据：红灯 `1420b68`（2 个预期 collection ImportError）；实现 `8e34a40` 后目标 21/21、全仓 Python 175/175、Web 6/6、Ruff、strict mypy（contracts/domain/infrastructure）、repository validator、pnpm frozen install/peers/check/build 全通过；QA attempt 001 PASS（0 P0/P1/P2，静态推演）；本会话 live 重放八类变异全部失败关闭。
- 性能/安全/运维影响：仅测试目录写 SQLite；无网络、Provider、secret、真实用户数据或费用；错误 details 只含 rule/版本号/ID，不含正文。
- 回滚：回退 `8e34a40` 可禁用持久化 prototype；红灯测试保留，不得以删除测试替代不变量。
- 遗留风险与下一步：浏览器自动保存/API/UI 接入、FTS5 搜索、导入、加密、多进程、云端与真实 Provider 仍关闭；下一工作项从失败 persistence API 红灯进入第 4 步 UI/API 接入。

## 2026-08-14 — 实现本地持久化 API sidecar 与 Web 自动保存

- 关联 ID：WORK-2026-014、ADR-0005、ADR-0011、REQ-2026-006、REQ-2026-008、TR-20260814-006。
- 实际变化：新增 `apps/api` FastAPI composition root（loopback、CORS 精确白名单、`/api/health`、CourseGraph GET/PUT、backup，扁平化错误响应，路径遍历拒绝）；Web 端新增 `api.ts`（PersistApi、uuidv7、snapshot↔canonical 转换、http client）并接入 App（挂载加载、600ms debounce 自动保存、连接/保存状态显示、API 不可达降级）；`packages/infrastructure` 补充 `__init__.py`；CI 覆盖 apps。
- 影响模块/接口/schema/migration/prompt：新增 `apps/api` 与 Web API client；复用 graph v1 契约与 workspace adapter；无新 canonical contract/migration/prompt。
- 兼容性：新增 fastapi/uvicorn/httpx2 依赖（已锁定）；`uv run pytest` 因旧 venv 重定位改用 `uv run python -m pytest`；API 只绑定 127.0.0.1。
- 验证与证据：红灯 `4fe918b`（API 1 个 ImportError + Web 4 个新测试失败）；实现 `6c0c33c` 后 API 7/7、全仓 182/182、Web 10/10；QA attempt 001 PASS（0 P0/P1，3 P2）；P2-1 修复 `e0a4c72` 后 API 8/8、全仓 183/183，QA attempt 002 PASS；真实 uvicorn e2e smoke 全通过。
- 性能/安全/运维影响：loopback 单用户；CORS 白名单；错误 details 不含正文；无网络出站、Provider、secret、真实用户数据或费用。
- 回滚：回退 `e0a4c72` 可回到纯内存 Demo；红灯测试保留，不得以删除测试替代不变量。
- 遗留风险与下一步：Tauri 打包、认证/token（ADR-0011/SPK-009）、FTS5 搜索、导入、加密、多进程、云端与真实 Provider 仍关闭；P2-2（加载竞态）与 P2-3（关闭前 debounce 不 flush）为原型已知边界，记录于 QA 报告。

## 2026-08-14 — 实现 FTS5 基础搜索（笔记/概念全文检索）

- 关联 ID：WORK-2026-015、REQ-2026-006、REQ-2026-010、TR-20260814-007。
- 实际变化：workspace adapter 新增 FTS5 派生索引（`concept_search` 虚拟表，save 事务内原子重建）、`search_course_graph`（MATCH 主查 + 中文子串回退、query 长度/语法守卫、snippet 截断）、`SearchResult`；`apps/api` 新增 `GET /api/workspaces/{id}/search?q=...`（422 search_invalid_query/404）；Web 新增搜索框、结果下拉、点击定位、失败提示。
- 影响模块/接口/schema/migration/prompt：扩展 infrastructure/api/web；FTS5 表为派生索引，无新 canonical contract/migration/prompt。
- 兼容性：sqlite3 3.45.3 内置 FTS5；unicode61 对中文整串分词的限制由子串回退覆盖（明确记录为中文分词边界）。
- 验证与证据：Ready `e451057`；实现 `eeba073` 后搜索 10/10、全仓 193/193、Web 12/12；QA attempt 001 PASS（0 P0/P1，3 P2）；P2-2 修复 `d6c8e01`；真实 uvicorn e2e 中文搜索通过。流程偏差已披露：红灯测试与实现合并提交，红灯真实性经父提交 worktree/QA 双重复核。
- 性能/安全/运维影响：只读搜索端点；查询守卫与 snippet 截断；错误不含正文；无网络出站、Provider、secret、真实用户数据或费用。
- 回滚：回退 `d6c8e01` 可移除搜索；红灯测试保留，不得以删除测试替代不变量。
- 遗留风险与下一步：中文分词、模糊/纠错、文件内容检索（第 5 步）仍关闭；本工作项完成后第 4 步标记 100%，下一主项进入第 5 步导入资料与来源跳转。

## 2026-08-14 — 实现安全文件导入与资源注册

- 关联 ID：WORK-2026-016、REQ-2026-006、REQ-2026-010、NFR-2026-002、TR-20260814-008。
- 实际变化：schema v2 migration（resource/resource_version 表）；`import_resource`（类型/大小/路径守卫、SHA-256 去重、先落盘后提交、UUIDv7 磁盘文件名）、`list_resources`；API POST/GET resources 端点；Web 导入控件与资源列表；新增 python-multipart 依赖。
- 影响模块/接口/schema/migration/prompt：扩展 infrastructure/api/web；PRAGMA user_version 1→2（向前兼容）；无新 canonical contract/prompt。
- 兼容性：旧 v1 库自动迁移保留数据；文件只存受控数据目录；客户端文件名仅作 display_name。
- 验证与证据：Ready `293c0ef`；红灯 `50b3245`（API 1 ImportError + Web 3 失败）；实现 `10e104f` 后 import 14/14、全仓 207/207、Web 15/15；QA attempt 001 PASS（0 P0/P1，5 P2）；P2-1/P2-3 修复 `eee15d0` 后 import 15/15、全仓 208/208；真实 uvicorn e2e 通过。
- 性能/安全/运维影响：受控存储 + 路径逃逸拒绝 + 类型/大小守卫；错误不含正文；无网络出站、Provider、secret、真实用户数据或费用。
- 回滚：回退 `eee15d0` 可回到 v1 库（迁移前数据保留）；红灯测试保留，不得以删除测试替代不变量。
- 遗留风险与下一步：PDF 解析/查看器、Markdown 渲染、Anchor 生成与来源跳转、url/note 资源仍关闭，由第 5 步后续工作项承接。

## 2026-08-14 — 实现 PDF 文本解析与 Anchor 来源跳转

- 关联 ID：WORK-2026-017、REQ-2026-010、NFR-2026-002、TR-20260814-009。
- 实际变化：schema v3 migration（resource_segment + anchor 表）；`parse_pdf_resource`（pypdf 页文本、幂等、storage_key 越界守卫）、`get_page_text`（越界/未解析/漂移守卫）、`register_anchor`/`list_anchors`（UPSERT 返回实际 id、缺失资源 404）；API parse/pages/anchors 端点；Web 页文本查看器（打开/翻页/锚点跳转/漂移提示）。
- 影响模块/接口/schema/migration/prompt：扩展 infrastructure/api/web；PRAGMA user_version 2→3（向前兼容）；消费 Anchor v1 契约；无新 canonical contract/prompt。
- 兼容性：v2 库自动迁移保留数据；pypdf 6.15.0 已有；页文本 ≤ 单页提取。
- 验证与证据：Ready `2829ff2`；红灯 `53eb2cd`（API 1 ImportError + Web 3 失败）；实现 `8c3c620` 后 viewer 8/8、全仓 216/216、Web 18/18；QA attempt 001 PASS（0 P0/P1，6 P2）；P2 修复 `267fb7e` 后 viewer 10/10、全仓 218/218；真实 uvicorn e2e（金标 PDF 52 页）通过。
- 性能/安全/运维影响：只读受控资源；漂移不误跳；错误不含正文；无网络出站、Provider、secret、真实用户数据或费用。
- 回滚：回退 `267fb7e` 可回到导入-only；红灯测试保留，不得以删除测试替代不变量。
- 遗留风险与下一步：PDF.js 可视化渲染、bbox 高亮、Markdown/TXT 查看器、OCR、中文分词仍关闭，由第 5 步后续工作项承接。

## 2026-08-14 — 实现 PDF.js 可视化渲染与 bbox 区域高亮

- 关联 ID：WORK-2026-018、REQ-2026-010、NFR-2026-002、TR-20260814-010。
- 实际变化：`apps/web` 新增 PdfRenderer（pdfjs canvas 渲染、public worker 规避 Windows `@fs` 空格、bbox 高亮覆盖层、canvas 撑开容器保证窄视口对齐）；API 新增 file 端点与 anchors POST；`get_resource_file_path`（storage_key 越界守卫 + 文件缺失 404）；build 产物含 worker。
- 影响模块/接口/schema/migration/prompt：扩展 infrastructure/api/web；无 schema/migration；public/pdf.worker.min.mjs 为 Apache-2.0 运行时资源；无新 canonical contract/prompt。
- 兼容性：pdfjs-dist 6.2.108；dev/build 用同一 public worker URL；窄视口（≤800px）bbox 对齐。
- 验证与证据：Ready `54a108b`；红灯 `275d7c6`（API 2 失败 + Web 2 失败）；实现 `2601215` 后 223/223、Web 20/20；QA attempt 001 FAIL（1 P1：窄视口 bbox 错位 + 7 P2）；修复 `d56e7ef` 后 224/224、Web 20/20；真实浏览器（CDP）完整渲染/高亮/窄视口验证 aligned。
- 性能/安全/运维影响：本地 canvas 渲染无网络；file 端点受控读取 + 越界守卫；错误不含正文；无 Provider、secret、真实用户数据或费用。
- 回滚：回退 `d56e7ef` 可回到页文本查看器；不影响既有持久化/导入/跳转证据。
- 遗留风险与下一步：文本层与页面文本高亮联动、多页连续滚动渲染、Markdown/TXT 可视化渲染、OCR、中文分词仍关闭；本工作项完成后第 5 步标记 100%，下一主项进入第 6 步人工编辑安全感。

## 2026-08-14 — 新增人工验证启动入口与用户手册重写

- 关联 ID：WORK-2026-014/018、REQ-2026-010。
- 实际变化：新增 `uv run python -m apps.api --data-root <dir> [--port N] [--origin URL]` 启动入口（loopback + Vite dev origins 默认允许，供人工验证直接启动本地 API）；补 `apps/__init__.py`/`apps/api/__init__.py` 修正 mypy 包识别（此前 main.py 被同时匹配为 "main" 与 "apps.api.main"）；重写 `docs/USER_MANUAL.md` 为当前已验证能力手册（持久化/保存状态、FTS5 搜索、安全导入、PDF 页文本与渲染视图、锚点跳转与 bbox 高亮、漂移保护）+ 分步人工验收清单。
- 影响模块/接口/schema/migration/prompt：新增 `apps/api/__main__.py` 与两个 `__init__.py`；无 schema/migration/prompt 变化。
- 兼容性：`python -m apps.api` 通过 sys.path 加载 packages 源树，行为与 pytest 一致；mypy 覆盖 11 源文件。
- 验证与证据：`ff02c3e`（启动入口）+ `356a75e`（手册）；health 200、allowed origin 200、evil origin 无 ACAO 头；全仓 224/224、mypy 11 源文件、ruff 全绿、repository validator PASS。
- 性能/安全/运维影响：无部署或常驻服务变化；数据目录默认用户主目录 `knowledge-tree-data`，文档提示用户自选位置。
- 回滚：回退 `ff02c3e` 即恢复无启动入口状态（临时脚本仍可用）；`356a75e` 仅文档。
- 遗留风险与下一步：无新增风险；人工验收清单为端到端补充，自动化未覆盖部分（关闭重开、非默认端口、漂移场景）由用户在真实浏览器按手册执行。

## 2026-08-14 — 收口 PDF.js 渲染验证并标记第 5 步完成

- 关联 ID：WORK-2026-018、TR-20260814-010、REQ-2026-010。
- 实际变化：生成 TR-20260814-010 报告与 evidence 包（QA attempt 001 FAIL 记录 + P1/P2 修复说明 + 浏览器验证结果），同步全部文档（DEVELOPMENT_LOG、OPS_LOG、ENGINEERING_PLAN、TRACEABILITY_MATRIX、路线图、checkpoint、work-items README、WORK-2026-018 状态），第 5 步标记 100%、MVP 约 70%。
- 影响模块/接口/schema/migration/prompt：仅文档与证据；无代码/schema/migration/prompt 变化。
- 验证与证据：`ecd03b4`；收口后 validator、Ruff、pytest 224/224、Web 20/20、浏览器自动检测（CDP 完整渲染/高亮/窄视口 aligned）全绿。
- 回滚：回退 `ecd03b4` 仅撤销文档收口；不影响实现提交与证据。
- 遗留风险与下一步：第 5 步完成；下一主项为第 6 步人工编辑安全感（WORK-2026-019），真实 Provider/Web 与 owner 接受保持禁用。

## 2026-08-14 — 交付检查第一轮：同步本地门、错误码、风险与手册

- 关联 ID：WORK-2026-013..018。
- 实际变化：`bf35b18` 关闭 DoD 缺口——AGENTS.md/README 本地门命令更新（ruff 覆盖 packages/apps、mypy 含 packages+apps/api、pytest 用 `python -m pytest`）；README 当前状态更新为第 4–5 步能力与双终端启动；DEVELOPMENT_LOG 补启动入口/手册条目；ERROR_CODE_CATALOG 新增"已验证实现"表（14 个错误码）并勾选 DoD 清单（仅遥测 metric 留空）；RISK_REGISTER/TRACEABILITY_MATRIX 新增 RISK-2026-013/014；checkpoint 记录启动入口与人工验收交接。
- 验证与证据：`bf35b18`；validator、Ruff、pytest 224/224、Web 20/20 全绿。
- 回滚：回退 `bf35b18` 仅撤销文档修正；不影响实现与证据。
- 遗留风险与下一步：交付检查持续进行（见下一条）。

## 2026-08-14 — 交付检查第二轮：报告索引、环境清单与 CI 命令

- 关联 ID：WORK-2026-013..018、TR-20260814-005..010。
- 实际变化：`f56c99e`——test-reports/README.md 索引补 TR-004..010；ENVIRONMENT_INVENTORY.md local-dev 更新到第 4–5 步 prototype 状态；CI pytest 统一为 `uv run python -m pytest`（消除 Windows venv 重定位歧义）；OPS_LOG 登记该环境缺口；全量核验 13 个 TR 证据 checksums 逐字节匹配（无漂移）。
- 验证与证据：`f56c99e`；validator、Ruff、pytest 224/224、Web 20/20 全绿。
- 回滚：回退 `f56c99e` 仅撤销文档/CI 命令修正；不影响实现与证据。
- 遗留风险与下一步：人工验收按 `docs/USER_MANUAL.md` 清单执行；第 6 步待建。

## 2026-08-14 — 实现持久化 GraphPatch 提交门与跨会话撤销/重做

- 关联 ID：WORK-2026-019、REQ-2026-006/008、NFR-2026-001/003、ADR-0005、WORK-2026-005/011/013/014。
- 实际变化：`packages/infrastructure` 新增 `apply_graph_patch`/`undo_graph`/`redo_graph`——从持久化初始图（`meta.course_graph_initial`）+ 记录日志重建历史，经 `GraphHistory.apply_patch`（确认门 + 四维锁 + revision 冲突 + 重复 change_id）后把图/记录/初始图/栈指针（`meta.course_graph_applied`）单事务原子提交；`save_course_graph` 改为整图替换语义（覆盖 initial、清空历史）；`apps/api` 新增 `POST .../graph/patches|undo|redo` 与 `GET .../history`，服务端固定 trusted actor 为 local-user。
- 影响模块/接口/schema/migration/prompt：扩展 infrastructure/api；无新 canonical contract/ADR/migration/prompt；复用 schema v3 的 `meta`/`history_records` 表。
- 兼容性：旧库（无 initial、history 空）向后兼容，首次 patch 固化 initial；undo/redo 后 revision 保持单调（保留运行时 revision）；幂等拒绝跨会话重复 change_id。
- 验证与证据：Ready `4f5fbd3`；红灯 `db3cb26`（apply_graph_patch ImportError）；实现 `e0a5ed9` + 格式 `49e78eb`；定向 13/13、全仓 237/237、Web 20/20、validator/Ruff/mypy/锁依赖/构建全绿；职责隔离 QA 待执行。
- 性能/安全/运维影响：单事务原子防部分写入；record 仅含变化实体 before/after 与语义 hash，不落 reason/secret/来源全文；无网络/Provider/真实用户数据或费用。
- 回滚：回退 `e0a5ed9` 即回到整图 PUT-only；不改 GraphPatch preview 与纯领域 history；红灯保留。
- 遗留风险与下一步：前端仍整图 PUT 保存（后端已加整图替换语义）；跨会话撤销/锁定前端 UI 待 WORK-2026-020；职责隔离 QA 签字后生成 TR 证据。

## 2026-08-14 — 锁定维度存储保护与 WebUI 锁定/撤销接入

- 关联 ID：WORK-2026-020、REQ-2026-006/008、NFR-2026-001/003、ADR-0005、WORK-2026-005/011/019。
- 实际变化：后端 `save_course_graph` 新增锁定维度保护（`_guard_locked_dimensions`）——整图替换时拒绝锁降级（`lock_downgraded`）、锁定维度内容变化（`content_changed`）、锁定概念删除（`concept_deleted`），锁定项在存储边界不被覆盖；前端 `api.ts` 四维锁保真往返（`locks`/`revision` 读写）并新增 `applyPatch`/`undoGraph`/`redoGraph` 与 `buildSetLockPatch`；`App.tsx` 统一 `toggleLock(content|position)`——有后端走 patch 门 `set_lock`（先 `saveGraph` 同步首跑基础图）、无后端会话内；撤销/重做在会话栈空时回退后端 `undo/redo`；节点卡片显示内容锁标记。
- 影响模块/接口/schema/migration/prompt：扩展 infrastructure/api/web；无新 canonical contract/ADR/migration/prompt。
- 兼容性：锁保真后整图 PUT 不再丢失四维锁；`positionLocked` 与 `locks.position`/`layout.pinned` 一致；无后端（`<App />`）行为保持会话内不变，既有组件测试不受影响。
- 验证与证据：后端 lock-guard 4/4；Web 新增 `App.lock.test.tsx` 2/2；全仓 pytest 241/241、Web 22/22、validator/Ruff/mypy/锁依赖/构建全绿；真实浏览器 CDP 端到端（点击锁定内容→后端 locks.content=true→锁定后改 label 409 target_locked→撤销→锁解除）PASS。
- 性能/安全/运维影响：锁保护为纯内存 diff（O(概念数)），无网络/Provider/真实用户数据或费用；错误仅含 target_id/dimension/rule，不落正文。
- 回滚：回退 `618420c`/`c70d339` 即回到无锁保护/无锁定 UI 状态；不改变已验证 GraphPatch 提交门与纯领域 history。
- 遗留风险与下一步：普通编辑（增删改/拖动）仍走整图 PUT（清空历史），其跨会话撤销尚未覆盖；冲突预览 UI、崩溃恢复 UI、前端 patch 化保存待后续；职责隔离 QA 待执行。

## 2026-08-14 — WORK-2026-019/020 职责隔离 QA 收口（TR-20260814-011）

- 关联 ID：WORK-2026-019/020、TR-20260814-011、NFR-2026-001/003、ADR-0005。
- 实际变化：职责隔离 QA（graph_qa_fresh）对冻结 `c70d339` 返回 FAIL（2 P0、3 P1、3 P2）；修复 `a6a471a` 关闭 P0-2（撤销/重做补自动保存）、P1-1（content 锁护整个 concept）、P1-2（`_guard_revision_monotonic` 拒绝 revision 回退，新增 `revision_conflict` 409）、P1-3（前端编辑前查锁）、P2-1（positionLocked 兼容旧 pinned）、P2-3（body 上限 10 MiB），各配回归测试；P0-1（普通编辑跨会话撤销）与 P2-2（单用户并发 TOCTOU）记为边界（归 WORK-2026-021 / 单用户本地）。
- 影响模块/接口/schema/migration/prompt：扩展 infrastructure/api/web；新增稳定错误码 `revision_conflict`；无 schema/migration/prompt 变化。
- 兼容性：旧库向后兼容；content 锁语义与 domain 门对齐（保护整个 concept）；positionLocked 兼容 `layout_items.pinned` 旧数据。
- 验证与证据：`0ecdb1b` 封存 QA 报告 + evidence + TR 报告；全仓 pytest 243/243（lock guard 6/6）、Web 23/23、validator/Ruff/mypy/锁依赖/构建全绿；QA attempt 001 FAIL 记录 + 修复说明保留于 `evidence/TR-20260814-011/`。
- 性能/安全/运维影响：锁保护纯内存 diff；body 上限防大 payload；错误仅含标识，不落正文/secret。
- 回滚：回退 `a6a471a` 回到 QA 前实现；QA FAIL evidence 保留；不回退既已验证 GraphPatch/纯领域 history。
- 遗留风险与下一步：第 6 步核心完成标志已兑现（锁定项不被覆盖、失败/重启不重复写入）；普通编辑跨会话撤销、冲突预览 UI、崩溃恢复 UI 归 WORK-2026-021；真实 Provider/Web 与 owner 接受保持禁用。

## 2026-08-14 — 冲突预览与备份/恢复 UI（WORK-2026-021）

- 关联 ID：WORK-2026-021、REQ-2026-006/008、NFR-2026-001、WORK-2026-019/020。
- 实际变化：后端新增 `list_backups`/`restore_backup_by_name`（纯文件名 + backups_dir 内 + 存在三重守卫）与 `GET .../backups`、`POST .../restore` 端点（`backup_invalid` 422 / `backup_checksum_mismatch` 409）；前端 `api.ts` 新增 `backupGraph`/`listBackups`/`restoreBackup`/`listHistory` 且 `loadGraph`/`saveGraph` 错误透传 `code`；`App.tsx` 新增 `saveErrorMessage`（锁定/版本冲突/数据损坏 → 具体提示）、`loadGraph` 区分 `workspace_corrupt`、侧边栏"备份数据"按钮、备份列表恢复入口与版本历史面板（vN→vN+1 + change_id 前缀）。
- 影响模块/接口/schema/migration/prompt：扩展 infrastructure/api/web；新增稳定错误码 `backup_invalid`/`backup_checksum_mismatch`；无 schema/migration/prompt。
- 兼容性：恢复走 checksum 校验；备份名守卫防路径逃逸；旧库无备份时列表为空。
- 验证与证据：`fb745bd`；后端 backup_api 3/3（round trip/路径遍历/缺失）；Web 新增冲突提示 + 备份按钮 2/2；全仓 pytest 246/246、Web 25/25、validator/Ruff/mypy/锁依赖/构建全绿。
- 性能/安全/运维影响：备份为 sqlite 在线备份 + sha256 sidecar；恢复替换 db 前校验和；无网络/Provider/真实用户数据。
- 回滚：回退 `fb745bd` 即回到无备份/恢复 UI 状态；不影响已验证提交门/锁定保护。
- 遗留风险与下一步：第 6 步产物基本齐全（锁定/撤销/冲突预览/崩溃恢复），普通编辑 patch 化保存（跨会话撤销覆盖所有编辑）与版本历史 UI 面板仍待；真实 Provider/Web 与 owner 接受保持禁用。

## 2026-08-14 — 普通编辑 patch 化保存与跨会话撤销（WORK-2026-022）

- 关联 ID：WORK-2026-022、REQ-2026-006/008、NFR-2026-001/003、ADR-0005、WORK-2026-005/019、TR-20260814-013。
- 实际变化：GraphPatch v1 契约新增 `delete_concept`/`delete_edge`（含 EdgeTarget，生成 TS/Python 产物）；领域 `_apply_delete_concept`（锁定概念删除拒绝 + 存活端点 relations 锁检查 + 级联）与 `_apply_delete_edge`；后端 `save_course_graph` 改为首次整图替换、后续 diff 生成有序 patch 走 `apply_graph_patch`（`_build_diff_patch`：删边→删概念→建概念→建边→update/lock/annotation→layout），普通编辑保留历史、跨会话撤销覆盖所有编辑；删除死代码 `_guard_locked_dimensions`/`_guard_revision_monotonic` 等（锁/revision 由提交门接管）。
- 影响模块/接口/schema/migration/prompt：扩展 GraphPatch v1 canonical schema（新增两个操作）、contracts-ts/py 生成产物、infrastructure；无 migration/prompt。
- 兼容性：锁语义收敛为提交门（锁降级=用户主动解锁）；noop 保存不递增 revision；前端零改动（继续整图 PUT）。
- 验证与证据：`ab50aa2` 实现；`7106621` QA 修复；QA attempt 001 FAIL（3 P1 + 2 P2）→ 复审 PASS；全仓 pytest 256/256、Web 27/27、contracts-ts drift、validator/Ruff/mypy/构建全绿；证据 `TR-20260814-013`。
- 性能/安全/运维影响：diff 为 O(V+E) 纯内存；删除为硬删除 + 历史可恢复（tombstone 软删除未引入）；错误仅含标识，不落正文/secret。
- 回滚：回退 `ab50aa2`/`7106621` 即回到整图替换保存；不回退已验证 GraphPatch 提交门/纯领域 history。
- 遗留风险与下一步：**第 6 步完成（100%）**，"不依赖 AI 也能使用"的手工 Alpha 形成；tombstone 软删除、真实 Provider/Web、owner 接受保持禁用，第 7 步 DeepSeek 适配待 owner 提供 API Key 与预算。

## 2026-08-14 — Markdown/TXT 文本查看器（WORK-2026-023）

- 关联 ID：WORK-2026-023、REQ-2026-010、WORK-2026-016。
- 实际变化：前端 `api.ts` 新增 `getResourceText(resourceId)`（经 `GET .../resources/{id}/file` 读取原文，复用 WORK-2026-018 的 file 端点）；`App.tsx` `openViewer` 按 mime 分流——PDF 走页文本/锚点，`text/*`（Markdown/TXT）读取原文进入文本查看器；资源列表对 `text/*` 资源开放"打开"按钮；查看器控件按 mime 显示（PDF 显示翻页/文本/渲染，MD/TXT 仅显示关闭）。填补第 5 步"MD/TXT 导入后无法查看内容"的缺口。
- 影响模块/接口/schema/migration/prompt：仅扩展 apps/web；后端复用既有 file 端点，无新端点/schema/migration/prompt。
- 兼容性：PDF 查看器行为不变；`text/*` 资源无翻页/渲染/锚点，仅纯文本查看。
- 验证与证据：`78c5264`；Web 新增 `opens a markdown resource in the text viewer`（getResourceText + 文本渲染）；全仓 pytest 256/256、Web 28/28、validator/Ruff/mypy/构建全绿。
- 性能/安全/运维影响：file 端点受控读取 + storage_key 越界守卫；错误不含正文；无网络/Provider/真实用户数据。
- 回滚：回退 `78c5264` 即回到 PDF-only 查看器；不影响持久化/导入/提交门证据。
- 遗留风险与下一步：Markdown 渲染为纯文本（无富文本渲染）；文本层与页面文本高亮联动、多页连续滚动仍为后续；真实 Provider/Web 与 owner 接受保持禁用。

## 2026-08-14 — Markdown 富文本渲染（WORK-2026-024）

- 关联 ID：WORK-2026-024、REQ-2026-010、WORK-2026-023。
- 实际变化：新增 `apps/web/src/markdown.ts` 的 XSS 安全 `renderMarkdown`——先 `escapeHtml`（& < > " '）再应用标题(1–3)/加粗/斜体/行内代码/无序列表/围栏代码块，输出仅含本模块生成的标签；`App.tsx` 对 `text/markdown` 资源经 `markdown-body` 渲染视图（`dangerouslySetInnerHTML`，因先转义故安全），`text/plain` 保持 `<pre>` 纯文本；`styles.css` 新增 markdown-body 基础排版。
- 影响模块/接口/schema/migration/prompt：仅扩展 apps/web；无后端/schema/migration/prompt 变化。
- 兼容性：TXT 仍纯文本；PDF 查看器行为不变；Markdown 从纯文本升级为富文本显示。
- 验证与证据：`0310061`；`markdown.test.ts` 3/3（格式渲染 + 注入转义 + 代码块）；全仓 pytest 256/256、Web 31/31、validator/Ruff/mypy/构建全绿。
- 性能/安全/运维影响：渲染为纯函数，先转义防 XSS（无第三方渲染依赖）；无网络/Provider/真实用户数据。
- 回滚：回退 `0310061` 即回到 Markdown 纯文本查看；不影响导入/查看器/提交门证据。
- 遗留风险与下一步：Markdown 富文本仅支持最小语法子集（无表格/链接/任务列表）；文本层与页面文本高亮联动、多页连续滚动、tombstone 软删除仍为后续；真实 Provider/Web 与 owner 接受保持禁用。

## 2026-08-14 — 知识树画布平移与缩放（WORK-2026-025）

- 关联 ID：WORK-2026-025、REQ-2026-006、WORK-2026-012。
- 实际变化：`App.tsx` 画布新增平移/缩放——滚轮缩放（0.5×–2.5×，步进 0.1）、拖动空白区域平移、节点拖动按 zoom 换算屏幕增量；`canvas-surface` 用 `transform: translate(pan) scale(zoom)`，`canvas-viewport` 由 scroll 改为 `overflow: hidden`；`centerOnNode`（pan 定位）取代原 scrollLeft 的选中/搜索定位；`styles.css` 加 `transform-origin:0 0`/`touch-action:none`/grab 光标。
- 影响模块/接口/schema/migration/prompt：仅扩展 apps/web；无后端/schema/migration/prompt 变化。
- 兼容性：节点世界坐标不变（仅渲染变换）；拖动/排布/锁定/撤销行为不变；现有移动节点测试经事件冒泡仍通过。
- 验证与证据：`8563fad`；Web 新增 `zooms the canvas with the wheel`（transform scale 断言）；全仓 pytest 256/256、Web 32/32、validator/Ruff/mypy/构建全绿。
- 性能/安全/运维影响：纯 CSS transform 渲染，无重排；`touch-action:none` 抑制浏览器默认手势；无网络/Provider/真实用户数据。
- 回滚：回退 `8563fad` 即回到 scroll-only 画布；不影响持久化/提交门/查看器证据。
- 遗留风险与下一步：缩放已支持鼠标位置为中心（`62e0b72`，zoom/pan 合并为 camera 状态原子更新）；文本层与页面文本高亮联动、多页连续滚动、tombstone 软删除仍为后续；真实 Provider/Web 与 owner 接受保持禁用。

## 2026-08-12 — 建立总体架构技术基线

- 状态：已形成文档，未开始实现。
- 变化：定义模块化单体、本地 SQLite/云端 PostgreSQL、GraphPatch、Anchor、任务和可观测性方向。
- 验证：文档静态复核；没有原型或性能证据。
- 遗留风险：所有工程初值有待阶段 0 校准。

---

## 新条目模板

```markdown
## YYYY-MM-DD — <标题>

- 关联 ID：
- 实际变化：
- 影响模块/接口/schema/migration/prompt：
- 兼容性：
- 验证与证据：
- 性能/安全/运维影响：
- 回滚：
- 遗留风险与下一步：
```
