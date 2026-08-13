# 环境与版本清单

> status: baseline placeholder  
> 当前没有已建立的开发、测试、staging 或 production 环境。表格不得提前填写设计目标。

## 环境索引

| Environment ID | 用途 | 状态 | Owner | OS/Region | 当前 Release/Build | Config Fingerprint | 数据分类 | 最近验证 | Runbook |
|---|---|---|---|---|---|---|---|---|---|
| local-dev | 未来本地开发 | not_created | 待定 | 待定 | — | — | 合成/许可 fixture | — | — |
| ci | 未来自动测试 | not_created | 待定 | 待定 | — | — | 固定 fixture | — | — |
| test | 未来集成测试 | not_created | 待定 | 待定 | — | — | 合成/脱敏 | — | — |
| staging | 未来发布候选 | not_created | 待定 | 待定 | — | — | 受控，禁止随意复制生产 | — | — |
| production | 未来实际运营 | not_created | 待定 | 待定 | — | — | 真实用户数据 | — | — |

## 单个环境必须记录

```text
environment_id / purpose / owner / support_hours
OS/architecture/region/timezone
app/desktop/sidecar/build/commit
DB/API/GraphPatch/Anchor/parser/prompt/model-policy versions
dependency lock hashes
config fingerprint and feature flags
llm providers config/policy version and fingerprint
enabled provider/protocol/deployment/model/capability snapshot
Provider secret reference status（只记 present/rotated/revoked，不记值）
database/object/queue/observability endpoints（不含秘密）
backup policy / last successful restore test
data classification / access roles / retention
capacity limits / known differences / maintenance window
```

## 漂移控制

- 环境变化必须关联 `CHG`、构建或版本化配置；
- 生产手工变更立即登记，随后补成声明式配置；
- 每个 Release Candidate 比较 staging/production 与预期 manifest；
- 诊断时先比较环境 fingerprint，不凭“配置应该一样”推断；
- 秘密只记录引用和轮换状态，禁止写值。
