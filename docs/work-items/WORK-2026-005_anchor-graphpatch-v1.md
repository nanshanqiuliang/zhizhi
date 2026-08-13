# WORK-2026-005：冻结 Anchor / GraphPatch v1 并实现纯领域验证

```yaml
status: ready
type: spike
owner: Codex (domain/contracts implementation role)
reviewers: [ai_qa_auditor, workspace_owner]
related_ids: [REQ-2026-007, REQ-2026-008, REQ-2026-009, REQ-2026-010, NFR-2026-001, NFR-2026-002, NFR-2026-003, ADR-0001, ADR-0004, ADR-0006, ADR-0012, ADR-0016, RISK-2026-001, RISK-2026-002, RISK-2026-003]
target_stage: "阶段 0 / 自然语言第 2 步"
risk: high
created_at: 2026-08-14T00:00:00+08:00
updated_at: 2026-08-14T00:00:00+08:00
```

## 问题与结果

- 用户/工程问题：笔记、节点、连线、来源位置和人工锁定目前只有架构描述，没有可执行 contract。前端、存储和 AI 若各自定义写入语义，会产生循环、错跳、覆盖人工内容和无法撤销的问题。
- 期望结果：冻结最小 `Anchor v1`、`GraphPatch v1` 和核心 enum，并用不依赖框架/数据库/LLM 的纯领域 validator 证明关键不变量。
- 成功如何被观察：合法 patch 可得到确定性预览；无效 schema、陈旧 revision、缺失目标、锁定覆盖、重复/自环/跨课程边、先修环和 AI 无证据边以稳定错误失败；同一输入产生同一结果且不修改原图。

## 范围

- In scope：JSON Schema 单一事实源；Anchor 的 source state/selectors/status；课程图最小 snapshot；GraphPatch actor/confirmation/operations；概念、边、布局和锁定操作；DAG/版本/证据/锁校验；纯 Python validator；contract/property/security tests；TypeScript 类型生成入口设计。
- Out of scope：数据库写入与 migration、FastAPI/OpenAPI、React Flow 页面、PDF.js resolver、真正 undo/redo 持久化、merge/split/snapshot、AI/Provider、网络和用户真实内容。
- 受影响模块/接口/数据：`packages/contracts-*`、`packages/domain`、`docs/contracts`、`tests/contract|unit|security`；不接入产品数据库。
- 依赖和假设：WORK-2026-002 的个人 MVP 开发默认值已由 `TR-20260814-001` QA PASS；ADR-0016 的正式 owner 接受不是离线 spike 的前置条件，但阶段出口前仍需确认；业务 ID 使用 UUIDv7；JSON Schema 2020-12；当前只需要内存 snapshot 证明领域语义。

## v1 最小契约

### Anchor v1

- `resource_id`、`resource_version_id`、`source_state.content_hash` 和 parser identity 必填。
- selectors 支持 `page_bbox`、`text_quote`、`text_position`、`heading_path`；至少一个。
- page 从 1 开始；bbox 为左上原点 `[x0,y0,x1,y1]` 且 `0 <= x0 < x1 <= 1`、`0 <= y0 < y1 <= 1`。
- text position 为半开区间 `[start,end)` 且 `0 <= start < end`；quote exact 只允许定位所需短摘录。
- 状态 enum：`valid|recovered|ambiguous|drifted|missing`；本工作项只验证/存储，不实现解析恢复算法。

### CourseGraph snapshot v1

- 最小节点：id/course/label/origin/review state/revision/四维 locks（content、relations、position、annotations）。
- 最小边：id/course/source/target/type/origin/review state/confidence/evidence IDs/locked/revision。
- 最小 layout item：view/concept/x/y/pinned/revision。
- `prerequisite_of` 必须保持 DAG；其他关系允许环。

### GraphPatch v1

- 顶层绑定 patch/course/base revision/actor/reason/confirmation/operations。
- 本 spike 白名单：`create_concept`、`update_concept`、`create_edge`、`set_lock`、`upsert_annotation`、`set_layout_item`。
- 每个 operation 有 `op_id`；修改既有目标必须携带 `expected_updated_revision_no`。
- user patch 默认仍要求 confirmation，只有显式 `confirmed=true` 才可进入 apply-ready；AI/import/system patch 始终 `requires_confirmation=true` 且不能在本工作项 apply。
- validator 只返回预览后的新 snapshot 与 findings；不写数据库、不改变输入、不执行副作用。

## 风险影响

- 数据/schema/migration：首次产品 contract，版本为 v1；没有数据库 migration。后续物理模型必须映射而不能改变其含义。
- 安全/隐私：不含用户真实内容；quote 设置长度上限；validator 无文件/网络/数据库能力。
- 并发/幂等/恢复：`base_revision_no` 和 target expected revision 检测陈旧写；重复 op/target 组合失败关闭；真正 operation log/恢复后置。
- 性能/容量/成本：以小图和 500 节点工程初值做线性/近线性验证；不调用模型，无费用。
- 可观测性/诊断：异常使用稳定 snake_case code，details 只含 ID/cycle path/op id，不含笔记正文。
- 用户文档：无可见功能，不修改 USER_MANUAL 的可用能力声明。

## 验收标准

- [ ] AC-1：Anchor/GraphPatch/graph snapshot schema 可由 Draft 2020-12 validator 重跑，enum 只在 schema 定义。
- [ ] AC-2：合法 user patch 产生确定性预览，input graph/patch 不变；确认状态明确。
- [ ] AC-3：AI/import/system patch 无法绕过 preview/confirmation 或修改任一 locked 维度。
- [ ] AC-4：`prerequisite_of` 的自环、重复边和任意长度环返回 `graph_cycle_detected` 或稳定对应错误，并给 cycle path/op id。
- [ ] AC-5：revision 漂移、目标缺失、端点跨 course、证据缺失、非法 selector/bbox/quote 均失败关闭。
- [ ] AC-6：人工创建不伪造 AI confidence；AI concept 至少有 source mention/evidence reference，AI prerequisite edge 至少一个 evidence ID。
- [ ] AC-7：属性测试覆盖任意成功 patch 后 DAG、locked 不变、输入不可变和确定性。
- [ ] 错误和恢复路径：每个拒绝不产生部分 snapshot；调用方可基于 code/details 修正或刷新后重试。
- [ ] 回滚/禁用方法：删除/回退未接入产品的 v1 schema/validator 即可；不得用旧草案绕过后续 accepted contract。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-GRAPH-001 | contract | 三份 v1 schema 正/负 fixture | 合法通过，非法路径稳定失败 | 待 TR |
| TC-GRAPH-002 | unit | create/update/edge/lock/annotation/layout | 预览确定且 input 不变 | 待 TR |
| TC-GRAPH-003 | property | 任意成功 prerequisite patch | 结果始终 DAG | 待 TR |
| TC-GRAPH-004 | security | AI 覆盖四维 lock/绕过 confirmation | 全部拒绝 | 待 TR |
| TC-GRAPH-005 | concurrency | base/target revision 漂移 | `revision_conflict` | 待 TR |
| TC-ANCH-001 | contract/property | page/bbox/text/heading selectors | 边界正确，非法坐标/范围拒绝 | 待 TR |

## 交付物与关闭

- Commit/PR：待实现；分支 `feature/WORK-2026-005-anchor-graphpatch-v1`。
- Contract/ADR/migration/prompt：Anchor/GraphPatch/graph snapshot v1 schema；补齐 ADR-0001/0004/0006/0012；无 migration/prompt。
- Test Run：待建立。
- Release：无；仅阶段 0 prototype contract。
- 观察结果：待实现与职责隔离 QA。
- 未完成项的新 ID：持久化/revision/undo、API、UI、resolver、parser 分别进入后续工作项，不在本 spike 偷跑。
