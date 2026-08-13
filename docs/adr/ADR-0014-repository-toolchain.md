# ADR-0014：仓库工具链与最小质量门

```yaml
status: proposed
date: 2026-08-13
decision_owner: technical_lead
related_ids: [WORK-2026-006, NFR-2026-005]
supersedes: null
```

## Context

- 约束、问题、事实和未知：基线指定 Python、React/TypeScript、Tauri/Rust，但当前机器只有 Git、Python/uv、Node/pnpm；远端归属、许可证与 Rust 安装尚未决定。
- 架构/安全/运维/数据影响：第一步必须可复现、默认离线验证，且不能因为缺少桌面代码就虚构 Rust 构建证据。

## Decision Drivers

- 锁定依赖并能在 Windows 与 CI 重跑；
- 普通 PR 不接触真实 LLM 或秘密；
- 保持语言工具相互独立，避免为了空骨架增加运行时耦合；
- 失败必须返回非零并定位到第一个坏边界。

## Considered Options

### Option A：uv + pnpm workspace + GitHub Actions

- 优点：与既定 Python/TypeScript 技术栈一致，锁文件和本地命令简单；后续可添加 Rust job。
- 缺点/风险：暂时不能证明 Tauri 编译；远端平台仍未批准。

### Option B：一次性脚本，不建立锁文件与 CI

- 优点：初期文件少。
- 缺点/风险：不可复现，无法形成 PR 门和构建来源，违反流程基线。

## Decision

- 选择：提议 Option A；本地先落地 uv、pnpm workspace 和声明式 CI，等待技术负责人批准后转为 accepted。
- 理由：在现有工具可用范围内建立真实证据，同时让 Rust 缺口显式可见。
- 明确不解决：远端仓库平台、分支保护、许可证、桌面打包签名和发布。

## Consequences

- 正面：后续工作拥有固定命令、锁文件、schema/秘密门和最小前端回归。
- 负面/技术债：Rust/Tauri、SBOM、provenance、依赖漏洞与许可证策略仍需后续门补齐。
- 对接口、迁移、测试、可观测性、运维的要求：CI 禁止 live LLM；新增工具必须有失败测试和稳定退出码；结果同步到测试报告与环境清单。

## Rollback or Migration

- 回滚/替代触发：技术负责人选择其他包管理或 CI 平台。
- 路径与成本：在产品代码前替换根工具配置；保持语言包边界和测试语义不变。

## Evidence and Review

- Prototype/Test：`TR-20260813-002` 待生成。
- 批准：待项目技术负责人评审；当前 `proposed` 不冒充正式决策。
- 复审条件/日期：Rust/Tauri 首个 manifest、远端仓库确定或阶段 0 入口评审时复审。
