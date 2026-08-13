# WORK-2026-004：建立微积分金标集与许可清单

```yaml
status: in_progress
type: spike
owner: Codex (dataset author / implementation role)
reviewers: [workspace_owner, ai_subject_reviewer, ai_qa_auditor]
related_ids: [CHG-2026-001, ADR-0015, REQ-2026-002, REQ-2026-003, REQ-2026-004, REQ-2026-005, NFR-2026-002, NFR-2026-008, NFR-2026-009, RISK-2026-001, RISK-2026-005, RISK-2026-010, RISK-2026-011]
target_stage: "阶段 -1 / 阶段 0 入口准备"
risk: high
created_at: 2026-08-13T18:25:00+08:00
updated_at: 2026-08-13T22:15:00+08:00
```

## 问题与结果

- 用户/工程问题：Anchor、解析器和 AI 质量没有合法、冻结、可复跑的微积分样本，不能开始高风险原型或评测。
- 期望结果：保留已完成的 v1 金标包和历史真人签字 contract；新增 v2 AI harness 机器复核原型，使 AI 学科/QA 子 Agent可通过受控检索/搜索和证据链自动审查 30/40/50 数据。
- 成功如何被观察：v1 证据不被改写；v2 schema 绑定数据、模型、prompt、context、tool policy、harness 与 artifact hash；mock/replay 双 Agent、同源降级、分歧裁决和安全失败可重跑。

## 范围

- In scope：既有 MIT OCW v1 fixture；`calculus-independent-review.v2` 机器证明、AI 学科/QA/裁决角色、确定性 mock harness、只读 SearchProvider fixture、evidence ledger、30/40/50 覆盖、运行隔离/同源披露、owner 风险接受边界和安全变异测试。
- Out of scope：整站镜像、完整教材再发布、习题答案、中文翻译、GraphPatch/Anchor 正式 contract、未经门禁的真实 Provider/Web 调用、Agent 直接写库/批准、商业使用。
- 受影响模块/接口/数据：`evals/calculus-v1` 测试数据与 dataset schema；不接入产品数据库。
- 依赖和假设：用户批准 MIT OCW 资料；OCW 页面和教材适用 CC BY-NC-SA 4.0，MIT 名称仅用于必要署名；项目用途保持非商业研发。

## 风险影响

- 数据/schema/migration：新增独立 eval fixture v1 schema，不是产品数据库 schema；后续 Anchor/GraphPatch 必须显式映射，不能直接复用。
- 安全/隐私：公开教材，无个人资料/秘密；不执行 PDF 内指令。
- 并发/幂等/恢复：下载按 SHA-256 固定；重复获取须校验 hash，内容变化创建新 dataset version。
- 性能/容量/成本：只保留约 719 kB 第 2 章 PDF；不调用 LLM，无模型费用。
- 可观测性/诊断：validator 返回稳定非零和具体路径；测试报告记录 PDF/hash/page/fixture 版本。
- 用户文档：非用户功能；README 和许可清单说明非商业限制。

## 验收标准

- [x] AC-1：第 2 章 PDF 来自 MIT OCW 官方资源页，记录 52 页、736149 bytes、SHA-256、获取时间和 URL；复核时远端重下摘要一致。
- [x] AC-2：dataset card/NOTICE 正确署名 Gilbert Strang、MIT OCW，链接 CC BY-NC-SA 4.0，说明修改和非商业/ShareAlike 边界。
- [x] AC-3：30 个规范概念均有稳定 ID、名称、定义摘要和至少一个来源锚点。
- [x] AC-4：40 条 prerequisite 关系端点存在、无重复、无自环、形成 DAG，并带依据锚点与标注理由；独立学科判断仍待复核。
- [x] AC-5：50 个页级锚点在 1..52 范围内，绑定 PDF SHA-256，并覆盖目标主题；不使用伪造 bbox。
- [x] AC-6：schema/语义/许可/计数自动校验及失败变异测试通过；页 1/16/37/41/45/48/51 渲染抽检通过。
- [x] 错误和恢复路径：CLI 返回稳定 `calculus_dataset_invalid` 和非零；校验失败不得进入 parser/AI eval；远端资源变化时保留旧 hash，创建新 dataset 版本。
- [x] 回滚/禁用方法：回退实现提交 `e918fdf`；不得删除上游许可/来源记录来“消除”限制。
- [x] AC-7：独立复核执行包通过 schema、dataset ID/version/hash、30/40/50 精确覆盖和签字状态校验；待签模板通过普通门，`require complete` 硬门在学科复核与 QA 均签字前以稳定错误和非零退出阻断。
- [x] AC-8：v2 machine attestation contract 完整记录 actor/run/lineage、provider/model/revision、prompt/context/tool-policy/harness/input/output hash、证据/反证、不确定性和工具轨迹。
- [x] AC-9：AI 学科与 QA 使用不同 run/prompt/context，QA 绑定冻结学科 artifact；共享会话硬失败，相同模型/Provider 自动标为 `correlated_review`。
- [x] AC-10：确定性 mock/replay harness 覆盖 accept/dispute/abstain/inconclusive、第三方裁决、30/40/50 覆盖、提示注入、工具越权、输入漂移、伪引用、超时和预算失败。
- [x] AC-11：机器审查只能进入 `machine_reviewed`/`machine_verified`；`accepted_with_owner_risk` 显式绑定 owner、风险、范围、内容 hash、policy、时间/期限，且不能豁免硬安全不变量。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-DATA-001 | contract | dataset schema 与精确计数 | 30/40/50，字段合法 | TR-20260813-003 |
| TC-DATA-002 | property | 关系端点、自环、重复与 DAG | 全部成立；变异失败 | TR-20260813-003 |
| TC-DATA-003 | contract | PDF hash/页数/anchor 边界 | 全部匹配 | TR-20260813-003 |
| TC-DATA-004 | security/legal | 署名、许可、非商业与 ShareAlike 元数据 | 缺失时失败 | TR-20260813-003 |
| TC-DATA-005 | visual | 代表页面 Poppler render | 清晰、页码/章节可辨 | TR-20260813-003 |
| TC-DATA-006 | contract/review | 独立复核包绑定、覆盖、分歧与双签门 | 待签模板合法；缺项/重复/hash 漂移/伪签字失败 | TR-20260813-004 |
| TC-AIREV-001..010 | contract/security/replay | v2 provenance、隔离、证据、搜索、失败与风险接受 | mock/replay 可重跑；所有硬不变量失败关闭 | 首轮 28/28 后经隔离学科 dispute 修复为 32/32；全套当前 75/75；正式 TR 待复核 |

## 交付物与关闭

- Commit/PR：数据集 `e918fdf915d635760a86842ba1ccee933f962ed1`；复核门 `232d0cdc48c25d8cd986013ea21b8060fd37336f`；无远端 PR。
- Contract/ADR/migration/prompt：eval fixture schema v1；v2 machine review schema + review policy/prompt/context v2；无产品 migration。
- Test Run：`TR-20260813-003`（数据集作者验证）与 `TR-20260813-004`（独立复核门验证）均为 CONDITIONAL GO；真实独立复核待完成。
- Release：无；仅非商业研发 fixture。
- 观察结果：复核门实现提交上 43/43 Python、1/1 Web 及完整本地门通过；待签包普通门通过，完成门按预期以 `calculus_review_invalid`/退出 1 阻断；此前 7 张代表页清晰可辨。
- 未完成项：v2 contract、mock harness 和安全 fixture 已实现；首轮实现提交 `73a74da` 被隔离 AI 学科子 Agent以证据自证/错绑、范围和裁决 ledger 问题判定 `dispute`，当前修复待提交并复核。v1 不接受 AI 伪签，真实联网另受 WORK-2026-007/008 门控制。
