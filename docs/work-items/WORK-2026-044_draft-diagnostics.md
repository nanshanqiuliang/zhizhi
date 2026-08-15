# WORK-2026-044：草案生成可诊断化与鲁棒性（错误码 rule 显示 + 块数上限 + 抽取容错）

```yaml
status: ready
type: bugfix
owner: Codex (api + web role)
reviewers: [ai_qa_auditor, workspace_owner]
related_ids: [WORK-2026-009, WORK-2026-026, WORK-2026-043, REQ-2026-001, NFR-2026-001]
target_stage: "阶段 1 / 第 10 步后使用反馈第三轮（草案生成失败）"
risk: low
created_at: 2026-08-16T00:05:00+08:00
updated_at: 2026-08-16T00:05:00+08:00
```

## 问题与结果

- 用户/工程问题：桌面版生成思维导图报「草案生成失败 draft_invalid」，但界面不显示 `rule` 子
  错误码，无法定位（可能是 `no_new_concepts`/`draft_extraction_failed`/preview 校验失败）。
  且大 PDF（实测 paper.pdf：88 页 27.9 万字符）单资源模式分块约 232 个，无块数上限、任意一块
  LLM 返回畸形/空 JSON 即整次失败。
- 期望结果：① Web 错误提示显示 `code/rule`（如 `draft_invalid/no_new_concepts`）；② 单资源
  模式同样限 40 块（与全库一致），超长资料截断处理；③ 抽取/关系容错：单块 `DraftExtractionError`
  跳过该块继续（传输/鉴权类 LLMProviderError 仍 502 显式失败，不吞错）；全部失败才 422
  `no_new_concepts`。
- 成功如何被观察：红灯测试（rule 进入错误消息、max_chunks 生效、容错继续）→ 实现；用
  paper.pdf（本地只读抽取已确认 27.9 万字符文字层）跑单资源/全库生成（注入确定性 generator）
  得到草案而非失败；全仓门全绿。

## 范围

- In scope：
  - `apps/web/src/api.ts`：`readError`/`generateDraft`/相关方法抛错带 `rule`（`code/rule`）。
  - `apps/web/src/App.tsx`：草案/回答/指令错误提示显示 `code/rule`。
  - `knowledge_tree_infrastructure/ai_draft.py`：`build_incremental_ai_draft` 增 `max_chunks`
    参数（与 `build_workspace_ai_draft` 一致的截断语义）。
  - `apps/api/ai_draft.py`：单资源与全库 generator 均传入 `max_chunks=40`；新增 fail-soft
    抽取/关系包装（仅捕获 `DraftExtractionError`，跳过该块/返回空关系）。
  - 测试：api.test.ts（rule 进入消息）、App 组件（草案错误显示 rule）、内核（max_chunks 截断）、
    fail-soft 包装（坏块跳过、其余保留；LLMProviderError 不吞）。
- Out of scope：画布无限延伸（WORK-2026-045 后续）；扫描件 OCR；PPTX；Web 搜索 agent。
- 受影响模块：`api.ts`、`App.tsx`、`ai_draft.py`（infra + api）、相关测试。
- 依赖和假设：paper.pdf 已有文字层（已实测）；DeepSeek 可用；块失败=内容畸形，传输失败=502。

## 风险影响

- 数据/schema/migration：无。
- 安全/隐私：错误消息只含 code/rule（不回显文本/推理内容）。
- 并发/幂等/恢复：无。
- 性能/容量/成本：单资源 40 块上限约束成本与耗时。
- 可观测性/诊断：错误码带 rule，可定位；抽取消极但可用（部分成功不整次失败）。
- 用户文档：手册错误提示说明。

## 验收标准

- [ ] AC-1：Web 草案错误显示 `code/rule`（rule 存在时）。
- [ ] AC-2：`build_incremental_ai_draft(max_chunks=40)` 截断超长文本（计数 extractor 断言）。
- [ ] AC-3：单块 `DraftExtractionError` 被跳过、其余块正常抽取；`LLMProviderError` 不被吞
  （仍传播 → 502）。
- [ ] AC-4：全部抽取失败 → 422 `no_new_concepts`（清晰报错）。
- [ ] AC-5：全仓门（validator/Ruff/mypy/pytest/Web）全绿；桌面产物重建。
- [ ] 错误和恢复路径：同 AC-3/4。
- [ ] 回滚/禁用方法：回退本提交即回旧行为。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-DIAG-001 | unit/api | generateDraft 422 带 rule | 错误消息含 `code/rule` | api.test |
| TC-DIAG-002 | component | 草案失败提示显示 rule | 界面含 rule 文本 | App.test |
| TC-DIAG-003 | unit | max_chunks 截断 | extractor 调用 ≤40 | kernel test |
| TC-DIAG-004 | unit | fail-soft 跳过坏块 | 其余概念保留 | fail-soft test |
| TC-REPO-001 | repository | 全仓门 | validator/Ruff/mypy/pytest/Web | 待实现 |

## 交付物与关闭

- Commit/PR：分支 `feature/WORK-2026-044-draft-diagnostics`；Ready → 红灯 → 实现。
- Contract/ADR/migration/prompt：无。
- Test Run：TC-DIAG-001..004 + 全仓门。
- Release：随下一个桌面构建。
- 观察结果：错误可定位；paper.pdf 单资源/全库生成不再因块失控/单块失败而整次失败。
- 未完成项的新 ID：画布无限延伸（045）、扫描件提示/OCR、PPTX、Web 搜索 agent。
