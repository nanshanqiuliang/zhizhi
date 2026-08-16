# WORK-2026-047：完整编辑工具箱（自由建块 / 接线 / 断线）+ 拖拽后跳变修复

```yaml
status: ready
type: feature
owner: web + api + QA
reviewers: [project_owner, qa]
related_ids: [WORK-2026-040, WORK-2026-045, REQ-2026-001, NFR-2026-001]
target_stage: 第 10 步后反馈修复
risk: low
created_at: 2026-08-16T00:00:00Z
updated_at: 2026-08-16T00:00:00Z
```

## 问题与结果

- 用户/工程问题：
  ① 拖拽移动 block 后画布仍发生跳变偏移——根因：真实浏览器在 pointerup 后会补发
  `click`，节点 `onClick=selectNode` 调 `centerOnNode` 重定心相机，拖拽结束后画布
  整体跳动（WORK-2026-040 只修了拖拽起点，未修拖拽后的 click）。
  ② 编辑功能不完整：只有「添加子概念」，没有自由建块（自行绘图）、块间连线（自行
  接线）、总纲/根节点、断线等；且边类型在 UI 往返中被硬编码为 `related_to`
  （`api.ts` snapshotToGraph L238），AI 草案产生的 `prerequisite_of` 等类型在保存时丢失。
- 期望结果：画布上可自由添加概念块与总纲块并拖到任意位置；可进入「连线」模式点选
  两个块建立带类型（相关/先修/包含/举例）的连线；可在详情面板断开连线；拖拽后画布
  不跳变；边类型在保存/加载往返中保留。
- 成功如何被观察：① 拖拽释放后（含随后 click）相机不变；普通点击仍居中；② 「添加
  概念」「添加总纲」生成无父连线的自由块；③ 「连线」模式先点起点再点终点生成指定
  类型连线；④ 详情面板「关联关系」可删除连线；⑤ 保存→重载后边类型不丢失。

## 范围

- In scope：
  - 跳变修复：`suppressRecentOnClick` ref——`endDrag`（有位移时）置位，`selectNode`
    消费并跳过 `centerOnNode`；普通点击仍居中。
  - `api.ts`：`ConceptEdge` 增可选 `edge_type`（`EdgeKind`）；`snapshotToGraph` 用
    `edge.edge_type ?? "related_to"`；`graphToSnapshot` 回填类型。
  - 画布工具栏：`添加概念`（自由块，视口中心放置，无父连线）、`添加总纲`（root）、
    `连线`（模式切换 + 边类型选择 + Esc 退出 + 起点高亮）；连线模式点击不选中/不居中。
  - 详情面板：「关联关系」列表（选中节点相邻边：指向/来自 + 类型标签 + 删除按钮），
    关系锁保护（两端的 `relations` 锁任一为真则拒绝断线）。
  - 边渲染：`<path>` 增加 `aria-label="连线：A → B（类型）"`（可测、可定位）。
  - 红绿灯 Web 测试 + api 转换测试；全部门禁 + 桌面重建 + QA。
- Out of scope：拖拽时实时橡皮筋预览线；边编辑（改类型）；右键菜单；多选。
- 受影响模块/接口/数据：仅 `apps/web`（App.tsx、api.ts、styles.css、测试）。无契约/
  迁移；后端 diff 保存路径不变（WORK-2026-022 自动生成 create/delete_edge）。
- 依赖和假设：后端提交门已支持 create_concept/create_edge/delete_edge（user 起源、
  confidence null、四维锁）；diff 保存按 from/to 计算边变更，类型经快照往返保留。

## 风险影响

- 数据/schema/migration：无 canonical 契约变化；修复了保存时边类型被改写成
  related_to 的往返缺陷（向前兼容：旧数据无类型按 related_to 处理）。
- 安全/隐私：无变化。
- 并发/幂等/恢复：沿用既有提交门/自动保存/撤销；断线/连线均入历史可撤销。
- 性能/容量/成本：无显著变化。
- 可观测性/诊断：无变化。
- 用户文档：`USER_MANUAL` 补充画布编辑说明（自由建块/连线/断线）。

## 验收标准

- [ ] AC-1：拖拽节点后释放（含浏览器补发的 click）相机不跳变；普通点击节点仍居中。
- [ ] AC-2：`添加概念`/`添加总纲` 生成无父连线的自由块，位置在视口中心（无上界钳制）。
- [ ] AC-3：连线模式：起点→终点生成所选类型边；同点自连被拒；关系锁阻止连线/断线。
- [ ] AC-4：详情面板可删除选中节点的相邻连线。
- [ ] AC-5：边类型经 snapshotToGraph/graphToSnapshot 往返保留（默认 related_to）。
- [ ] 错误和恢复路径：重复连线被拒并提示；Esc/再点按钮退出连线模式。
- [ ] 回滚/禁用方法：回退实现提交即回旧行为（含旧边类型改写缺陷）。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-EDIT-001 | Web | 拖拽后 click 不重定心 | 相机 transform 不变 | `App.edit.test.tsx` |
| TC-EDIT-002 | Web | 普通点击居中 | 相机 transform 变化 | 同上 |
| TC-EDIT-003 | Web | 添加概念/总纲自由块 | 新块无父连线、root tone | 同上 |
| TC-EDIT-004 | Web | 连线模式建立带类型边 | `连线：A → B（先修）` 出现 | 同上 |
| TC-EDIT-005 | Web | 详情面板断线 | 边消失 | 同上 |
| TC-EDIT-006 | api | 边类型转换往返 | 默认/保留类型 | `api.test.ts` |
| TC-EDIT-007 | 全部门禁 | 既有测试不回归 | Web 全量 + pytest + 构建绿 | 门禁输出 |
| TC-EDIT-008 | desktop e2e | 冻结产物冒烟 | 18/18 | `scripts/desktop_e2e.py` |

## 交付物与关闭

- Commit/PR：红灯测试 → 实现 → 文档 → 证据封存。
- Contract/ADR/migration/prompt：无。
- Test Run：Web 全量、pytest、ruff/mypy/validator/pnpm。
- Release：桌面 exe/安装器/zip 重建。
- 观察结果：QA 封存 `TR-20260815-009`。
- 未完成项的新 ID：拖拽橡皮筋预览、边类型编辑（如需要另立）。
