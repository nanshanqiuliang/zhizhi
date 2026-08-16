# QA TR-20260815-010 — 尝试与过程记录（WORK-2026-048 内置 MCP server）

## 角色与隔离
- 独立 QA 角色；与实现者角色分离（独立运行/提示词/工件；本 QA 在 E:\知识树 - 副本 工作树与隔离 worktree 中执行，实现提交 fab4d70/944a996 由编排中的实现角色完成）。
- **correlation 披露：correlated_review** —— 本 QA 与实现者同属同一自动化编排流程，可能同模型/供应商（本 QA 运行于 DeepSeek 系模型）；`human_signature=false`、`owner_acceptance=false`，机器证明不冒充人类签名，最终残余风险接受权归工作区所有者。
- 未修改任何产品代码、未提交任何 git 变更；QA 产物全部落盘于 evidence/TR-20260815-010/ 与 docs/test-reports/TR-20260815-010_mcp-server.md。
- 勘察时发现工作树存在未提交的文档修改（docs/USER_FACING_DEVELOPMENT_ROADMAP.md、docs/USER_MANUAL.md、docs/ai-mindmap-agent-harness.md，均为 WORK-2026-048 的用户文档更新）——非本 QA 产生，QA 全程未改动并保留（change hygiene：不碰无关用户改动）。

## 阶段一：红灯真值（隔离 worktree）
- `git worktree add --detach E:\ztree-qa-worktree-010 HEAD` → worktree 内 `uv sync --locked --group dev`（mcp 1.29.0，满足 mcp<2）。
- 改名 `apps/api/mcp_server.py` → `mcp_server.py.bak` 后运行 `uv run python -m pytest -q tests/integration/test_mcp_bridge.py`：
  **collection error：ModuleNotFoundError: No module named 'apps.api.mcp_server'（1 error in 1.35s）** → 红灯成立（测试确实依赖被审模块，删模块即红）。
- 还原后同命令 → **7 passed**。worktree 已 `git worktree remove --force` + `git worktree prune`，worktree list 仅剩主检出。

## 阶段二：全部门禁（HEAD 主检出）
- 12 项门禁全绿：uv sync（91 packages）、validate_repository、ruff format（118 files）、ruff check、mypy scripts（16 files）、mypy --strict 含 apps/desktop（**41 files**）、pytest **476 passed + 5 skipped**、pnpm install frozen、peers、check（**16 files/64 tests**）、build、contracts-ts drift。
- 过程插曲（记录备查）：门禁脚本初版在脚本内硬编码中文仓库路径，PowerShell 5.1 以 ANSI 读无 BOM UTF-8 脚本导致路径乱码、误在 evidence/ 下执行；已改为从 $PSScriptRoot 推导仓库根（ASCII-only 脚本体）并重跑，重跑结果全绿。日志编码统一为 UTF-16LE（与既有封存证据一致）。

## 阶段三：对抗探针（15 项，脚本 probes/qa_probe_mcp.py，uv run python 真实运行）
- 首轮 **13/15**：P-012/P-013 FAIL，经查均为**探针自身缺陷**（非产品缺陷）：
  1. P-012：应用端点 `/api/workspaces` 返回 `{"workspaces":[...]}` 对象而非裸数组，探针按裸数组解析得到空列表 → 修正为取 payload["workspaces"]。
  2. P-013：无 key 断言在「播种前」调用 preview_draft，此时工作区不存在，返回 workspace_missing（fail-closed 正确）而非 ai_not_available → 修正为播种后再断言 ai_not_available，并保留播种前调用作为附加 fail-closed 验证。
- 修正后 **15/15 PASS**（logs/probes-mcp.log；首轮 logs/probes-mcp-run1.log 保留备查）。
- 关键结果：
  - 工具集精确 4 个、无 write/apply/submit/commit/save/delete/accept（P-001；stdlib 会话 P-010 与冻结 exe P-013 同样精确 4 个）。
  - preview_draft 单资源（md 与 PDF）→ requires_confirmation=true/confirmed=false、生成器收到正确文本、图 revision 不变（P-002/P-007；PDF 走 parse_pdf_resource，抽取 129,604 字符）。
  - 无 key（无注入/无 ai.json/无 env）→ 结构化 `ai_not_available/key_required`，服务其余调用仍正常（P-003）。
  - 未知工作区/无 db/无图 → 结构化 workspace_missing / workspace_corrupt（P-004）。
  - validate_patch 全分支：合法→requires_confirmation；confirmed:true→ready_to_apply（history_records=0，未写库）；actor 不符→patch_invalid/actor_context_mismatch；base_revision 冲突→patch_invalid/base_revision_mismatch；requires_confirmation=false→patch_invalid/confirmation_required（P-005）。
  - list_workspaces 空根→[]、噪声目录忽略、播种后→1（P-006）。
  - 空资源工作区全库草案→draft_invalid/no_resources；坏生成器输出（无 ops/无 patch/坏 base/抛 DraftError）全部结构化 fail-closed（P-008/P-009）。
  - stdio 真实会话（源码自举）initialize/tools/list/call 全通（P-010）；未知工作区报错后会话存活、参数错误 isError 后会话存活（P-011）。
  - 并发：`zhizhi.exe --no-window` sidecar（同数据根）健康 + /api/workspaces 返回 1 个 + MCP stdio 客户端同根 list/read 正常 → 只读并发安全；终止后端口释放（P-012/P-012b）。
  - 冻结 exe `--mcp-stdio`：initialize + 4 工具 + 空根 [] + 会话中播种后 read_workspace 返回图 + 无 key ai_not_available；关闭会话后 exe 进程数 after=0，无残留（P-013）。
  - `python -m apps.api.mcp_server --help` 正常（P-014）。

## 观察与分级（全部如实记录，未改产品代码）
- P0/P1：无。
- P2：无（未发现本变更引入的缺陷）。
- P3 观察：
  1. 任务探针规格写「actor 不符 → permission_denied」，实际 validate_patch 对 GraphPatchError 统一映射为 `patch_invalid` + rule=actor_context_mismatch（MCP 工具错误命名空间为 {patch_invalid, draft_invalid, workspace_*, ai_not_available}，rule 区分细节）。满足工作项 AC-4「越权补丁返回稳定错误、不写库」；属行为命名差异，非缺陷。
  2. mcp SDK 1.29 + pydantic-settings 在 server/client 启动时输出 `IncompleteFieldDefinitionWarning: Field 'lifespan' ...`（上游 SDK 内部 forward-ref 警告，走 stderr 不污染 stdio；pytest 全量同样 1 warning）。无功能影响。
  3. 冻结 exe 探针仅验证 stdio 协议/读路径；AI 草案路径因无 key 只验证到 fail-closed 边界（真实 LLM 路径由既有 476 测试与 live-gate 门禁覆盖，live 需显式 RUN_LIVE_LLM_TESTS=1 + key，未启用）。
  4. worktree 红灯语义说明：改名 mcp_server.py 使测试 collection 失败（导入错误），红灯成立；绿灯为 7 passed。

## 结论
- 判定 **PASS**（0 P0 / 0 P1 / 0 P2 / 4 P3 观察）。红灯→绿灯闭环、12 项门禁全绿、15/15 对抗探针通过（含真实 stdio 协议、冻结 exe、sidecar 并发只读安全、错误隔离）；未发现本变更引入的缺陷。
- human_signature=false、owner_acceptance=false：机器 QA 证据不冒充人类签名；最终残余风险接受权归工作区所有者。
