# AI Web QA attempt 001 — FAIL

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: graph_qa_fresh
reviewed_commit: 5aab0e378a44086cfe16b0e19eea8f6ca93b9b47
ready_commit: 87fb4020d3f1adecf5a2592ede32ea169ee09548
red_baseline_commit: 4caa76aa9858d609b364146f1877be48062fdadd
decision: fail
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Findings

- P0: none.
- P1: the mobile breakpoint hides every capability-boundary disclosure.
  `@media (max-width: 820px)` hides `.mode-badges` (sample data / AI not
  connected), `.session-notice` (current session only), and
  `.statusbar > span` (database not connected). At 390px the user can still see
  “保存修改” without seeing that the edit is not persistent and no AI/import/
  database capability exists. This violates AC-6 and the honest capability
  boundary.
- P2: no other finding.

## Binding and verification

- Direct chain confirmed: `87fb402` Ready → `4caa76a` red (5/5 failed against
  the old status page) → `5aab0e3` implementation.
- Frozen static review found exactly 8 sample nodes and no fetch, XHR,
  WebSocket, browser storage, IndexedDB, cookie, or external URL use.
- Isolated archive checks passed TypeScript, ESLint, Vitest 5/5, and production
  build.
- Independent DOM mutations passed 8/8: no-move pointer selection creates no
  history; edit/add/leaf-delete/drag undo-redo; new branch clears redo; reset
  restores 8 nodes and clears history.
- Static checks confirmed non-leaf deletion rejection, locked auto-layout,
  toolbar/region/navigation labels, and initial disabled history controls.

## Limitations

- The reviewer browser surface was unavailable, so it did not independently
  measure 1440/390 overflow, console errors, pointer capture, focus, or contrast.
- The reviewer did not rerun full Python or locked dependency gates.
- Concurrent documentation changes were ignored; app conclusions are frozen to
  the reviewed commit.

This failed machine review is preserved and must not be rewritten. A later
passing attempt may supersede it but cannot turn it into a human signature or
workspace-owner risk acceptance.
