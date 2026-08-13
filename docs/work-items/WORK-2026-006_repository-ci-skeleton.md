# WORK-2026-006：建仓和最小 CI/证据骨架

```yaml
status: verification
type: ops
owner: Codex (implementation role)
reviewers: [project_owner, qa, operations]
related_ids: [NFR-2026-005, NFR-2026-006, RISK-2026-004]
target_stage: "阶段 -1"
risk: medium
created_at: 2026-08-13T17:57:12+08:00
updated_at: 2026-08-13T18:13:00+08:00
```

## 问题与结果

- 用户/工程问题：现有基线没有 Git 身份、依赖锁、可运行校验、模块目录或 CI，后续实现无法可靠追溯和复现。
- 期望结果：建立本地仓库和最小可重跑质量门，使后续工作能按提交、测试和证据推进。
- 成功如何被观察：干净检出后，Python 仓库校验和测试、TypeScript 类型检查/测试/构建均可按锁文件执行；无真实 LLM 调用。

## 范围

- In scope：本地 Git、`AGENTS.md`、忽略/换行规则、仓库目录、Python/Node 工具配置、LLM 配置 schema 校验、秘密扫描、最小 React 状态页、CI workflow、锁文件和测试报告。
- Out of scope：远端仓库和分支保护、许可证选择、Rust/Tauri 安装、业务数据库、Anchor/GraphPatch 正式 schema、真实 Provider、金标数据、发布产物。
- 受影响模块/接口/数据：仓库治理、`apps/web` 壳、静态工具；不创建用户数据或公开 API。
- 依赖和假设：采用架构基线的 Windows x64、本地单用户安全默认；Python 3.12、uv、Node 24、pnpm 11 可用；当前 Rust 缺失。

## 风险影响

- 数据/schema/migration：只验证现有 LLM 配置 schema，不建立数据库 migration。
- 安全/隐私：新增疑似密钥扫描；测试禁止网络和真实用户内容。
- 并发/幂等/恢复：不适用；没有运行时写操作。
- 性能/容量/成本：只运行快速静态/单元门；不会产生模型费用。
- 可观测性/诊断：CI 输出测试结论；正式证据写入不可变测试报告。
- 用户文档：README 明示当前仅为骨架，不宣称产品能力。

## 验收标准

- [x] AC-1：本地 Git `main` 基线提交与 `feature/WORK-2026-006-repository-skeleton` 分支存在。
- [x] AC-2：`uv.lock`、`pnpm-lock.yaml` 存在，锁定安装后所有本地门通过。
- [x] AC-3：LLM YAML 通过正式 JSON Schema 与跨引用/能力语义校验，失败 fixture 被测试覆盖。
- [x] AC-4：最小 React 状态页通过类型检查、单元测试、production build 和桌面/窄屏浏览器检查。
- [x] AC-5：CI 默认不访问真实 Provider，且在 Rust manifest 不存在时明确跳过而非伪报通过。
- [x] 错误和恢复路径：任一门失败返回非零；移除新增骨架即可回到文档基线提交。
- [x] 回滚/禁用方法：回退本工作项提交；保留根基线提交，不删除用户原始文档。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-REPO-001 | 静态 | 必需目录、文件与锁文件 | 缺失时失败 | TR-20260813-002 |
| TC-LLM-009 | 契约 | schema、引用、能力、端点和预算 | 合法配置通过，变异配置失败 | TR-20260813-002 |
| TC-SEC-001 | 安全 | 版本化文件疑似密钥扫描 | 无密钥；命中时失败 | TR-20260813-002 |
| TC-WEB-001 | 组件 | 状态页渲染 | 显示阶段和禁用状态 | TR-20260813-002 |
| TC-BUILD-001 | 构建 | Python/TypeScript 静态、测试与 Web build | 全部通过 | TR-20260813-002 |

## 交付物与关闭

- Commit/PR：`bd66e8b30b958f822f0c11c871361d44337acebd`；远端 PR 不在授权范围。
- Contract/ADR/migration/prompt：ADR-0014（工具链骨架，proposed）；无 migration/prompt 变化。
- Test Run：`TR-20260813-002` passed / CONDITIONAL GO（独立 QA pending）。
- Release：无；本骨架不可发布。
- 观察结果：本地开发预览桌面/390px DOM、console 和布局通过；尚无发布运行环境。
- 未完成项的新 ID：Rust/Tauri 环境、远端治理、许可证仍归 WORK-2026-003/006 后续验收。
