# TR-20260813-004：微积分金标独立复核门验证

> 本报告是 WORK-2026-004 的增量验证记录，冻结实现提交 `232d0cdc48c25d8cd986013ea21b8060fd37336f` 上的待签复核执行包。它不修改或取代 `TR-20260813-003`，也不冒充独立学科复核或独立 QA 签字。

```yaml
status: passed
test_level: contract
owner: Codex (implementation / separate verification; independent reviewers pending)
related_ids: [WORK-2026-004, NFR-2026-002, NFR-2026-008, RISK-2026-001, RISK-2026-005]
build_id: 232d0cdc48c25d8cd986013ea21b8060fd37336f
started_at: 2026-08-13T20:05:00+08:00
finished_at: 2026-08-13T20:27:36+08:00
supersedes: null
```

## 目的、范围和门槛

- 目的：把独立学科复核与 QA 双签从文字要求落实为版本化、逐条覆盖、可失败的机器门，避免遗漏条目、数据漂移、自签或只给总体结论。
- In scope：`independent-review.v1` schema、待签复核包、复核指南、30 个概念/40 条关系/50 个锚点的精确覆盖、内容摘要绑定、分歧裁决、学科/QA 身份分离及完成态与 `gold.json` 审批态同步。
- Out of scope：替代真人学科判断、替项目负责人指派复核者、签署风险接受、bbox/区域级金标、parser/LLM 质量和真实 Provider 调用。
- 普通门通过定义：待签模板结构合法、覆盖完整且绑定当前金标内容；仓库日常开发可继续处理同一工作项。
- 完成门通过定义：所有逐条决定完成、分歧被独立裁决、许可确认、学科与 QA 由不同人员按序签字，且数据集状态同步为 `approved`。
- 本轮预期状态：普通门 PASS；`--require-complete` 必须以稳定错误 `calculus_review_invalid` 和退出码 1 失败。这是门禁正确阻止提前关闭，不是测试失败。

## 冻结环境

```text
OS: Microsoft Windows 11 Home China 10.0.26200 / x64 / Asia/Shanghai
CPU: AMD Ryzen 9 7940HX with Radeon Graphics
RAM: 16,334,233,600 bytes
locale: zh-CN
Python: 3.12.6 / uv 0.12.3 / pypdf 6.15.0
Node: 24.14.1 / pnpm 11.19.0
commit: 232d0cdc48c25d8cd986013ea21b8060fd37336f
uv.lock sha256: b0655498ba30cf987d8059291e1bbdada717185ab68871af369fb67d3b13f7cf
pnpm-lock.yaml sha256: 457e5378ea60e6451ec4e352e2ba3db35dec4d4f051efb3e8e6cf3ad966261ba
gold.json sha256: 53268e3b7b54a9596ac73fc0e6096c5e8aa1941a534be0635591d42510d0e299
review subject sha256: 6e31f3fc332510b379a864c780488cf2acd32e9d4f9fad2b96076ae4603467a3
independent-review.json sha256: 3545fe1a84783e291d6cb69e511c3ffa1edd9e5c6d65a1788fc09658ce0c38f5
independent-review.schema.json sha256: e39bfa5f5f7ef16f511ed3d0e1be63446fa96dffae79e5b07a0e4c1800c8481d
dataset: calculus-continuity-differentiability-v1 / 1.0.0-draft.1 / author_reviewed
review: independent-review.v1 / subject=pending / qa=pending
Provider/model/prompt/sampling/seed: none/not applicable
network: none; no LLM or external service calls
```

## 方法

- 先以未签模板和完成态伪造变异建立失败测试，再实现最小 schema、领域校验器与 CLI；复核校验代码不依赖 FastAPI、数据库、LLM SDK 或存储实现。
- 内容摘要对规范化金标计算，只排除可变审批元数据 `status` 与 `review`；概念、关系、锚点、来源、许可或其他内容变化都会使旧复核包失效。
- 变异覆盖：摘要漂移、条目缺失/重复、未解释分歧、未完成逐条决定、身份/时序错误、自行裁决、未解决分歧、许可未确认、学科/QA 同人，以及完成签字与数据集审批不同步。
- 仓库默认门校验当前待签包；当金标或 QA 出现完成态时自动升级为完成门，不能靠漏传 `--require-complete` 绕过。
- 执行 `AGENTS.md` 的完整 Python/Web 本地门、专用普通门、预期失败完成门及 `git diff --check`。

## 结果

| Test ID | 场景 | Expected | Actual | Result | Bug | Evidence |
|---|---|---|---|---|---|---|
| TC-DATA-006 | 待签模板绑定与 30/40/50 覆盖 | 普通门通过 | 30/40/50；subject/QA 均 pending；退出 0 | PASS | — | validator / contract tests |
| TC-DATA-006 | 数据漂移、缺项、重复与伪签字变异 | 全部被拒绝 | 相关负向测试全部通过 | PASS | — | `test_calculus_dataset.py` |
| TC-DATA-006 | 分歧、裁决、身份分离与签字时序 | 合法完成样本通过；非法状态失败 | 正/负向组合全部符合预期 | PASS | — | `test_calculus_dataset.py` |
| TC-DATA-006 | 当前待签包执行完成门 | 稳定失败，退出 1 | `FAIL [calculus_review_invalid]: independent review is incomplete`；退出 1 | PASS | — | evidence gate summary |
| TC-BUILD-001 | 仓库完整本地门 | 全部返回 0 | Python 43/43、Web 1/1，format/lint/type/peer/build 全绿 | PASS | — | evidence gate summary |

专用合同文件共收集 33 个测试，其中 19 个直接覆盖新增独立复核门；仓库总计 43 个 Python 测试。完成门的非零退出为当前状态的预期证据，未被计为失败门。

## 证据完整性

- Evidence manifest：`evidence/TR-20260813-004/manifest.json`。
- checksums：`evidence/TR-20260813-004/checksums.sha256`；实现输入和锁文件摘要同时冻结在环境记录中。
- 命令、普通门/完成门结果和全仓摘要位于同一证据目录。
- 脱敏检查：仅含公开教材标识、公开许可、工具版本、摘要和测试结果；无用户内容、API Key、Provider 请求/响应或本机秘密。

## 结论

- Decision：CONDITIONAL GO——独立复核执行包与防绕过门已实现并验证，可交付真实独立学科复核者和 QA 使用。
- 工作项状态：仍为 `verification`；数据集仍为 `author_reviewed`，不是 `approved`。
- 阻断缺陷：本轮自动化范围内无；关闭 WORK-2026-004 仍被真实独立学科复核和独立 QA 签字阻断。
- 风险接受：无；自动门不能替代学科责任或 QA 风险接受。
- 下一步 Owner：项目负责人指派两名不同人员；学科复核者逐条填写复核包并处理分歧，QA 在其后核对许可、证据和门禁，再创建新的独立签字报告。不得改写本报告或 `TR-20260813-003`。
