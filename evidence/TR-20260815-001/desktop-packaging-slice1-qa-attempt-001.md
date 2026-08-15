# AI QA attempt 001 — Windows 桌面封装切片 1（WORK-2026-033，第 10 步切片 1）

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: ai_qa_auditor
decision: pass
reviewed_commit: fa8be626c72be4a3854ea98427cb11a4681c6cbe
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

**PASS** — 0 P0 / 0 P1；5 个非阻塞 P2。这是对冻结提交 `fa8be62`
（WORK-2026-033 第 10 步切片 1：`create_app(web_dist)` 同源自托管 + frozen 感知
`_runtime` + `apps/desktop/launcher.py` 生命周期/单实例 + PyInstaller onedir 冻结 +
`desktop_e2e.py`）的职责隔离机器审查。

## Red/green chain

Ready `3fc46c7` → 红灯 `8edf336` → 核心实现 `39117a1` → 打包+e2e `545b404` →
docs/tests `fa8be62`。红灯真值经**实际运行**确认：在 `%TEMP%` 分离 worktree checkout
`8edf336`，运行 `test_desktop_serve.py` 得 2 failed（`TypeError: create_app() got an
unexpected keyword argument 'web_dist'` + `ModuleNotFoundError: No module named
'apps.desktop.launcher'`），与提交信息一致。

## Gates（本人执行，精确数字）

- 聚焦测试 `test_desktop_serve.py` + `test_desktop_launcher.py`：**8/8**。
- 全仓 pytest：**442 passed + 5 skipped**（skip 为 live-LLM 门，需 `RUN_LIVE_LLM_TESTS`+key）。
- `ruff check .`：clean；`ruff format --check`：104 文件。
- `mypy scripts`：14 文件；`mypy --strict packages + apps/api + apps/desktop`：37 文件。
- `scripts.validate_repository`：PASS（含 secret scan）。
- Web（tsc + eslint）：**41/41**；`pnpm peers check`：无问题；`pnpm --filter web build` 通过。
- 冻结产物 `scripts/desktop_e2e.py`：**15/15 PASS**（健康/UI/数据目录/图 PUT-GET/导入/
  补丁+撤销/AI 无 key 503/单实例 fail-closed/陈旧锁接管/端口释放）。

## 附加执行探针

- **冻结态 `config/llm` 解析**：以伪 `DEEPSEEK_API_KEY` 启动冻结 exe 并 POST 空 `/ai-draft`，
  得 **422 `draft_invalid/resource_id_missing`**（而非 503），证明 `load_and_validate_llm_config
  (runtime_root())` 在冻结进程内成功加载并校验了打包进 `_MEIPASS` 的 `config/llm`，且零网络。
- 打包内容核实：`_internal/config/llm/{providers,model-policies}.yaml` 与
  `_internal/web_dist/{index.html,pdf.worker.min.mjs}` 均在盘上。

## Findings（非阻塞 P2）

| Sev | 位置 | Finding | 处置 |
|-----|------|---------|------|
| P2 | launcher.py 单实例 | 健康探测只探一次，启动窗口内 A 已写锁但未绑定端口时 B 可能抢锁 | 已由 `0067aae` 修复（`_is_running_with_retry`） |
| P2 | web/main.tsx + build | `--port ≠ 8000` 时 SPA 仍硬编码 8000 → 跨源被 CORS 拦截 | 已由 `0067aae` 修复（桌面构建 `VITE_LOCAL_API=""` 同源相对基址） |
| P2 | docs | 工作项 `updated_at` 未更新；AC-5 证据描述与提交证据不一致；TC-DSK-002 标待实现 | 文档边界，随本轮文档同步修正 |
| P2 | launcher.py `_run` | `web_dist` 非目录时静默 API-only，无提示 | 已由 `0067aae` 修复（stderr 警告） |
| P2 | e2e | 「优雅退出」证据实为 TerminateProcess 硬杀；`should_exit` 优雅路径仅静态追踪 | 记录为原型边界（Windows 自动测 Ctrl+C 不可靠） |

## 执行 vs 静态追踪

- **执行**：上述全部 11 项门、红灯真值（分离 worktree）、冻结 e2e 15/15、伪 key 冻结
  `config/llm` 探针。未改任何仓库文件（worktree 与 `%TEMP%`；`apps/web/dist` 被 pnpm build
  重建但已 gitignore 且源一致）。
- **静态追踪**：`should_exit` 优雅退出路径、`runtime_root()` 父级算术、路由优先级与
  Starlette 1.6.0 `StaticFiles.lookup_path` 目录逃逸防护、spec `parents[1]` 算术、P2-1
  启动窗口竞态。

## Disclosure

本报告为独立 AI QA 子 Agent（与实现 Agent 角色分离、同模型相关性）进行的机器审查，
是证据与工程发现的证明，**不是**人类签名，也非 owner 接受。该切片的最终残余风险接受
属于 workspace owner。
