# TR-20260814-021：AI 修改历史验证（WORK-2026-032，第 9 步收尾）

> 本报告密封 `954a7c82c507f101107b1c235e67aa4f0b4ec19e` 的
> WORK-2026-032（第 9 步收尾：`GraphChangeRecord.source` + `apply_graph_patch(source)` +
> `/interpret/accept` + `GET /history` source + Web「AI」标记）。它证明版本历史面板可区分
> 哪些修改来自 AI（草案/指令）还是手动编辑，且历史记录向后兼容（旧记录无 source 视为 manual、
> digest 不变）。

```yaml
status: passed
test_level: unit_integration_component_repository
owner: ai_qa_auditor
related_ids: [WORK-2026-032, WORK-2026-011, WORK-2026-019, WORK-2026-022, WORK-2026-026, WORK-2026-027, WORK-2026-029, REQ-2026-006, NFR-2026-001]
build_id: 954a7c82c507f101107b1c235e67aa4f0b4ec19e
started_at: 2026-08-15T08:45:00+08:00
finished_at: 2026-08-15T09:30:00+08:00
supersedes: null
```

## 目的与门槛

- 证明历史记录携带 `source`（manual/ai_draft/ai_command），`accept_ai_draft`→ai_draft、
  `/interpret/accept`→ai_command、其余 manual。
- 证明 `GET /history` 返回 source；Web 版本历史面板对非 manual 来源显示「AI」标记。
- 证明向后兼容：旧记录（无 source）反序列化为 manual 且 digest 校验一致。
- 证明 digest 完整性：篡改 source 稳定拒绝。

## 方法与结果

| Test ID | 场景 | Actual | Result |
|---|---|---|---|
| TC-AIH-001 | record source 往返 + 向后兼容 | manual 无 source 键、ai_draft 含 source；旧格式→manual + digest 一致 | PASS |
| TC-AIH-002 | AI 接受标记 | accept_ai_draft→ai_draft；/interpret/accept→ai_command；缺省 manual | PASS |
| TC-AIH-003 | `/history` 返回 source | 每条含 source | PASS |
| TC-AIH-004 | Web 版本历史「AI」标记 | 非 manual 显示「AI」 | PASS |
| TC-REPO-001 | 完整门 | pytest 434/434 + 5 skipped；Ruff；strict mypy（33）；validator；Web 41/41 | PASS |
| QA-001 | 职责隔离对抗审查 | 32 探针全通过；红灯→绿灯真实 DB 迁移证明 | PASS（0 P0/P1，4 informational P2） |

职责隔离 QA 对冻结 `954a7c8` 返回 **PASS**（0 P0/P1；4 个 informational P2 均 Accept）。
对抗审查覆盖向后兼容（红灯代码写的 DB 在绿灯载入为 manual、digest 有效）、digest 完整性、
提交门/原子性、重放/撤销/重做、端点矩阵。QA 为只读机器审查；`correlated_review`，非 owner 接受。

## 证据

- `evidence/TR-20260814-021/`：attempt 001 报告、`manifest.json`、`checksums.sha256`、
  `commands.txt`、`environment.json`、`gate-summary.txt`。
- 全仓 pytest 434/434 + 5 skipped；validator PASS；Ruff/strict mypy 全绿；Web 41/41。本轮无网络。

## 遗留边界

- P2（informational，均 Accept）：`source` 为开放字符串标记（非 enum，内部使用）；`record_to_json`
  与领域 `_record_payload` 跨层重复 digest 逻辑（当前字节一致，仅漂移风险）；Web 徽标在陈旧后端
  缺 source 的边界下会误标（monorepo 前后端同发，api.ts 类型要求 source）。
- 第 9 步收尾：**向量检索为唯一 owner 未决项**（Embedding provider 未决）。
- `correlated_review`：机器证明、同源披露；最终残余风险接受归 workspace owner。
