# TR-20260814-014：LLM 概念抽取与关系候选验证（WORK-2026-009 切片 2）

> 本报告密封 `1394a1e65d6e42b7429ef3deb4399338fdf47883` 的
> WORK-2026-009（GraphPatch v1 提交门 + canonical LLM port + DeepSeek adapter）切片 2：
> `LlmConceptExtractor`/`LlmRelationProvider` 与 live 冒烟。
> 它证明 AI 草案流水线已接上真实 DeepSeek 概念抽取与先修关系候选，草案只经提交门
> 以 `requires_confirmation` 落库；形状违规失败关闭、内容噪声丢弃、证据绑定 chunk
> anchor。

```yaml
status: passed
test_level: contract_repository_e2e_live
owner: ai_qa_auditor
related_ids: [WORK-2026-009, WORK-2026-007, WORK-2026-008, REQ-2026-006, NFR-2026-006, NFR-2026-007, NFR-2026-008, WORK-2026-005]
build_id: 1394a1e65d6e42b7429ef3deb4399338fdf47883
started_at: 2026-08-15T02:05:00+08:00
finished_at: 2026-08-15T02:50:00+08:00
supersedes: null
```

## 目的与门槛

- 证明 `knowledge_tree_infrastructure/ai_draft_llm.py` 的 `LlmConceptExtractor`/
  `LlmRelationProvider` 实现草案 `ConceptExtractor`/`RelationCandidateProvider`
  Protocol：经 canonical LLM port（`concept_extract`/`relation_validate` task
  profile）抽取概念与 `prerequisite_of` 候选，证据绑定 chunk anchor。
- 证明 AI 输出是不可信草稿：形状违规以 `draft_extraction_failed` 失败关闭；未知端点/
  自环/重复边内容噪声丢弃；错误 details 仅标识、不含正文/推理/密钥。
- 证明生成 patch 恒为 `proposed` + `requires_confirmation`，经既有提交门才可落库，
  绝不直写数据库、不覆盖锁定项。
- 证明真实 DeepSeek 受控 live 冒烟（`RUN_LIVE_LLM_TESTS` + `DEEPSEEK_API_KEY`
  双门控）费用受控、报告无正文无密钥。

## 方法与结果

| Test ID | 场景 | Actual | Result |
|---|---|---|---|
| TC-AIDRAFT-007 | LLM 抽取/关系候选离线契约 | mock adapter 无网络抽取/关系候选；形状违规失败关闭；噪声丢弃；evidence 绑定；端到端 patch 经提交门 | 18/18 PASS |
| TC-AIDRAFT-008 | live 冒烟（真实 DeepSeek） | 极限/连续/导数/可导 + 4 条 prerequisite_of；preview=requires_confirmation、12 ops；427/3435 tokens、~$0.004、~57.5s | PASS |
| TC-REPO-001 | 完整 Python/仓库门 | 全仓 386/386 + 5 skipped；Ruff；strict mypy（packages 26 + scripts 11）；validator（含 secret scan） | PASS |
| TC-REPO-002 | TS/Web/依赖/构建门 | Web 32/32；pnpm 冻结 install/peers/check/build | PASS |
| QA-001 | 职责隔离对抗审查 | 红绿链验证；25+ 畸形答案形状绕过全部失败关闭；evidence/contract 绕过无路径；注入面/错误卫生/不可变性/冒烟失败关闭验证 | PASS（0 P0/P1；3 P2 边界） |

职责隔离 QA 对冻结 `1394a1e` 返回 **PASS**（0 P0/P1；3 个 P2 记录为 prototype
边界：模型提供 label 进入异常 details、单条 user 消息的固有注入面、live 门控在 CI
静默跳过）。红灯真值由父提交 `1407427` 无 `ai_draft_llm` 模块/测试文件确认（过程
披露：红灯测试与实现合并为同一提交）。QA 为只读机器审查；`correlated_review`，
非 owner 接受。

## 证据

- `evidence/TR-20260814-014/`：`ai-draft-llm-qa-attempt-001.md`、`manifest.json`、
  `checksums.sha256`、`commands.txt`、`environment.json`、`gate-summary.txt`。
- `evals/calculus-v1/ai-draft-live-smoke.json`：live 冒烟报告（仅 label/用量/费用）。
- 全仓 pytest 386/386 + 5 skipped；repository validator PASS；Ruff/strict mypy 全绿。

## 遗留边界

- P2：`DraftExtractionError` details 含模型提供的 `label`/`type` 标识（identifier-only
  成立，但 label 可被敌对模型答案影响）。
- P2：chunk 文本仅进单条 user 消息（固有 prompt-injection 面，由严格 schema + 形状
  校验缓解）。
- P2：无 `RUN_LIVE_LLM_TESTS` 时 live 冒烟静默 skip（文档化 opt-in 门控）。
- `relation_validate` 思考模式延迟 ~57s 为原型边界，后续可评估降级/异步策略。
- `correlated_review`：机器证明、同源披露；最终残余风险接受归 workspace owner。
