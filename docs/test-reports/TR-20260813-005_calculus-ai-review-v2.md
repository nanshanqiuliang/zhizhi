# TR-20260813-005：微积分 AI 机器复核 v2 离线原型验证

> 本报告冻结实现提交 `ae834d9051553aa02a079e72ce2bf6bd8955c081` 的离线 prototype 结果，并追加保存所有失败/修复 attempt。它不改写 `TR-20260813-003/004`，也不是人类签字、workspace-owner 风险接受、发布批准或启用真实 Provider 的授权。

```yaml
status: passed
test_level: ai_eval
owner: ai_qa_auditor
related_ids: [WORK-2026-004, ADR-0015, REQ-2026-002, REQ-2026-003, REQ-2026-004, REQ-2026-005, NFR-2026-009, RISK-2026-010, RISK-2026-011, RISK-2026-012]
build_id: ae834d9051553aa02a079e72ce2bf6bd8955c081
started_at: 2026-08-13T23:10:29+08:00
finished_at: 2026-08-13T23:16:30+08:00
supersedes: null
```

## 目的、范围和门槛

- 对应需求/风险/缺陷：验证职责隔离 AI 学科/QA/裁决角色、content-addressed handoff、30/40/50 replay、证据/tool provenance、同源披露和失败关闭；关闭首轮 QA 的 3 个 P1、3 个 P2。
- In scope：`calculus-machine-review.v2`、mock role policy/harness、冻结 PDF 页文本 replay、schema/contract/security mutation、完整仓库门和隔离机器证明。
- Out of scope：真实 LLM/Web Search、产品数据库、商业使用、authenticated owner acceptance、产品级 `machine_reviewed`/`machine_verified`、52 页重新视觉复核。
- 通过定义：完整门全绿；学科 artifact 绑定；QA 对冻结修复提交给出 PASS；没有未关闭 P0/P1/P2；mock 仍稳定为 `inconclusive`/非产品可用。
- 失败定义：输入/证据/trace/policy/artifact 漂移被接受，角色共享 run/session，mock 被提升为产品状态，或 QA 发现未关闭 P0/P1/P2。
- 工程初值：30 concepts / 40 relations / 50 anchors，subject/QA 各 120 条 trace；这些是冻结数据集的精确规模，不外推为产品容量指标。

## 冻结环境

```text
Windows 11 x64 10.0.26200; Asia/Shanghai; zh-CN
Python 3.12.6; uv 0.12.3; Node 24.14.1; pnpm 11.19.0; Git 2.53.0
commit ae834d9051553aa02a079e72ce2bf6bd8955c081
dataset calculus-continuity-differentiability-v1 / 1.0.0-draft.2 / author_reviewed
review calculus-machine-review.v2; harness calculus-ai-review-harness.v2.mock.1
execution deterministic_mock_replay; machine_state inconclusive
network none; provider mock fixture only; no secret or external service
```

锁文件、policy、schema、实现、数据集和机器证明摘要见 evidence manifest/checksums。

## 方法

- 实现采用红灯回归：QA attempt 001 的 6 类缺陷先得到 8 个失败测试（8 failed / 31 passed），最小修复后 targeted suite 39/39。
- AI 学科角色在三次隔离 attempt 中依次记录争议、修复复核和 accept；QA attempt 001 保留 FAIL，不被覆盖；QA attempt 002 绑定 `ae834d9` 并显式 supersede 前一份 QA artifact。
- QA 复放 mock→controlled-live、空/篡改 trace、伪 owner、claim 替换、tool-policy 替换、adjudicator session 复用及额外组合。
- 完整命令见 `evidence/TR-20260813-005/commands.txt`。
- 已知限制：AI 角色无外部模型/Provider 独立性证明，因此保守标记 `correlated_review`；mock replay 只验证 contract 与控制，不建立产品级学科证据。

## 结果

| Test ID | 场景 | Expected | Actual | Result | Bug | Evidence |
|---|---|---|---|---|---|---|
| TC-AIREV-001 | provenance、输入与 artifact hash 绑定 | 漂移失败关闭 | prompt/context/policy/harness/input/output 绑定通过 | PASS | — | contract tests / QA-002 |
| TC-AIREV-002 | 角色 run/prompt/context/session 隔离 | 共享状态拒绝 | subject、QA、裁决 run/session 变异均拒绝 | PASS | — | QA-002 |
| TC-AIREV-003 | 30/40/50 finding/evidence/trace 覆盖 | 精确全覆盖 | 120 findings；subject/QA 各 120 trace | PASS | — | gate summary |
| TC-AIREV-004 | claim/evidence position/identity | 错绑拒绝 | claim 替换、伪引用、错误 position 均拒绝 | PASS | — | QA-001/002 |
| TC-AIREV-005 | 工具最小权限和 trace 完整性 | 越权/缺失/篡改拒绝 | allowlist、coverage、query/result/status/call ID 全绑定 | PASS | — | QA-002 |
| TC-AIREV-006 | 提示注入与不可信来源 | 指令不影响审查 | 注入 fixture 失败关闭 | PASS | — | contract tests |
| TC-AIREV-007 | accept/dispute/abstain/timeout/budget | 确定性状态转换 | dispute 裁决；其余失败转 inconclusive | PASS | — | harness tests |
| TC-AIREV-008 | 同模型/Provider 相关性 | 自动披露 | `correlated_review` | PASS | — | QA-002 |
| TC-AIREV-009 | mock/live/owner 安全边界 | 不得产品提升 | controlled-live 与任何 owner artifact 均拒绝；mock 保持 inconclusive | PASS | — | QA-002 |
| TC-AIREV-010 | 全仓回归与构建 | 全绿 | pytest 84/84、Web 1/1、validator/Ruff/mypy/build 全通过 | PASS | — | gate summary |

QA attempt 001 的 3 个 P1 和 3 个 P2 已全部回归关闭；attempt 002 未发现新 P0/P1/P2。

## 证据完整性

- Evidence manifest：`evidence/TR-20260813-005/manifest.json`。
- checksums：`evidence/TR-20260813-005/checksums.sha256`。
- 原始证明：同目录保留 subject attempts 001..003、QA attempts 001..002；失败 attempt 001 未删除或改写。
- 脱敏检查：无秘密、用户内容、数据库、真实 Provider 日志或隐藏推理；机器证明明确 `human_signature=false`、`owner_acceptance=false`。
- 复跑命令：`evidence/TR-20260813-005/commands.txt`。

## 结论

- Decision：GO（仅限 WORK-2026-004 离线 prototype 和后续 contract 输入）。
- 阻断缺陷：无未关闭 P0/P1/P2。
- 接受风险及批准人：没有记录 owner 风险接受；同源相关性、真实搜索污染和共同 harness 缺陷仍保留在 RISK-2026-010..012。
- 未验证项：真实 Provider/Web、authenticated owner、产品状态机、持久化/UI、商业许可适用性、产品区域 Anchor 指标。
- 下一步/Owner/期限：WORK-2026-007/008/010 分别承担 provider contract/live gate/产品化 harness；在其门禁前真实能力保持关闭。
- QA 签字：AI machine attestation `ai-qa-attempt-002.md`，decision PASS，`correlation_classification=correlated_review`；不是人类签字。
