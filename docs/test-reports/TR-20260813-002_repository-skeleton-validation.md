# TR-20260813-002：仓库与最小 CI 骨架验证

> 本报告冻结 WORK-2026-006 在提交 `bd66e8b30b958f822f0c11c871361d44337acebd` 上的本地结果。它不证明远端 CI、Rust/Tauri、安装包或任何产品业务能力可用。

```yaml
status: passed
test_level: contract
owner: Codex (separate verification pass; independent QA pending)
related_ids: [WORK-2026-006, NFR-2026-005, NFR-2026-006, RISK-2026-004]
build_id: bd66e8b30b958f822f0c11c871361d44337acebd
started_at: 2026-08-13T18:05:00+08:00
finished_at: 2026-08-13T18:13:00+08:00
supersedes: null
```

## 目的、范围和门槛

- 对应需求/风险：建立可追溯、锁定依赖、默认离线的后续开发入口；防止配置漂移和秘密误提交。
- In scope：必需目录/文件、LLM 配置 JSON Schema 与跨文件语义、疑似密钥、Python 格式/lint/type/test、Node peer dependencies、TypeScript type/lint/component test/build、默认桌面宽度与 390px 窄屏浏览器渲染。
- Out of scope：Git 远端/分支保护、托管 CI 实际运行、Rust/Tauri、数据库、Anchor/GraphPatch v1、真实 DeepSeek、金标、发布/SBOM/provenance。
- 通过定义：所有本地命令从锁文件执行并返回 0；页面关键阶段/禁用状态可访问，控制台无 warning/error；失败变异能被拒绝。
- 失败定义：任一命令非零、配置变异被接受、疑似密钥未检出、页面错误宣称真实能力或布局裁切。
- 阻断定义：依赖无法按锁文件安装，或本机工具缺失导致范围内检查无法执行。

## 冻结环境

```text
OS: Windows 10 Home China / x64 / Asia/Shanghai
CPU: AMD Ryzen 9 7940HX with Radeon Graphics
RAM: 16 GB
Python: 3.12.6 / uv 0.12.3
Node: 24.14.1 / pnpm 11.19.0
Rust/Cargo: not installed; out of scope and explicitly not claimed
commit: bd66e8b30b958f822f0c11c871361d44337acebd
uv.lock sha256: a3ececab91c4545c6bb10eb95fe2d04c235f889546eeb54a775042491050b58b
pnpm-lock.yaml sha256: 457e5378ea60e6451ec4e352e2ba3db35dec4d4f051efb3e8e6cf3ad966261ba
LLM config fingerprint: c6c44958e21761ddec500c0dd651c0a32d62f102f17759158169a6f05ec65e7e
DB/API/GraphPatch/Anchor: not created/not frozen
test data: deterministic configuration mutations and synthetic secret markers only
Provider/model/prompt: no live Provider; RUN_LIVE_LLM_TESTS unset/disabled
```

## 方法

- 命令：按 `AGENTS.md` 本地门执行，使用失败即退出的 PowerShell 链；最后运行 `git diff --check`。
- 样本：Python 10 tests、Web 1 component test、5 Provider/7 task profiles；浏览器默认桌面宽度与 390×844 两个视口。
- 变异：未知 Provider 字段、未知 deployment、能力不足、非 HTTPS、fallback 超全局上限、私钥/API token 标记。
- 浏览器：本地 Vite 服务；读取 DOM、console 和全页截图。首次桌面检查发现标题裁切，修复响应式网格和字号后重新执行桌面/窄屏检查。
- 已知限制：没有托管 CI run ID；视觉检查是两个代表性视口，不是完整浏览器矩阵；没有独立 QA 人员签字。

## 结果

| Test ID | 场景 | Expected | Actual | Result | Bug | Evidence |
|---|---|---|---|---|---|---|
| TC-REPO-001 | 必需仓库路径与锁文件 | 全部存在 | 全部存在 | PASS | — | `validate_repository.py` PASS |
| TC-LLM-009 | JSON Schema、引用、能力、HTTPS、预算 | 有效配置通过，6 类变异失败 | 通过；变异均被拒绝 | PASS | — | Python contract tests 6/6 |
| TC-SEC-001 | 疑似密钥 | 版本化文本无命中；合成命中被检出 | 符合 | PASS | — | Python security tests 2/2 |
| TC-BUILD-001-PY | Python format/lint/type/test | 全部返回 0 | 9 files formatted；ruff/mypy 通过；10/10 tests | PASS | — | 本地严格链输出 |
| TC-BUILD-001-WEB | peer/type/lint/test/build | 全部返回 0 | peer 无问题；1/1 test；Vite build 成功 | PASS | — | 本地严格链输出 |
| TC-WEB-001 | 阶段/禁用状态可访问 | 显示阶段 -1、真实 LLM 未启用 | DOM 符合，console 空 | PASS | — | 浏览器 DOM/console |
| TC-WEB-002 | 默认桌面与 390px 响应式 | 无裁切、状态卡可读 | 首轮桌面失败；修复后两视口通过 | PASS after fix | — | 修复后浏览器截图/DOM |
| TC-CI-001 | CI 默认禁 live LLM、桌面门不伪报 | env=0；无 Cargo manifest 时声明 skip | workflow 静态复核符合 | PASS (static only) | — | `.github/workflows/ci.yml` |

## 证据完整性

- Evidence manifest：本报告、提交 `bd66e8b`、`uv.lock`、`pnpm-lock.yaml`、测试源与 CI workflow。
- checksums：锁文件与配置 fingerprint 见冻结环境。
- 原始日志/trace/截图：命令输出与本次浏览器会话；未纳入仓库，报告只保留可重跑摘要。
- 脱敏检查：只使用合成标记；未使用 API Key、用户文档或 Provider 响应。
- 复跑命令：见根 `AGENTS.md` 的 Local verification；浏览器运行 `pnpm --filter @knowledge-tree/web dev --host 127.0.0.1 --port 4173` 后检查 `/`。

## 结论

- Decision：CONDITIONAL GO——允许提交 WORK-2026-006 的本地骨架并进入项目负责人/QA 评审；不允许宣称远端 CI、桌面构建或产品能力完成。
- 阻断缺陷：范围内无。
- 接受风险及批准人：尚无；独立 QA、远端治理、Rust 工具链和许可证均待项目负责人安排。
- 未验证项：Git 托管/分支保护、Linux/托管 runner、Rust/Tauri、SBOM/provenance、安装包与发布恢复。
- 下一步：先完成 WORK-2026-006 验收和 WORK-2026-004 的合法金标输入/双人复核安排；不得跳到 AI 或 GraphPatch 实现。
- QA 签字：`same_person_due_to_team_size`（仅分时复核）；独立 QA pending。
