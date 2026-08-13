# Independent review guide

本文件供项目负责人指派的独立学科复核者和 QA 使用。作者不得代填签字。

> 历史 v1 指南：CHG-2026-001 已将后续路径改为 AI harness 自动机器复核。不得把 AI 子 Agent名称填入本文所述真人 `signoff` 字段；v1 保持 pending，直至新的 v2 machine-attestation contract 和 harness 通过验证。AI 角色卡见 `docs/ai-review/ROLE_CARDS.md`。

## 冻结输入

- 数据：`gold.json`，版本 `1.0.0-draft.2`；
- 复核内容 SHA-256：`6e31f3fc332510b379a864c780488cf2acd32e9d4f9fad2b96076ae4603467a3`（规范化数据排除可变的 `status`/`review` 审批元数据）；
- 来源：`source/mit-ocw-res-18-001-chapter-02-derivatives.pdf`；
- 复核记录：`independent-review.json`；
- 许可与限制：先阅读 `NOTICE.md` 和 `DATASET_CARD.md`。

如果复核内容摘要变化，停止复核并要求作者创建新数据版本或重新冻结复核包；不得手工修改 `review_subject_sha256` 以绕过漂移。最终审批状态更新不改变该摘要，概念/关系/锚点/来源/许可变化会改变摘要。

## 学科复核步骤

1. 将 `subject_signoff.status` 改为 `in_progress`，填写真实复核者姓名；不要填写 `completed_at`。
2. 对 30 个概念逐条检查名称、定义摘要和 `anchor_ids`，把 `decision` 改为 `accept` 或 `dispute`。
3. 对 40 条关系检查端点、方向、教学前置合理性、理由和证据页。
4. 对 50 个锚点打开对应 PDF 页，检查主题、章节路径和概念映射；本包只验页级，不验 bbox。
5. `dispute` 必须同时填写 `comment` 和可执行的 `proposed_change`；裁决前 `resolution=pending`。由项目负责人或指定裁决者（不得是提出该分歧的学科复核者）裁决后，改为 `accept_proposed` 或 `reject_proposed`，填写 `resolution_comment`、`resolution_by` 和 `resolved_at`。不得只写“不同意”。
6. 阅读许可说明后把 `license_notice_seen` 改为 `true`。
7. 全部条目已有决定后，填写 `subject_signoff.reviewer`、`completed_at`，状态改为 `complete`。
8. 运行普通校验；不要替 QA 签字。

## QA 步骤

1. 确认复核包仍绑定冻结 hash，30/40/50 条目无缺失或重复。
2. 检查每个 `dispute` 是否有理由和建议，确认分歧已进入裁决流程；QA 不自行修改金标来消除分歧。
3. 确认学科签字 complete、许可已确认、命令可复跑、完整门仍保持可见。
4. QA 必须是不同于学科复核者的真实人员，且不得早于学科签字；填写 `qa_signoff.reviewer`、`completed_at`，状态改为 `complete`。
5. 将 `gold.json` 的 `review.independent.reviewer/status` 与学科签字同步，并把数据集状态改为 `approved`；一次性提交这些状态变更。
6. 运行 `--require-complete` 硬门；通过后仍需按治理流程形成新的独立测试报告/签字记录，不能改写已冻结的 `TR-20260813-003`。

## 命令

```powershell
# 待签模板和复核过程中的结构/覆盖校验（当前应 PASS）
uv run python -m scripts.validate_calculus_review

# 完整独立验收门（当前应 FAIL；学科与 QA 双签后才允许 PASS）
uv run python -m scripts.validate_calculus_review --require-complete
```

完整门失败不会阻止继续填写复核包；它会阻止 WORK-2026-004 被错误关闭、阻止数据集标为 `approved`，也不能被 feature flag 绕过。
