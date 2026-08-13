# AI Subject Machine Attestation — Attempt 002

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: ai_subject_reviewer
reviewed_commit: 3f9b637
reviewed_commit_full: 3f9b6376a6ab96cc6d0127b488d0f4da8fb7ec4d
parent_commit: 73a74da
previous_attestation_decision: dispute
decision: dispute
human_signature: false
workspace_modified: false
network_used: false
qa_agent_outputs_used: false
```

## 独立运行

本次为新的隔离、只读 resumed audit。指定文件与 `3f9b637` 无工作树差异；未读取其他代理产物、联网或修改文件。

## 上轮发现解决状态

| 上轮发现 | 状态 | 证据 |
|---|---|---|
| mock evidence 自 gold 合成并可能冒充真实证明 | 已解决（mock 路径） | 从 SHA-256 校验后的 PDF 提取页文本并绑定页 hash；mock 强制 `inconclusive`、`subject_evidence_established=false`、`product_eligible=false`。 |
| finding/evidence claim 未绑定 | 已解决 | 校验 finding claim 与 support/counterevidence position。 |
| included_sections 与 anchors 不一致 | 已解决 | scope 与实际 anchors 均为 2.1..2.7。 |
| 多证据及裁决 evidence 表达不足 | 部分解决 | subject ledger 取消 120 上限；裁决增加 ledger/tool trace/evidence/confidence/uncertainty，但 position 尚未校验。 |
| a036 措辞误导 | 已解决 | 改为乘积、商与幂函数求导法则综合练习。 |

## 新发现

### P1 — `controlled_live` assurance 可在无学科证据时伪称产品级

schema 未约束 `product_eligible => subject_evidence_established`；validator 只校验 mock 组合。内存变异把 artifact 改为 controlled_live/controlled_sources、`subject_evidence_established=false`、`product_eligible=true`、`machine_verified`、QA pass 后，当前 validator 错误接受。

### P2 — 裁决 counterevidence 未校验 position

裁决只校验 evidence ID 存在且 claim 相同，未要求 `evidence_ids -> support`、`counterevidence_ids -> counterevidence`。把同一 support evidence 同时放进两者后仍错误通过。

## 覆盖与验证

- concepts/relations/anchors：30/40/50，total claims 120/120。
- included sections expected/actual：2.1..2.7。
- relevant tests：65/65 passed。
- 执行 `git show`、限定 diff、`git diff --quiet`、pytest，以及两项 Python 内存安全变异。

## 限制

- 本轮聚焦上轮发现与差异，未重新做全 PDF 视觉审阅。
- 未测试真实 provider；controlled-live 发现来自离线 contract 变异。
- 本证明不是隐藏思维链、真人签字、发布批准或 owner 风险接受。
