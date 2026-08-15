# WORK-2026-036：画布拖拽修复（仅左键按住时拖拽，第 10 步后用户反馈）

```yaml
status: ready
type: bugfix
owner: Codex (web role)
reviewers: [ai_qa_auditor, workspace_owner]
related_ids: [REQ-2026-001, NFR-2026-001]
target_stage: "阶段 1 / 第 10 步后使用反馈修复"
risk: low
created_at: 2026-08-15T22:30:00+08:00
updated_at: 2026-08-15T22:30:00+08:00
```

## 问题与结果

- 用户/工程问题：使用反馈——「鼠标松开了但拖拽依然在进行，除非双击鼠标」；期望「鼠标左键
  按住 block 时才能拖拽」。根因：`moveDrag` 不检查鼠标按键，且无 pointer capture，pointerup
  丢失后 `drag.current` 残留，后续任意 pointermove（未按鼠标）继续拖动。
- 期望结果：仅左键按住时拖拽；松开（`buttons & 1 == 0`）即结束拖拽并提交移动；pointer
  capture 保证 pointerup 不丢失。
- 成功如何被观察：红灯测试（未按鼠标的 pointermove 不再移动节点）→ 修复后通过；既有拖拽测试
  用 `buttons: 1` 适配后仍通过；Web 全绿。

## 范围

- In scope：`apps/web/src/App.tsx` 的 `startDrag`/`startPan`/`moveDrag`/`endDrag`——`moveDrag`
  首行检查 `(event.buttons & 1) === 0` 则 `endDrag(event)`；`startDrag`/`startPan` 增加
  `setPointerCapture(pointerId)`（容错 try/catch）；canvas-surface 增 `onPointerCancel={endDrag}`。
- Out of scope：触摸/触控笔；多指针手势；性能优化。
- 受影响模块：`apps/web/src/App.tsx`；`App.test.tsx` 既有拖拽测试补 `buttons: 1`。
- 依赖和假设：jsdom 环境 `setPointerCapture` 可能缺失/抛错，需容错。

## 风险影响

- 数据/schema/migration：无。
- 安全/隐私：无。
- 并发/幂等/恢复：无。
- 性能/容量/成本：无。
- 可观测性/诊断：无。
- 用户文档：手册「画布拖拽」描述微调（可选）。

## 验收标准

- [ ] AC-1：按住左键（buttons 含 1）时 pointermove 拖动节点。
- [ ] AC-2：未按左键（buttons 不含 1）的 pointermove 不拖动、立即结束拖拽（位置不再变化）。
- [ ] AC-3：既有「移动节点」测试（补 `buttons: 1`）通过；Web 全绿。
- [ ] 错误和恢复路径：`setPointerCapture` 缺失/抛错时静默降级（不影响拖拽主体逻辑）。
- [ ] 回滚/禁用方法：回退本提交即回旧拖拽行为。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-DRAG-001 | component | 按住左键拖拽移动 | 位置变化 | App.test 新用例 |
| TC-DRAG-002 | component | 松开后 pointermove 不再拖 | 位置不变 | App.test 新用例 |
| TC-REPO-001 | repository | 全仓门 | pytest/ruff/mypy/Web | 待实现 |

## 交付物与关闭

- Commit/PR：分支 `feature/WORK-2026-036-drag-fix`；Ready → 红灯 → 实现。
- Contract/ADR/migration/prompt：无。
- Test Run：TC-DRAG-001/002 + Web 全绿。
- Release：随下一个桌面构建。
- 观察结果：拖拽仅在左键按住时进行，松开即停。
- 未完成项的新 ID：无。
