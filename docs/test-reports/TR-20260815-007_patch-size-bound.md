# TR-20260815-007：GraphPatch 操作数上限放宽验证（WORK-2026-046 / maxitems 修复）

> 本报告密封 `f8d673c`（HEAD `bc08d8f`）的 WORK-2026-046：`GraphPatch.operations.maxItems`
> 100 → 5000（canonical 契约 + 生成产物；向后兼容、schema_version 不变、上限仍强制）。
> 它证明：一次全库思维导图生成（≤40 块、多概念/块）的草案不再被 100 操作上限误伤
> （契约 150 操作接受、API 全库 240 操作草案 200）；越界仍 fail-closed
> （上限+1 拒绝 `maxItems`）；冻结 exe 已内嵌 5000 上限（120 操作补丁接受并提交、
> 5001 操作拒绝）；全部门禁全绿。

```yaml
status: passed
test_level: unit_integration_contract_repository_e2e
owner: ai_qa_auditor
related_ids: [WORK-2026-046, WORK-2026-043, WORK-2026-044, REQ-2026-001, NFR-2026-001]
build_id: f8d673c
started_at: 2026-08-16T03:01:00+08:00
finished_at: 2026-08-16T03:12:00+08:00
supersedes: null
```

## 目的与门槛

- 证明红灯真值：在隔离 worktree 将契约还原为 `maxItems=100` 后，两个回归测试
  （契约 150 操作接受、API 全库 240 操作草案 200）确实失败且 `rule=maxItems`；
  还原为 5000 后通过（确认测试有效、修复有效）。
- 证明放宽后行为正确：5000 操作恰好接受；5001 拒绝（`maxItems`）；0 操作拒绝
  （`minItems`）；≤100 操作旧补丁仍接受（向后兼容）。
- 证明语义护栏未退化：重复 op_id / 重复操作 target / user 起源概念非 null 置信度
  仍被拒绝（`duplicate_operation_id` / `duplicate_operation_target` /
  `user_confidence_must_be_null`）。
- 证明 API fail-closed 不变：全库无资源 422 `no_resources`；无生成器 503
  `ai_not_available`；单资源模式仍工作。
- 证明生成产物一致：Python 镜像与 canonical JSON 逐字段相等且 `maxItems=5000`；
  TS 产物无漂移（`generate.mjs --check` + `tsc` 通过）。
- 证明冻结 exe 内嵌修复：health 200、建工作区 200、无 key `/ai-draft` 503
  （fail-closed）、120 操作补丁接受并提交、5001 操作拒绝 `maxItems`、进程终止后
  端口释放。
- 证明全仓门全绿（含新增证据文件后复跑）。

## 方法与结果

| Test ID | 场景 | Actual | Result |
|---|---|---|---|
| TC-RED-001 | worktree 还原 cap=100：契约 150 操作 | `ContractValidationError: graph_patch at operations violates maxItems` | PASS（红灯如声明） |
| TC-RED-002 | worktree 还原 cap=100：API 全库 240 操作 | 422 `{"code":"draft_invalid","rule":"maxItems","contract":"graph_patch","path":"operations"}` | PASS（红灯如声明） |
| TC-RED-003 | worktree 还原 cap=5000：两回归测试 | 契约 2 passed + API 1 passed | PASS（绿灯如声明） |
| TC-PATCH-BOUND-001 | 契约 150 操作补丁 | `validate_contract("graph_patch", ...)` 通过 | PASS |
| TC-PATCH-BOUND-002 | 契约 5001 操作补丁 | 拒绝，`rule == "maxItems"` | PASS |
| TC-PATCH-BOUND-003 | API 全库 240 操作草案 | 200 + `requires_confirmation`（240 操作） | PASS |
| TC-PATCH-BOUND-004 | 全部门禁 | pytest 469/469 + 5 skipped；ruff；mypy 40；validator；Web 53/53；e2e 18/18；drift 无 | PASS |
| TC-PATCH-BOUND-005 | 冻结 exe 冒烟 | exe 探针 9/9（含 120 操作提交、5001 拒绝） | PASS |
| QA-001 | 职责隔离对抗审查 | 红灯重跑 + 15/15 探针 + exe 9/9 探针 | PASS（0 P0/P1，P3 观察 5 项） |

## 对抗探针明细（15/15 PASS）

契约层（`validate_contract("graph_patch", ...)` / `preview_graph_patch`）：

| Probe | 场景 | 结果 |
|---|---|---|
| P-C-001 | 5000 操作恰好接受 | PASS（等于上限） |
| P-C-002 | 5001 操作拒绝 | PASS（`rule=maxItems`） |
| P-C-003 | 0 操作拒绝 | PASS（`rule=minItems`） |
| P-C-004 | 重复 op_id 拒绝 | PASS（`duplicate_operation_id`） |
| P-C-005 | 重复操作 target 拒绝 | PASS（`duplicate_operation_target`） |
| P-C-006 | 150 操作接受（用户回归场景） | PASS |
| P-C-007 | 2500 操作接受（全库现实最坏情况） | PASS |
| P-C-008 | 100 操作（旧上限内）仍接受 | PASS（向后兼容） |
| P-C-009 | user 起源概念 confidence=0.9 拒绝 | PASS（`user_confidence_must_be_null`） |

API 层（TestClient + 注入生成器，独立临时数据目录）：

| Probe | 场景 | 结果 |
|---|---|---|
| P-A-001 | 全库 240 操作草案 | PASS（200 + `requires_confirmation`） |
| P-A-002 | 全库无资源 | PASS（422 `draft_invalid/no_resources`） |
| P-A-003 | 无 workspace 生成器 | PASS（503 `ai_not_available`，fail-closed） |
| P-A-004 | 单资源模式（resource_id 给定） | PASS（200 + `requires_confirmation`） |

生成产物一致性：

| Probe | 场景 | 结果 |
|---|---|---|
| P-G-001 | 生成 Python 镜像 == canonical JSON（逐字段）；operations.maxItems==5000 | PASS |
| P-G-002 | contracts-ts `graph-v1.ts` 无漂移（schema_version=1；drift 门 exit 0） | PASS |

## 冻结 exe 探针（9/9 PASS）

`dist/zhizhi/zhizhi.exe --no-window --port <空闲> --data-root <临时>`：

| Probe | 场景 | 结果 |
|---|---|---|
| EXE-000 | 冻结产物存在 | PASS（8,632,729 字节，重建于 3:01:14，晚于 f8d673c 3:00:26） |
| EXE-001 | GET /api/health | PASS（200 `{"status":"ok"}`） |
| EXE-002 | POST /api/workspaces | PASS（200 + id） |
| EXE-003/003b | POST /ai-draft（全库模式 / 单资源模式，无 key） | PASS（均 503 `ai_not_available`，fail-closed） |
| EXE-004 | 120 操作补丁（旧上限 100 之外） | PASS（200 applied + change_id + revision_no=1） |
| EXE-005 | 5001 操作补丁 | PASS（422 `patch_invalid` / `rule=maxItems`） |
| EXE-006 | 120 概念持久化（基线 1 + 120） | PASS（concepts=121） |
| EXE-007 | 终止进程 + 端口释放 | PASS（in_use=False） |

## 门禁汇总

- `scripts.validate_repository`：PASS（含 secret scan；证据文件加入后复跑仍 PASS）
- `ruff format --check packages scripts tests apps`：116 文件 OK；`ruff check .`：clean
  （证据文件加入后复跑仍 clean）
- `mypy scripts`：16 文件 OK；`mypy --strict`（packages+apps）：40 文件 OK
- `pytest`：**469 passed + 5 skipped**（live DeepSeek 需 `RUN_LIVE_LLM_TESTS=1` +
  `DEEPSEEK_API_KEY`，本环境无 key → 如实 skipped）
- `pnpm install --frozen-lockfile` / `pnpm peers check`：OK
- `pnpm check`：**53/53**（14 files）；`pnpm build`：OK（chunk 体积告警为既有提示，与本变更无关）
- 契约 drift：`pnpm --filter @knowledge-tree/contracts-ts check`
  （`generate.mjs --check` + `tsc --noEmit`）exit 0（无漂移）
- 桌面 e2e：**18/18**

## 发现（分级与建议）

| Sev | 位置 | Finding | 建议 |
|---|---|---|---|
| P3 | 契约测试 | `test_graph_patch_enforces_operation_bound` 从 canonical JSON 读取上限；若生成产物漂移（如未重新生成），该测试仍可能通过（5001 > 漂移后的更低上限同样触发 maxItems），不敏感于产物漂移 | 建议测试从运行时产物 `graph_contract_document()` 读取上限，或在测试中同时断言 canonical 与生成产物一致（现由 drift 门 + P-G-001 兜底） |
| P3 | 集成测试 | `test_ai_draft_workspace_mode_no_resources_returns_422` 只断言 `code==draft_invalid`，未钉死 `rule==no_resources`（P-A-002 已确认实际为 no_resources） | 建议补断言 `rule == "no_resources"` 以提高回归精度 |
| P3 | 文档/工程 | DoD 文档同步（`docs/ENGINEERING_PLAN.md`、`docs/TRACEABILITY_MATRIX.md`、`docs/work-items/README.md` 含 WORK-2026-046 行）存在于工作树但**未提交**（3:02:05–3:02:21 由实现侧写入，非 QA 所为；QA 未修改、未提交） | 由实现者/owner 在封存时一并提交；QA 遵守「不提交任何 git 变更」 |
| P3 | 冻结产物 | 任务简报称 exe 约 18MB，实际 `zhizhi.exe` 8,632,729 字节（约 8.2MB）；重建时间 3:01:14 晚于修复提交，且 EXE-004/005 直接证明内嵌 5000 上限 | 记录实际尺寸，后续简报以实测为准 |
| P3 | 性能/容量 | 5000 操作单事务补丁（约数 MB JSON）未做基准测量；工作项已声明 SQLite 顺序应用、本地单用户可接受 | 如需，可另开性能项测量 5000 操作提交耗时（不在本变更范围） |

## 环境与披露

- 环境：Windows；Python 3.12.6；uv 0.12.3；Node 24.14.1；pnpm 11.19.0；分支
  `feature/WORK-2026-046-patch-size-bound`（HEAD `bc08d8f`）；评审提交 `f8d673c`。
- live DeepSeek 未执行（无 key，5 个 live 用例如实 skipped）；AI 路径经注入生成器
  验证，冻结 exe 无 key 503 fail-closed 已验证。
- **correlation 披露**：本报告为职责隔离的机器审查（`correlated_review`）——
  QA 与实现者为独立角色（隔离运行/提示词/上下文），但可能为同一模型/供应商；
  `human_signature=false`、`owner_acceptance=false`；本报告不构成人类签名，最终
  残余风险接受属于 workspace owner。QA 未修改任何产品代码。

## 证据

- `evidence/TR-20260815-007/`：QA attempt、manifest、checksums、commands、
  environment、gate-summary、探针脚本与原始输出（probes_graph_patch_cap.py /
  probe_frozen_exe.py / probes-output.log / exe-probe-output.log）。
- 本报告 `docs/test-reports/TR-20260815-007_patch-size-bound.md`。
