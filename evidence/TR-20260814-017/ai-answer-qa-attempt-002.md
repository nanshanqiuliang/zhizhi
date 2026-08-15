# AI QA attempt 002 — sourced Q&A fix (superseding, WORK-2026-028)

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: ai_qa_auditor
decision: pass
reviewed_commit: 9e06ebf04c7ddfb0badf5911cef9f4af692e5fb7
supersedes: attempt 001 (47d6c6f, PASS with 3 P2)
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

**PASS** — 0 P0 / 0 P1。这是对修复提交 `9e06ebf` 的超越审查（attempt 001 对 `47d6c6f`
已 PASS，含 3 个非阻塞 P2；本轮闭合 A2/A3，A1 保持文档化边界）。

## Closure proofs

- **A2（长度契约漂移）— CLOSED**：`POST /answer` 改为 `len(question) > 100` → 422
  `answer_invalid/question_too_long`（对齐检索 `_MAX_QUERY_LENGTH=100`），消除 101–500 的
  未文档化 `search_invalid_query` 带；新回归 `test_answer_endpoint_question_too_long`
  （150 字符 → 422、rule==question_too_long）通过。
- **A3（双击竞态）— CLOSED**：`handleAsk` 前置 `answerStatus === "asking"` 守卫，
  阻塞 Enter/按钮双路径重入；按钮 asking 时禁用；正常流不变。
- **A1（搜索路径 DDL）— 文档化既有边界，无代码变更**：`_ensure_search_table` 幂等
  `CREATE VIRTUAL TABLE IF NOT EXISTS`，与 GET /search、save 路径共享，无内容变更，
  正常 API 流不可达；记录于提交信息 + 既有 TR-20260814-007 §3 P2-3。

## Gates（本人执行，精确数字）

answer 7/7；全仓 409/409 + 5 skipped；ruff format/check pass（88 文件）；strict mypy
31 文件；validator PASS（含 secret scan）；Web answer 1/1；`pnpm check` 38 tests + tsc +
eslint 0 warnings。

## Core properties — no regression

只读回答端点；失败关闭 503/422/404/200-no-matches；密钥卫生；检索编号/反向回退/
确定性；Web 可点击来源。

## Conclusion

PASS。`correlated_review`（机器证明、同源披露），非 owner 接受。
