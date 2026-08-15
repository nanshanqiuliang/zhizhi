# AI QA attempt 002 — NL→GraphPatch fix (superseding, WORK-2026-029)

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: ai_qa_auditor
decision: pass
reviewed_commit: 9a255d2953d2cacd864127116f0df97a3d9c69a5
supersedes: attempt 001 (b4fde38, PASS with 3 P2)
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

**PASS** — 0 P0 / 0 P1。这是对修复提交 `9a255d2`（父 `b4fde38`）的超越审查
（attempt 001 已 PASS，含 3 个非阻塞 P2；本轮闭合 P2-1/P2-2/P2-3）。

## Closure proofs

- **P2-1（错误详情回显）— CLOSED**：`_digest() = sha256(value)[:12]`；`resolve` →
  `label_hash`、`set_lock_shape` → `dimension_hash`、`edge_type_invalid` →
  `edge_type_hash`。探针：未知 label「请帮我锁定极限的内容」→ details
  `{'rule':'target_unknown','label_hash':'b35ce7e3dcf0'}`，原始文本不出现（stdlib
  sha256 独立复算一致；非串 label 123 经 repr 哈希）。API 映射 CommandError → 422
  `{code, **details}`，不回显。后续 `9abd339` 又使 `op_unknown` 发 `op_hash`。
- **P2-2（Python 回归）— CLOSED**：`test_command_api.py` 12 测试，6 个新回归在场。
- **P2-3（Web 回归）— CLOSED**：`App.command.test.tsx` 3 测试（accept/reject/503）。

## Gates（本人执行，精确数字）

command 12/12；全仓 421/421 + 5 skipped；ruff format/check pass（91 文件）；strict
mypy 33 文件；validator PASS（含 secret scan）；Web command 3/3；`pnpm check` 41 tests
+ tsc + eslint 0 warnings。

## Core properties — no regression

label→id 失败关闭 casefold 映射；精确 revision 绑定（含非零=3）；proposal-only patch；
提交门接受（confirmed=true → /graph/patches）；/interpret 只读；secret scan PASS；
503/422/404 no-500。

## Conclusion

PASS。`correlated_review`（机器证明、同源披露），非 owner 接受。
