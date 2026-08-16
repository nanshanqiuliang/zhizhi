# TR-20260816-005 QA 报告：WORK-2026-054 思维导图垂直树形排版

- test_run_id: `TR-20260816-005`
- reviewed_commit: `9ba7344`（实现提交，分支 `feature/WORK-2026-049-empty-graph-crash`）
- 工作项文档: `docs/work-items/WORK-2026-054_vertical-tree-layout.md`
- 判定: **PASS**（0 P0 / 0 P1 / 0 P2 / 0 P3 新发现）
- 角色隔离声明: 本报告由独立 QA 角色出具，与实现者角色分离（独立运行、独立工件）；
  **correlation 披露：`correlated_review`**——本 QA 与实现者（提交作者 Codex，AI 实现）
  同属自动化编排流程，可能同模型/供应商；`human_signature=false`、
  `owner_acceptance=false`（机器证明不冒充人类签名，最终残余风险接受权归工作区所有者）。

---

## 1. 红灯真值（真实运行，实现前）

```
uv run python -m pytest -q tests/unit/test_draft_layout_tree.py
    -> 5 failed, 1 passed（旧网格布局：父不居中/间距 220、140 过小/无边概念挤顶行/深链不对齐）
       （存档 logs/red-run-python.log）
pnpm --filter @knowledge-tree/web exec vitest run src/App.layout2.test.tsx
    -> 3 failed（硬编码 layoutWorkspace：自定义图/孤立节点/锁定切断均不满足）
       （存档 logs/red-run-web.log）
```

## 2. 绿灯与全部门禁（在 `9ba7344` 上真实运行）

| 门禁 | 结果 |
|---|---|
| `test_draft_layout_tree.py`（domain） | 6/6 passed：父居中于子块（精确中点）、子 y-父 y ≥200、同父相邻子 x 差 ≥240、宽兄弟组（4 子）均匀且父居中、深链（5 级）严格垂直同 x、无边概念底行（y > 全部树节点）且均布、同输入确定性、DAG 双父节点恰一坐标且层取最长链 |
| `App.layout2.test.tsx`（web） | 3/3 passed：自定义图（1 父 3 子）子块低于父 ≥190、相邻子 ≥240、父 left == 子块中点（toBeCloseTo）；孤立节点底行 + 横向 ≥240 展开；锁定节点精确原位且其自由子成均匀行 |
| 既有回归 | 拓扑分层（`test_ai_draft`）、锁定保持 + 示例重载（`App.test`）等全绿 |
| `uv run python -m scripts.validate_repository` | PASS |
| `uv run ruff format --check ...` | 129 files already formatted |
| `uv run ruff check .` | All checks passed |
| `uv run mypy scripts` / strict | 16 / **45 source files** 无问题 |
| `uv run python -m pytest -q` | **521 passed, 6 skipped** in 39.19s |
| `pnpm check` | **21 files / 79 tests** 全绿 |
| `pnpm build` / contracts-ts / peers | 全绿（chunk 警告既有） |

## 3. 验收标准核对

| AC | 结果 |
|---|---|
| AC-1 父居中于子块 | PASS（domain 精确中点 + web toBeCloseTo） |
| AC-2 父子 y 差 ≥200 / 相邻子 x 差 ≥240（domain 默认 210/260） | PASS |
| AC-3 无先修边概念底行 | PASS（domain + web） |
| AC-4 确定性 + DAG 单坐标 | PASS |
| AC-5 Web 自动排布通用化（任意图/锁定切断/环安全/孤立底行） | PASS |
| AC-6 既有测试全绿 + 全门禁 + CI | PASS（CI 见 OPS_LOG run 记录） |
| 回滚 | 回退提交即回旧布局（无数据迁移） |

## 4. 安全与边界审查

- 主父链环检测：LLM 环状先修关系不会导致递归死循环（`_in_parent_cycle` 提升
  环成员为根）；草案 ≤40 块（max_chunks 上限），递归深度安全。
- Web 端 BFS visited 防环：用户自由连线成环时排布收敛，未到达节点保持原位。
- 锁定节点：位置与语义完全不变（既有测试回归确认）。

## 5. 结论

WORK-2026-054 验收标准全部满足；AI 草案初始布局与「自动排布」均为上下为主的
垂直树形、父居中、间距宽松。**判定 PASS**。
