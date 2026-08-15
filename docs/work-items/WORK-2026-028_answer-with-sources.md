# WORK-2026-028：带来源问答（第 9 步切片 1）

```yaml
status: ready
type: feature
owner: Codex (retrieval + api + web role)
reviewers: [ai_qa_auditor, workspace_owner]
related_ids: [WORK-2026-008, WORK-2026-015, WORK-2026-016, WORK-2026-017, WORK-2026-026, WORK-2026-027, REQ-2026-006, NFR-2026-006, NFR-2026-007, NFR-2026-008]
target_stage: "阶段 1 / 自然语言第 9 步切片 1（带来源问答）"
risk: medium
created_at: 2026-08-15T04:45:00+08:00
updated_at: 2026-08-15T04:45:00+08:00
```

## 问题与结果

- 用户/工程问题：第 8 步已让 AI 从资料生成知识树草案；但用户尚不能用自然语言提问，让 AI 基于本地笔记/概念/资料给出**带来源引用**的回答并点回原文。第 9 步"对话、检索和持续整理"的第一步正是"带来源问答"。
- 期望结果：`POST /api/workspaces/{id}/answer`（body `{question}`）——先本地检索相关上下文（复用 FTS5 `search_course_graph` 搜概念/笔记，按命中拼接带引用号的上下文），再经注入式 answer generator 调用 DeepSeek `answer_with_sources` 任务配置，返回 `{answer, sources:[{id, label, kind}]}`；**不写库**；无 generator 时 503 `ai_not_available`。Web 提供提问框 + 回答面板，来源可点击跳回概念/资料。
- 成功如何被观察：从失败测试启动；离线 mock 契约测试（无网络）验证上下文检索 + 回答解析 + 来源绑定；端点失败关闭；回答仅在注入 generator 时产生；全仓门全绿。

## 范围

- In scope：
  - `packages/infrastructure/.../`：`build_answer_context(layout, question)`——FTS5 检索概念/笔记命中，产出带 `[1]`/`[2]` 引用号的上下文串 + `sources` 列表（概念 id/label、笔记）；纯只读、无 LLM 调用。
  - `apps/api/answer.py`：`AnswerGenerator = Callable[[question, context, sources], {answer, sources}]`；`build_deepseek_answer_generator()`——仅 `DEEPSEEK_API_KEY` 存在时构造，复用 `answer_with_sources` task profile（thinking enabled，预算约束），解析模型 JSON/文本回答，返回 `{answer, sources}`。
  - `apps/api/main.py`：`POST /api/workspaces/{id}/answer`——注入式 `answer_generator`；无 generator 503；body 校验；上下文检索失败/空命中稳定失败；返回 `{answer, sources}`。
  - `apps/web/src/api.ts` + `App.tsx`：`askQuestion(question)`；提问框 + 回答面板；来源点击跳回概念/资料查看器；`ai_not_available` → "AI 未连接"。
  - 测试：`tests/integration/test_answer_api.py`（离线 fake generator + FTS5 上下文）+ Web `App.answer.test.tsx`。
- Out of scope：向量检索/Embedding（`multilingual_embedding` 未解析，后续切片）；自然语言转 GraphPatch、增量重建、AI 修改历史（第 9 步后续切片）；流式回答；多轮对话上下文。
- 受影响模块/接口/数据：新增 `apps/api/answer.py` 与基础设施 `build_answer_context`；扩展 `apps/api/main.py`、`apps/web`；无 canonical contract/migration/prompt 变更（复用 `answer_with_sources` task profile 与 GraphPatch/资源/锚点契约）。
- 依赖和假设：WORK-2026-008（DeepSeek adapter + `answer_with_sources` profile，owner 已批准 `enabled:true`）、WORK-2026-015（FTS5 搜索）、WORK-2026-016/017/018/026/027（资源/锚点/查看器/草案来源）已验证；回答不写库、不改图；仅注入 generator 时发起真实 LLM 调用。

## 设计边界

- 领域/契约不变：回答只读，不改图、不写库；来源引用为 FTS5 命中（概念 id/笔记），点击跳回复用既有查看器/节点定位。
- 上下文检索确定性、无网络；错误 details 仅标识，不含正文/问题/推理内容。
- 回答生成受 `answer_with_sources` task profile 预算约束（attempt/金额/回退）；密钥仅 env。
- 回答不冒充带来源的精确引用：来源为"检索命中"，明确不声称逐句 grounding（逐句引用为后续增强）。

## 风险影响

- 数据/schema/migration：无 migration；仅只读检索 + 无状态回答。
- 安全/隐私：问题与回答不落盘、不落日志；错误仅标识；密钥仅 env。
- 并发/幂等/恢复：无写、无副作用。
- 性能/容量/成本：FTS5 O(命中)；LLM 调用受预算约束。
- 可观测性/诊断：稳定错误码 `ai_not_available`(503)、`answer_invalid`(422)；来源仅标识。
- 用户文档：用户手册补"提问 → 带来源回答 → 点回原文"；明确"来源为检索命中"边界。

## 验收标准

- [ ] AC-1 (c1)：`build_answer_context` 对 FTS5 命中产出带引用号的上下文与 sources；空命中稳定返回（无回答/提示无相关内容）。
- [ ] AC-2 (c2)：`POST /answer` 注入 fake generator 时返回 `{answer, sources}`；无 generator 503；空/超长 question 422；未知 workspace 404。
- [ ] AC-3 (c3)：离线 mock 契约——回答解析（JSON/纯文本）与来源绑定确定性、无网络；generator 抛错映射稳定错误。
- [ ] AC-4 (c4)：Web 提问框 → 回答面板展示 answer + 可点击来源（跳回概念/资料）；`ai_not_available` → "AI 未连接"。
- [ ] AC-5 (c5)：repository 门：validator、Ruff、scripts + strict package mypy（含 apps/api）、全仓 pytest、Web 全绿。
- [ ] 错误和恢复路径：无 generator/无命中/非法输入稳定失败关闭；回答不写库。
- [ ] 回滚/禁用方法：回退本工作项提交即回到无问答能力；不设 `DEEPSEEK_API_KEY` 则端点 503；红灯与证据保留。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-ANSWER-001 | integration | `build_answer_context` | FTS5 命中 + 引用号 + sources | 待实现 |
| TC-ANSWER-002 | integration | `/answer` 端点 | fake generator 回答 + 失败关闭 | 待实现 |
| TC-ANSWER-003 | contract | 离线回答解析 | JSON/文本解析 + 来源绑定 + 确定性 | 待实现 |
| TC-ANSWER-004 | component | Web 提问/回答/来源跳转 | 提问→回答→点来源 | 待实现 |
| TC-REPO-001 | repository | 全仓门 | validator/Ruff/mypy/pytest/Web | 待实现 |

## 交付物与关闭

- Commit/PR：分支 `feature/WORK-2026-009-ai-draft-pipeline`（第 9 步切片 1 沿用）；Ready → 红灯 → 实现 → QA。
- Contract/ADR/migration/prompt：无新 canonical contract/ADR/migration/prompt；复用 `answer_with_sources` profile。
- Test Run：TC-ANSWER-001..004 + 全仓门。
- Release：无托管发布；真实 DeepSeek 调用仅 `DEEPSEEK_API_KEY` opt-in。
- 观察结果：带来源问答闭环打通；回答只读、来源可点回。
- 未完成项的新 ID：向量检索、自然语言转 GraphPatch、增量重建、AI 修改历史（第 9 步后续切片）。
