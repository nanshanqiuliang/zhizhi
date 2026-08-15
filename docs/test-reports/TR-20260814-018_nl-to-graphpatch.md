# TR-20260814-018：自然语言转 GraphPatch 验证（WORK-2026-029，第 9 步切片 2）

> 本报告密封 `9abd33989fa2d94b9ca9f5282a7d28816f28917d` 的
> WORK-2026-029（第 9 步切片 2：`build_command_patch` + `POST /interpret` +
> Web 指令预览/接受/拒绝）。它证明用户可用自然语言下达图修改指令（锁定/先修关系），
> AI 解释为 `proposed` GraphPatch，经预览确认后由既有提交门写入、可撤销；解释只读、
> 未知概念/操作/维度失败关闭。

```yaml
status: passed
test_level: integration_component_repository_e2e_live
owner: ai_qa_auditor
related_ids: [WORK-2026-029, WORK-2026-008, WORK-2026-005, WORK-2026-019, WORK-2026-022, WORK-2026-028, REQ-2026-006, NFR-2026-001, NFR-2026-006, NFR-2026-007, NFR-2026-008]
build_id: 9abd33989fa2d94b9ca9f5282a7d28816f28917d
started_at: 2026-08-15T05:45:00+08:00
finished_at: 2026-08-15T06:30:00+08:00
supersedes: null
```

## 目的与门槛

- 证明 `build_command_patch` 把 label 引用操作确定性映射为合法 GraphPatch v1
  （`set_lock`/`create_edge`，精确 revision 绑定，actor=user、proposal-only）。
- 证明未知 label/op/dimension/edge_type/非 dict 操作以 `CommandError` 稳定拒绝，错误
  details 仅标识（`*_hash`，不回显 LLM 文本）。
- 证明 `POST /interpret` 注入式 generator 返回 `{summary, patch}`；无 generator 503；
  空/超长/畸形输出 422；只读不写库；接受经提交门写入并可撤销。
- 证明 Web 指令输入 → 预览 → 接受/拒绝；`ai_not_available` → "AI 未连接"。

## 方法与结果

| Test ID | 场景 | Actual | Result |
|---|---|---|---|
| TC-CMD-001 | `build_command_patch` 映射 | set_lock/create_edge + 预览 + 非零 revision 绑定 | PASS |
| TC-CMD-002 | 失败关闭 | 未知/空 label、未知 op、非法 dimension/edge_type、非 dict op | PASS |
| TC-CMD-003 | `/interpret` 端点 | fake generator + 503/422/404 | PASS |
| TC-CMD-004 | Web 命令/预览/接受/拒绝 | 命令→预览→接受经提交门→拒绝丢弃；503 | PASS |
| TC-REPO-001 | 完整门 | pytest 421/421 + 5 skipped；Ruff；strict mypy（33）；validator | PASS |
| TC-REPO-002 | Web/构建门 | Web 41/41；pnpm check/build | PASS |
| QA-001/002 | 职责隔离对抗审查 | attempt001 PASS（0 P0/P1，3 P2）→ 修复 `9a255d2`+`9abd339` → attempt002 PASS（0 P0/P1） | PASS |

职责隔离 QA：attempt 001 对冻结 `b4fde38` 返回 **PASS**（0 P0/P1；3 个非阻塞 P2：
错误详情回显 label、回归覆盖缺口、Web 覆盖缺口）；修复 `9a255d2`（label/dimension/
edge_type/op 改发 `*_hash` + 补 6 个 Python 回归 + 3 个 Web 回归）与 `9abd339`（op_hash
一致性）后 attempt 002 返回 **PASS**（0 P0/P1）。QA 为只读机器审查；`correlated_review`，
非 owner 接受。

## 证据

- `evidence/TR-20260814-018/`：attempt 001/002 报告、`manifest.json`、`checksums.sha256`、
  `commands.txt`、`environment.json`、`gate-summary.txt`。
- live e2e（orchestrator，owner key env-only）：「连续以极限为前提，并锁定极限的内容」
  → `create_edge` + `set_lock`，接受后边 + 内容锁落库。
- 全仓 pytest 421/421 + 5 skipped；validator PASS；Ruff/strict mypy 全绿；Web 41/41。

## 遗留边界

- 指令仅支持 `set_lock`/`create_edge`（`create_concept`/`update_concept`/`delete_*` 为后续切片，
  涉及证据要求）；向量检索、增量重建、AI 修改历史为第 9 步后续切片。
- `LLMProviderError` 502 body 传播 provider `error.details`（既有通道，与命令无关）。
- `correlated_review`：机器证明、同源披露；最终残余风险接受归 workspace owner。
