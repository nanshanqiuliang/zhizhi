# ADR-0006：AI 只能产生草案，不直接写入知识图

```yaml
status: proposed
date: 2026-08-14
decision_owner: workspace_owner / technical_lead (exact confirmation pending)
related_ids: [WORK-2026-005, REQ-2026-008, RISK-2026-002]
supersedes: null
```

## Context and decision

AI 输出是不可信草案。AI/import/system patch 即使 payload 自称 `confirmed=true`，v1 preview 也只返回 `requires_confirmation`；调用方还必须在 payload 之外传入可信 actor type/ID，任何自报身份不一致都以 `permission_denied` 拒绝。AI 概念必须有 evidence reference，AI 先修边必须有 evidence，且任何角色都不能覆盖锁定维度。

本离线实现不调用模型、不写数据库、不认证 owner，也不提供自动接受策略。

## Consequences and rollback

- 人工确认和持久化由后续 application/API 工作项完成。
- 真正 Provider 仍受独立 live gate；本 ADR 不能用来授权联网或费用。
- 此安全不变量不提供“关闭后自动写入”的回滚模式；若产品策略演进，必须通过新的认证 owner policy、ADR 和测试门。
