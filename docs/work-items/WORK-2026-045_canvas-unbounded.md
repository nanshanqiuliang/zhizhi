# WORK-2026-045：画布无限延伸（去钳制 + 随内容生长）

```yaml
status: ready
type: feature
owner: web + QA
reviewers: [project_owner, qa]
related_ids: [WORK-2026-043, WORK-2026-046, REQ-2026-001]
target_stage: 第 10 步后反馈修复
risk: low
created_at: 2026-08-16T00:00:00Z
updated_at: 2026-08-16T00:00:00Z
```

## 问题与结果

- 用户/工程问题：知识树画布被硬编码在 1000×650（`.canvas-surface` 固定尺寸、
  `overflow: hidden`；`edge-layer` SVG `viewBox="0 0 1000 650"`），且节点拖拽被钳制在
  x∈[8,835]、y∈[8,555]（`App.tsx` `moveDrag` 的 `Math.min(835/555)`）。后果：① 一次
  全库思维导图（WORK-2026-043/046，上限 5000 操作）的自动布局可远超 1000×650，大量
  节点落在画布外不可见、不可达；② 用户想把节点拖到更远位置时被"钉"在边界。
- 期望结果：画布随内容生长（无固定上界，保留 1000×650 下限）；节点可拖到任意远；
  边层 SVG viewBox 与画布尺寸同步；缩放/平移不受影响。
- 成功如何被观察：① 把节点拖过旧边界（x>835 或 y>555）后节点停在目标位置而非边界；
  ② 拖远后 `.canvas-surface` 宽高与 `edge-layer` viewBox 随内容变大；
  ③ 自动排布/接受 AI 草案的超大布局不被裁剪。

## 范围

- In scope：`moveDrag` 去掉上界钳制（保留 x/y≥8 下限防节点不可达）；新增纯函数
  `canvasSurfaceSize(nodes)`（内容包围盒 + 边距，下限 1000×650）并应用于
  `.canvas-surface` 内联宽高与 `edge-layer` 的 viewBox/宽高；图例移出变换画布
  （锚定视口，不随巨大画布漂移）；红绿灯 Web 测试；全部门禁 + 桌面重建 + QA。
- Out of scope：负坐标处理（布局从 (0,0) 出发、拖拽保留 ≥8 下限，负坐标裁剪为已知
  残留）；自动布局函数本身（`layoutWorkspace`/`assign_draft_layout` 已无界，不钳制）；
  视口自动居中/跟随；性能基准（超大画布渲染）。
- 受影响模块/接口/数据：仅 `apps/web`（`App.tsx`、`styles.css`、新测试）。无契约/迁移。
- 依赖和假设：节点宽高固定 150×68（CSS）；相机变换作用于整个 surface；缩放时拖拽
  delta 已按 `camera.zoom` 折算；默认 `camera.zoom=1` 时 jsdom 测试可精确断言坐标。

## 风险影响

- 数据/schema/migration：无（纯前端渲染）。
- 安全/隐私：无变化。
- 并发/幂等/恢复：无变化（坐标仍是普通数值，走既有提交门/自动保存）。
- 性能/容量/成本：超大画布（如 5000 操作草案 → 数万像素宽）的 grid 背景与 SVG 渲染
  开销线性增长；默认视口只绘制可视部分（overflow hidden），可接受；不做基准。
- 可观测性/诊断：无变化。
- 用户文档：`USER_MANUAL` 画布说明可补一句"画布随内容无限延伸"。

## 验收标准

- [ ] AC-1：拖拽节点至 x>835 / y>555 后节点坐标等于目标（去钳制）。
- [ ] AC-2：画布表面宽高随节点包围盒增长（>1000×650），`edge-layer` viewBox 同步。
- [ ] AC-3：空画布/示例图保持 1000×650 下限，既有拖拽/缩放/平移测试不回归。
- [ ] 错误和恢复路径：无新增错误路径；坐标下限仍 ≥8。
- [ ] 回滚/禁用方法：回退实现提交即回固定画布。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-CANVAS-001 | Web | 节点拖过旧边界 | 坐标 >835/555 | `App.canvas.test.tsx` |
| TC-CANVAS-002 | Web | 拖远后表面/viewBox 增长 | 宽高 >1000×650 且 viewBox 同步 | 同上 |
| TC-CANVAS-003 | Web | `canvasSurfaceSize` 纯函数 | 空→1000×650；大坐标→包围盒+边距 | 同上 |
| TC-CANVAS-004 | 全部门禁 | 既有测试不回归 | Web 全量 + pytest + 构建绿 | 门禁输出 |
| TC-CANVAS-005 | desktop e2e | 冻结产物冒烟 | 18/18 | `scripts/desktop_e2e.py` |

## 交付物与关闭

- Commit/PR：红灯测试 → 实现 → 文档 → 证据封存。
- Contract/ADR/migration/prompt：无。
- Test Run：Web 全量（53→56+）、pytest、ruff/mypy/validator/pnpm。
- Release：桌面 exe/安装器/zip 重建。
- 观察结果：QA 封存 `TR-20260815-008`。
- 未完成项的新 ID：负坐标裁剪与视口自动居中（如需要另立）。
