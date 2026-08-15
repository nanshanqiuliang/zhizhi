# AI QA attempt 001 — AI edit history (WORK-2026-032, Step 9 final)

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: ai_qa_auditor
decision: pass
reviewed_commit: 954a7c82c507f101107b1c235e67aa4f0b4ec19e
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

**PASS** — 0 P0 / 0 P1；4 个非阻塞 P2（informational，均 Accept）。这是对冻结提交
`954a7c8`（WORK-2026-032 第 9 步收尾：`GraphChangeRecord.source` + `/interpret/accept` +
`GET /history` source + Web「AI」标记）的职责隔离机器审查。

## Red/green chain

Ready（docs）→ 红灯（source 缺失 + /interpret/accept 404，4 failed）→ 实现 `954a7c8`。
红灯真值经实际运行确认（TypeError / 无 source attr / KeyError / 404）。

## Gates（本人执行，精确数字）

ai_edit_history 4/4；回归（graph_history + patch_gate + diff_save_undo）25/25；全仓
434/434 + 5 skipped；ruff format/check pass（94 文件）；strict mypy 33 文件；validator
PASS（含 secret scan）；Web 41/41（tsc + eslint 0 warnings）。

## Adversarial mutation review（scratch 脚本，已删除，32 探针全通过）

- A 向后兼容：manual 记录 JSON 无 source 键、往返 manual；ai_draft JSON 含 source；旧格式
  payload 载入为 manual 且 digest 有效；manual digest == 旧格式 digest；真实跨提交证明
  （红灯代码写的 DB 在绿灯载入为 manual、undo/redo/replay 正常）。
- B digest 完整性：给 manual JSON 加 source、ai_draft→ai_command、删 source、source→int
  均 `record_tampered/record_digest_mismatch`；领域 `_validate_record` 一致拒绝。
- C 提交门/原子性：apply_graph_patch 缺省 manual；accept_ai_draft 存 ai_draft；未确认/过期
  patch 零记录写入。
- D 重放/撤销/重做：source 跨 replay/undo/redo 保留。
- E 端点：/history 每条返回 source；/interpret/accept→ai_command；缺 patch 422；非法 patch
  非 2xx 且无记录；/ai-draft/accept→ai_draft。

## Findings（informational，均 Accept）

| Sev | 位置 | Finding |
|-----|------|---------|
| P2 | workspace.py:864 | `str(parsed.get("source","manual"))` 把任意 JSON 值强转 str；digest 绑定该值，API 从不传调用方可控 source → 无完整性/权限影响。 |
| P2 | graph_history.py:49 | `source: str = "manual"` 未校验（开放字符串非 enum）；与"source 为标记"设计一致，领域内部使用。 |
| P2 | App.tsx:1157 | 徽标对 `source !== "manual"` 显示；陈旧后端缺 source 会把 undefined 渲染为 AI 徽标（monorepo 前后端同发，api.ts 类型要求 source）。 |
| P2 | workspace record_to_json vs 领域 _record_payload | 跨层重复 digest/payload 逻辑（当前字节一致，仅漂移风险）。 |

## Conclusion

PASS。`correlated_review`（机器证明、同源披露），非 owner 接受。
