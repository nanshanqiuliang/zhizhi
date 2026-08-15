# AI QA attempt 002 — AI draft API + Web accept/reject (superseding, WORK-2026-026 slice 3)

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: ai_qa_auditor
decision: pass
reviewed_commit: d47ce88a3221d2edc1d1a5ff64025d771b0ebe27
supersedes: attempt 001 (dfbcc30, FAIL 1 P1 + 3 P2)
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

**PASS** — 0 P0 / 0 P1。这是对修复提交 `d47ce88` 的职责隔离只读机器审查（超越 attempt 001）。
P1（PDF 漂移守卫恒真）已闭合；P2-1（启动崩溃）与 P2-3（过期 docstring）已闭合；P2-2
（evidence 信任注记）保持为文档化无代码变更边界。最终残余风险接受归 workspace owner。

## Finding closures

| # | Severity | Status | Proof |
|---|----------|--------|-------|
| P1 | drift 守卫恒真 | CLOSED | 修复前（`git show dfbcc30`）`parsed_hash = str(row[1])` 为 `_check_drift` 再读的同一列，恒真；修复后取 `resource_segment` 的 parse-time `content_hash` 传入（对齐 `get_page_text`）。动态：同一变异脚本在 dfbcc30 worktree 上 NO_RAISE（返回 129604 字符），在 HEAD 上 RAISED `source_changed`。回归测试 `test_read_resource_text_pdf_drift_detected` 通过。 |
| P2-1 | generator 启动崩溃 | CLOSED | config 加载 + adapter 接线包进 `try/except (OSError, ValueError, KeyError, TypeError, RepositoryValidationError): return None`。动态：`DEEPSEEK_API_KEY=sk-test` + 临时副本坏配置（repo 配置未动）→ 畸形 YAML/模式非法/缺文件/无 key 均返回 None；完好配置正对照返回 callable。 |
| P2-3 | 过期 docstring | CLOSED | 两测试文件模块 docstring 由红灯改为绿灯描述。 |
| P2-2 | evidence 信任注记 | 边界 | 无代码变更；上游 `build_draft_patch` 已强制 evidence，user patch 契约合法允许空 evidence。 |

## Gates（本人执行，精确数字）

| # | Command | Result |
|---|---------|--------|
| 1 | `pytest tests/integration/test_ai_draft_api.py tests/integration/test_resource_text.py -q` | 9 passed（5 api + 4 resource_text，含漂移回归） |
| 2 | `pytest -q` | 395 passed, 5 skipped |
| 3 | `ruff format --check packages scripts tests apps` + `ruff check .` | 85 files formatted / all passed |
| 4 | `mypy --strict packages/... apps/api` | Success: 30 files |
| 5 | `python -m scripts.validate_repository` | PASS（含 secret scan） |
| 6 | Web draft test + `pnpm check` | 3 passed；35 passed（9 files）+ tsc + eslint 0 warnings |

## Core-loop regression — none

生成只读（端点以 `preview_graph_patch(...).status == requires_confirmation` 校验、
`confirmed=False`、无 DB 写）；接受仅经提交门（持久概念 `origin=user`/`review_state=accepted`/
`confidence=null`/evidence 保留）；503 `ai_not_available` 失败关闭保持；domain
`build_draft_patch`（origin=ai/proposed + confidence）不变；无密钥落盘（`git grep 'sk-...'` 0 命中，
key 仅 env）。

## Conclusion

PASS。`correlated_review`（机器证明、同源披露），非 owner 接受。
