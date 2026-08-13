# AI Subject Machine Attestation — Attempt 001

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: ai_subject_reviewer
reviewed_commit: 73a74da
reviewed_commit_full: 73a74da7ff1f2eec23e8b36559533073a66d606c
decision: dispute
human_signature: false
workspace_modified: false
network_used: false
other_agent_outputs_used: false
```

## 独立运行说明

本次为隔离的只读学科审查 run。未读取或依赖其他子代理产物，未联网，未修改或提交任何文件。所有文本文件通过 `git show 73a74da:<path>` 读取冻结 blob；PDF 工作树文件先与冻结提交比较无差异，再核验 SHA-256 后读取。

## 覆盖与验证

- concepts：30/30；ID 唯一，均有有效 anchor 引用；未发现明显数学错误。
- prerequisite relations：40/40；端点全存在，无重复、自环，DAG 访问 30/30 节点；方向整体合理。
- anchors：50/50；ID 唯一，页码 1..50，均绑定已知资源；主要映射得到 PDF 文本支持。
- PDF：52 页、736149 bytes、SHA-256 `c6a89688e956bc83c75c073068e9be3e7e8317377bd34e2a9d905fcb1af119fb`，与 `gold.json` 一致。
- `tests/contract/test_ai_review_harness.py`：28 passed。

实际命令包括 `git show`/`git diff --quiet`、`Get-FileHash`、Python+pypdf PDF 文本提取、Python 数据计数/DAG/引用校验和 pytest。

## 发现

### P1 — Mock replay 证据由待审数据自身合成

`ReplaySearchProvider.from_dataset()` 从 `gold.json` item 生成 replay record；`content_sha256` 哈希 item 与 source hash，而非 PDF 页内容。120 项默认 `accept`/0.99，QA 机械结果也直接置真。它只能证明内部自洽，不能证明真实学科证据，且缺少不可误读的 mock-only 语义。

### P1 — Finding 与 evidence 的 claim 未绑定

validator 只验证 evidence ID 存在，不验证 evidence 的 `claim_id` 等于 finding 的 `claim_id`，因此其他 claim 的证据可错误支持当前 accept。

### P1 — 数据集范围声明不完整

`included_sections` 仅声明 2.1、2.3、2.6、2.7，但 50 anchors 还包含 2.2、2.4、2.5，共 22/50 anchors 落在未声明章节。

### P2 — 裁决证据表达不足

subject finding 基本支持 accept/dispute/abstain/inconclusive/evidence/counterevidence/uncertainty，但 ledger 固定 120 项，evidence 无支持/反对立场，裁决缺少 evidence、counterevidence、confidence、uncertainty。

### P2 — a036 措辞误导

a036 把 2.5 Exercises 表述为“复合求导法则综合练习”，而 PDF 指向 product/quotient/power rules；建议改为“乘积、商与幂函数求导法则综合练习”。

## 限制

- 使用 PDF 文本提取和重点页检查，未重做 52 页图像级视觉审阅。
- 未联网复核远端内容或许可。
- 本证明不是隐藏思维链、真人签字、发布批准或 owner 风险接受。
