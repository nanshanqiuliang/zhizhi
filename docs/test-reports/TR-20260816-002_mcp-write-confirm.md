# TR-20260816-002 QA 报告：WORK-2026-050 MCP 写工具 + 应用内确认机制

- test_run_id: `TR-20260816-002`
- reviewed_commit: `9a8374a`（实现提交，分支 `feature/WORK-2026-049-empty-graph-crash`，含先行的 WORK-2026-049 提交）
- 工作项文档: `docs/work-items/WORK-2026-050_mcp-write-confirm.md`
- 判定: **PASS**（0 P0 / 0 P1 / 0 P2 / 2 P3 观察/覆盖边界）
- 角色隔离声明: 本报告由独立 QA 角色出具，与实现者角色分离（独立运行、独立工件）；
  **correlation 披露：`correlated_review`**——本 QA 与实现者（提交作者 Codex，AI 实现）
  同属自动化编排流程，可能同模型/供应商；`human_signature=false`、
  `owner_acceptance=false`（机器证明不冒充人类签名，最终残余风险接受权归工作区所有者）。

---

## 1. 红灯真值（真实运行）

实现前（仅新增测试文件）：

```
uv run python -m pytest -q tests/integration/test_proposal_store.py tests/integration/test_proposal_confirm_api.py tests/integration/test_mcp_bridge.py
    -> ModuleNotFoundError: No module named 'knowledge_tree_infrastructure.proposals'
       2 errors during collection（存档 logs/red-run-python.log）
pnpm --filter @knowledge-tree/web exec vitest run src/App.proposals.test.tsx
    -> 4 failed（类型/方法缺失，存档 logs/red-run-web.log）
```

## 2. 绿灯与全部门禁（在 `9a8374a` 上真实运行）

| 门禁 | 结果 |
|---|---|
| 提议存储（`test_proposal_store.py`） | 7/7 passed（保存/列表/读取/原子文件/pending 单向迁移/路径穿越拒绝/排序） |
| API 确认流（`test_proposal_confirm_api.py`） | 6/6 passed（pending 摘要/接受经提交门 + source=mcp_proposal + accepted/重复 settle 409/拒绝不动图/过期补丁 409 保持 pending/未知 id 404） |
| MCP 桥（`test_mcp_bridge.py`） | 11/11 passed（原 7 + 新 4：提议不写库/非法 fail-closed 无落盘/状态观察三态/未知 id）；stdio 子进程冒烟列出 **6 工具** |
| Web（`App.proposals.test.tsx`） | 4/4 passed（列表/接受后刷新 loadGraph+listProposals/拒绝/无提议时隐藏） |
| `uv run python -m scripts.validate_repository` | PASS |
| `uv run ruff format --check packages scripts tests apps` | 121 files already formatted |
| `uv run ruff check .` | All checks passed |
| `uv run mypy scripts` | 16 source files 无问题 |
| `uv run python -m mypy --strict ...` | **42 source files** 无问题（+1 = proposals.py） |
| `uv run python -m pytest -q` | **493 passed, 5 skipped** in 25.25s（476 既有 + 17 新增；5 跳 = live DeepSeek 门禁，无 key） |
| `pnpm check` | **18 files / 72 tests** 全绿（68 既有 + 4 新增） |
| `pnpm build` | OK（chunk-size 警告为既有问题） |
| `pnpm --filter @knowledge-tree/contracts-ts check` | exit 0（无契约 drift） |
| `pnpm peers check` | No peer dependency issues found |

## 3. 验收标准核对

| AC | 结果 |
|---|---|
| AC-1 工具集 = 6、禁写子串断言保留 | PASS（`test_mcp_toolset_is_read_only` + stdio 冒烟） |
| AC-2 propose_patch 落 pending、图库不变；非法补丁无落盘 | PASS（2 用例） |
| AC-3 accept → applied + revision+1 + source=mcp_proposal + accepted；重复 → 409 | PASS（2 用例） |
| AC-4 reject → rejected、图库不变 | PASS |
| AC-5 过期补丁 → 409 patch_revision_conflict、保持 pending | PASS |
| AC-6 proposal_status 三态 + change_id；未知 → proposal_missing | PASS（2 用例） |
| AC-7 Web 面板列出/接受/拒绝、接受后刷新 | PASS（4 用例） |
| 回滚 | 回退提交回 048 形态；`proposals/` 目录可独立删除（代码审查确认） |

## 4. 发现与观察

- **P3-001（覆盖边界）**：冻结 exe 的 MCP 冒烟未在本 TR 重跑——`mcp_server.py`/
  `main.py` 变更后产物尚未重建；stdio 协议冒烟（源码子进程）已覆盖 6 工具枚举与
  调用。产物重建后按 WORK-2026-048 的冻结冒烟流程复测。
- **P3-002（设计边界，非缺陷）**：会话级"自动确认"开关未实现（按工作项 Out of
  scope，需独立 harness 评审）；当前每条提议都需应用内逐条确认——这是有意的
  安全默认。
- vite chunk >500KB 警告（既有，沿用 TR-20260815-010 P-3-004）。

## 5. 安全审查要点（harness 约束核对）

1. 外部 AI 无图库写路径：`propose_patch` 仅写 `proposals/*.json`；`apply_graph_patch`
   只被 sidecar API 的 accept 端点调用（本地回环 + CORS 白名单，与既有写端点同权限面）。
2. 无自确认：MCP 工具集经 stdio 冒烟与单元断言双重验证不含 accept/apply/commit 类。
3. 预确认补丁 fail-closed：`propose_patch` 要求 preview.status ==
   `requires_confirmation`（confirmed=true 的补丁被拒绝，`patch_not_proposed`）。
4. 双重校验：入队时 `preview_graph_patch`，确认时 `apply_graph_patch` 提交门（锁/
   修订/历史/duplicate change id）。
5. 路径穿越：proposal_id 严格 UUID 正则；note 截断 500 字符；原子写。

## 6. 结论

WORK-2026-050 验收标准全部满足，红灯真值与全量门禁真实存档。**判定 PASS**。
