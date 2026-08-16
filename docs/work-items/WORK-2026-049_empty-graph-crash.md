# WORK-2026-049：空工作区（0 节点）渲染崩溃修复（BUG-2026-001）

```yaml
status: ready
type: bugfix
owner: web + QA
reviewers: [project_owner, qa]
related_ids: [BUG-2026-001, WORK-2026-014, WORK-2026-045, WORK-2026-047, REQ-2026-001]
target_stage: 第 11 步 Beta 加固与扩展
risk: low
created_at: 2026-08-16T00:00:00Z
updated_at: 2026-08-16T00:00:00Z
```

## 问题与结果

- 用户/工程问题：契约允许空图（`concepts` 无 minItems），`loadGraph` 返回 0 节点时
  App 渲染崩溃（`Cannot read properties of undefined (reading 'tone')`，QA
  `TR-20260815-008` P-008 首报，`BUG-2026-001` 在案）。除加载路径外，复查发现
  **用户在 UI 内即可触发的同类路径**：删除最后一个节点时 `deleteSelected` 读取
  `parent.id`（`parent` 为 undefined）、空图上加块后撤销时 `restoreDrafts` 读取
  `node.id`——同样崩溃。
- 期望结果：0 节点时应用不崩溃，右侧详情面板替换为空态引导（提示 + 「添加总纲」
  按钮，复用 `addConcept("root")`）；删除最后一个节点、撤销回空图、加载空图
  三条路径均安全落到空态。
- 成功如何被观察：① `loadGraph` 返回空 concepts 时 App 正常渲染空态引导；
  ② 空态点「添加总纲」出现新总纲块且可继续编辑；③ 删除唯一节点后显示空态、
  不崩溃；④ 空图加块后撤销回到空态、不崩溃；⑤ 既有 Web 测试全绿。

## 范围

- In scope：
  - `apps/web/src/App.tsx` 四处防御 + 空态 UI：
    1. 详情面板渲染守卫：`present.nodes.length === 0` 时渲染空态引导区块
       （复用 `detail-panel`/`edge-empty`/`primary-button` 样式），不渲染
       依赖 `selectedNode` 的详情内容；
    2. 加载路径（`loadGraph` 成功分支）：仅当 `saved.nodes[0]` 存在时恢复选中，
       不再回退到示例节点（避免选中一个不在图中的节点）；
    3. `restoreDrafts`：`node` 不存在时直接返回（覆盖撤销/重做回空图）；
    4. `deleteSelected`：删除最后一个节点后 `parent` 不存在时跳过选中恢复。
  - 测试：`apps/web/src/App.empty.test.tsx`（新文件，4 个用例覆盖上述路径）。
  - 文档：BUG_REGISTER 状态流转、ENGINEERING_PLAN/DEVELOPMENT_LOG/
    TRACEABILITY_MATRIX 登记。
- Out of scope：后端强制非空图（契约保持允许空图，属有意设计）；空态下的
  onboarding 引导增强（导入资料教学等，后续 UX 切片）；负坐标/视口居中。
- 受影响模块/接口/数据：仅 `apps/web/src/App.tsx` 渲染与本地状态恢复；无
  契约/API/持久化变化。
- 依赖和假设：无新依赖；空态文案与既有 UI 风格一致。

## 风险影响

- 数据/schema/migration：无（纯前端渲染防御）。
- 安全/隐私：无新增面。
- 并发/幂等/恢复：撤销/重做/删除路径在空图边界从崩溃变为安全空态，行为
  兼容性仅限异常边界（原行为是崩溃）。
- 性能：无影响（单次 length 判断）。
- 可观测性：空态为可见 UI 状态，无需日志。
- 用户文档：USER_MANUAL 空态说明一句话补充。

## 验收标准

- [ ] AC-1：`loadGraph` 返回 `{nodes: [], edges: []}` 时 App 渲染空态引导而非崩溃。
- [ ] AC-2：空态「添加总纲」创建 root 块并进入正常编辑流。
- [ ] AC-3：删除唯一未锁定叶节点后进入空态，无崩溃。
- [ ] AC-4：空图上加块后撤销回到空态，无崩溃。
- [ ] 回滚：回退本提交即回到崩溃行为；无数据迁移。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-EMPTY-001 | web 单测 | 空图加载 | 空态引导渲染、无 TypeError | `App.empty.test.tsx` |
| TC-EMPTY-002 | web 单测 | 空态添加总纲 | root 块出现、详情恢复 | 同上 |
| TC-EMPTY-003 | web 单测 | 删除最后一个节点 | 空态、无崩溃 | 同上 |
| TC-EMPTY-004 | web 单测 | 撤销回空图 | 空态、无崩溃 | 同上 |
| TC-EMPTY-005 | 全部门禁 | 回归 | pytest + Web + 构建绿 | 门禁输出 |

## 交付物与关闭

- Commit/PR：红灯测试 → 实现 → 文档 → 证据封存。
- Contract/ADR/migration/prompt：无。
- Test Run：`TR-20260816-001`。
- Release：桌面产物随下一切片统一重建（本修复不单独发版）。
- 观察结果：BUG-2026-001 → ready_for_release（随产物发布后 closed）。
