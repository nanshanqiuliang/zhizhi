# AI QA attempt 001 — 草案生成可诊断化与鲁棒性（WORK-2026-044）

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: ai_qa_auditor
decision: pass
reviewed_commit: 0abe9e9
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

**PASS** — 0 P0 / 0 P1；4 个 P2 + 1 观察（P2 均由 `33ba11a` 修复，观察记录为边界）。这是对
WORK-2026-044（错误码 rule 显示、单资源 40 块上限、fail-soft 抽取容错）的职责隔离机器审查。

## 红灯真值（隔离 worktree 实际重跑）

- `c549a17`（红灯）：`test_ai_draft_robustness.py` 1 failed（`TypeError: max_chunks`）；
  `api.test.ts` 1 failed（消息只有 `draft_invalid` 无 rule）。与提交声明一致。

## Gates（本人执行，精确数字）

- 聚焦 pytest（robustness）：3 passed；全仓 pytest：**466 passed + 5 skipped**。
- `ruff check`/`format`：clean（116 文件）。
- `mypy scripts`：16 文件；`mypy --strict`（incl. apps/desktop）：40 文件。
- `scripts.validate_repository`：PASS（含 secret scan）。
- `pnpm check`：**52/52**（14 files）。
- 桌面 e2e（重建后的冻结 exe）：**18/18**；`--no-window` 探针 `POST /ai-draft` 无 key → 503。
- 冻结产物与源码构建差异仅 API-base 字面量（已验证冻结包为修复版）。

## Adversarial probes（16/17 Python + 8/8 TS）

- **rule 组合**：`formatCode` 有 rule → `code/rule`；无 rule → `code`；无 code → `""`（`||` 兜底）；
  非 JSON body 容错。
- **max_chunks**：>2 块文本 + max_chunks=2 → extractor 调用 ≤2；`None` 无上限。
- **fail-soft**：某块 `DraftExtractionError` → 跳过、其余保留；`LLMProviderError`
  （provider_connection_failed）→ 传播（502）；关系坏响应 → `()`。
- **端点**：无 key 503；全失败 422（`draft_invalid/no_concepts`，见 P2-1）；坏块不 abort。
- **安全**：错误只含 code/rule，无提示/推理文本泄露。

## Findings（P2，均非阻塞，已由 `33ba11a` 修复 / 记录）

| Sev | 位置 | Finding | 处置 |
|-----|------|---------|------|
| P2 | main.py /ai-draft | 真实全失败路径经 `validate_draft` 抛 `draft_invalid/no_concepts`，端点 `no_new_concepts` 分支不可达 | 端点映射为 `no_new_concepts` |
| P2 | App.tsx/测试 | 计划中的组件测试未交付（AC-1 仍经 err.message + api.test 成立） | 补 App.draft 用例（code/rule 显示） |
| P2 | api.ts formatCode | `rule:null` 会渲染 `code/null` | 排除 null |
| P2 | workspace generator | 依赖 `build_workspace_ai_draft` 默认 max_chunks=40 而非显式传 | 显式传 `_MAX_CHUNKS` |
| 观察 | fail-soft | 单块 details 被吞（全失败时隐藏 invalid_json 等），防御纵深，可接受 | 记录为边界 |

## 执行 vs 静态追踪

- **执行**：全部门、红灯重跑（隔离 worktree）、16/17 Python 探针 + 8/8 TS 探针、桌面 e2e
  18/18、冻结包内容比对。未改仓库文件。
- **静态追踪**：`validate_draft` 空草案路径（已由探针验证）、无 key 503 路径。

## Disclosure

本报告为独立 AI QA 子 Agent（与实现 Agent 角色分离、同模型相关性）进行的机器审查，是证据与
工程发现的证明，**不是**人类签名、非 owner 接受。最终残余风险接受属于 workspace owner。
