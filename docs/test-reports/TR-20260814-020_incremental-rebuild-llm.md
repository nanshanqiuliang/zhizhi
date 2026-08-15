# TR-20260814-020：增量重建 LLM 接线验证（WORK-2026-031，第 9 步切片 3b）

> 本报告密封 `f0459f436bd2fe9337ffe896aaed2e8fa649e4b6` 的
> WORK-2026-031（第 9 步切片 3b：`build_incremental_ai_draft` + generator 改增量路径 +
> `/ai-draft` 增量）。它证明「生成草案」对非空图自动增量：既有概念去重不重复创建、
> 跨图关系可指向既有概念、仅新概念创建，经提交门确认后写入。

```yaml
status: passed
test_level: integration_contract_repository_e2e_live
owner: ai_qa_auditor
related_ids: [WORK-2026-031, WORK-2026-030, WORK-2026-009, WORK-2026-026, REQ-2026-006, NFR-2026-001, NFR-2026-006, NFR-2026-007, NFR-2026-008]
build_id: f0459f436bd2fe9337ffe896aaed2e8fa649e4b6
started_at: 2026-08-15T07:45:00+08:00
finished_at: 2026-08-15T08:30:00+08:00
supersedes: null
```

## 目的与门槛

- 证明 `build_incremental_ai_draft` 抽取新概念后对既有 label 去重、以"既有占位 + 新概念"并集
  让关系提供器跨图提议、过滤既有↔既有关系。
- 证明 generator 改增量路径后 `/ai-draft` 对非空图只创建新概念、跨图关系端点指向既有 id。
- 证明空图退化为全量、确定性、输入不可变、密钥 env-only。

## 方法与结果

| Test ID | 场景 | Actual | Result |
|---|---|---|---|
| TC-INCRB-001 | 离线去重 + 过滤 | 冲突 candidate 丢弃、既有↔既有关系丢弃、占位空 evidence | PASS |
| TC-INCRB-002 | generator 端到端 | 非空图无重复 create + 预览 requires_confirmation | PASS |
| TC-INCRB-003 | 空图退化 + fail-closed | 空图 ≡ 全量；无 key → generator None | PASS |
| TC-REPO-001 | 完整门 | pytest 430/430 + 5 skipped；Ruff；strict mypy（33）；validator | PASS |
| QA-001/002 | 职责隔离对抗审查 | attempt001 PASS（0 P0/P1，4 P2）→ 修复 `f0459f4` → attempt002 PASS（0 P0/P1） | PASS |

职责隔离 QA：attempt 001 对冻结 `d012660` 返回 **PASS**（0 P0/P1；4 个非阻塞 P2 覆盖缺口）；
修复 `f0459f4`（测试强化，无生产代码变更）后 attempt 002 返回 **PASS**（0 P0/P1）。
QA 为只读机器审查；`correlated_review`，非 owner 接受。

## 证据

- `evidence/TR-20260814-020/`：attempt 001/002 报告、`manifest.json`、`checksums.sha256`、
  `commands.txt`、`environment.json`、`gate-summary.txt`。
- live e2e（orchestrator，owner key env-only）：非空图（极限）→ 新概念 [导数, 连续]、
  关系 极限→连续/极限→导数/连续→导数、create_concept [导数, 连续]（极限未重建）。
- 全仓 pytest 430/430 + 5 skipped；validator PASS；Ruff/strict mypy 全绿。

## 遗留边界

- `update_concept`/`update_edge`（证据增强/既有概念更新）为后续；向量检索受 Embedding
  provider 未决阻塞；AI 修改历史待后续。
- `correlated_review`：机器证明、同源披露；最终残余风险接受归 workspace owner。
