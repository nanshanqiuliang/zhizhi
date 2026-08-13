# Knowledge Tree Agent

本项目将实现一个本地优先、来源可追溯、人工修改优先的知识树工具。系统以规范化概念为核心，以先修 DAG 为学习投影，以原始资料锚点为证据；AI 只产生待校验、待审核的草案。

## 当前状态

当前仍处于早期工程阶段。仓库已完成微积分 30/40/50 金标 fixture、离线 AI 机器复核 v2 prototype、Anchor/GraphPatch v1 与内存回放/撤销 prototype，并交付了可操作的“知枝”知识树 Web developer demo。Demo 可编辑 8 节点示例树、增删叶节点、拖动/排布/锁定并在本会话撤销/重做；`TR-20260814-004` 已通过职责隔离 QA。真实 LLM/Web、资料导入、本地持久化、owner 风险接受和桌面安装包仍未启用。

不要把当前骨架当作 MVP。阶段事实以 [工程计划](docs/ENGINEERING_PLAN.md) 为准。

如果只想了解“现在做到哪一步、什么时候能看到可用网页或 App”，请查看 [自然语言开发路线](docs/USER_FACING_DEVELOPMENT_ROADMAP.md)。

本地查看当前 Demo：

```powershell
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
uv run ruff format --check scripts tests
uv run ruff check .
uv run mypy scripts
uv run pytest
pnpm install --frozen-lockfile
pnpm peers check
pnpm check
pnpm build
```

所有 LLM 检查默认只使用静态配置或 fixture，不会发起真实 API 请求。
