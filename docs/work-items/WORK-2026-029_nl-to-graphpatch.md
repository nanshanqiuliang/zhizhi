# WORK-2026-029：自然语言转 GraphPatch（第 9 步切片 2）

```yaml
status: ready
type: feature
owner: Codex (command + api + web role)
reviewers: [ai_qa_auditor, workspace_owner]
related_ids: [WORK-2026-008, WORK-2026-005, WORK-2026-019, WORK-2026-022, WORK-2026-028, REQ-2026-006, NFR-2026-001, NFR-2026-006, NFR-2026-007, NFR-2026-008]
target_stage: "阶段 1 / 自然语言第 9 步切片 2（自然语言转 GraphPatch）"
risk: high
created_at: 2026-08-15T05:45:00+08:00
updated_at: 2026-08-15T05:45:00+08:00
```

## 问题与结果

- 用户/工程问题：第 9 步切片 1 已实现"带来源问答"，但用户还不能用自然语言直接要求图修改（如"连续以极限为前提""锁定极限的内容"），让 AI 产出可预览、可确认、可撤销的 GraphPatch。这是第 9 步完成标志"对话产生的图修改可预览、确认、撤销"的核心。
- 期望结果：`POST /api/workspaces/{id}/interpret`（body `{command}`）——注入式 command generator（`command_interpret` task profile）把命令解释为操作列表（label 引用），服务端确定性 `build_command_patch` 把 label 映射为既有概念 id、生成 `proposed`（`requires_confirmation=true`、`confirmed=false`、actor=user）GraphPatch，返回 `{summary, patch}`；**不写库**；无 generator 503；未知概念/操作/维度失败关闭。Web 命令输入 → 预览（摘要 + 拟操作）→ 接受（`POST graph/patches` confirmed）或拒绝。
- 成功如何被观察：从失败测试启动；`build_command_patch` 确定性把 label 操作映射为合法 patch（经 `preview_graph_patch` 预览）；未知 label 拒绝；接受经提交门写入并可撤销；全仓门全绿。

## 范围

- In scope：
  - `packages/infrastructure/.../command.py`：`CommandError`（稳定错误，仅标识）；`build_command_patch(graph, operations, *, id_factory, reason)`——支持 `set_lock`（dimension content/position）、`create_edge`（edge_type 四类）；label→既有概念 id 严格映射（未知 label 拒绝）；生成 `create_edge` 的 edge（origin=user/review_state=accepted/confidence=null/evidence_ids=[]/revision_no=0）与 `set_lock`（expected_updated_revision_no=概念当前 revision）；返回 `proposed` patch。
  - `apps/api/command.py`：`CommandGenerator = Callable[[command, concepts], {summary, operations}]`；`build_deepseek_command_generator()`——`command_interpret` profile（thinking disabled，预算约束），严格 JSON 输出；config 失败关闭返回 None。
  - `apps/api/main.py`：`POST /api/workspaces/{id}/interpret`——注入式 `command_generator`，无 generator 503；body 校验；载图 → concepts → generator → `build_command_patch` → `preview_graph_patch`（user actor，必须 `requires_confirmation`）；返回 `{summary, patch}`。
  - `apps/web/src/api.ts` + `App.tsx`：`interpretCommand(command)`；命令输入 + 预览面板（摘要 + 操作列表）→ 接受/拒绝。
  - 测试：`tests/integration/test_command_api.py`（`build_command_patch` 确定性 + 端点 + 失败关闭，fake generator 无网络）+ Web `App.command.test.tsx`。
- Out of scope：`create_concept`/`update_concept`/`delete_*`（含证据要求，后续切片）；向量检索；增量重建；AI 修改历史；多轮对话上下文。
- 受影响模块/接口/数据：新增 `packages/infrastructure/.../command.py` 与 `apps/api/command.py`；扩展 `apps/api/main.py`、`apps/web`；无 canonical contract/migration/prompt 变更（复用 GraphPatch v1 + `command_interpret` profile）。
- 依赖和假设：WORK-2026-008（DeepSeek adapter + `command_interpret` profile）、WORK-2026-005/019/022（GraphPatch 提交门）、WORK-2026-028（问答切片）已验证；解释只读、仅用户确认后经提交门写入；命令/概念列表仅进 user 消息。

## 设计边界

- 领域/契约不变：生成的 patch 恒 `proposed` + `requires_confirmation=true` + `confirmed=false` + `actor=user`；接受复用既有 `POST graph/patches` 提交门（锁定/revision/确认门）。
- label→id 严格映射：操作里的 target/source/target 必须是当前图概念 label（casefold 精确匹配），未知即 `CommandError`，绝不猜测。
- `create_edge` 语义：`source` 是 `target` 的先修（`prerequisite_of`）；自环/重复边由提交门拒绝。
- 解释不写库、不改图；错误 details 仅标识（label/op/dimension），不含命令正文/推理。

## 风险影响

- 数据/schema/migration：无 migration；仅只读解释 + 无状态 patch 生成。
- 安全/隐私：命令与概念列表仅进 user 消息、不落盘/日志；密钥仅 env；错误仅标识。
- 并发/幂等/恢复：解释无副作用；接受走幂等 change_id 提交门；revision 冲突/锁定由门拒绝。
- 性能/容量/成本：单次 LLM 调用受 `command_interpret` 预算约束。
- 可观测性/诊断：稳定错误码 `ai_not_available`(503)、`command_invalid`/`command_label_unknown`(422)。
- 用户文档：用户手册补"自然语言命令 → 预览 → 接受/拒绝"；明确"仅锁定与先修关系命令"边界。

## 验收标准

- [ ] AC-1 (c1)：`build_command_patch` 确定性把 label 操作映射为合法 patch（`preview_graph_patch` 预览 `requires_confirmation`）；`set_lock` 的 `expected_updated_revision_no` = 概念当前 revision。
- [ ] AC-2 (c2)：未知 label/op/dimension 以 `CommandError` 稳定拒绝；patch 绝不半成品。
- [ ] AC-3 (c3)：`POST /interpret` 注入 fake generator 返回 `{summary, patch}`；无 generator 503；空/超长 command 422；未知 workspace 404。
- [ ] AC-4 (c4)：接受路径——把返回 patch 置 `confirmed=true` 后 `POST graph/patches` 写入（set_lock/create_edge），重载图可见、可撤销；拒绝不写库。
- [ ] AC-5 (c5)：Web 命令输入 → 预览摘要/操作 → 接受/拒绝；`ai_not_available` → "AI 未连接"。
- [ ] AC-6 (c6)：repository 门：validator、Ruff、scripts + strict package mypy（含 apps/api）、全仓 pytest、Web 全绿。
- [ ] 错误和恢复路径：解释失败/未知 label/无 generator 稳定失败关闭；解释不写库。
- [ ] 回滚/禁用方法：回退本工作项提交即回到无自然语言图修改能力；不设 `DEEPSEEK_API_KEY` 则端点 503；红灯与证据保留。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-CMD-001 | integration | `build_command_patch` | set_lock/create_edge 映射 + 预览 + revision | 待实现 |
| TC-CMD-002 | integration | 失败关闭 | 未知 label/op/dimension 拒绝 | 待实现 |
| TC-CMD-003 | integration | `/interpret` 端点 | fake generator + 503/422/404 | 待实现 |
| TC-CMD-004 | component | Web 命令/预览/接受/拒绝 | 命令→预览→接受经提交门 | 待实现 |
| TC-REPO-001 | repository | 全仓门 | validator/Ruff/mypy/pytest/Web | 待实现 |

## 交付物与关闭

- Commit/PR：分支 `feature/WORK-2026-009-ai-draft-pipeline`（第 9 步切片 2 沿用）；Ready → 红灯 → 实现 → QA。
- Contract/ADR/migration/prompt：无新 canonical contract/ADR/migration/prompt；复用 `command_interpret` profile 与 GraphPatch v1。
- Test Run：TC-CMD-001..004 + 全仓门。
- Release：无托管发布；真实 DeepSeek 调用仅 `DEEPSEEK_API_KEY` opt-in。
- 观察结果：自然语言图修改闭环（命令 → 预览 → 接受经提交门）；解释只读。
- 未完成项的新 ID：`create_concept`/`update_concept`/`delete_*` 命令、向量检索、增量重建、AI 修改历史。
