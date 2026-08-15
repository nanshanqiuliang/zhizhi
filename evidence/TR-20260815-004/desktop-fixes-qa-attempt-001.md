# AI QA attempt 001 — 第 10 步后 5 项使用反馈修复（WORK-2026-036..039）

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: ai_qa_auditor
decision: pass
reviewed_commits:
  - 69d0de92f83665e47d50e32dc5b7cec1d0c429fb   # 036 drag
  - 1f01795ef5aa4857c5a171ee9309c2a70baa3aac   # 037 reveal
  - abf2d9a6f6ef03159f3e140c74c92cdcb9f1f4eb   # 038 ai settings
  - e0fc05f                                     # 039 workspaces
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

**PASS** — 0 P0 / 0 P1；1 P2 + 3 P3（P2 已由 `c577928` 修复，P3 记录为边界/说明）。这是对
WORK-2026-036..039（拖拽、打开本地目录、AI 接入设置、多课程）四项修复的职责隔离机器审查。

## Ready→red→green（037/038/039 红灯真值实际重跑）

| 项 | Ready | 红灯 | 绿灯 | 红灯验证 |
|---|---|---|---|---|
| 036 拖拽 | 06dd1f5 | 5b08f3c | 69d0de9 | 静态追踪（pre-fix 缺 buttons 校验） |
| 037 reveal | 3aa031c | 07a6ba4 | 1f01795 | 执行：open-dir 404 |
| 038 AI 设置 | 0840999 | 0871465 | abf2d9a | 执行：2 failed（404） |
| 039 多课程 | 342c5e3 | 575a45c | e0fc05f | 执行：2 failed（404） |

红灯重跑用 `git archive` 到 `%TEMP%`（仓库未动）+ 仓库 `.venv`。

## Gates（本人执行，精确数字）

- 聚焦 pytest（reveal+ai_settings+workspaces）：**6 passed**。
- 全仓 pytest：**454 passed + 5 skipped**（live-LLM 门）。
- `ruff check .`：clean；`ruff format --check`：**1 file 未格式化**（`test_resource_reveal.py:26`，
  由红灯 07a6ba4 带入绿灯 1f01795）→ P2 已由 `c577928` 修复（113 files formatted）。
- `mypy scripts`：16 文件；`mypy --strict`（packages+apps/api+apps/desktop）：40 文件。
- `scripts.validate_repository`：**PASS**（含 secret scan）。
- `pnpm check`：tsc + eslint 0 warnings + vitest **13 文件 / 47 tests**。
- 桌面 e2e（冻结 exe）：**18/18**；冻结产物新端点探针：**12/12**（workspaces/settings/ai、
  open-dir/reveal 均在冻结 exe 中生效）。

## Adversarial probes（45/45 API 探针 + 3 微探针通过）

- **拖拽**：buttons:0 的 pointermove 结束拖拽；`setPointerCapture` try/catch 兼容 jsdom；
  canvas 有 `onPointerCancel`；Web 47/47。
- **Reveal**：仅返回守卫路径；explorer spy 收到正确参数（reveal=`/select,`，open-dir=目录）；
  `os.name=posix` 时零 spawn；缺失资源/工作区 404；无 resources 目录 422；篡改 storage_key
  （`..\..\outside.txt`）→ 404 `storage_key_unsafe` 且不 spawn explorer。
- **AI 设置**：配置文件优先 + env 兜底 + 损坏 `ai.json`→env；GET 不回显 key；PUT
  `""/空格/42/None/[]` → 422；`ai.json` 精确写/删；DELETE 后三个 AI 端点 → 503 fail-closed；
  fake key 非 `sk-` 前缀 → secret scan 干净。
- **Workspaces**：create→list→图含根概念（课程名）；名称 422 边界（空/空白/51 字符/非字符串，
  50 字符 OK）；非 UUIDv7 id → 404；两个工作区隔离。
- **安全**：launcher 绑定 127.0.0.1 + `allowed_origins=[]`；无 `ai.json`/env/secret 文件入库。

## Findings

| Sev | 位置 | Finding | 处置 |
|-----|------|---------|------|
| P2 | test_resource_reveal.py:26 | 未 ruff 格式化（红灯带入绿灯），违反 037 AC-5 全门全绿 | `c577928` 修复（113 files formatted） |
| P2* | api.ts snapshotToGraph | 非默认课程保存的图内部 workspace_id/course_id 为默认值（目录级隔离完好；039 设计边界已接受） | 记录为 MVP 边界 |
| P3 | DELETE /settings/ai + env key | env 兜底不清除（configured:true, enabled:false）；桌面版无 env 不受影响 | 记录为文档化边界 |
| P3 | startPan/startDrag | 不滤 `event.button`，右键按下会短暂启动拖拽后立即结束 | `c577928` 修复（button===0 过滤） |

*P2（文档化接受）：目录级隔离经验证完好，图内部 id 不匹配为已知 MVP 限制（039 文档设计边界）。

## 执行 vs 静态追踪

- **执行**：全部门、037/038/039 红灯重跑、45 API 探针、冻结 exe 探针、no-op/args 探针、
  损坏 ai.json 探针、env-DELETE 边界探针、桌面 e2e、文档阅读。未改仓库文件（探针在 `%TEMP%`）。
- **静态追踪**：036 红灯 vitest 失败（diff + 测试逻辑）、多工作区 Web 切换流程（组件测试覆盖）、
  GUI 窗口视觉（无头不可断言）。

## Disclosure

本报告为独立 AI QA 子 Agent（与实现 Agent 角色分离、同模型相关性）进行的机器审查，是证据与
工程发现的证明，**不是**人类签名、非 owner 接受。最终残余风险接受属于 workspace owner。
