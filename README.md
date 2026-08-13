# Knowledge Tree Agent

本项目将实现一个本地优先、来源可追溯、人工修改优先的知识树工具。系统以规范化概念为核心，以先修 DAG 为学习投影，以原始资料锚点为证据；AI 只产生待校验、待审核的草案。

## 当前状态

当前处于“阶段 -1：架构与证据准备”。本仓库已开始执行第一轮动工顺序的第 1 步：建立本地 Git、模块目录、校验脚本、最小前端壳和 CI 证据骨架。尚未冻结 Anchor/GraphPatch v1，尚未导入金标数据，未启用真实 LLM，也没有可发布桌面安装包。

不要把当前骨架当作 MVP。阶段事实以 [工程计划](docs/ENGINEERING_PLAN.md) 为准。

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
