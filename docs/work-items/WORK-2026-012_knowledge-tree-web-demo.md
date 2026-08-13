# WORK-2026-012：交付可操作的示例数据知识树 Web Demo

```yaml
status: ready
type: feature
owner: Codex (web frontend role)
reviewers: [ai_qa_auditor, workspace_owner]
related_ids: [REQ-2026-001, REQ-2026-006, REQ-2026-008, NFR-2026-001, WORK-2026-005, WORK-2026-011, TR-20260814-002, TR-20260814-003]
target_stage: "阶段 1 / 自然语言第 3 步"
risk: medium
created_at: 2026-08-14T02:00:00+08:00
updated_at: 2026-08-14T02:00:00+08:00
```

## 问题与结果

- 用户/工程问题：当前 Web 只有工程状态页，用户看不到笔记 App 或知识树。底层合同已经足够稳定，可以先用示例数据证明核心交互，而不等待数据库和真实 AI。
- 期望结果：把状态页替换为桌面优先、移动可用的三栏知识树工作台；用户可选择节点、编辑标题/笔记、添加子概念、删除叶节点、拖动位置、自动排布，并在当前会话撤销/重做。
- 成功如何被观察：启动 Web 后第一屏就是微积分示例知识树；完成“选择极限 → 添加子概念 → 修改内容 → 撤销/重做 → 拖动/自动排布”不需要命令行。

## 范围

- In scope：React 内存状态、版本化示例数据、三栏布局、课程/笔记列表、SVG/HTML 树状画布、节点和连线、选择/编辑、添加子节点、删除叶节点、Pointer 拖动、自动树状布局、会话 undo/redo、空态/状态提示、响应式/键盘/可访问性、组件/交互/浏览器视觉测试。
- Out of scope：Python API、SQLite、刷新持久化、文件导入、PDF viewer、真实 GraphPatch 网络调用、多人、Tauri、AI/DeepSeek、自动生成知识树、来源定位、完整 React Flow/ELK 500 节点性能。
- 受影响模块/接口/数据：仅 `apps/web` 与 user-facing/engineering docs；不改 canonical graph schema、domain 或数据库。
- 依赖和假设：示例数据明确标记为 Demo；当前 Web 可用原生 React/SVG 实现 8–12 节点树，不为小切片新增大型图形依赖；后续 API 接入时以 GraphPatch/History 替换本地 reducer。

## UI/交互边界

- 桌面：顶部工具栏；左 260px 笔记/课程；中间可滚动画布；右 300px 详情。窄屏按画布→详情→笔记堆叠，所有操作仍可达。
- 画布节点使用 button 语义；选中、锁定、来源数量可辨识；连线不抢焦点。
- 添加子节点要求先选中父节点；删除仅允许叶节点，避免隐式级联；失败给可见提示。
- 拖动只改当前会话位置；自动排布保留“固定位置”节点；锁只在 Demo 中展示/切换 position 标记，不宣称真实 AI 重建保护已接入。
- undo/redo 为前端当前会话 reducer，明确“不保存，刷新会复位”；不冒充 WORK-2026-011 Python history 已经接入浏览器。

## 风险影响

- 数据/schema/migration：只用非真实 fixture；无 schema/migration。前端局部类型不得重新定义 canonical enum；需要 enum 时从 contracts-ts 导入。
- 安全/隐私：不读取文件/网络/secret；示例笔记为自写短文本。
- 并发/幂等/恢复：单页内存；刷新丢失并明确提示。undo/redo 仅本会话，不声称崩溃恢复。
- 性能/容量/成本：目标 12 节点内流畅；不做 500 节点性能声明；无模型费用。
- 可观测性/诊断：用户状态条显示成功/限制；控制台无 error；不记录正文遥测。
- 用户文档：更新路线与 USER_MANUAL 的“当前可用 Demo/不可用”边界。

## 验收标准

- [ ] AC-1：第一屏显示“微积分”课程、至少 6 个树节点和方向连线，节点可键盘/鼠标选择，详情与笔记联动。
- [ ] AC-2：编辑标题/笔记、添加子概念、删除叶节点均有组件测试；删除非叶节点失败且不丢数据。
- [ ] AC-3：pointer 拖动改变节点位置；自动排布恢复树状层级并保留 position-locked 节点。
- [ ] AC-4：undo/redo 覆盖编辑、添加、删除和位置变化；新操作清空 redo；按钮 disabled 状态正确。
- [ ] AC-5：桌面 1440×900 与移动 390×844 无横向页面溢出，主要操作可见，focus/aria/contrast 基本合格。
- [ ] AC-6：界面明确“示例数据 / 仅本次会话 / AI 未连接”，不声称保存、导入、来源回跳或 AI 构图已可用。
- [ ] 错误和恢复路径：无选择、非叶删除、空标题以可见状态提示；可撤销或重新载入示例。
- [ ] 回滚/禁用方法：回退 WORK-2026-012 提交恢复工程状态页；不影响 contracts/domain evidence。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-WEB-001 | component | 初始三栏/示例树/状态边界 | 结构和免责声明可读 | 待红灯/TR |
| TC-WEB-002 | interaction | select/edit/add/delete | state 与 UI 一致，限制失败关闭 | 待红灯/TR |
| TC-WEB-003 | interaction | drag/auto layout/lock | 位置改变，locked 保留 | 待红灯/TR |
| TC-WEB-004 | reducer | undo/redo/branch/reset | 栈语义正确 | 待红灯/TR |
| TC-WEB-005 | accessibility | keyboard/labels/focus/disabled | 关键控制可达 | 待红灯/TR |
| TC-WEB-006 | browser | 1440×900/390×844 | 无页面横溢，布局可用 | 待截图/TR |

## 交付物与关闭

- Commit/PR：分支 `feature/WORK-2026-012-knowledge-tree-web-demo`；先提交失败组件测试，再提交最小 UI。
- Contract/ADR/migration/prompt：复用现有 contracts-ts enum；无新 contract/ADR/migration/prompt。
- Test Run：Vitest、TypeScript、ESLint、production build、浏览器 desktop/mobile；全仓门按 DoD 执行。
- Release：无托管发布；本地 `pnpm --filter @knowledge-tree/web dev` 可预览。
- 观察结果：待实现，不提前声明 App 已完成。
- 未完成项的新 ID：API/SQLite persistence、文件导入、viewer/source resolver、真实 GraphPatch bridge、AI 草案分别后续建项。
