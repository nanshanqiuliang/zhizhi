# TR-20260815-009 QA 报告：WORK-2026-047 完整编辑工具箱 + 拖拽跳变修复

- test_run_id: `TR-20260815-009`
- reviewed_commit: `c878c44`（feat(web): edit toolbox - free blocks, connect/disconnect, drag-jump fix）
- red baseline: `8a67656`（仅红灯测试、无实现）
- 工作项文档: `docs/work-items/WORK-2026-047_edit-toolbox.md`
- 判定: **PASS**（0 P0 / 0 P1 / 1 P2 遗留（pre-existing，非本变更引入）/ 3 P3 观察）
- 角色隔离声明: 本报告由独立 QA 角色出具，与实现者角色分离（独立运行、独立提示词、独立工件）；**correlation 披露：`correlated_review`** —— 本 QA 与实现者同属自动化编排流程，可能同模型/供应商（本 QA 运行于 DeepSeek 系模型）；`human_signature=false`、`owner_acceptance=false`（机器证明不冒充人类签名，最终残余风险接受权归工作区所有者）。
- 约束合规：未提交任何 git 变更；未修改产品代码（探针临时测试文件执行后已从 `apps/web/src` 移除并归档）；所有断言基于真实运行输出。

---

## 1. 红灯真值（隔离 worktree @8a67656，全部真实运行）

`git worktree add --detach` 至临时目录，安装依赖后执行：

```
pnpm --filter @knowledge-tree/web exec vitest run src/App.edit.test.tsx src/api.test.ts
```

**红灯（8a67656，仅测试无实现）：** `Test Files 2 failed (2)；Tests 6 failed | 5 passed (11)`

| 用例 | 实际结果 |
|---|---|
| api.test：preserves a typed edge through graphToSnapshot → snapshotToGraph | FAIL（边类型未往返，硬编码 related_to） |
| App.edit：does not recenter the canvas after a node drag + browser click | FAIL（拖拽后 click 重定心跳变） |
| App.edit：adds a free concept block without a parent edge | FAIL（无「添加概念」按钮） |
| App.edit：adds a root outline block | FAIL（无「添加总纲」按钮） |
| App.edit：connects two blocks with the selected edge type | FAIL（无「连线」入口） |
| App.edit：disconnects an edge from the detail panel | FAIL（无断线入口） |

5 个通过项语义上本就应绿：3 项既有 persist api 测试 + “plain click still recenters”（旧行为本就居中）+ “type-less 默认 related_to”（旧硬编码本就输出 related_to）。

**绿灯（HEAD=c878c44，含实现）：** 同一命令 → `Test Files 2 passed (2)；Tests 11 passed (11)`。

红灯/绿灯输出分别存盘：`evidence/TR-20260815-009/logs/redlight-8a67656.log`、`head-c878c44.log`。worktree 已移除并 `git worktree prune`（目录残留手动清理）。

## 2. 全部门禁（HEAD 真实运行）

| 门禁 | 结果 |
|---|---|
| `uv sync --locked --group dev` | PASS（81 packages resolved） |
| `uv run python -m scripts.validate_repository` | PASS（skeleton/secret scan/graph/LLM 契约/复包/v2 mock-replay） |
| `uv run ruff format --check packages scripts tests apps` | PASS（116 files already formatted） |
| `uv run ruff check .` | PASS（All checks passed） |
| `uv run mypy scripts` | PASS（16 source files，无问题） |
| `uv run python -m mypy --strict packages/contracts-py/src packages/domain/src packages/infrastructure/src apps/api apps/desktop` | PASS（40 source files，无问题；含 apps/desktop） |
| `uv run python -m pytest -q` | **469 passed, 5 skipped**（5 skip = live DeepSeek 门禁无 key，符合预期） |
| `pnpm install --frozen-lockfile` | PASS（Already up to date） |
| `pnpm peers check` | PASS（No peer dependency issues found） |
| `pnpm check`（tsc -b + eslint --max-warnings 0 + vitest） | PASS：**16 files / 64 tests 全绿**（App.edit 6、api 5、App.test 9、layout 3、persist 6、lock 6、draft 6、command 3、canvas 3、workspaces、ai-settings、answer、PdfViewer/Render、markdown、ResourceImport） |
| `pnpm build` | PASS（vite built ~188ms；chunk>500kB 警告为既有提示） |
| `pnpm --filter @knowledge-tree/contracts-ts check` | PASS（exit 0：generate --check + tsc，无契约 drift；另直接复核 `node scripts/generate.mjs --check` 与 `tsc --noEmit` 均 exit 0） |

证据：`evidence/TR-20260815-009/gates/*.log`、`gate-summary.txt`。

## 3. 对抗探针（18 项 vitest + 6 项后端闭环 + 10 项 exe + 18 项 e2e）

探针脚本存 `evidence/TR-20260815-009/probes/`，输出存 `logs/`。首轮 18 项 Web 探针中 2 项失败，均为**探针自身问题**（未等待异步 loadGraph、断言与产品实际契约不符——关系锁拒绝时保留起点高亮属设计选择），修正后全绿；未发现产品缺陷。

| ID | 探针 | 结果 |
|---|---|---|
| P-001 | 连续 3 轮「拖拽 + 浏览器补发 click」循环，相机 transform 恒不变 | PASS |
| P-002 | 普通点击节点仍居中（相机变化） | PASS |
| P-003 | 无位移拖拽（原地按下抬起）→ click 仍居中 | PASS |
| P-004 | 连线模式下点击节点不重定心、不选中 | PASS |
| P-101 | 自连（同点两次）被拒：无新边、状态提示、起点高亮清除 | PASS |
| P-102 | 重复连线被拒（正/反向均检测），边数不变 | PASS |
| P-103 | 关系锁（任一端 relations 锁）拒绝连线：无新边 + 状态提示；起点保留可继续连自由端点；锁定端点作首点同样被拒 | PASS |
| P-104 | 关系锁拒绝断线：边保留 + 状态提示 | PASS |
| P-105 | Esc 退出连线模式并清除起点高亮（combobox 消失、按钮去 active） | PASS |
| P-106 | `connect-source` 高亮只落在起点；选「先修」建边后 `连线：函数 → ε-δ 语言（先修）` 出现 | PASS |
| P-201 | 添加概念：位置=视口中心（相机平移后 x=2125，**无 835/555 上界**）、无父连线、非锁定 | PASS |
| P-202 | 添加总纲：root 块、`.node-type`=「主题」、视口中心、无父连线 | PASS |
| P-203 | 新自由块可拖到 (908,708)，无上界钳制 | PASS |
| P-301 | 边类型 snapshotToGraph → graphToSnapshot → snapshotToGraph 双程往返保留 prerequisite_of | PASS |
| P-302 | 无类型快照默认 related_to；未知类型回退 undefined（向前兼容） | PASS |
| P-303 | 断线 → 自动保存 → 卸载重挂载（loadGraph 返回已存快照）→ 边仍消失（持久化闭环） | PASS |
| P-304 | 断线后「撤销」→ 边恢复（历史可撤销） | PASS |
| P-305 | BUG-2026-001 空工作区崩溃在 HEAD 仍复现（反向断言：通过=缺陷确认） | PASS（=缺陷复现） |
| P-401~406 | 后端 TestClient 闭环：PUT 含 prerequisite_of 的 canonical 图 → GET 返回 prerequisite_of；二次 PUT（diff 保存经提交门新增 part_of）→ GET 返回 [part_of, prerequisite_of]；history 有记录 | 6/6 PASS |
| P-501~510 | 冻结 exe：health 200；GET / 返回 index.html（id=root）；/assets/* 的 sha256 与冻结包内置一致；冻结包 == HEAD 桌面式重建（`VITE_LOCAL_API=""` 经 Python env dict）哈希一致；终止后端口释放 | 10/10 PASS |
| P-601 | `uv run --group build python scripts/desktop_e2e.py` | **18/18 PASS**（health/UI 同源服务/数据目录/图 PUT-GET/patch+undo/资源导入/AI fail-closed 503/单实例互斥/端口释放/陈旧锁接管/window 冒烟） |

关键发现记录：
- **边类型闭环（AC-5）**：根因在 Web 层 `api.ts` snapshotToGraph 硬编码 `related_to`；修复后类型经 `snapshotToGraph→PUT→GET→graphToSnapshot` 完整保留。后端 diff 保存 `_build_diff_patch` 将完整 edge 对象（含 `edge_type`）放入 `create_edge`，提交门接受 4 种类型，二次保存经真实提交门验证。
- **哈希一致性核查**：`pnpm build`（无 `VITE_LOCAL_API`）产物 JS 哈希与冻结包不同，差异仅为 API base（默认 `http://127.0.0.1:8000` vs 同源相对基址）——桌面构建 `VITE_LOCAL_API=""` 的既定行为（TR-20260815-008 已登记 P3）。按 `scripts/build_desktop.py` 同法（空串必须经 Python subprocess env dict 传递；Windows 下 `set VAR=` 会删除变量、pwsh/cmd shim 会丢弃空环境变量）重建后哈希与冻结包**完全一致** → 冻结 exe（2026-08-16 13:36:36）确为当前 HEAD 源码的桌面式构建。

## 4. 发现（按严重级）

- **P0**：无。
- **P1**：无。
- **P2（1 项，pre-existing，不阻塞 PASS）**：
  - **BUG-2026-001 空工作区渲染崩溃**：`loadGraph` 返回 0 节点（契约合法，无 minItems）时 App 在详情面板读 `selectedNode.tone` 抛 `TypeError`。探针 P-305 确认 HEAD 仍复现；与 TR-20260815-008 P-008 一致（16e72c4 已复现确认非 WORK-2026-045/047 引入）。当前后端 `create_workspace` 恒建 1 根节点故生产不触发。建议另立工作项做空态兜底（无节点时显示引导，不渲染选中详情）。
- **P3（3 项观察）**：
  - 桌面构建与普通 `pnpm build` 的 JS 哈希差异（`VITE_LOCAL_API=""` 既定行为，既有，已登记）。
  - vite chunk>500kB 警告（既有提示，非错误）。
  - 关系锁拒绝连线时保留起点高亮（设计选择：允许改选终点；无新边 + 状态提示正确），可选后续工作项加 toast 引导。

## 5. 验收标准对照

- AC-1（拖拽后不跳变、普通点击居中）：红灯 FAIL → 绿灯 P-001/P-002/P-003 PASS。
- AC-2（添加概念/总纲自由块、视口中心、无上界）：P-201/P-202/P-203 PASS。
- AC-3（连线模式、自连拒绝、关系锁阻止连线/断线）：P-101/P-103/P-104 PASS。
- AC-4（详情面板断线）：P-303/P-304 PASS（含保存→重载、历史撤销）。
- AC-5（边类型往返保留、默认 related_to）：P-301/P-302/P-401~406 PASS（Web 单测 + 真实后端闭环）。
- 错误/恢复路径（重复连线拒绝、Esc 退出）：P-102/P-105 PASS。
- 全量回归：Web 64/64、pytest 469+5、构建、契约 drift 全绿。
- 桌面冒烟：desktop e2e 18/18、exe 探针 10/10。

## 6. 结论

判定 **PASS**。WORK-2026-047 的红灯→绿灯闭环、全部门禁、18 项对抗探针、后端边类型持久化闭环、冻结 exe 探针（HTTP/资产层 + e2e 18/18）全部通过；未发现本变更引入的缺陷。唯一遗留 P2（BUG-2026-001 空工作区崩溃）为 pre-existing，按 BUG_REGISTER 记录另立工作项。机器 QA 证据不冒充人类签名（`human_signature=false`、`owner_acceptance=false`），最终残余风险接受权归工作区所有者。

- 证据目录：`evidence/TR-20260815-009/`（manifest.json / checksums.sha256 / commands.txt / environment.json / gate-summary.txt / qa-attempt.md / gates / logs / probes）
- 复查方式：`git -C <repo> diff 8a67656 c878c44` 复核实现范围；重跑本节命令复核结果。
