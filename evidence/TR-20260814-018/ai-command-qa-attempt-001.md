# AI QA attempt 001 — natural-language -> GraphPatch (WORK-2026-029, Step 9 slice 2)

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: ai_qa_auditor
decision: pass
reviewed_commit: b4fde38ba8fdbcf03bcd760a4645af778e170307
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

**PASS** — 0 P0 / 0 P1；2+1 个非阻塞 P2。这是对冻结提交 `b4fde38`
（WORK-2026-029 切片 2：`build_command_patch` + `POST /interpret` + Web 指令预览/接受/拒绝）
的职责隔离机器审查。

## Red/green chain

Ready（docs）→ 红灯 `9c65a8b`（ModuleNotFoundError + Web 无指令输入）→ 实现
`b4fde38`。红灯真值经实际运行确认（`ModuleNotFoundError: knowledge_tree_infrastructure.command`
+ `getByRole("textbox", {name:/向知识树下达指令/})` 找不到）。

## Gates（本人执行，精确数字）

command 6/6；全仓 415/415 + 5 skipped；ruff format/check pass（91 文件）；strict
mypy 33 文件（+ scripts 11）；validator PASS（含 secret scan）；Web command 1/1；
`pnpm check` 39 tests + tsc + eslint 0 warnings；`pnpm build` exit 0。

## Adversarial review（scratch worktree，已删除）

Part A 20/20 需求探针通过：label 映射失败关闭（未知/非串/空）、未知 op、非法
dimension/edge_type、非 dict op → CommandError/422；精确 revision 绑定；proposal 标志；
自环/重复边/过期 base/locked target/未确认被门拒绝（interpret 只读）；畸形 LLM 输出
422 永不 500；503/404/422 矩阵；密钥 env-only；发给 LLM 的概念仅 {id,label}；
/interpret 零写（history/anchors/graph 不变）。Part B 12 变异 6 捕获 / 6 幸存（覆盖缺口）。

## Findings

| Sev | Finding |
|-----|---------|
| P2 | 错误 details 原样回显 LLM 发出的 target label——行为异常的模型把整条命令当 label 会导致命令正文进入 422 body（仅回给本地请求者，不落盘/日志，但偏离"仅标识"）。 |
| P2 | 回归覆盖缺口：committed 6 测试未覆盖非串/空 label、未知 op、非法 dimension、非法 edge_type、非 dict op、非零 revision 绑定（fixture 全 revision 0）。 |
| P2 | Web 测试仅覆盖 interpret+preview；accept-flips-confirmed/reject-never-applies/ai_not_available 无测试。 |

## Post-review fix

`9a255d2`：P2-1 label/dimension/edge_type 改发 `*_hash`（sha256[:12]）；P2-2 补 6 个回归；
P2-3 补 3 个 Web 回归。`9abd339`：op_unknown 也改发 `op_hash`（QA note 一致性）。

## Superseding review

见 `ai-command-qa-attempt-002.md`：对 `9a255d2` 返回 PASS（0 P0/P1）。
