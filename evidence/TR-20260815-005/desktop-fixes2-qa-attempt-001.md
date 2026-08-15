# AI QA attempt 001 — 第 10 步后第二轮使用反馈修复（WORK-2026-040..043）

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: ai_qa_auditor
decision: pass
reviewed_commits:
  - 992af8b   # 040 drag-background stability
  - 93321f5   # 041 filename preservation
  - f7c845a   # 042 layout (right column + resizable/hideable sidebar)
  - cba4238   # 043 whole-workspace mind-map agent
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

**PASS** — 0 P0 / 0 P1 / 0 P2；3 个 P3（由 `cf1bdad` 全部修复）。这是对
WORK-2026-040..043（拖拽背景稳定、文件名保留、AI 内容右移 + 边栏可调/隐藏、全库思维导图
agent）四项修复的职责隔离机器审查。

## 红灯真值（实际重跑）

- **040**：在 `3cb1734`（红灯）worktree 运行新 Web 用例「keeps the canvas background stable
  while dragging a node」→ **失败**（拖拽时 canvas-surface transform 变为 `translate(-190px,
  -239px) scale(1)`）；HEAD `50ef3aa` 通过。追踪确认红灯版 `startDrag→selectNode→centerOnNode`
  vs 绿灯版 `selectNodeKeepCamera`。
- **041**：在 `5b7c3e2`（红灯）worktree 运行 `test_resource_filename.py` → **3/3 失败**（UUID
  命名、无 `.md` 后缀）；HEAD 通过 3/3。

## Gates（本人执行，精确数字）

- 聚焦 pytest（workspace_ai_draft + resource_filename + ai_draft_api）：**12 passed**。
- 全仓 pytest：**461 passed + 5 skipped**。
- `ruff check .`：clean；`ruff format --check`：115 文件。
- `mypy scripts`：16 文件；`mypy --strict`（packages+apps/api+apps/desktop）：40 文件。
- `scripts.validate_repository`：**PASS**（含 secret scan）。
- `pnpm check`：tsc + eslint + vitest **51 tests（14 files）**。
- 冻结 exe（`dist/zhizhi/zhizhi.exe`，043 后重建）：`desktop_e2e.py` **18/18**；`--no-window`
  探针——workspaces 200、`POST /ai-draft {}` 无 key → 503、settings 无 key 回显。

## Adversarial probes（28 断言 + 3 边界场景，全通过）

- **文件名**：`/`、`\` 拒绝（`invalid_name`）；`<>:"|?*` 与控制字符中性化；`CON/PRN/COM1/LPT9/NUL`
  防护（`file_CON.md` 等）；300 字符 stem 截断（len 123）；冲突 `笔记-1.md`/`笔记-2.md`；相同内容
  幂等去重且**无残留文件**；`get_resource_file_path` 解析在工作区内；display_name 元数据保留。
- **内核** `build_workspace_ai_draft`：`max_chunks` 上限（6 ≤ 40）；既有概念保持占位、不重建；
  按资源 `deterministic_uuidv7(resource_id)` 锚点；existing↔existing 关系丢弃。
- **端点**：无 generator → 503；空语料 → 422 `no_resources`；有 generator → 200；单资源模式
  语义不变；**PDF 自动解析 → 200 + 真实抽取文本**（金标微积分 PDF + 注入确定性 generator，
  零网络）；坏 PDF 逐资源跳过；全坏 → 422；`GET /api/settings/ai` 无 key 回显。
- **拖拽/布局**：`startDrag` 用 `selectNodeKeepCamera`（App.tsx:954），搜索/来源跳转仍居中；
  `.right-column` 包裹 detail + draft + answer + command；隐藏/显示切换 `.hidden`；resize
  170–480 钳制且仅左键。
- **harness 文档** `docs/ai-mindmap-agent-harness.md` 7 条约束全部与实现对应（不可信草案/
  预览确认/证据同事务/确定性校验/fail-closed/预算/Key 处理）。

## Findings（P3，均非阻塞，已由 `cf1bdad` 修复）

| Sev | 位置 | Finding | 处置 |
|-----|------|---------|------|
| P3 | ai_draft_llm.py `deepseek_relation_provider` | 陈旧 helper 仍绑定 thinking=enabled（未使用，未来接线会静默回归） | 改为 disabled + 更新文档 |
| P3 | main.py /ai-draft | 非字符串 `resource_id`（如 123）被当作全库模式 | 422 `resource_id_invalid` |
| P3 | main.py /ai-draft | 零新概念时返回晦涩的空补丁校验错误 | 422 `no_new_concepts` |

## 执行 vs 静态追踪

- **执行**：全部门、040/041 红灯重跑（隔离 worktree）、28 断言对抗探针、PDF 自动解析、冻结
  exe 探针、桌面 e2e。未改仓库文件（临时 worktree/探针已清理）。
- **静态追踪**：live DeepSeek 适配器行为（thinking=disabled、8192 tokens 只读不跑）、
  DAG/环拒绝（由 461 测试套件覆盖）、LLM 预算交互。

## Disclosure

本报告为独立 AI QA 子 Agent（与实现 Agent 角色分离、同模型相关性）进行的机器审查，是证据与
工程发现的证明，**不是**人类签名、非 owner 接受。最终残余风险接受属于 workspace owner。
