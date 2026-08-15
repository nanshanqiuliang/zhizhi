# TR-20260814-017：带来源问答验证（WORK-2026-028，第 9 步切片 1）

> 本报告密封 `9e06ebf04c7ddfb0badf5911cef9f4af692e5fb7` 的
> WORK-2026-028（第 9 步切片 1：`build_answer_context` + `POST /answer` +
> Web 提问/回答/来源跳转）。它证明用户可向本地知识提问，得到基于 FTS5 检索命中
> 的带来源回答、来源可点回概念节点，且回答只读、失败关闭、无 Key 时 503。

```yaml
status: passed
test_level: integration_component_repository_e2e_live
owner: ai_qa_auditor
related_ids: [WORK-2026-028, WORK-2026-008, WORK-2026-015, REQ-2026-006, NFR-2026-006, NFR-2026-007, NFR-2026-008]
build_id: 9e06ebf04c7ddfb0badf5911cef9f4af692e5fb7
started_at: 2026-08-15T04:45:00+08:00
finished_at: 2026-08-15T05:30:00+08:00
supersedes: null
```

## 目的与门槛

- 证明 `build_answer_context` 用 FTS5 正向命中 + 反向子串回退把问题映射为带引用号
  `[n]` 的上下文 + 概念来源，确定性、无网络。
- 证明 `POST /answer` 注入式 answer generator 返回 `{answer, sources}`；无 generator
  503 `ai_not_available`；空/超长问题 422；无命中 200 `{note:"no_matches"}`；只读不写库。
- 证明 Web 提问框 → 带来源回答面板，来源可点回概念节点；`ai_not_available` → "AI 未连接"。

## 方法与结果

| Test ID | 场景 | Actual | Result |
|---|---|---|---|
| TC-ANSWER-001 | `build_answer_context` | FTS5 命中 + 反向回退 + 引用号 + sources；确定性 | PASS |
| TC-ANSWER-002 | `/answer` 端点 | fake generator 回答 + 失败关闭（503/422/404/200-no-matches） | PASS |
| TC-ANSWER-003 | 回答解析 | 离线确定性 + 来源绑定 + 无幻觉路径 | PASS |
| TC-ANSWER-004 | Web 提问/回答/来源跳转 | 提问→回答→点来源 | PASS |
| TC-REPO-001 | 完整门 | pytest 409/409 + 5 skipped；Ruff；strict mypy（31）；validator | PASS |
| TC-REPO-002 | Web/构建门 | Web 38/38；pnpm check/build | PASS |
| QA-001/002 | 职责隔离对抗审查 | attempt001 PASS（0 P0/P1，3 P2）→ 修复 `9e06ebf` → attempt002 PASS（0 P0/P1） | PASS |

职责隔离 QA：attempt 001 对冻结 `47d6c6f` 返回 **PASS**（0 P0/P1；3 个非阻塞 P2：
搜索路径 DDL 只读破例、问题长度契约漂移、Web 双击竞态）；修复 `9e06ebf`（问题上限
对齐 100 + 回归、`handleAsk` 加 asking 守卫）后 attempt 002 返回 **PASS**（0 P0/P1；
A1 保持文档化既有边界）。QA 为只读机器审查；`correlated_review`，非 owner 接受。

## 证据

- `evidence/TR-20260814-017/`：attempt 001/002 报告、`manifest.json`、`checksums.sha256`、
  `commands.txt`、`environment.json`、`gate-summary.txt`。
- live e2e（orchestrator，owner key env-only）：「什么是极限」→ 回答并引用 `[1] 极限`。
- 全仓 pytest 409/409 + 5 skipped；validator PASS；Ruff/strict mypy 全绿；Web 38/38。

## 遗留边界

- P2/A1：搜索路径 `_ensure_search_table` 在 migrated-but-never-saved DB 上执行幂等
  `CREATE VIRTUAL TABLE IF NOT EXISTS`（既有共享代码，GET /search 同路径，无内容变更，
  正常 API 流不可达）——文档化边界。
- 来源为 FTS5 检索命中，明确不冒充逐句 grounding；向量检索为第 9 步后续切片。
- `correlated_review`：机器证明、同源披露；最终残余风险接受归 workspace owner。
