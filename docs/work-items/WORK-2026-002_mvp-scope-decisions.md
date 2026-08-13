# WORK-2026-002：冻结个人笔记 App 首版范围

```yaml
status: in_progress
type: docs
owner: workspace_owner / product role
reviewers: [technical_owner, qa]
related_ids: [REQ-2026-001, REQ-2026-006, REQ-2026-007, REQ-2026-008, REQ-2026-009, REQ-2026-010, ADR-0016]
target_stage: "阶段 -1 / 自然语言第 1 步"
risk: medium
created_at: 2026-08-14T00:00:00+08:00
updated_at: 2026-08-14T00:00:00+08:00
```

## 问题与结果

- 用户/工程问题：产品愿景已经明确，但支持平台、首批格式、数据删除、AI 权限、概念粒度和多人边界仍散落在 Proposal/架构建议中，后续实现容易反复返工。
- 期望结果：把用户已认可的自然语言路线和安全默认值固化为可执行的个人 MVP 产品边界；无法安全代替用户决定的付费预算和公开发布治理继续失败关闭。
- 成功如何被观察：架构第 21 节十项问题都有明确答案、延期责任或禁用边界；WORK-2026-005 可以在不依赖真实 Provider、Embedding、远端仓库或许可证选择的前提下进入 Ready。

## 范围

- In scope：Windows 单用户本地优先、首批资料格式、核心离线行为、数据目录/备份/删除承诺、AI 写入确认、概念粒度、PPTX/Markdown/多人边界。
- Out of scope：确定真实 LLM 金额预算、选择 Embedding Provider、启用真实 Provider/Web、确定远端仓库公开性/项目代码许可证、实现任何产品功能。
- 受影响模块/接口/数据：产品需求、路线、工程计划和后续 Anchor/GraphPatch 设计；没有运行时数据或 API 变化。
- 依赖和假设：用户先前认可 `USER_FACING_DEVELOPMENT_ROADMAP.md` 中“除非随后修改，按默认值推进”，随后明确要求继续开发。

## 决策清单

| 架构问题 | 首版决定 | 后续边界 |
|---|---|---|
| 平台 | Windows 10/11 x64；先交付同源 Web UI，再封装 Tauri | macOS/Linux 不进入个人 MVP 打包矩阵 |
| 微积分资料 | 使用仓库已冻结的 MIT OCW 非商业 fixture 和 hash/许可记录 | 用户真实资料不得提交仓库 |
| LLM/Embedding/网络 | DeepSeek 为首个目标；金额预算和 Embedding 未批准 | live/Embedding 保持禁用，分别由 WORK-2026-007/008/009 解除 |
| 离线要求 | 笔记、图编辑、查看、搜索、备份等核心功能可离线；AI 是可选联网能力 | 首版不承诺本地大模型或完全离线 AI |
| 数据/备份/删除 | 默认使用 OS 应用数据目录；用户显式选择导出/备份位置；workspace 可确认后逻辑彻底删除其原件、索引、缓存和派生数据 | SSD/备份介质上的物理不可恢复擦除不作承诺；实现前需恢复测试 |
| AI 自动接受 | 默认关闭；任何持久 GraphPatch 都先预览并由用户确认 | 将来仅能由独立策略和 owner opt-in 放宽低风险标注 |
| 概念粒度 | 每课程选择“主题/标准概念/细节”；默认标准概念；模型只能建议 | 粒度切换不得静默删除或合并锁定内容 |
| PPTX 定位 | 不进入首批格式；后续最低承诺为 slide/page 级 | shape 级只有通过专门锚点评测后才承诺 |
| Markdown/Obsidian | 首批支持 Markdown/TXT；普通链接最多生成 `related_to` 候选 | 不把文档链接自动解释为 `prerequisite_of`；完整 Obsidian vault 迁移后置 |
| 云端/多人 | 不进入个人 MVP；保留 `workspace_id` 领域边界 | 不提前实现租户、团队权限或协作 UI |

## 风险影响

- 数据/schema/migration：后续 schema 必须保留 workspace、锁维度、来源和 revision；本工作项不创建 migration。
- 安全/隐私：真实用户内容默认本地且不得进入仓库/证据；联网 AI 必须显式启用并显示将发送的范围。
- 并发/幂等/恢复：个人 MVP 仍需 operation log、幂等 patch 和备份恢复证据；本工作项只冻结承诺。
- 性能/容量/成本：真实模型金额阈值仍未知，因此所有 live deployment 保持 disabled；不产生费用。
- 可观测性/诊断：未来日志只记录 ID、大小、hash、状态和稳定错误码，不记录笔记/PDF 正文。
- 用户文档：当前没有这些用户功能；`USER_MANUAL.md` 继续只描述工程预览，不能提前宣称可用。

## 验收标准

- [x] AC-1：架构第 21 节十项问题均有决定、明确延期或安全禁用状态。
- [x] AC-2：个人 MVP 明确为 Windows 单用户、本地核心可离线、无 Docker、Web UI 与桌面共用产品逻辑。
- [x] AC-3：首批格式为 Markdown/TXT/PDF；PPTX/DOCX/OCR 和完整 Obsidian 迁移不进入首个闭环。
- [x] AC-4：AI 所有持久图修改默认预览确认，人工内容/关系/位置/标记可分别锁定。
- [x] AC-5：数据目录、导出/备份、workspace 删除及不承诺物理安全擦除的边界明确。
- [x] 错误和恢复路径：付费预算、Embedding、live、远端治理未批准时稳定保持禁用，不以占位值绕过。
- [x] 回滚/禁用方法：后续用户可通过变更请求修订产品默认值；在新决策接受前仍使用本记录。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-PLAN-001 | static | 第 21 节问题到决策逐项映射 | 10/10 有答案或禁用边界 | ADR-0016 / 本工作项 |
| TC-PLAN-002 | static/security | 未批准外部能力 | live、Embedding、owner acceptance 仍关闭 | repository validator / config |
| TC-PLAN-003 | traceability | PRD、计划、路线和工作项一致 | 无矛盾/陈旧状态 | 文档链接与仓库门 |

## 交付物与关闭

- Commit/PR：决策基线 `8ff376d0aa339143332a47500646b455148b1169`；本 superseding 提交包含 QA 修复候选，完整 SHA 由复审证据绑定；无远端 PR。
- Contract/ADR/migration/prompt：ADR-0016；REQ-2026-006..010；无 migration/prompt。
- Test Run：决策映射 10/10；基线及本次 superseding 修正的完整仓库门均通过（84 Python / 1 Web）；隔离 QA attempt 001 为 FAIL（1 P1 / 2 P2），复审待完成。
- Release：无；纯产品边界决策。
- 观察结果：内容边界完整且足以作为 WORK-2026-005 离线输入；未认证 owner 批准、冻结状态陈旧和 correlated-review 状态语义需在关闭前修复。不产生用户可见功能，不增加 live 权限或费用。
- 未完成项的新 ID：预算/Provider 为 WORK-2026-007/008；Embedding 为 WORK-2026-009；owner auth/harness 为 WORK-2026-010；仓库/许可证为 WORK-2026-003。
