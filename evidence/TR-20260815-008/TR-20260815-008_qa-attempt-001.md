# TR-20260815-008 QA 报告：WORK-2026-045 画布无限延伸（去钳制 + 随内容生长）

- test_run_id: `TR-20260815-008`
- reviewed_commit: `6277db7`（实现提交；HEAD `ce80bd2` 为模块拆分提交，同属本变更）
- red baseline: `16e72c4`（仅红灯测试、无实现）
- 工作项文档: `docs/work-items/WORK-2026-045_canvas-unbounded.md`
- 判定: **PASS**（0 P0 / 0 P1 / 1 P2 遗留（pre-existing，非本变更引入）/ 5 P3 观察）
- 角色隔离声明: 本报告由独立 QA 角色出具，与实现者角色分离（独立运行、独立提示词、独立工件）；**correlation 披露：`correlated_review`**——本 QA 与实现者（提交作者 Codex，AI 实现）同属自动化编排流程，可能同模型/供应商（本 QA 运行于 DeepSeek 系模型）；`human_signature=false`、`owner_acceptance=false`（机器证明不冒充人类签名，最终残余风险接受权归工作区所有者）。

---

## 1. 红灯真值（隔离 worktree，全部真实运行）

在 `git worktree add --detach` 的 16e72c4 隔离目录安装依赖后执行：

```
pnpm --filter @knowledge-tree/web exec vitest run src/App.canvas.test.tsx
```

**红灯（16e72c4，预期 3 failed）：**

| 用例 | 实际结果 |
|---|---|
| drags a node beyond the old 835/555 clamp bounds | FAIL：`expected 835 to be greater than 835`（节点被钳制在 835/555） |
| grows the canvas surface and edge layer with content | FAIL：`expected NaN to be greater than 1000`（surface 无内联宽高，固定 1000×650） |
| keeps a 1000x650 floor ... in the size helper | FAIL：`TypeError: canvasSurfaceSize is not a function`（实现不存在） |

**绿灯（HEAD=ce80bd2，含 6277db7 实现）：** 同一命令 → `3 passed`（Test Files 1 passed）。

红灯与绿灯输出分别存档：`red-run-wt.log`、`green-run.log`。worktree 已移除并 `git worktree prune`。

## 2. 全部门禁（在 HEAD 上真实运行）

| 门禁 | 结果 |
|---|---|
| `uv run python -m scripts.validate_repository` | PASS（含 secret scan、graph/LLM 契约、复习包、v2 mock/replay） |
| `uv run ruff format --check packages scripts tests apps` | 116 files already formatted |
| `uv run ruff check .` | All checks passed（证据文件加入后重跑仍 clean） |
| `uv run mypy scripts` | 16 source files，无问题 |
| `uv run python -m mypy --strict packages/contracts-py/src packages/domain/src packages/infrastructure/src apps/api apps/desktop` | 40 source files，无问题 |
| `uv run python -m pytest` | **469 passed, 5 skipped** in 25.67s（5 跳 = 实时 DeepSeek 门禁，无 key，符合预期） |
| `pnpm install --frozen-lockfile` | Already up to date |
| `pnpm peers check` | No peer dependency issues found |
| `pnpm check`（tsc + eslint --max-warnings 0 + vitest） | **15 files / 56 tests 全绿**（含 App.test 9、App.layout 3、App.persist 6、App.lock 6、App.draft 6、App.canvas 3 等） |
| `pnpm build` | OK（203ms；chunk-size 警告为既有问题） |
| `pnpm --filter @knowledge-tree/contracts-ts check` | exit 0（generate.mjs --check + tsc，无契约 drift） |

## 3. 对抗探针（vitest，真实执行，14/15 PASS）

探针脚本：`probes/App.qa-probes.test.tsx`（执行副本），输出：`probes-output.log`。

| ID | 探针 | 结果 |
|---|---|---|
| P-001 | 拖拽到 (5000,4000)：节点精确落在 (5015,4105)（origin 115/205 + delta 4900/3900，无上界）；surface 增长 5213×4221 且 viewBox 同步 | PASS |
| P-002 | 负向拖拽 (-2000,-2000)：x=y=8（≥8 下限兜住）；surface 回落 1000×650 | PASS |
| P-003 | zoom=2 拖拽：client delta 400/200 ÷ zoom → 节点精确位移（closeTo） | PASS |
| P-004 | zoom=0.5 拖拽：delta 按 zoom 折算精确（closeTo） | PASS |
| P-005 | `canvasSurfaceSize` 纯函数：[]→1000×650；{x:5000,y:3000}→5198×3116；负坐标→下限；中间节点不影响（只取最大 x/y）；边界 802/534→1000×650、803/535→1001×651 | PASS |
| P-006 | surface 内联宽高 == edge-layer viewBox == `canvasSurfaceSize(nodes)`；拖远后三者同步 | PASS |
| P-007 | `.canvas-legend` 是 `.canvas-viewport` 直接子元素（parentElement 判定），不在 `.canvas-surface` 内，无 transform | PASS |
| P-008 | 空工作区（loadGraph 返回 0 节点）渲染不报错 | **FAIL（真实缺陷，见发现 P2）** |
| P-009 | 位置锁定节点拖拽被拒（状态提示"位置已锁定"），surface 不增长（锁未被绕过） | PASS |
| P-010 | 自动排布后 surface == 布局包围盒（1000×650），viewBox 同步 | PASS |
| P-010b | 先拖远再锁定再排布：锁定节点位置保持 (5015,4105)，surface 保持 5213×4221 | PASS |
| P-011 | mock api loadGraph 返回 x=5000 节点 → surface 增长 5198×3116，节点 style left=5000px 可见 | PASS |
| P-012 | 拖远后 edge-layer path 坐标越过旧边界（course→limit 路径含 5090/4105） | PASS |
| P-013 | 滚轮缩放钳制 [0.5, 2.5]（scale(2.5) 封顶、scale(0.5) 触底） | PASS |
| P-014 | 拖节点不移动相机（transform 不变）；空白处平移仍移动相机（translate(50px,40px)） | PASS |

> 首轮 5 个失败中 4 个为探针脚本自身问题（浮点 `scale(2.000000000000001)` 断言过严、锁定/拖拽顺序逻辑错误、surface 尺寸合法变化被误判为"背景不稳"），修正断言后全部转绿；P-008 为真实产品缺陷。

## 4. 冻结 exe 探针（HTTP 层，6/6 PASS）

`dist/zhizhi/zhizhi.exe`（2026-08-16 12:56:54 重建，8,632,729 字节）：

| ID | 探针 | 结果 |
|---|---|---|
| EXE-001 | 起服务后 GET /api/health | 200 |
| EXE-002 | GET / 返回 index.html（含 #root、title） | PASS |
| EXE-003 | index.html 引用的 `/assets/*` 均在冻结包内存在（index-BEtXJdQj.js + index-DAqfXjrT.css） | PASS |
| EXE-004 | 服务端资产字节 SHA256 == 冻结包内嵌资产 SHA256（js `fc655ccd04f6`、css `0c2c9ff15181`） | PASS |
| EXE-005 | 冻结 JS 含本变更实现标记：无旧 835/555 钳制、有 ≥8 下限、有 canvas-surface | PASS |
| EXE-006 | terminate 后端口释放 | PASS |

`uv run --group build python scripts/desktop_e2e.py` → **18/18 checks passed**（health、ui-index、data-dir、graph PUT/GET 往返、patch+undo、资源导入、ai-draft 无 key 503 fail-closed、单实例互斥、端口释放、stale-lock 接管、窗口模式 health/存活/端口释放）。

**边界如实记录：** Web 画布拖拽/缩放行为（P-001..014）只能在 Web/vitest 层验证；冻结 exe 在本环境仅做 HTTP/资产/进程级验证（无浏览器自动化、无需 API key）。冻结包与 HEAD 源码一致性已通过"桌面构建配置重现"证明（见 P3-1）。

## 5. 发现（按 P0/P1/P2/P3 分级）

- **P0：无。**
- **P1：无。** 本变更范围内未发现阻塞缺陷；全部验收标准（AC-1 去钳制精确落点、AC-2 表面/viewBox 随内容增长、AC-3 1000×650 下限与既有回归）均验证通过。
- **P2（1 项，pre-existing，非本变更引入，不阻塞本次 PASS）：空工作区渲染崩溃。**
  - 现象：`loadGraph` 返回 0 节点的 schema-合法快照时，App 在详情面板抛 `TypeError: Cannot read properties of undefined (reading 'tone')`（`App.tsx:1523`，`selectedNode` 在 `nodes` 为空时为 undefined）。
  - 复现：P-008 探针（本报告第 3 节）FAIL；在 16e72c4 隔离 worktree 用同一探针复现同样崩溃（App.tsx:1507，同代码不同行号）→ **确认为 pre-existing**，非 WORK-2026-045 引入（变更仅涉及 moveDrag/surface/legend）。
  - 可达性：CourseGraph 契约 `concepts` 仅有 `maxItems` 无 `minItems`（schema 合法）；但当前后端流程（create_workspace 恒建 1 个根概念、UI 只允许删叶子）不会产生空图，实际触发概率低。
  - 建议：另立工作项，为 `selectedNode` 增加空态兜底（如 `present.nodes[0] ?? 占位节点`）并补测试。
- **P3（5 项观察，非阻塞）：**
  1. 冻结 exe 内嵌 JS 哈希（`index-BEtXJdQj.js`）与默认 `pnpm build` 产物（`index-fVCMW_zK.js`）不同 —— 原因已实证：`scripts/build_desktop.py` 以 `VITE_LOCAL_API=""`（同源相对 API 基址，WORK-2026-033 P2-2 既定配置）构建；在 HEAD worktree 用同环境重现得到**字节一致**的 `index-BEtXJdQj.js`。CSS 哈希两侧一致。属预期配置差异，非缺陷。
  2. 滚轮缩放存在浮点漂移（10 次 ±0.1 后 `scale(2.000000000000001)`），仅影响字符串显示，坐标断言按 closeTo 处理。
  3. 系统存在用户安装版 zhizhi 进程（PID 17784，`%LOCALAPPDATA%\Programs\知枝\zhizhi.exe`，启动于 12:25:39，早于本会话）；与探针无关（探针进程均已 terminate 且端口释放，EXE-006 与 e2e 端口检查通过），未作处理。
  4. `pnpm build` chunk >500 kB 警告（既有，未动）。
  5. vitest 下 pdf.js "Please use the `legacy` build" 警告（既有噪音）。

## 6. PASS 判定依据

1. 红灯→绿灯闭环成立：16e72c4 3 failed（精确对应三个缺陷面：835/555 钳制、固定 1000×650、`canvasSurfaceSize` 缺失），HEAD 3 passed。
2. 全部门禁绿：pytest 469+5（跳转符合无 key 门禁）、Web 56/56（含既有拖拽/缩放/平移/背景稳定回归）、tsc/eslint 0 警告、ruff/mypy/validator/契约 drift 全过、build 成功。
3. 14/15 对抗探针 PASS，覆盖任务清单全部要求（去钳制精确性、zoom 折算、纯函数边界、表面/viewBox 一致性、图例锚定、既有回归、锁定拒绝、自动排布包围盒、远坐标图谱加载、空画布下限、边层越界、缩放钳制、相机稳定）。
4. 冻结产物：6/6 资产/服务探针 + 桌面 e2e 18/18，冻结包与 HEAD 源码经桌面构建配置重现字节一致。
5. 唯一失败探针 P-008 指向的缺陷经 16e72c4 复现确认 pre-existing，与本变更无关，不构成对 WORK-2026-045 的回归；作为 P2 遗留记录，建议另立工作项。

> 本报告所有结论基于真实运行输出（见 evidence 目录日志）；未修改任何产品代码；未提交任何 git 变更。
