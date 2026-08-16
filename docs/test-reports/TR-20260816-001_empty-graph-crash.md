# TR-20260816-001 QA 报告：WORK-2026-049 空工作区（0 节点）渲染崩溃修复（BUG-2026-001）

- test_run_id: `TR-20260816-001`
- reviewed_commit: `5094482`（实现提交，分支 `feature/WORK-2026-049-empty-graph-crash`）
- 工作项文档: `docs/work-items/WORK-2026-049_empty-graph-crash.md`
- 判定: **PASS**（0 P0 / 0 P1 / 0 P2 / 0 P3 新发现；1 既有观察沿用）
- 角色隔离声明: 本报告由独立 QA 角色出具，与实现者角色分离（独立运行、独立工件）；
  **correlation 披露：`correlated_review`**——本 QA 与实现者（提交作者 Codex，AI 实现）
  同属自动化编排流程，可能同模型/供应商；`human_signature=false`、
  `owner_acceptance=false`（机器证明不冒充人类签名，最终残余风险接受权归工作区所有者）。

---

## 1. 红灯真值（真实运行）

在实现前的工作区（仅新增 `apps/web/src/App.empty.test.tsx`、无 App.tsx 修改）执行：

```
pnpm --filter @knowledge-tree/web exec vitest run src/App.empty.test.tsx
```

**红灯（预期 4 failed，实际 4 failed / 4 errors）：**

| 用例 | 实际结果 |
|---|---|
| renders an empty-state guide ... saved graph has no nodes | FAIL：渲染抛 `Cannot read properties of undefined (reading 'tone')`（App.tsx:1666 `selectedNode.tone`） |
| recovers from an empty graph by adding a root concept | FAIL：同上（空态 UI 不存在，`getByRole("region", { name: "空工作区引导" })` 找不到之前已因渲染崩溃失败） |
| does not crash when deleting the last remaining node | FAIL：`deleteSelected` 中 `parent.id` 读取 undefined |
| does not crash when undoing an addition back to an empty graph | FAIL：`restoreDrafts` 中 `node.id` 读取 undefined |

红灯输出存档：`evidence/TR-20260816-001/logs/red-run.log`（4 failed, 4 errors, exit 1）。

**绿灯（`5094482` 实现后）：** 同一命令 → `1 passed (4 tests)`。
绿灯输出存档：`evidence/TR-20260816-001/logs/green-run.log`。

## 2. 全部门禁（在 `5094482` 上真实运行）

| 门禁 | 结果 |
|---|---|
| `uv run python -m scripts.validate_repository` | PASS（skeleton/secret scan/graph+LLM contracts/review packet/v2 mock-replay） |
| `uv run ruff format --check packages scripts tests apps` | 118 files already formatted |
| `uv run ruff check .` | All checks passed |
| `uv run mypy scripts` | 16 source files 无问题 |
| `uv run python -m mypy --strict packages/contracts-py/src packages/domain/src packages/infrastructure/src apps/api apps/desktop` | 41 source files 无问题 |
| `uv run python -m pytest -q` | **476 passed, 5 skipped** in 24.27s（5 跳 = live DeepSeek 门禁，无 key，符合预期） |
| `pnpm check`（tsc + eslint --max-warnings 0 + vitest） | **17 files / 68 tests 全绿**（64 既有 + 4 新增） |
| `pnpm build` | OK（chunk-size 警告为既有问题，非本变更引入） |
| `pnpm --filter @knowledge-tree/contracts-ts check` | exit 0（无契约 drift） |
| `pnpm peers check` | No peer dependency issues found |

## 3. 验收标准核对

| AC | 结果 |
|---|---|
| AC-1 空图加载渲染空态引导而非崩溃 | PASS（TC-EMPTY-001，真实红灯→绿灯） |
| AC-2 空态「添加总纲」创建 root 块并进入编辑流 | PASS（TC-EMPTY-002：新总纲块出现、概念标题输入框值为「新总纲」） |
| AC-3 删除唯一未锁定叶节点后进入空态 | PASS（TC-EMPTY-003） |
| AC-4 空图上加块后撤销回到空态 | PASS（TC-EMPTY-004：空态重现且新总纲块消失） |
| 回滚 | 回退 `5094482` 即回到崩溃行为；无迁移（代码审查确认，纯前端渲染防御） |

## 4. 发现与观察

- **P3（既有，非本变更引入）**：vite chunk >500KB 警告（`pnpm build`）沿用
  `TR-20260815-010` P-3-004 记录，未变化。
- 覆盖边界：桌面 e2e（pywebview 18 用例）未在本 TR 重跑——纯 Web 渲染变更且
  `pnpm check`/`pnpm build` 全绿；e2e 随下次桌面产物重建统一复测（与 049 工作项
  「不单独发版」约定一致）。
- 后端 `create_workspace` 仍恒建 1 根节点，空图只能经契约直连/API/删光节点到达；
  本修复保证所有到达路径安全。

## 5. 结论

WORK-2026-049 验收标准全部满足，红灯真值与全量门禁真实存档。**判定 PASS**。
BUG-2026-001 → `ready_for_release`，随下次桌面产物重建发布后转 `closed`。
