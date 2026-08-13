# TR-20260813-001：多 LLM 配置静态验证

> 本报告只证明文档与配置静态一致，不证明真实 DeepSeek API 可用。

```yaml
status: passed
test_level: contract
owner: Codex（实施前文档整理）
related_ids: [WORK-2026-007, NFR-2026-006, NFR-2026-007]
build_id: documentation-only
started_at: 2026-08-13T16:00:00+08:00
finished_at: 2026-08-13T16:40:00+08:00
supersedes: null
```

## 目的、范围和门槛

- In scope：YAML 可解析、JSON Schema 文件可解析、deployment/task 引用完整、能力包含关系、HTTPS/host allowlist、预算正值、fallback 上限、疑似密钥和 Markdown 相对链接；
- Out of scope：schema validator 运行、Provider adapter、网络、API Key、DeepSeek live smoke、模型质量/成本/延迟和 Runbook 演练；
- 通过条件：静态脚本无断言失败，链接/秘密扫描通过；
- 限制：工程尚无 Git/build/锁文件，脚本以内联只读检查执行，尚未成为 CI 资产。

## 冻结环境

```text
OS: Windows / PowerShell
timezone: Asia/Shanghai
workspace: E:\知识树
Python: 3.12.6
PyYAML: 6.0.3
app/build/commit: 不存在（documentation-only）
config: llm-providers.v1 revision 1 / llm-model-policies.v1 policy 1
provider live access: disabled
```

## 结果

| Test ID | 场景 | Expected | Actual | Result | Bug | Evidence |
|---|---|---|---|---|---|---|
| CFG-001 | YAML 解析 | 两个文件解析为 object | 通过 | PASS | — | 控制台输出 |
| CFG-002 | JSON Schema 文法 | 两个 schema 为合法 JSON | 通过 | PASS | — | 静态脚本 |
| CFG-003 | deployment 引用 | task 引用均存在 | 3 deployments / 7 profiles | PASS | — | `PASS: 3 deployments...` |
| CFG-004 | capability preflight | 每个候选满足 required capabilities | 无缺项 | PASS | — | 静态脚本 |
| CFG-005 | endpoint/secret ref | HTTPS、host allowlist、引用 scheme 合法 | 通过 | PASS | — | 静态脚本 |
| CFG-006 | budget/fallback | 正值且不超过 global limit | 通过 | PASS | — | 静态脚本 |
| SEC-001 | 疑似真实密钥 | 不存在 | 未发现 | PASS | — | allowlist pattern scan |
| DOC-001 | Markdown 相对链接 | 不存在断链 | 未发现 | PASS | — | PowerShell link scan |

## 结论

- Decision：CONDITIONAL GO，仅允许进入实现前评审；
- 阻断真实启用：产品代码、正式 schema validation、受控密钥、TC-LLM-001..009、EVAL-LLM-001 和 `RB-PROV-001` 演练均不存在；
- DeepSeek 在 `providers.yaml` 中继续保持 `enabled: false`；
- 下一步：建仓后把本次静态检查固化为脚本和 PR gate，再实现 mock/fixture 与 DeepSeek adapter。
