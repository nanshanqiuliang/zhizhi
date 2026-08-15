# Knowledge Tree Agent

本项目将实现一个本地优先、来源可追溯、人工修改优先的知识树工具。系统以规范化概念为核心，以先修 DAG 为学习投影，以原始资料锚点为证据；AI 只产生待校验、待审核的草案。

## 当前状态

当前仓库已完成微积分 30/40/50 金标 fixture、离线 AI 机器复核 v2 prototype、Anchor/GraphPatch v1 与内存回放/撤销 prototype，并交付了本地优先的个人知识树 prototype：可编辑“知枝”知识树、自动保存到本地 SQLite、全文搜索、安全导入 Markdown/TXT/PDF、PDF 页文本与 PDF.js 渲染视图、锚点目录跳转与 bbox 区域高亮、内容漂移保护，以及人工编辑安全感（第 6 步已完成）：内容/位置锁定（锁定项在整图保存时不被覆盖）、跨会话撤销/重做（覆盖所有编辑）、冲突预览、崩溃恢复与版本历史。`TR-20260814-002..013` 已通过职责隔离 QA（第 2–6 步完成）。第 7 步（安全接入真实 AI）已完成（100%）：canonical LLM contract、mock、DeepSeek OpenAI Chat Completions adapter、金额预算、受控回退、真实 live smoke 5/5、微积分金标基线（EVAL-LLM-001）、RB-PROV-001 演练与隔离审查（修复全部 blocking）均完成；workspace owner 已于 2026-08-14 批准 DeepSeek deployment `enabled: true`。第 8 步（AI 自动生成知识树草案）切片 1+2+3+4 已实现：纯领域草案内核与离线编排、真实 DeepSeek 概念抽取/关系候选（live 冒烟 `AI-DRAFT-LIVE-SMOKE-001`）、草案 API 端点与 Web「生成草案 → 预览 → 接受/拒绝」（WORK-2026-026）、来源锚点落库 + 点来源跳回原文（WORK-2026-027）。第 9 步（对话/检索）已完成（约 100%，向量检索为唯一 owner 未决项）：带来源问答（WORK-2026-028）+ 自然语言转 GraphPatch（WORK-2026-029）+ 增量重建（WORK-2026-030/031）+ AI 修改历史（WORK-2026-032，版本历史面板标记 AI 来源）。个人可用 MVP 粗略约 90%。owner 风险接受、向量检索（Embedding provider 未决）、桌面安装包仍未启用。

不要把当前原型当作最终 MVP。阶段事实以 [工程计划](docs/ENGINEERING_PLAN.md) 为准。

如果只想了解“现在做到哪一步、什么时候能看到可用网页或 App”，请查看 [自然语言开发路线](docs/USER_FACING_DEVELOPMENT_ROADMAP.md)。

本地运行（人工验证，需要两个终端；详见 [用户手册](docs/USER_MANUAL.md)）：

```powershell
# 终端 1：启动本地 API（数据目录放仓库外）
uv run python -m apps.api --data-root C:\Users\<你>\knowledge-tree-data

# 终端 2：启动 Web
pnpm --filter @knowledge-tree/web dev
```

## 结构

- `apps/`：桌面、Web、API 与 Worker 组合入口；
- `packages/`：领域、应用、契约、基础设施和算法边界；
- `config/llm/`：不含秘密的 Provider 与模型策略配置；
- `scripts/`：仓库、配置和秘密静态校验；
- `tests/`：单元、契约、集成、安全与 E2E 证据；
- `docs/`：计划、工作项、ADR、测试报告和运维事实源。

## 本地开发门

要求 Python 3.12、uv、Node.js 与 pnpm。当前机器未安装 Rust；在创建 `apps/desktop/Cargo.toml` 之前，桌面编译门保持未适用并记录为环境缺口。

```powershell
uv sync --locked --group dev
uv run python -m scripts.validate_repository
uv run ruff format --check packages scripts tests apps
uv run ruff check .
uv run mypy scripts
uv run python -m mypy --strict packages/contracts-py/src packages/domain/src packages/infrastructure/src apps/api
uv run python -m pytest
pnpm install --frozen-lockfile
pnpm peers check
pnpm check
pnpm build
```

所有 LLM 检查默认只使用静态配置或 fixture，不会发起真实 API 请求；真实 DeepSeek smoke 仅在 `RUN_LIVE_LLM_TESTS=1` 且提供 `DEEPSEEK_API_KEY` 时运行，默认跳过。
