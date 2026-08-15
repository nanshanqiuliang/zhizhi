# WORK-2026-039：多课程 / 新建课程（多工作区，第 10 步后用户反馈）

```yaml
status: ready
type: feature
owner: Codex (api + web role)
reviewers: [ai_qa_auditor, workspace_owner]
related_ids: [WORK-2026-013, WORK-2026-014, REQ-2026-001, NFR-2026-001]
target_stage: "阶段 1 / 第 10 步后使用反馈修复"
risk: medium
created_at: 2026-08-15T23:20:00+08:00
updated_at: 2026-08-15T23:20:00+08:00
```

## 问题与结果

- 用户/工程问题：使用反馈——「没有添加其他笔记、新建课程的功能，目前只能使用试用的笔记」。
  当前 Web/桌面应用硬编码单一工作区（`WORKSPACE_ID` 常量），无法新建/切换课程。
- 期望结果：侧边栏列出课程（工作区），「新建课程」创建新工作区（初始图含一个主题节点）并
  切换；点击课程切换其知识树与资料；每门课程数据独立（图/资源/历史/备份）。
- 成功如何被观察：红灯测试（`GET/POST /api/workspaces` 缺失 404）→ 实现；列出/新建/切换课程
  的集成与组件测试通过；全仓门全绿。

## 范围

- In scope：
  - `apps/api/main.py`：`GET /api/workspaces`（枚举 `data_root/*` UUIDv7 目录 + 图元数据：
    名称=根概念标签、概念数、更新时间）；`POST /api/workspaces`（`{name}` → 生成 workspace id +
    初始图（单根概念）→ 返回 `{id, name}`）；名称校验（非空 ≤50）。
  - `apps/web/src/api.ts`：`httpPersistApi(baseUrl, workspaceId = DEFAULT)` 参数化 URL 工作区；
    `listWorkspaces()`、`createWorkspace(name)`。
  - `apps/web/src/App.tsx`：`apiFactory` prop（生产）或 `api` prop（测试）→ `effectiveApi`
    useMemo（随 workspaceId 重建）；侧边栏课程列表 + 「新建课程」+ 点击切换；切换后重载图与资料。
  - 测试：`tests/integration/test_workspaces.py`；Web 组件测试（可选）。
- Out of scope：课程重命名/删除；跨课程复制/移动；课程封面/图标；工作区多笔记细分（第 11 步）。
- 受影响模块：`apps/api/main.py`、`apps/web/src/{api.ts, App.tsx, main.tsx}`、相关测试。
- 依赖和假设：后端本就按 URL workspace id 分目录存储（`data_root/<uuid>`）；图内部
  workspace_id/course_id 与 URL 不必一致（`save_course_graph` 不做匹配校验，MVP 接受）。

## 设计边界

- 领域/契约：无新 canonical contract；新增本地工作区列表/创建端点。
- 隔离：每工作区独立图/资源/历史/备份；切换课程不共享数据。
- 名称：课程名 = 根概念（无入边的概念）标签；无图时「未命名课程」。
- 兼容：`api` prop 兼容既有测试（单工作区行为不变）；`apiFactory` 供生产多工作区。

## 风险影响

- 数据/schema/migration：无迁移；新工作区为新增目录/图。
- 安全/隐私：仅本机；名称/枚举经 UUIDv7 + 目录存在性守卫。
- 并发/幂等/恢复：创建幂等（新 id）；切换重载幂等。
- 性能/容量/成本：列表读每个工作区图（个人规模可接受）。
- 可观测性/诊断：切换/新建有状态反馈。
- 用户文档：手册「多课程」章节。

## 验收标准

- [ ] AC-1：`GET /api/workspaces` 列出既有工作区（id/名称/概念数/更新时间）。
- [ ] AC-2：`POST /api/workspaces {name}` 创建新工作区（初始图含根概念）并返回 id。
- [ ] AC-3：名称缺失/超长/非字符串 → 422。
- [ ] AC-4：Web 侧边栏列出课程，「新建课程」创建并切换；点击课程切换（重载图与资料）。
- [ ] AC-5：既有 `api` prop 测试不受影响（单工作区兼容）。
- [ ] AC-6：全仓门（validator/Ruff/mypy/pytest/Web）全绿。
- [ ] 错误和恢复路径：列表/创建失败明确报错；切换失败回退当前课程。
- [ ] 回滚/禁用方法：回退本提交即回单一工作区。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-WS-001 | integration | GET /workspaces 列出现有 | id/name/concepts | 待实现 |
| TC-WS-002 | integration | POST 创建 + 再 GET 出现 | 新工作区可列出/可载图 | 待实现 |
| TC-WS-003 | integration | 名称非法 422 | name_invalid | 待实现 |
| TC-WS-004 | component | 新建/切换课程 | 调用 createWorkspace + 切换 | 待实现 |
| TC-REPO-001 | repository | 全仓门 | validator/Ruff/mypy/pytest/Web | 待实现 |

## 交付物与关闭

- Commit/PR：分支 `feature/WORK-2026-039-multi-workspace`；Ready → 红灯 → 实现。
- Contract/ADR/migration/prompt：无新 canonical contract；新增本地工作区端点。
- Test Run：TC-WS-001..004 + 全仓门。
- Release：随下一个桌面构建。
- 观察结果：可新建课程并在多课程间切换。
- 未完成项的新 ID：课程重命名/删除、工作区多笔记、跨课程迁移（第 11 步）。
