# WORK-2026-055：知识点来源跳转（文档锚点 + 网址链接）

```yaml
status: ready
type: feature
owner: api + infrastructure + web + QA
reviewers: [project_owner, qa]
related_ids: [WORK-2026-027（来源锚点）, WORK-2026-053（Web 搜索来源）, REQ-2026-001]
target_stage: 第 11 步 Beta 加固与扩展
risk: low
created_at: 2026-08-16T00:00:00Z
updated_at: 2026-08-16T00:00:00Z
```

## 问题与结果

- 用户/工程问题：知识点 block 无法一键跳到其来源——AI 文档草案的锚点只在草案
  预览时有「跳回原文」（接受后入口消失，且只跳第一个）；Web 搜索草案的来源 URL
  只在草案面板显示，**接受写入后与概念彻底失联**；手动链接能力缺失。
- 期望结果：① 详情面板新增「来源与链接」区：文档锚点列表（资源名 + 页码，点击
  打开查看器并跳到对应页）+ 网页链接列表（点击打开浏览器）；② 接受 Web 搜索
  草案时，来源 URL **自动**作为 `link_N` annotations 写入每个新建概念；③ 手动
  「添加链接」输入框（`upsert_annotation` 提交门写入，annotations 锁保护）；④ 画布
  上有来源/链接的节点显示 🔗 角标。
- 成功如何被观察：端点按概念返回锚点（含资源名/页码/类型）；详情面板渲染两类
  来源并可交互；搜索草案接受后 patch 携带 link annotations；全门禁 + CI 绿。

## 范围

- In scope：
  - `packages/infrastructure/.../workspace.py`：`get_anchors_by_ids(layout, ids)`
    （SQL IN 查询，缺失 id 静默跳过）。
  - `apps/api/main.py`：`GET /api/workspaces/{id}/concepts/{concept_id}/anchors`
    ——图读概念 `evidence_ids` → anchor 表 join `list_resources` 资源名/mime；
    未知概念 404；无 evidence 返回空列表。
  - `apps/web`：`api.ts` `ConceptAnchor` 类型 + `listConceptAnchors?` +
    `buildUpsertLinkPatch`（mirror `buildSetLockPatch`）；`App.tsx` 详情面板
    「来源与链接」块（锚点→openViewer+跳页；链接→window.open；添加链接输入）、
    选中概念变化时拉取锚点、acceptDraft 对搜索草案自动注入 `link_1..N`
    annotations、画布 🔗 角标；`styles.css` 样式。
  - 测试：`tests/integration/test_concept_anchors_api.py` + 
    `apps/web/src/App.sources.test.tsx`。
- Out of scope：删除/编辑已存链接（`upsert_annotation` 按 kind 替换语义下可先
  覆盖同序号；完整删除走 update_concept，后续切片）；链接标题/备注（Annotation
  仅 kind/value）；问答/指令引用链接；非 PDF 文档的页内定位（MD/TXT 跳转=打开）。
- 受影响模块/接口/数据：新增 1 只读端点 + 1 infra 查询 + 前端块；无契约/迁移
  变化（annotations 是既有自由字段，`link_N` 符合 kind pattern）。
- 依赖和假设：概念 `evidence_ids` 与 anchor 表的既有关联（WORK-2026-027）；
  `upsert_annotation` 按 kind 替换（编号 kind 实现多链接，幂等）。

## 风险影响

- 安全/隐私：链接 value 上限 512 字符（契约）；window.open 仅用户点击触发；
  annotation 写入走提交门（annotations 锁保护，锁定概念不可加链接）。
- 兼容性：既有 annotations（note 等）不受影响（kind 不同不冲突）；既有草案/
  锚点行为不变。
- 回滚：回退提交即回无跳转形态；link annotations 随图数据保留（无害）。

## 验收标准

- [ ] AC-1：端点按概念返回锚点列表（anchor_id/resource_id/page/label/
  resource_name/mime）；悬空 evidence id 跳过；未知概念 404。
- [ ] AC-2：详情面板显示文档锚点（点击打开查看器跳页）与链接（点击 window.open）。
- [ ] AC-3：搜索草案接受时新概念 annotations 自动携带全部来源 URL（link_1..N）。
- [ ] AC-4：手动添加链接经 `upsert_annotation` 提交门写入（下一个 link_N 序号）。
- [ ] AC-5：有来源/链接的节点显示 🔗 角标。
- [ ] AC-6：全门禁 + CI 绿。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-SRC-001 | integration | 端点 join/悬空/404/空 | 见 AC-1 | `test_concept_anchors_api.py` |
| TC-SRC-002 | web | 面板渲染 + 两类跳转 | 见 AC-2 | `App.sources.test.tsx` |
| TC-SRC-003 | web | 搜索草案自动注入 | 见 AC-3 | 同上 |
| TC-SRC-004 | web | 手动添加链接 patch 形状 | 见 AC-4 | 同上 |
| TC-SRC-005 | 全部门禁+CI | 回归 | 全绿 | 门禁/CI |

## 交付物与关闭

- Commit/PR：红灯测试 → 实现 → 文档 → 证据封存 + 推送 CI。
- Test Run：`TR-20260816-006`。
- Release：桌面产物重建。
- 未完成项的新 ID：链接删除/编辑；链接标题；MD/TXT 页内定位。
