# AI Subject Machine Attestation — Attempt 003

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: ai_subject_reviewer
reviewed_commit: db0831b
reviewed_commit_full: db0831b0806d82e7bab95e2ad804bfe69e8d81cd
parent_commit: 3f9b637
previous_decision: dispute
decision: accept
human_signature: false
workspace_modified: false
network_used: false
qa_agent_outputs_used: false
```

## Resolution

| Previous finding | Resolution | Evidence |
|---|---|---|
| `controlled_live` could be product eligible/verified without established subject evidence | Resolved | Validator now enforces product eligibility requires subject evidence; reviewed/verified states require both flags; owner acceptance cannot replace missing subject evidence. |
| adjudication support/counterevidence position was not checked | Resolved | Validator now validates support and counterevidence positions separately. |

No new P0/P1/P2 was found in the `3f9b637..db0831b` diff.

## Verification

Scoped files matched frozen commit `db0831b`; no working-tree divergence was used.

Commands included `git show`, `git diff 3f9b637 db0831b`, `git diff --quiet`, targeted pytest and Python in-memory replay of:

- prior adjudication position mutation → rejected with `adjudication counterevidence has incorrect position`;
- prior controlled-live false-subject-evidence mutation → rejected with `product eligibility requires established subject evidence`;
- owner acceptance with missing subject evidence → rejected with `owner risk acceptance cannot replace missing subject evidence`.

Targeted tests: 67/67 passed.

## Scope and limitations

- 本轮聚焦前一轮两个发现及新提交差异；未重新审阅未变化的 120 个 claims 与完整 PDF。
- 未运行真实 provider 或 controlled-live，只证明确定性 contract 失败行为。
- `accept` 仅表示前述实现争议在冻结提交 `db0831b` 解决；不是隐藏思维链、真人签字、发布批准或 owner 风险接受。
