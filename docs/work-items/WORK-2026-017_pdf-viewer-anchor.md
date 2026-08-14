# WORK-2026-017：PDF 文本解析与 Anchor 来源跳转

```yaml
status: verified_prototype
type: feature
owner: Codex (parser + viewer + anchor role)
reviewers: [ai_qa_auditor, workspace_owner]
related_ids: [REQ-2026-006, REQ-2026-010, NFR-2026-002, ADR-0001, WORK-2026-004, WORK-2026-005, WORK-2026-016, TR-20260814-005, TR-20260814-008, TR-20260814-009]
target_stage: "阶段 1 / 自然语言第 5 步"
risk: high
created_at: 2026-08-14T09:30:00+08:00
updated_at: 2026-08-14T09:45:00+08:00
```

## 问题与结果

- 用户/工程问题：WORK-2026-016 已能把 PDF 安全导入并注册为资源，但导入后无法查看内容、无法从知识树节点跳回资料来源的原文位置；第 5 步完成标志"点击节点可稳定打开正确资料位置；找不到或资料漂移时明确提示，不误跳"未兑现。
- 期望结果：新增 PDF 文本解析与页级查看：对已导入的 PDF 资源提取页文本（存 `resource_segment`）、API 提供页文本读取与 Anchor 定位端点、Web 提供页文本查看器与"从节点跳回原文"入口；以微积分金标 50 个页级锚点验收；资料漂移（hash 变化）时明确提示不误跳。
- 成功如何被观察：导入金标 PDF 后，在 Web 查看器打开其第 2 页并看到与 pypdf 提取一致的文本；节点带 anchor 时点击跳转到对应页并高亮定位；资源 hash 漂移时提示"资料已变化，无法定位"而非错误跳转。

## 范围

- In scope：`packages/infrastructure` 新增 PDF 解析器（pypdf 提取页文本 → `resource_segment` 表，schema v3 migration）；Anchor 解析与校验（复用 `knowledge_tree_contracts` anchor 契约）；API 新增 `GET /api/workspaces/{id}/resources/{rid}/pages/{n}`（页文本）、`GET /api/workspaces/{id}/resources/{rid}/anchors`（该资源锚点列表）与按 anchor 定位端点；Web 新增页文本查看器面板与"来源"跳转按钮；金标 50 锚点验收测试。
- Out of scope：真实 PDF.js 渲染（本步用页文本查看器，PDF.js 可视化渲染为后续工作项）、bbox 区域高亮（页文本级定位）、Markdown/TXT 查看器、OCR、中文分词、云端、加密、真实 AI/Provider。
- 受影响模块/接口/数据：扩展 `packages/infrastructure`（schema v3 + `resource_segment` 表 + PDF 解析）、`apps/api`、`apps/web`；Anchor v1 canonical schema 已冻结（WORK-2026-005），本步消费它不修改它；无新 canonical contract/prompt。
- 依赖和假设：pypdf 已锁定（6.x）；`resource_segment(id, resource_version_id, ordinal, page, text, text_hash, parse_confidence)`；锚点 selectors 支持 `page`/`text_position`/`page_bbox`；金标锚点 `selector.page` 直接映射页序；漂移检测用 `resource_version.content_hash` 与解析时 source_state.content_hash 比对。

## 安全与边界

- 页文本端点只返回已导入资源的内容，不越权读取仓库或 workspace 之外文件；解析器只接受已注册的 resource_version 的受控副本路径。
- 页文本长度限制（单页 ≤ 64 KiB 或截断）与错误脱敏；漂移时不返回旧定位，只给稳定错误 `source_changed`。
- Anchor 定位不做模糊匹配：找不到精确页/文本 → `anchor_not_found`，绝不跳到错误位置。

## 风险影响

- 数据/schema/migration：schema v3（resource_segment 表）；旧库迁移保留数据；解析结果绑定 resource_version 与 content_hash。
- 安全/隐私：只读受控资源；无网络出站；错误不含正文。
- 并发/幂等/恢复：解析幂等（同 resource_version 重复解析返回既有结果）；单用户本地。
- 性能/容量/成本：52 页金标 PDF 秒级解析；单页文本 ≤64 KiB；无模型费用。
- 可观测性/诊断：稳定错误码（`source_changed`/`anchor_not_found`/`parse_failed`）；不落正文。
- 用户文档：更新 USER_MANUAL 与路线第 5 步进度；明确"页文本查看器 ≠ PDF.js 渲染"边界。

## 验收标准

- [x] AC-1：导入的 PDF 可解析为页文本并存入 `resource_segment`（每页一条，含 text_hash）；重复解析幂等。
- [x] AC-2：`GET .../resources/{rid}/pages/{n}` 返回该页文本与元数据；页越界/未解析 → 稳定错误；缺失 workspace/resource → 404。
- [x] AC-3：`GET .../resources/{rid}/anchors` 返回该资源锚点列表（复用 canonical anchor 结构）；缺失资源 404。
- [x] AC-4：按 anchor 定位：金标 50 锚点的 `selector.page` 均能定位到对应页；文本漂移（content_hash 变化）→ `source_changed` 不误跳。
- [x] AC-5：Web 提供页文本查看器（选择资源→翻页）与"从节点跳回原文"入口（节点携带 anchor 时可跳转）；漂移/缺失时明确提示。
- [x] AC-6：集成/组件/安全测试覆盖正/负路径；全仓门通过。
- [x] 错误和恢复路径：未解析资源提示"请先解析"；解析失败以稳定错误返回且不污染既有数据。
- [x] 回滚/禁用方法：回退本工作项提交可回到导入-only；不影响既有持久化与导入证据。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-VIEW-001 | integration | PDF 解析 → segment | 每页文本+hash，幂等 | 10/10 PASS / TR-009 |
| TC-VIEW-002 | integration | 页文本端点 | 正确文本/越界/未解析/404 | 10/10 PASS / TR-009 |
| TC-VIEW-003 | integration | anchors 端点 | 金标 50 锚点、UPSERT、缺失 404 | 10/10 PASS / TR-009 |
| TC-VIEW-004 | security | 漂移/缺失定位 | source_changed/anchor_not_found，不误跳 | 10/10 PASS / TR-009 |
| TC-VIEW-005 | component | Web 查看器与跳转 | 翻页、跳转、漂移提示 | Web 18/18 PASS / TR-009 |
| TC-REPO-001 | repository | 全仓门 | validator/Ruff/mypy/pytest/Web | 218/218、18/18 PASS / TR-009 |

## 交付物与关闭

- Commit/PR：分支 `feature/WORK-2026-017-pdf-viewer-anchor`；Ready `2829ff2`，红灯 `53eb2cd`，实现 `8c3c620`，P2 修复 `267fb7e`。
- Contract/ADR/migration/prompt：schema v3（resource_segment/anchor）；消费 anchor v1 契约；无新 canonical contract/prompt。
- Test Run：viewer 10/10、全仓 Python 218/218、Web 18/18、Ruff、strict mypy、repository validator、frozen installs/peers/check/build 全通过；职责隔离 QA attempt 001 PASS；真实 uvicorn e2e（金标 PDF）PASS；证据为 `TR-20260814-009`。
- Release：无托管发布；本地 API + Web 可演示 PDF 页文本查看与跳转。
- 观察结果："从节点跳回资料原文页"prototype 已验证；PDF.js 真实渲染、bbox 高亮属于后续。
- 未完成项的新 ID：PDF.js 可视化渲染、bbox 区域高亮、Markdown/TXT 查看器、OCR、中文分词分别后续建项。
