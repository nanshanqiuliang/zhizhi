# WORK-2026-052：远端仓库接入与 CI 首跑（第 11 步清账项）

```yaml
status: ready
type: ops
owner: repo + qa
reviewers: [project_owner]
related_ids: [WORK-2026-006（CI workflow 声明）, WORK-2026-049/050/051（main 追平）]
target_stage: 第 11 步 Beta 加固与扩展
risk: low
created_at: 2026-08-16T00:00:00Z
updated_at: 2026-08-16T00:00:00Z
```

## 问题与结果

- 用户/工程问题：`.github/workflows/ci.yml` 已声明但仓库无远端、从未有 CI run 证据
  （AGENTS.md/OPS_LOG 记录的环境缺口）；main 已追平至 `155cc32`，具备首跑条件。
- 期望结果：在 owner GitHub 账号下创建**私有**远端（许可证意图未决，闭源为安全默认），
  推送 main，CI 首跑全绿并留存 run 证据；workflow 与本地门禁基线对齐。
- 成功如何被观察：① `gh run list` 显示 main push 触发 run 且三 job（python/web/
  desktop-contract）全部 success；② workflow 覆盖本地全量门禁（含 mypy strict
  apps/desktop 与 contracts-ts drift 门）。

## 范围

- In scope：
  - `.github/workflows/ci.yml` 对齐当前基线：`mypy --strict` 目标补 `apps/desktop`
    （43 文件口径）；web job 增加 `pnpm --filter @knowledge-tree/contracts-ts check`。
  - `gh repo create`（私有）+ `git remote add origin` + `git push -u origin main`。
  - CI 失败项修复（仅限 workflow/环境差异，不触产品代码）。
  - 文档：OPS_LOG/DEVELOPMENT_LOG/checkpoint/AGENTS.md 缺口说明更新。
- Out of scope：公开仓库/许可证决策（owner 未决项维持）；发布分支保护规则/必检 CI
  （建议 owner 后续在 GitHub 设置）；feature 分支推送策略；产物（dist）发布。
- 受影响模块/接口/数据：仅 workflow 文件与 git 远端配置；无产品代码变化。
- 依赖和假设：gh CLI 已认证（账号 nanshanqiuliang，repo+workflow scopes）；本地与 CI
  工具版本一致（uv 0.12.3 / node 24.14.1 / pnpm 11.19.0，已核对）；网络可达 GitHub。

## 风险影响

- 安全/隐私：**私有仓库**（least-exposure，许可证未决不公开）；推送内容 = git 已提交
  历史（secret scan 门禁绿；未跟踪的 paper.pdf/工作目录/用户文件不包含）；历史含本地
  路径与 QA 证据文件，属仓库既有治理产物。
- 数据/schema/migration：无。
- 并发/幂等/恢复：CI 可重复触发；远端可删（`gh repo delete`）完全回退。
- 可观测性：CI run URL 即证据。

## 验收标准

- [x] AC-1：远端私有仓库存在且 main 推送成功（`d131e2c`）。
- [x] AC-2：CI run 三 job 全绿（含对齐后的 mypy 43 文件口径 + contracts-ts drift 门）。
- [x] AC-3：workflow 与本地门禁清单一致（AGENTS.md 列举命令全覆盖）。
- [x] 回滚：`git remote remove origin` + `gh repo delete` 即完全移除远端与 CI。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-CI-001 | ops | push main 触发 run | run 启动 | `gh run list` |
| TC-CI-002 | CI | python job | validator/ruff/mypy/pytest 绿 | run 日志 |
| TC-CI-003 | CI | web job | install/peers/check/build/contracts 绿 | run 日志 |
| TC-CI-004 | CI | desktop-contract job | 无 Rust manifest 声明通过 | run 日志 |

## 交付物与关闭

- Commit/PR：workflow 对齐提交 + 文档提交。
- Test Run：CI run URL（记录于 OPS_LOG/checkpoint）。
- 未完成项的新 ID：分支保护/必检 CI（owner GitHub 设置项）；公开化与许可证决策。
