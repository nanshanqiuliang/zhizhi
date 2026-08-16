# TR-20260816-004 QA 报告：WORK-2026-053 Web 搜索 agent「主题→搜网→思维导图」

- test_run_id: `TR-20260816-004`
- reviewed_commit: `e91944b`（实现提交，分支 `feature/WORK-2026-049-empty-graph-crash`）
- 工作项文档: `docs/work-items/WORK-2026-053_web-search-agent.md`
- 判定: **PASS**（0 P0 / 0 P1 / 0 P2 / 2 P3 观察/覆盖边界）
- 角色隔离声明: 本报告由独立 QA 角色出具，与实现者角色分离（独立运行、独立工件）；
  **correlation 披露：`correlated_review`**——本 QA 与实现者（提交作者 Codex，AI 实现）
  同属自动化编排流程，可能同模型/供应商；`human_signature=false`、
  `owner_acceptance=false`（机器证明不冒充人类签名，最终残余风险接受权归工作区所有者）。

---

## 1. 红灯真值（真实运行，实现前）

```
uv run python -m pytest -q tests/unit/test_web_search_provider.py tests/integration/test_web_search_api.py
    -> ModuleNotFoundError: No module named 'knowledge_tree_infrastructure.web_search'
       （存档 logs/red-run-python.log）
pnpm --filter @knowledge-tree/web exec vitest run src/App.websearch.test.tsx
    -> 3 failed（方法/UI 缺失，存档 logs/red-run-web.log）
```

## 2. 绿灯与全部门禁（在 `e91944b` 上真实运行）

| 门禁 | 结果 |
|---|---|
| `test_web_search_provider.py`（unit） | 6/6 passed（tavily/brave 解析+URL/鉴权头、HTTP 401→`web_search_failed/http_error`、网络错误、非 JSON、空/超长 query）——全部经注入 opener，零网络 |
| `test_web_search_api.py`（integration） | 6/6 passed（设置往返脱敏/非法 provider 422、无 key 503、注入链路 requires_confirmation+sources+图库 revision 不变、坏 query/空结果 422） |
| `test_mcp_bridge.py` | 新增 3/3 + 工具集更新（8 工具、禁写子串断言保留；search_draft 不写库；无 key fail-closed） |
| `App.websearch.test.tsx` | 3/3 passed（设置保存、主题生成+来源链接、未配置提示） |
| `uv run python -m scripts.validate_repository` | PASS |
| `uv run ruff format --check packages scripts tests apps` | 128 files already formatted |
| `uv run ruff check .` | All checks passed |
| `uv run mypy scripts` | 16 source files 无问题 |
| `uv run python -m mypy --strict ...` | **45 source files** 无问题（+1 = web_search.py） |
| `uv run python -m pytest -q` | **515 passed, 6 skipped** in 26.06s（6 跳 = 5 live DeepSeek + 1 live web search，无 key，符合双门设计） |
| `pnpm check` | **20 files / 76 tests** 全绿 |
| `pnpm build` / contracts-ts / peers | 全绿（chunk 警告既有） |

## 3. 验收标准核对

| AC | 结果 |
|---|---|
| AC-1 设置端点（key 不回显、非法 provider 拒绝） | PASS |
| AC-2 无 key → 503 `web_search_not_available`（API+MCP 一致） | PASS |
| AC-3 注入链路 requires_confirmation + sources + 图库不变 | PASS |
| AC-4 坏 query/空结果 → 422；网络/HTTP → 502 +rule | PASS（unit 6 用例） |
| AC-5 MCP 工具集 = 8，禁写子串断言保留 | PASS |
| AC-6 Web 设置块/主题按钮/来源显示 | PASS |
| AC-7 live 双门默认 skip | PASS（pytest 6 skipped 含 1 web-search live） |
| 回滚 | 回退提交 + 删 `web-search.json`（代码审查确认） |

## 4. 安全审查要点（harness 门核对）

1. **零网络出口默认**：无 key 时 API/MCP 均结构化 fail-closed，不发任何请求
   （`test_web_search_draft_requires_configuration` / `test_search_draft_without_
   configuration_fails_closed`）。
2. **受控密钥**：仅 HTTPS；key 只进请求头，不进错误 details/日志；设置端点
   `configured/enabled/provider` 不含 key（测试断言 `"brave-secret-key" not in
   response.text`）。
3. **不可信输入**：搜索摘要仅作草案素材；结果 patch 经 `preview_graph_patch`
   防御性校验且必须 `requires_confirmation`；落库仍走应用内确认 + `apply_graph_
   patch` 提交门。
4. query ≤200 字符；仅保留 HTTPS 结果；摘要截断 1000 字符；15s 超时。

## 5. 发现与观察

- **P3-001（覆盖边界）**：真实 provider（Tavily/Brave + DeepSeek 全链路）未在本 QA
  启用（无 key）；live 冒烟双门默认 skip，由 owner 配 key 后复测。
- **P3-002（既有更新）**：设置按钮更名「AI 设置」→「AI 与搜索设置」，
  `App.ai-settings.test.tsx` 断言同步更新（对话框 aria-label 不变）。
- vite chunk >500KB 警告（既有）。

## 6. 结论

WORK-2026-053 验收标准全部满足，红灯真值与全量门禁真实存档。**判定 PASS**。
