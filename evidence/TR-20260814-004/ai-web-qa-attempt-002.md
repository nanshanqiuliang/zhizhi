# AI Web QA attempt 002 — PASS

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: graph_qa_fresh
reviewed_commit: fff1ce697cf3524fb7622f36cedfc63136e990f2
red_regression_commit: c8c6bf99d8cb008c111ed4918320c58b2f8074fe
original_implementation_commit: 5aab0e378a44086cfe16b0e19eea8f6ca93b9b47
decision: pass
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

- P0: none.
- P1: none.
- P2: none.
- New findings: none.

The P1 from attempt 001 is closed at the frozen fix commit.

## Binding and verification

- Direct chain confirmed: `5aab0e3` original implementation → `c8c6bf9` red
  regression (1 failed / 5 passed) → `fff1ce6` fix.
- In an isolated Git archive, TypeScript, ESLint, Vitest 6/6, and the production
  build all passed.
- Independent DOM mutations plus the existing tests passed 8/8.
- `aside[aria-label="演示能力边界"]` is accessible and contains “示例数据”,
  “仅本次会话”, “AI 未连接”, “无资料导入”, and “未连接数据库”; “保存修改”
  remains enabled.
- CSS defaults the compact disclosure to hidden for desktop and explicitly
  overrides it to `display: flex` in `@media (max-width: 820px)`, with no later
  hiding rule.
- No regression was found in the 8-node fixture, no-move selection history,
  add/leaf-delete/reset, editing, undo/redo, drag, locking, or auto-layout.
- No fetch, XHR, WebSocket, browser storage, IndexedDB, cookie, or external URL
  use was found.

## Limitations

- The reviewer browser surface was unavailable, so its review used frozen CSS,
  DOM checks, and production build instead of an independent 390px screenshot,
  console log, or computed-style measurement. The implementer evidence records
  those browser measurements separately.
- The reviewer did not rerun the full Python suite or locked installs.
- Concurrent documentation/screenshots were excluded; all app conclusions are
  frozen to `fff1ce6`.

This is correlated machine review, not a human signature, release approval, or
workspace-owner residual-risk acceptance.
