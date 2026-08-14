# WORK-2026-015：FTS5 基础搜索（笔记/概念全文检索）

```yaml
status: verified_prototype
type: feature
owner: Codex (search + api + web role)
reviewers: [ai_qa_auditor, workspace_owner]
related_ids: [REQ-2026-006, REQ-2026-010, NFR-2026-001, WORK-2026-013, WORK-2026-014, TR-20260814-005, TR-20260814-006, TR-20260814-007]
target_stage: "阶段 1 / 自然语言第 4 步"
risk: medium
created_at: 2026-08-14T08:15:00+08:00
updated_at: 2026-08-14T08:40:00+08:00
```

## 问题与结果

- 用户/工程问题：第 4 步主要产物包含"基础搜索"，但当前持久化闭环（WORK-2026-013/014）只支持保存/加载/备份，没有对已保存笔记与概念标题做全文检索；随着课程变大，用户无法从笔记内容定位节点。
- 期望结果：新增基于 SQLite FTS5 的本地全文搜索：已保存 CourseGraph 的 concept label 与 note annotation 建立可搜索索引；API 暴露 `GET /api/workspaces/{id}/search?q=...`；Web 提供搜索框，输入关键词返回匹配节点并可点击定位。
- 成功如何被观察：保存含特定词的笔记后，在 Web 搜索框输入该词能列出匹配概念；点击结果定位到节点；空查询/无匹配/非法 workspace 给出稳定反馈。

## 范围

- In scope：`knowledge_tree_infrastructure.workspace` 新增 FTS5 索引（建表/重建/查询）；`apps/api` 新增 search 端点（校验 query、复用 workspace 数据目录、返回匹配 concept 的 id/label/note 片段）；`apps/web` 新增搜索框 UI 与结果列表；集成/组件测试。
- Out of scope：中文分词（FTS5 unicode61 按空格/标点切分，中文整词匹配有限，作为已知边界）、模糊/纠错、按边/位置搜索、搜索历史、多 workspace 搜索、FTS5 之外的向量检索、文件内容检索（第 5 步）。
- 受影响模块/接口/数据：扩展 `packages/infrastructure` workspace adapter 与 `apps/api`、`apps/web`；不改 canonical graph schema、migration v1（FTS5 表为派生索引，随 graph 内容重建）；无新 canonical contract/prompt。
- 依赖和假设：Python 3.12 sqlite3 内置 FTS5（已验证）；索引只针对已保存的 CourseGraph 内容，AI/导入不可绕过；查询参数做长度/字符限制与转义。

## 安全与边界

- 搜索端点只读；query 做长度限制（如 ≤100 字符）与 FTS5 语法安全处理（非法 MATCH 语法以稳定错误拒绝，不抛 500）。
- 不返回正文全文到错误消息；结果只含 id/label/note 片段（片段截断到安全长度）。
- 空查询返回空列表或 422 稳定拒绝；无匹配返回空列表 200。

## 风险影响

- 数据/schema/migration：FTS5 是派生索引，`save_course_graph` 后需同步重建；不新增 version migration。
- 安全/隐私：仅本地；query 与片段不出现在错误详情；无网络出站。
- 并发/幂等/恢复：单用户本地；索引重建在保存事务内完成；损坏索引可重建。
- 性能/容量/成本：单课程数百节点；FTS5 索引增量小；无模型费用。
- 可观测性/诊断：稳定错误码（如 `search_invalid_query`）；片段脱敏。
- 用户文档：更新 USER_MANUAL 与路线第 4 步完成状态；明确中文分词限制。

## 验收标准

- [x] AC-1：保存含特定词的 CourseGraph 后，FTS5 索引可查询到匹配 concept（label 与 note 均可命中）。
- [x] AC-2：`GET /api/workspaces/{id}/search?q=...` 返回 200 + 匹配列表（id/label/note 片段）；空查询/超长查询/非法 MATCH 语法稳定拒绝；无匹配返回空列表。
- [x] AC-3：Web 搜索框输入关键词显示匹配节点，点击后选中并滚动定位到该节点。
- [x] AC-4：搜索端点只读，不修改数据；缺失 workspace 返回 404 workspace_missing。
- [x] AC-5：集成/组件测试覆盖正/负路径；全仓门通过。
- [x] 错误和恢复路径：非法查询提示"搜索失败，请检查搜索词"；索引损坏可重建不崩溃。
- [x] 回滚/禁用方法：回退本工作项提交即可移除搜索；不影响持久化内核与证据。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-SEARCH-001 | integration | FTS5 索引建/查 | label/note 命中 | 10/10 PASS / TR-007 |
| TC-SEARCH-002 | integration | search 端点正/负路径 | 匹配列表、空/超长/非法 422、404 | 10/10 PASS / TR-007 |
| TC-SEARCH-003 | component | Web 搜索框交互 | 结果列表、点击定位 | Web 12/12 PASS / TR-007 |
| TC-REPO-001 | repository | 全仓门 | validator/Ruff/mypy/pytest/Web | 193/193、12/12 PASS / TR-007 |

## 交付物与关闭

- Commit/PR：分支 `feature/WORK-2026-015-fts5-search`；Ready `e451057`，实现 `eeba073`（红灯与实现合并，偏差已披露），P2-2 修复 `d6c8e01`。
- Contract/ADR/migration/prompt：无新 canonical contract；FTS5 表为派生索引；无 migration/prompt。
- Test Run：搜索 10/10、全仓 Python 193/193、Web 12/12、Ruff、strict mypy、repository validator、frozen installs/peers/check/build 全通过；职责隔离 QA attempt 001 PASS；真实 uvicorn e2e（中文搜索）PASS；证据为 `TR-20260814-007`。
- Release：无托管发布；本地 API + Web 可演示搜索。
- 观察结果：FTS5 基础搜索已验证，第 4 步最后一个主要产物完成；中文分词与文件内容检索属第 5 步。
- 未完成项的新 ID：中文分词、文件内容检索（第 5 步）、模糊搜索/纠错、搜索历史分别后续建项。
