# 环境与版本清单

> status: active inventory
> 本地开发工具门已建立；测试、staging 和 production 环境仍不存在。表格只记录实测事实。

## 环境索引

| Environment ID | 用途 | 状态 | Owner | OS/Region | 当前 Release/Build | Config Fingerprint | 数据分类 | 最近验证 | Runbook |
|---|---|---|---|---|---|---|---|---|---|
| local-dev | 本地仓库校验、Web 预览、持久化/PDF/锁定撤销/导入 prototype 与 DeepSeek adapter 受控验证 | verified_prototype | Codex（实现）/项目负责人待定 | Windows x64 / Asia-Shanghai | commit `358c303`+（第 4–7 步）/ no release | 见 `config/llm` fingerprint；无用户数据 | 合成/脱敏 fixture；无真实用户数据 | 2026-08-14 / TR-20260814-005..013 + DeepSeek live smoke 5/5 | 根 README/AGENTS + `docs/USER_MANUAL.md` + RB-PROV-001 |
| ci | 声明式 GitHub Actions 门 | declared_not_executed | 待定 | ubuntu-latest（设计值） | — | — | 固定 fixture | 无远端 run；workflow 仅触发 push main/PR，而工作均在 feature 分支；`RUN_LIVE_LLM_TESTS=0` 使 live 测试默认 skip | — |
| test | 未来集成测试 | not_created | 待定 | 待定 | — | — | 合成/脱敏 | — | — |
| staging | 未来发布候选 | not_created | 待定 | 待定 | — | — | 受控，禁止随意复制生产 | — | — |
| production | 未来实际运营 | not_created | 待定 | 待定 | — | — | 真实用户数据 | — | — |

## Provider 与密钥状态（local-dev）

| Provider | Protocol | Deployment | Model | Enabled | Capability snapshot | Secret reference 状态 |
|---|---|---|---|---|---|---|
| mock | mock | deterministic | mock-deterministic-v1 | true | 契约内嵌（text/JSON/stream/tool/thinking） | 无 |
| deepseek | openai_chat_completions | fast / quality | deepseek-v4-flash / deepseek-v4-pro | **false** | `config/llm/providers.yaml` 快照 + `/models` 探测一致 | `env://DEEPSEEK_API_KEY`（开发 live smoke 用；present，仅环境变量，不落盘） |
| openai / kimi / anthropic | openai_responses / openai_chat_completions / anthropic_messages | （未声明） | — | false | 配置预留 | 未配置 |

真实 DeepSeek smoke 仅在 `RUN_LIVE_LLM_TESTS=1` 且 `DEEPSEEK_API_KEY` 存在时运行，默认跳过；其余 provider 无 secret、无 live 证据，保持关闭。

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
