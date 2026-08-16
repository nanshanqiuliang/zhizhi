# WORK-2026-050：MCP 写工具 + 应用内确认机制（第 11 步切片 2）

```yaml
status: ready
type: feature
owner: api + infrastructure + web + QA
reviewers: [project_owner, qa]
related_ids: [WORK-2026-048, REQ-2026-001, NFR-2026-001, BUG-2026-001 无关]
target_stage: 第 11 步 Beta 加固与扩展
risk: high
created_at: 2026-08-16T00:00:00Z
updated_at: 2026-08-16T00:00:00Z
```

## 问题与结果

- 用户/工程问题：WORK-2026-048 的 MCP server 只读（4 工具、零写），外部 AI 客户端
  （Cursor/Claude Desktop 等）无法把补丁送进知枝——只能截图式看结果。harness 文档
  已预留方向：「后续切片加写工具必须重新过 harness 评审 + 应用内确认机制」。
- 期望结果：外部 AI 可经 MCP 提交 **GraphPatch 提议**（`propose_patch`）：提议经
  `preview_graph_patch` 防御性校验后落为 **pending 提议文件**（不写图库）；应用内
  UI 出现「外部提议」面板，用户**逐条人工确认**（接受走既有 `apply_graph_patch`
  提交门：锁/修订号/历史/可撤销；或拒绝）；外部 AI 只能经 `proposal_status`
  **观察**结果，**无任何自确认/自写库工具**（harness 硬约束延续）。
- 成功如何被观察：① MCP 工具集从 4 → 6（新增 `propose_patch`/`proposal_status`，
  仍无 apply/commit/save/accept 类工具名）；② `propose_patch` 后图库 revision 不变、
  `proposals/` 下出现 pending 提议；③ 应用内接受后 revision +1、历史
  source=`mcp_proposal`、提议转 accepted；拒绝后转 rejected；④ 接受过期补丁
  （base_revision 冲突）返回稳定错误、提议保持 pending；⑤ Web 面板可列出/接受/
  拒绝并刷新图；⑥ 全部门禁 + QA 封存。

## 范围

- In scope：
  - `packages/infrastructure/.../proposals.py`（新）：提议文件存储——
    `save_proposal`/`list_proposals`/`read_proposal`/`settle_proposal`；
    `proposals/<uuidv7>.json`（原子写 tmp+replace），payload 带 `schema_version: 1`、
    `status: pending|accepted|rejected`、`origin/note/created_at/status_at/change_id`；
    proposal_id 严格 UUID 形校验（防路径穿越）；仅 pending 可 settle。
  - `apps/api/main.py`：三个端点——`GET /api/workspaces/{id}/proposals`（pending 列表
    + 摘要，不含全量 patch）、`POST .../proposals/{proposal_id}/accept`（读提议 →
    `apply_graph_patch(trusted_actor=_LOCAL_ACTOR, source="mcp_proposal")` → settle
    accepted + change_id；失败不 settle、保持 pending）、`POST .../proposals/{proposal_id}/reject`。
  - `apps/api/mcp_server.py`：`propose_patch(workspace_id, patch, note="")`（防御性
    preview 校验 → 落 pending，返回 `proposal_id` + `requires_confirmation=true/
    confirmed=false`）；`proposal_status(workspace_id, proposal_id)`（只读观察）；
    更新 instructions 信任边界文案。
  - `apps/web`：`api.ts` `listProposals/acceptProposal/rejectProposal` +
    `ExternalProposal` 类型；`App.tsx` 右栏「外部提议（MCP）」面板（列表/接受/拒绝/
    刷新，挂载 + window focus + 操作后刷新；接受后 `loadGraph` 刷新画布）。
  - 测试：`tests/integration/test_proposal_store.py`、`test_proposal_confirm_api.py`、
    `test_mcp_bridge.py` 扩展、`apps/web/src/App.proposals.test.tsx`。
- Out of scope（后续切片）：会话级「自动确认」开关（默认关，需独立评审）；MCP
  客户端能力（调外部搜索 server）；提议 TTL/清理策略；多用户/远程模式
  （streamable-http）；B-lite agentic 绘图编排。
- 受影响模块/接口/数据：新增提议文件目录 `proposals/`（无 SQLite schema 变化、
  无迁移）；MCP 工具集 4→6（048 的工具集精确断言按本切片更新，禁写子串断言保留）；
  历史记录新 source 值 `mcp_proposal`（domain source 为自由字符串，无契约变化）。
- 依赖和假设：MCP server 与 sidecar API 以同一 `data_root` 文件系统共享提议
  （单用户本地场景，进程间以文件为信道）；`apply_graph_patch` 提交门在 accept 时
  重新校验（修订漂移 fail-closed）。

## 风险影响

- 数据/schema/migration：图库零 schema 变化；提议为独立 JSON 文件，删除目录即清空，
  回滚无残留。
- 安全/隐私（harness 评审要点）：① 外部 AI 永远不能写图库——`propose_patch` 只落
  pending 文件，accept 仅存在于应用内 API（本地回环 + CORS 白名单，与既有写端点
  同权限面），MCP 无 accept/apply 类工具；② 提议内容 = 外部不可信输入，accept 前
  经 `preview_graph_patch`（入队时）+ `apply_graph_patch`（确认时）双重校验，锁/
  修订冲突 fail-closed；③ `proposal_status` 只读；④ proposal_id 严格校验防路径
  穿越；note 字段视为文本展示（React 转义，不注入）。
- 并发/幂等/恢复：提议文件原子写；仅 pending→accepted/rejected 单向迁移（重复
  settle 返回 `proposal_state_conflict`）；接受失败（提交门拒绝）提议保持 pending
  可重试或拒绝；崩溃恢复 = 文件即真相。
- 性能/容量/成本：本地文件 IO，量级单用户；列表接口不返回全量 patch。
- 可观测性/诊断：稳定错误码 `proposal_invalid/proposal_missing/proposal_state_conflict/
  patch_invalid`（+rule）；历史 source=`mcp_proposal` 可追溯。
- 用户文档：USER_MANUAL「外部提议（MCP）」说明。

## 验收标准

- [ ] AC-1：MCP 工具集 = 6（新增 propose_patch/proposal_status），禁写子串
  （write/apply/submit/commit/save/delete/accept）断言仍通过。
- [ ] AC-2：`propose_patch` 合法补丁 → pending 提议 + proposal_id；图库 revision
  与 concepts 不变（不写库）；非法补丁 → 结构化 patch_invalid、无文件落盘。
- [ ] AC-3：应用内 accept → `applied` + change_id + revision +1 + 历史
  source=mcp_proposal + 提议 accepted；此后重复 accept → proposal_state_conflict。
- [ ] AC-4：reject → 提议 rejected、图库不变。
- [ ] AC-5：接受 base_revision 过期的提议 → 稳定错误（提交门拒绝）、提议保持
  pending。
- [ ] AC-6：`proposal_status` 返回 pending/accepted(+change_id)/rejected；未知 id →
  proposal_missing。
- [ ] AC-7：Web 面板列出/接受/拒绝提议，接受后画布刷新。
- [ ] 回滚/禁用：回退本切片提交即回到 048 的 4 工具只读形态；`proposals/` 目录
  可独立删除清理。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-PROP-001 | integration | 提议存储 CRUD/原子性/路径穿越 | 保存/列表/读取/settle 单向迁移、非法 id 拒绝 | `test_proposal_store.py` |
| TC-PROP-002 | integration | propose_patch 不写库 | pending + revision 不变；非法补丁无落盘 | `test_mcp_bridge.py` |
| TC-PROP-003 | integration | proposal_status 观察 | 三态 + change_id；未知 id fail-closed | 同上 |
| TC-PROP-004 | integration | 应用内 accept/reject | applied/source/accepted；reject 不动图 | `test_proposal_confirm_api.py` |
| TC-PROP-005 | integration | 重复 settle / 过期补丁 | proposal_state_conflict / 提交门稳定错误且保持 pending | 同上 |
| TC-PROP-006 | web 单测 | 面板交互 | 列表渲染/接受刷新/拒绝移除 | `App.proposals.test.tsx` |
| TC-PROP-007 | 全部门禁 | 回归 | pytest + Web + 构建绿 | 门禁输出 |

## 交付物与关闭

- Commit/PR：红灯测试 → 实现 → 文档 → 证据封存。
- Contract/ADR/migration/prompt：无 canonical 契约变化（提议 payload 为基础设施
  文件格式，`schema_version: 1` 自版本化）。
- Test Run：`TR-20260816-002`。
- Release：桌面产物随本切片统一重建（launcher/build.spec 无变化）。
- 观察结果：harness 文档（ai-mindmap-agent-harness.md）补 MCP 写桥约束一节。
- 未完成项的新 ID：会话级自动确认开关；提议 TTL/清理；B-lite agentic 编排。
