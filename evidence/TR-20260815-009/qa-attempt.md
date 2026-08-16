# QA TR-20260815-009 — 尝试与过程记录（WORK-2026-047 编辑工具箱）

## 角色与隔离
- 独立 QA 角色；与实现者分离运行环境/提示词/工件。实现者提交（c878c44 由自动化编排中的实现角色完成）。
- 本 QA 由 DeepSeek 系模型驱动 —— **correlation 披露：correlated_review**（与实现者可能同模型/供应商）。
- 未修改任何产品代码（git 工作树仅保留提交前既有的 docs/USER_MANUAL.md 修改与未跟踪项）；QA 产物全部落盘于 evidence/TR-20260815-009/ 与 docs/test-reports/TR-20260815-009_edit-toolbox.md。

## 阶段一：红灯真值（隔离 worktree）
- `git worktree add --detach <temp> 8a67656` → pnpm install（复用全局 store，4.3s）→ 红灯命令 → **6 failed | 5 passed**。
- 6 个失败与预期红灯一一对应（拖拽后重定心 / 无添加概念 / 无添加总纲 / 无连线 / 无断线 / 边类型未往返）；5 个通过项语义上本就该绿（既有 persist api 3 项、旧行为居中的 plain click、旧硬编码 related_to 的默认项）。
- HEAD 同命令 → **11/11 passed**。worktree 已移除 + prune（目录残留手动清理，无 git 变更）。

## 阶段二：全部门禁（HEAD）
全部真实运行，结果见 gate-summary.txt：validate_repository/ruff format/ruff check/mypy scripts/mypy --strict（含 apps/desktop）/pytest **469 passed + 5 skipped**/pnpm install frozen/peers/check（**64/64**）/build/contracts-ts drift 全绿。
- 注意：`uv sync --locked --group dev` 会卸载 build 组（pyinstaller 等）；desktop e2e 通过 `uv run --group build` 按需重装，已验证可行。
- 探针临时测试文件在 `pnpm check` 之前已从 apps/web/src 移除（保证 64/64 为基线套件计数）。

## 阶段三：对抗探针（18 项 vitest + 6 项后端 TestClient + 10 项 exe HTTP/资产 + 18 项 desktop e2e）
- 首轮 18 项探针中 2 项失败，均为探针自身问题（非产品缺陷）：
  1. P-103/P-104 未等待 mock api 异步 loadGraph 完成（样本数据尚未替换）→ 修正为 waitFor。
  2. P-103 断言过严：关系锁拒绝连线时产品设计保留起点高亮以便改选终点（无新边+状态提示才是契约）；且"再点连线按钮"实为退出连线模式（连线模式在成边后仍保持激活）→ 按真实契约重写断言并追加"锁只拦截锁定端点、起点可继续连自由端点"的验证。
- 修正后 18/18 全绿。产品零缺陷暴露；唯一"FAIL"是 P-305 的反向断言（语义=已确认 BUG-2026-001 在 HEAD 复现，属于既有 P2，非本变更引入）。

## 阶段四：边类型持久化闭环（真实后端）
- TestClient 起 apps.api.main.create_app：首次 PUT（whole-graph，含 prerequisite_of 边）→ GET 返回 prerequisite_of；二次 PUT（diff 保存：改 label + 新增 part_of 边，经提交门 create_edge）→ GET 返回 [part_of, prerequisite_of]；history 有记录 → **6/6 PASS**。证明 diff 保存不再把类型改写为 related_to（根因在 Web 层 snapshotToGraph 硬编码，已由 api.ts 修复并在 Web 单测覆盖）。

## 阶段五：冻结 exe（最后做）
- dist\zhizhi\zhizhi.exe 重建于 2026-08-16 13:36:36（含本变更）。
- 探针 10/10：health 200；GET / 返回 index.html（id=root）且 /assets/index-ec9Mn6UR.js、index-DimZVipg.css 的 sha256 与冻结包内置文件一致；进程终止后端口释放。
- **哈希一致性核查**：首轮 `pnpm build`（无 VITE_LOCAL_API）产物 JS 哈希与冻结包不同（index-Cc9qNbZx.js vs index-ec9Mn6UR.js）。经排查：差异仅 `var so=`（API base：默认 http://127.0.0.1:8000 vs 空串=同源相对基址），系桌面构建 `VITE_LOCAL_API=""` 的既定差异（TR-20260815-008 已登记 P3）；且 Windows 上 `set VAR=`/pwsh 空环境变量会被 cmd/pnpm shim 丢弃，必须像 scripts/build_desktop.py 那样用 Python subprocess env dict 传空串。按 build_desktop.py 同法重建 → **哈希与冻结包完全一致** → 冻结包确为当前 HEAD 源码桌面式构建，无陈旧。
- desktop_e2e.py：**18/18 PASS**（health/UI/数据目录/图 PUT-GET/patch+undo/资源导入/AI fail-closed/单实例互斥/端口释放/陈旧锁接管/window 冒烟）。
- 边界：exe 探针仅覆盖 HTTP 与资产层；画布交互行为以 vitest（jsdom）层为准，未做真人/真实浏览器操作。

## 阶段六：BUG-2026-001（pre-existing P2，如实记录不修）
- P-305 探针：loadGraph 返回空 concepts（契约合法）→ 渲染时 selectedNode 为 undefined → 读取 tone 崩溃，仍复现于 HEAD（console.error/window error 捕获到含 "tone"/"undefined" 的记录）。与 TR-20260815-008 P-008 结论一致：非 WORK-2026-047 引入，登记在 BUG_REGISTER 待另立工作项。

## 结论
- 判定 **PASS**（0 P0 / 0 P1 / 1 P2 既有 / 3 P3 观察）。
- P2：BUG-2026-001 空工作区崩溃（pre-existing，不阻塞）。
- P3：① 桌面构建与普通 `pnpm build` 的 JS 哈希差异来自 VITE_LOCAL_API="" 既定行为（既有，已登记）；② vite chunk>500kB 警告（既有）；③ 探针 P-103 首次暴露"关系锁拒绝连线时保留起点高亮"为产品设计选择（非缺陷），建议后续工作项可加 toast 引导（可选）。
- human_signature=false、owner_acceptance=false：本报告为机器 QA 证据，不冒充人类签名；最终残余风险接受权归工作区所有者。
