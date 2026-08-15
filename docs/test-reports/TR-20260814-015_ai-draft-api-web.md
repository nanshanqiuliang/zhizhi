# TR-20260814-015：AI 草案 API 端点与 Web 接受/拒绝验证（WORK-2026-026 切片 3）

> 本报告密封 `d47ce88a3221d2edc1d1a5ff64025d771b0ebe27` 的
> WORK-2026-026（第 8 步切片 3：`read_resource_text` + `POST /ai-draft` +
> DeepSeek 组合根 + Web 生成/预览/接受/拒绝）。它证明用户可见的
> "导入资料 → 生成 AI 草案 → 预览 → 接受写入"闭环打通，草案只经提交门落库、
> 不覆盖锁定项、无 Key 时失败关闭。

```yaml
status: passed
test_level: contract_integration_component_repository_e2e_live
owner: ai_qa_auditor
related_ids: [WORK-2026-026, WORK-2026-009, WORK-2026-005, WORK-2026-008, WORK-2026-014, WORK-2026-016, WORK-2026-017, WORK-2026-019, WORK-2026-022, REQ-2026-006, NFR-2026-001, NFR-2026-006, NFR-2026-007, NFR-2026-008, TR-20260814-014]
build_id: d47ce88a3221d2edc1d1a5ff64025d771b0ebe27
started_at: 2026-08-15T03:00:00+08:00
finished_at: 2026-08-15T03:45:00+08:00
supersedes: null
```

## 目的与门槛

- 证明 `read_resource_text`（MD/TXT 原文、PDF 已解析按页拼接、漂移/未解析/未知
  mime 失败关闭）。
- 证明 `POST /api/workspaces/{id}/ai-draft` 以注入式 generator 生成不可信草案 +
  `proposed`（`confirmed=false`）patch，无 generator 503 `ai_not_available`，返回前以
  本地 user 预览必须 `requires_confirmation` 失败关闭，绝不写库。
- 证明接受路径把 patch 置 `confirmed=true` 经既有 `POST graph/patches` 提交门写入
  （`origin=user`/`review_state=accepted`/`confidence=null`、保留 `evidence_ids`），拒绝不写库。
- 证明 Web 生成/预览/接受/拒绝与「AI 未连接」边界。

## 方法与结果

| Test ID | 场景 | Actual | Result |
|---|---|---|---|
| TC-AIDRAFT-API-001 | 端点生成 + 接受写入 | fake generator 草案 → 提交门写入 user/accepted/evidence 概念/边 | PASS |
| TC-AIDRAFT-API-002 | 端点失败关闭 | 无 generator 503 / 缺 id 422 / 资源缺失 404 | PASS |
| TC-AIDRAFT-API-003 | `read_resource_text` | MD/TXT/PDF/未解析/漂移/缺资源 | PASS |
| TC-AIDRAFT-WEB-001 | 草案预览 + 接受/拒绝 | 生成→预览→接受经提交门→拒绝丢弃；`ai_not_available`→「AI 未连接」 | PASS |
| TC-REPO-001 | 完整门 | pytest 395/395 + 5 skipped；Ruff；strict mypy（30）；validator | PASS |
| TC-REPO-002 | Web/构建门 | Web 35/35；pnpm check/build | PASS |
| QA-001/002 | 职责隔离对抗审查 | attempt001 FAIL（1 P1 + 3 P2）→ 修复 `d47ce88` → attempt002 PASS（0 P0/P1） | PASS |

职责隔离 QA：attempt 001 对冻结 `dfbcc30` 返回 **FAIL**（1 P1：`read_resource_text`
PDF 漂移守卫恒真，`source_changed` 不可达 + 3 P2）；修复 `d47ce88`（取 segment
parse-time `content_hash` 漂移校验 + 回归、config 加载失败关闭、docstring 修正）后
attempt 002 返回 **PASS**（0 P0/P1；P2-2 evidence 信任注记记录为无代码变更边界）。
QA 为只读机器审查；`correlated_review`，非 owner 接受。

## 证据

- `evidence/TR-20260814-015/`：attempt 001（FAIL）/002（PASS）报告、`manifest.json`、
  `checksums.sha256`、`commands.txt`、`environment.json`、`gate-summary.txt`。
- live e2e（orchestrator，owner key env-only）：导入 calculus.md → `/ai-draft` 抽取
  极限/连续/导数 + 3 prerequisite_of → 接受经提交门写入（user/accepted/evidence）。
- 全仓 pytest 395/395 + 5 skipped；validator PASS；Ruff/strict mypy 全绿；Web 35/35。

## 遗留边界

- P2：端点重新作者化后不再独立校验 evidence（上游 `build_draft_patch` 已强制，
  user patch 契约合法允许空 evidence）；草案 evidence 为合成 UUIDv7 来源引用，不落
  anchor 表——「点来源跳回原文」为后续切片。
- `relation_validate` 思考模式延迟较高（~57s）为原型边界。
- `correlated_review`：机器证明、同源披露；最终残余风险接受归 workspace owner。
