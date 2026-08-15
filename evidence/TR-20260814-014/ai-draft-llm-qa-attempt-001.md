# AI QA attempt 001 — LLM-backed AI draft extraction (WORK-2026-009 slice 2)

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: ai_qa_auditor
decision: pass
reviewed_commit: 1394a1e65d6e42b7429ef3deb4399338fdf47883
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

**PASS** — 0 P0/P1；3 个 P2 记录为 prototype 边界。这是对冻结提交 `1394a1e`
（WORK-2026-009 切片 2：`LlmConceptExtractor`/`LlmRelationProvider` +
live 冒烟脚本）的职责隔离只读机器审查。最终残余风险接受仍归 workspace owner。

## Red/green chain — VERIFIED

- `git show 1407427:packages/infrastructure/src/knowledge_tree_infrastructure/ai_draft_llm.py`
  与 `...tests/contract/test_ai_draft_llm.py` 在父提交均报 exit 128（路径不存在）；
  `git log --all -- <paths>` 仅 `1394a1e` 引入这两个文件。
- 过程披露确认：红灯测试与实现合并为同一提交（无独立红灯提交），红灯真值由父提交
  无模块/测试文件确认。提交 `1394a1e` 恰新增 4 个文件
  （`ai_draft_llm.py`、`test_ai_draft_llm.py`、`scripts/ai_draft_live_smoke.py`、
  `evals/calculus-v1/ai-draft-live-smoke.json`）。

## Gates personally run（全部绿）

| # | Command | Result |
|---|---------|--------|
| 1 | `uv run python -m pytest tests/contract/test_ai_draft_llm.py -q` | 18 passed |
| 2 | `uv run python -m pytest tests/contract/test_ai_draft_contract.py tests/integration/test_ai_draft_pipeline.py tests/unit/test_ai_draft.py -q` | 20 passed（无回归） |
| 3 | `uv run ruff format --check packages scripts tests apps` / `uv run ruff check .` | 82 files formatted / all passed |
| 4 | `uv run python -m mypy --strict packages/contracts-py/src packages/domain/src packages/infrastructure/src` | no issues in 26 files |
| 5 | `uv run python -m scripts.validate_repository` | PASS（含 secret scan：报告无密钥模式） |
| 6 | `uv run python -m pytest -q` | 386 passed, 5 skipped（skips = 既有 live-gated e2e） |

## Adversarial mutation review（物理执行，scratch harness 已删除）

- **Shape bypass**：缺 concepts/relations、非 list、非 dict 顶层、非 dict item、缺失/
  空白（含全角）/非字符串 label、confidence 越界/NaN/bool/string、aliases
  None/string/dict/非字符串 item/空白 item、未知/缺失边类型、缺失/空白端点、
  拼接 JSON、JSON 数组答案 → 全部按预期 rule 抛 `DraftExtractionError`，无一漏过。
- **Evidence bypass**：无 anchor 的 chunk → 概念 evidence 为空，patch 被
  `build_draft_patch` 以 `draft_evidence_required` 拒绝；关系 evidence 恰为端点
  evidence 的有序去重并集（含重叠 evidence 验证）。
- **Contract bypass**：patch 恒为 `requires_confirmation=True`、`confirmed=False`、
  actor `{"type":"ai"}`；AI actor 下提交门恒返回 `requires_confirmation`（即使
  confirmed 被篡改为 True）；`requires_confirmation=False` 被门拒绝
  （`confirmation_required`）；`build_draft_patch` 对无 evidence 的 AI 概念与
  `prerequisite_of` 边仍拒绝。无路径可达 `ready_to_apply`。
- **Noise handling**：未知端点/自环/重复边丢弃（first-wins）不崩溃；同对概念不同边
  类型保留。
- **Immutability**：chunk 文本、输入文本、concept 元组在 extract/provide/
  build_ai_draft 后不变。
- **Prompt injection**：捕获的 GenerationRequest 恰一条消息、role=user、chunk 文本
  仅在其中，无 system/developer 消息，附带严格输出 schema；labels 同样仅在 user
  消息。抽取器/提供器不记录、不持久化任何内容。
- **Secret/error hygiene**：错误文本恰为
  `draft_extraction_failed: AI draft extraction rejected`；chunk/note 文本不出现在
  `str(e)` 与 `details`（验证 no_json_object 与 invalid_json 路径）。新文件无
  `logging`/`logger`，无密钥字面量。
- **Smoke fail-closed**：无 env 时 `scripts.ai_draft_live_smoke.main()` 返回 0
  （skip）；`RUN_LIVE_LLM_TESTS=1` 无 key 时返回 1；静态审查确认
  `preview.status != "requires_confirmation"` 时 `return 1`；唯一文件写入是报告
  dict（绝不含 key；key 仅 env → adapter）。

## Findings

| # | Sev | 位置 | 描述 |
|---|-----|------|------|
| 1 | P2 | `ai_draft_llm.py:228,236,341` | `DraftExtractionError` details 含模型提供的 `label`/`type` 标识。"identifier-only" 成立（绝无 chunk/note 文本、推理或密钥），但敌对模型答案可向异常 details 注入任意 label 文本。 |
| 2 | P2 | `ai_draft_llm.py:55-73` | chunk 文本/labels 嵌入单条 **user** 消息（绝无 system/developer，不记录/持久化）。固有 LLM prompt-injection 面；由严格输出 schema + 形状校验 + 内容噪声丢弃缓解。prototype 边界，非代码缺陷。 |
| 3 | P2 | `scripts/ai_draft_live_smoke.py:107-109` | 无 `RUN_LIVE_LLM_TESTS` 时冒烟返回 0（skip），CI 会静默跳过 live 校验。文档化的 opt-in 门控设计。 |

## Conclusion

PASS（0 P0/P1）。3 个 P2 记录为 prototype 边界，无需代码修改。`correlated_review`：
机器证明、同源披露，非 owner 接受；最终残余风险接受归 workspace owner。
