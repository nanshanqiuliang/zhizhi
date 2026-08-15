# WORK-2026-026：AI 草案 API 端点与 Web 批量接受/拒绝（第 8 步切片 3）

```yaml
status: ready
type: feature
owner: Codex (ai-draft + api + web role)
reviewers: [ai_qa_auditor, workspace_owner]
related_ids: [WORK-2026-009, WORK-2026-005, WORK-2026-008, WORK-2026-014, WORK-2026-016, WORK-2026-019, WORK-2026-022, REQ-2026-006, NFR-2026-001, NFR-2026-006, NFR-2026-007, NFR-2026-008, TR-20260814-014]
target_stage: "阶段 1 / 自然语言第 8 步切片 3（草案 API 端点 + Web 批量接受/拒绝）"
risk: high
created_at: 2026-08-15T03:00:00+08:00
updated_at: 2026-08-15T03:00:00+08:00
```

## 问题与结果

- 用户/工程问题：第 8 步切片 1+2 已把纯领域草案内核与真实 DeepSeek 概念抽取/关系候选打通（QA PASS `TR-20260814-014`），但"从导入资料 → 生成草案 → 用户预览 → 接受后写入"的用户可见闭环缺失。草案目前只能在脚本/测试里生成，产品界面没有"生成草案、批量接受/拒绝"入口。
- 期望结果：`POST /api/workspaces/{id}/ai-draft` 端点把已导入资源文本（Markdown/TXT 原文、PDF 已解析页文本）经注入式 draft generator 转成不可信草案 + `proposed`（`confirmed=false`）GraphPatch，**不写库**；Web 在资料列表提供"生成草案"，展示概念/关系/置信度/来源，接受时把 patch 置 `confirmed=true` 经既有 `POST graph/patches` 提交门写入（锁定/revision/确认门全部生效），拒绝则丢弃。
- 成功如何被观察：从失败测试启动；端点对"无 generator/缺 resource_id/资源缺失/PDF 未解析/不支持 mime"稳定失败关闭；生成的 patch 经 `validate_contract("graph_patch")` 校验且 `requires_confirmation=true`、`confirmed=false`、`actor=user`；接受路径经提交门写入 AI `origin` 概念/边（带 evidence），拒绝路径不写库；全仓门全绿。

## 范围

- In scope：
  - `packages/infrastructure/.../workspace.py`：`read_resource_text(layout, resource_id)`——Markdown/TXT 读原文（UTF-8，解码失败 `parse_failed`）；PDF 要求已 `parse_pdf_resource`，按页拼接 `resource_segment`（未解析 `parse_pending`）；其他 mime `draft_unsupported_resource`。
  - `apps/api/main.py`：`POST /api/workspaces/{id}/ai-draft`（body `{resource_id}`）——`create_app` 新增注入式 `draft_generator: Callable[[resource_text, resource_id, current_graph], {draft, patch}] | None`；无 generator 返回 503 `ai_not_available`；资源读取/校验错误复用 `_http_error` 映射；返回前 `validate_contract("graph_patch", patch)` 且强制 `requires_confirmation=true`、`confirmed=false`、`actor={"type":"user","id":"local-user"}`。
  - `apps/api/ai_draft.py`：`build_deepseek_draft_generator()`——仅 `DEEPSEEK_API_KEY` 存在时构造（否则 None）；读 `config/llm`（复用 `load_and_validate_llm_config`）+ `model-policies` 预算；`build_ai_draft`（`deepseek_concept_extractor`/`deepseek_relation_provider`，evidence 绑定 per-chunk 合成 UUIDv7 anchor，草案来源引用、不落库）+ `build_draft_patch`，再把 patch `actor` 改写为 user（概念/边 `origin` 仍为 `ai`）返回。
  - `apps/api/__main__.py`：启动时若 `DEEPSEEK_API_KEY` 存在则注入真实 generator（显式 opt-in），否则端点 503。
  - `apps/web/src/api.ts` + `App.tsx`：`generateDraft(resourceId)`；资料列表"生成草案"按钮；草案预览面板（概念/关系/置信度/来源计数）；"接受"（patch.confirmed=true → `applyPatch` → 重载图）与"拒绝"；`ai_not_available` → 显示"AI 未连接"。
  - 测试：`tests/integration/test_ai_draft_api.py`（端点，注入确定性 fake generator，无网络）+ `read_resource_text` 单元/集成测试 + Web `App.draft.test.tsx`（mock fetch）。
- Out of scope：草案证据锚点真实落库与"点来源跳回原文"（后续切片，草案 evidence 为合成 UUIDv7 来源引用）；对话/检索（第 9 步）；PPTX/DOCX/OCR；真实 DeepSeek 调用除 `__main__` 显式 opt-in 外不进测试（测试全用 fake generator/mock）。
- 受影响模块/接口/数据：新增 `apps/api/ai_draft.py`；扩展 `workspace.py`（`read_resource_text`）、`apps/api/main.py`（端点 + 注入）、`apps/web/src/api.ts`/`App.tsx`；新增两个测试文件。无 canonical contract/migration/prompt 变更；`config/llm` 语义不变。
- 依赖和假设：WORK-2026-005（GraphPatch v1）、WORK-2026-008（DeepSeek adapter，owner 已批准 `enabled:true`）、WORK-2026-014（FastAPI sidecar）、WORK-2026-016（安全导入）、WORK-2026-017（PDF 页文本）、WORK-2026-019/022（提交门 + `POST graph/patches`）、WORK-2026-009 切片 1+2（草案内核 + LLM 抽取）已验证；端点绝不因草案生成写库；接受仅经既有提交门。

## 设计边界

- 领域/契约不变：`build_draft_patch` 输出的概念/边 `origin=ai`、`review_state=proposed`、`requires_confirmation=true`；API 层仅把 patch 顶层 `actor` 改写为本地 user（`confirmed=false`）以便用户确认，不改概念/边 provenance。
- 草案生成的证据为 per-chunk 合成 UUIDv7 anchor 引用，仅用于 `evidence_ids` 契约合规与来源展示，不落 `anchor` 表；"点来源跳转"明确不在本切片。
- 端点只读资源文本 + 调用注入 generator；generator 为 None 时 503 失败关闭，绝不静默回退到启发式（避免把启发式结果冒充真实 AI）。
- 接受路径复用 `POST graph/patches` 提交门：`base_revision_no` 与当前图不一致 → `revision_conflict`；锁定项覆盖 → `target_locked`；确认门 `requires_confirmation=true` + `confirmed=true`。
- 确定性：测试注入的 fake generator 确定性输出；真实 generator 的 `id_factory` 使用 `uuid7`（时间有序）。

## 风险影响

- 数据/schema/migration：无 schema/migration；仅新增读函数与端点。
- 安全/隐私：草案/端点错误仅含标识不含正文；generator 仅在 `DEEPSEEK_API_KEY` 存在时接线；密钥仅 env 不落盘；资源文本不落日志。
- 并发/幂等/恢复：生成不写库（幂等、无副作用）；接受走幂等 change_id 提交门。
- 性能/容量/成本：生成受 task profile 金额/attempt/回退预算约束；PDF 拼接页文本为 O(pages)。
- 可观测性/诊断：稳定错误码 `ai_not_available`(503)、`draft_invalid`/`draft_unsupported_resource`/`parse_pending`(422)、`draft_cycle_detected` 等；不落正文。
- 用户文档：路线第 8 步进度更新；用户手册补"生成草案 → 预览 → 接受/拒绝"步骤与"AI 未连接"边界。

## 验收标准

- [ ] AC-1 (c1)：`read_resource_text`——MD/TXT 读原文；PDF 未解析 `parse_pending`、已解析按页拼接；未知 mime `draft_unsupported_resource`；解码失败 `parse_failed`。
- [ ] AC-2 (c2)：`POST .../ai-draft` 注入 fake generator 时返回 `{draft, patch}`，patch 经 `validate_contract` 且 `requires_confirmation=true`、`confirmed=false`、`actor=user`。
- [ ] AC-3 (c3)：端点失败关闭——无 generator 503 `ai_not_available`；缺/非法 `resource_id` 422；资源缺失 404；PDF 未解析 422 `parse_pending`。
- [ ] AC-4 (c4)：接受路径——把返回 patch 置 `confirmed=true` 后 `POST graph/patches` 写入 AI `origin` 概念/边（带 evidence、`review_state=proposed`），重载图可见；拒绝路径不产生任何写。
- [ ] AC-5 (c5)：Web——资料列表"生成草案"→ 预览概念/关系/置信度；"接受"经提交门写入并刷新；"拒绝"丢弃；`ai_not_available` 显示"AI 未连接"。
- [ ] AC-6 (c6)：repository 门：validator、Ruff、scripts + strict package mypy（含 apps/api）、全仓 pytest、Web 全绿。
- [ ] 错误和恢复路径：generator 抛错（无 JSON/成环/无证据）→ 422 稳定错误码，不产出半成品；端点不写库。
- [ ] 回滚/禁用方法：回退本工作项提交即回到无 AI 草案 UI；不设置 `DEEPSEEK_API_KEY` 则端点 503；红灯与证据保留。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-AIDRAFT-API-001 | integration | 端点生成草案 + 接受写入 | fake generator 草案 → 提交门写入 AI 概念/边 | 待实现 |
| TC-AIDRAFT-API-002 | integration | 端点失败关闭 | 无 generator/缺 id/资源缺失/未解析 | 待实现 |
| TC-AIDRAFT-API-003 | unit | `read_resource_text` | MD/TXT/PDF/未解析/未知 mime/解码失败 | 待实现 |
| TC-AIDRAFT-WEB-001 | component | 草案预览 + 接受/拒绝 | 生成→预览→接受经提交门→拒绝丢弃 | 待实现 |
| TC-REPO-001 | repository | 全仓门 | validator/Ruff/mypy/pytest/Web | 待实现 |

## 交付物与关闭

- Commit/PR：分支 `feature/WORK-2026-009-ai-draft-pipeline`（切片 3 沿用）或新分支 `feature/WORK-2026-026-ai-draft-api-web`；Ready → 红灯 → 实现 → QA。
- Contract/ADR/migration/prompt：无新 canonical contract/ADR/migration/prompt；复用 GraphPatch v1 与 `config/llm` v1。
- Test Run：TC-AIDRAFT-API-001..003 + TC-AIDRAFT-WEB-001 + 全仓门。
- Release：无托管发布；真实 DeepSeek 调用仅 `__main__` 显式 opt-in（`DEEPSEEK_API_KEY`）。
- 观察结果：草案生成/预览/接受闭环打通；草案绝不直写库、不覆盖锁定项；AI 概念/边带 evidence 与 provenance。
- 未完成项的新 ID：草案证据锚点真实落库 + 点来源跳回原文（后续切片）。
