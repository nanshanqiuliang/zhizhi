# AI QA attempt 001 — sourced Q&A (WORK-2026-028, Step 9 slice 1)

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: ai_qa_auditor
decision: pass
reviewed_commit: 47d6c6f06908880482e5c566a979da12a9d013cd
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

**PASS** — 0 P0 / 0 P1；3 个非阻塞 P2。这是对冻结提交 `47d6c6f`
（WORK-2026-028 切片 1：`build_answer_context` + `POST /answer` + Web 提问/回答/来源跳转）
的职责隔离机器审查。

## Red/green chain

Ready（docs）→ 红灯（`test_answer_api.py` ImportError + Web 无提问框）→ 实现
`47d6c6f`。红灯真值由红灯提交无 `AnswerContext`/`build_answer_context` 符号、api.ts
无 `askQuestion`、App.tsx 无 `向本地知识提问` 确认。

## Gates（本人执行，精确数字）

answer 6/6；全仓 408/408 + 5 skipped；ruff format/check pass（88 文件）；strict
mypy 31 文件；validator PASS（含 secret scan）；Web answer 1/1；`pnpm check` 38 tests
+ tsc + eslint 0 warnings；`pnpm build` ok。

## Adversarial mutation review（scratch worktree，已删除）

- 只读：API 可达路径 POST /answer 后 db 哈希/图内容/revision 不变、无新文件。
- 失败关闭：无 generator 503；空 422；>500（现 >100）422；未知 workspace 404；无命中
  200 `{note:"no_matches"}` 且 generator 未被调用（无幻觉路径）；migrated-no-graph 404。
- 密钥卫生：key 仅 env（answer.py）；无 logging；502 details 仅标识；问题/上下文仅进
  单条 user 消息；validator secret scan PASS。
- 检索：`[n] label：snippet` 编号上下文 + sources；反向回退（什么是极限→极限）；确定性；
  空 → `("", ())`。
- Web：asking 时按钮禁用；回答面板渲染 answer + 可点击 `[n]` 来源；来源点击 → selectNode；
  `ai_not_available` → "AI 未连接，无法回答" 且清空 answer。

## Findings

| Sev | Finding |
|-----|---------|
| P2 | 只读破例：`build_answer_context`→`search_course_graph`→`_ensure_search_table` 在 migrated-but-never-saved DB 上执行 `CREATE VIRTUAL TABLE IF NOT EXISTS`（幂等 DDL 写）；既有共享代码（GET /search 同路径），无内容变更，正常 API 流不可达。 |
| P2 | 长度契约漂移：端点声明 >500→`question_too_long`，但检索上限 100 → 101–500 字符返回 422 `search_invalid_query` 而非被回答；失败关闭但未文档化拒绝带。 |
| P2 | Web 双击竞态：`handleAsk` 无 asking 守卫，Enter 在请求进行中可重触发（按钮已禁用，Enter 路径未守卫）→ 重复 POST。 |

## Post-review fix

`9e06ebf`：A2 端点问题上限对齐 100（422 `question_too_long` 一致）+ 150 字符回归；
A3 `handleAsk` 加 asking 守卫。A1 记录为文档化既有边界。

## Superseding review

见 `ai-answer-qa-attempt-002.md`：对 `9e06ebf` 返回 PASS（0 P0/P1）。
