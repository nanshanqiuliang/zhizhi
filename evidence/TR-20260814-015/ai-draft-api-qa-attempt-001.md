# AI QA attempt 001 — AI draft API + Web accept/reject (WORK-2026-026 slice 3)

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: ai_qa_auditor
decision: fail
reviewed_commit: dfbcc306d116c49d924d3ba9280e9c93e12c5ccb
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

**FAIL** — 1 P1 + 3 P2。这是对冻结提交 `dfbcc30`（WORK-2026-026 切片 3：AI 草案
API 端点 + Web 生成/预览/接受/拒绝）的职责隔离只读机器审查。核心闭环（生成 → 预览 →
确认 → 提交门）正确：生成只读、接受仅经提交门、无密钥落盘、provenance 保持
evidence。唯一 P1 是 `read_resource_text` 的 PDF 漂移守卫为恒真（死代码）。

## Findings

### P1

- **`workspace.py:1170-1179,1190`** — `read_resource_text` 的 PDF 漂移守卫恒真：
  `parsed_hash` 读自 `resource_version.content_hash`（`_check_drift` 再读同一行的同一列，
  比较恒等），`source_changed` 不可达。证明：变异 `resource_version.content_hash` 后
  `read_resource_text` 仍返回 129,604 字符不抛错；而既有 `get_page_text`（`segment_row[3]`
  传 parse-time hash）与 TC-VIEW-004 证明正确接线。影响有界（非 API 可达，需本地 DB 篡改），
  但"drift-checked"文档声明为假。

### P2

- `apps/api/ai_draft.py:76` — `build_deepseek_draft_generator` 调 `load_and_validate_llm_config`
  无 catch；设 Key 且配置损坏时 `python -m apps.api` 启动即崩（整 API down，非文档化 503）。
- `apps/api/main.py` + `ai_draft.py` — 端点重新作者化后不再独立校验 evidence；上游
  `build_draft_patch` 已强制 `draft_evidence_required`，且 user patch 契约合法允许空 evidence，
  属 defense-in-depth 注记（非代码缺陷）。
- 提交信息测试计数不实（"6+3=9" 实为 5+3=8）；红/绿灯 docstring 过期；无 `read_resource_text`
  漂移测试（P1 未被发现的根因）。

## Post-review fix

`d47ce88`：P1 改为把 `resource_segment` 的 parse-time `content_hash` 传入 `_check_drift`
（对齐 `get_page_text`），并补镜像 TC-VIEW-004 的漂移回归测试；P2-1 用 try/except 包裹
config 加载/adapter 接线返回 None（503 失败关闭）；P2-3 修正过期 docstring。

## Superseding review

见 `ai-draft-api-qa-attempt-002.md`：对 `d47ce88` 返回 PASS（0 P0/P1）。
