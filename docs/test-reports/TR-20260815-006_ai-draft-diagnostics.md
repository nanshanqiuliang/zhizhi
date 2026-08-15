# TR-20260815-006：草案生成可诊断化与鲁棒性验证（WORK-2026-044）

> 本报告密封 `0abe9e9` 的 WORK-2026-044（错误码 rule 显示、单资源 40 块上限、fail-soft 抽取
> 容错）。它证明：Web 草案/回答/指令失败提示显示精确 `code/rule`；长资料生成受 40 块上限约束；
> 单块畸形模型输出被跳过、其余继续，传输/鉴权错误仍 502。超集修复 `33ba11a` 关闭 4 个 P2。

```yaml
status: passed
test_level: unit_integration_component_repository_e2e
owner: ai_qa_auditor
related_ids: [WORK-2026-044, WORK-2026-009, WORK-2026-026, WORK-2026-043, REQ-2026-001, NFR-2026-001]
build_id: 0abe9e9
started_at: 2026-08-16T00:30:00+08:00
finished_at: 2026-08-16T00:58:00+08:00
supersedes: null
```

## 目的与门槛

- 证明 Web 错误消息显示 `code/rule`（如 `draft_invalid/no_new_concepts`）。
- 证明单资源与全库生成均限 40 块（长资料截断，成本/耗时可控）。
- 证明 fail-soft：单块 `DraftExtractionError` 跳过、其余保留；`LLMProviderError` 不吞（502）。
- 证明全失败 → 422 `draft_invalid/no_new_concepts`（一致、清晰）。
- 证明全仓门全绿。

## 方法与结果

| Test ID | 场景 | Actual | Result |
|---|---|---|---|
| TC-DIAG-001 | generateDraft 422 带 rule | 错误消息含 `draft_invalid/no_new_concepts` | PASS |
| TC-DIAG-002 | 草案失败提示显示 rule | 界面含 rule 文本（App.draft 用例） | PASS |
| TC-DIAG-003 | max_chunks 截断 | extractor 调用 ≤40（计数断言） | PASS |
| TC-DIAG-004 | fail-soft 跳过坏块 | 其余概念保留；LLMProviderError 传播 | PASS |
| TC-REPO-001 | 完整门 | pytest 466/466 + 5 skipped；ruff；mypy 40；validator；Web 52/52 | PASS |
| QA-001 | 职责隔离对抗审查 | 红灯重跑 + 16/17 Python + 8/8 TS 探针 + 冻结 e2e | PASS（0 P0/P1，4 P2 已修） |

职责隔离 QA 对 `0abe9e9` 返回 **PASS**（0 P0/P1；4 个 P2 由 `33ba11a` 修复）。QA 在隔离
worktree 重跑 044 红灯真值，执行 16/17 Python + 8/8 TS 对抗探针（rule 组合、块数截断、坏块
跳过、LLMProviderError→502、非 JSON 容错），并验证冻结 exe 内嵌修复版 Web 构建、无 key 503。

## 证据

- `evidence/TR-20260815-006/`：QA attempt 001、manifest、checksums、commands、environment、
  gate-summary。
- 本报告 `docs/test-reports/TR-20260815-006_ai-draft-diagnostics.md`。

职责隔离 QA 为 `correlated_review`（机器审查），非人类签名、非 owner 接受；最终残余风险接受属于
workspace owner。
