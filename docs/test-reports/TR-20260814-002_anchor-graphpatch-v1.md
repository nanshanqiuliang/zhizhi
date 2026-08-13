# TR-20260814-002：Anchor / GraphPatch v1 纯领域 prototype 验证

> 本报告冻结 `b946855c3f8d70a850f45ce2630303819c54e1dc`
> 的离线合同与纯领域验证结果。它不代表数据库、API、UI、持久化撤销、
> 真实 AI、发布或 workspace-owner 正式接受已经完成。

```yaml
status: passed
test_level: contract_domain_security
owner: graph_qa_fresh
related_ids: [WORK-2026-005, NFR-2026-001, NFR-2026-002, NFR-2026-003, ADR-0001, ADR-0004, ADR-0006, ADR-0012]
build_id: b946855c3f8d70a850f45ce2630303819c54e1dc
started_at: 2026-08-14T01:14:59+08:00
finished_at: 2026-08-14T01:29:40+08:00
supersedes: null
```

## 目的与门槛

- 验证 Anchor、CourseGraph 和 GraphPatch v1 以 canonical JSON Schema 为
  单一手工事实源，并在 Python/TypeScript 派生产物漂移时失败。
- 验证 GraphPatch preview 对 actor、confirmation、revision、四维锁、
  evidence/origin、端点与 prerequisite DAG 失败关闭，不改变输入且无副作用。
- 验证职责隔离 QA 的失败发现通过先红后绿的回归关闭，并保留失败 attempt。

## 方法与结果

| Test ID | 场景 | Actual | Result |
|---|---|---|---|
| TC-GRAPH-001 | 三份 schema 与派生产物 | canonical schema、Python runtime artifact、TS types 验证/漂移门通过 | PASS |
| TC-GRAPH-002 | 六类 operation preview | 确定性候选快照，input 不变，无持久副作用 | PASS |
| TC-GRAPH-003 | DAG/环/重复/500 节点初值 | 自环、长环、重复边失败关闭；属性/容量测试通过 | PASS |
| TC-GRAPH-004 | actor/确认/四维锁/evidence/origin | 越权与伪造均被稳定拒绝 | PASS |
| TC-GRAPH-005 | graph/target revision 漂移 | `revision_conflict`，无部分结果 | PASS |
| TC-ANCH-001 | 四种 selector/UUIDv7/hash/边界 | 合法通过，非法 bbox/position/quote/hash 拒绝 | PASS |
| TC-IO-001 | 冷启动 runtime 文件 I/O | 清缓存并禁用 `Path.read_text` 仍通过 | PASS |
| TC-REPO-001 | 完整 Python/仓库门 | 专项 50/50、集成 4/4、全仓 136/136、Ruff/mypy/validator | PASS |
| TC-REPO-002 | TS/Web/依赖/构建门 | frozen install、peers、generation/tsc、Web 1/1、build | PASS |

QA attempt 001 对 `a25470c` 找到 1 P1（冷启动读仓库 schema）和
1 P2（测试计数不清）。`1278e79` 先复现 P1，`5ff02a4` 修复生成/runtime
边界，`b946855` 更正记录；attempt 002 对冻结提交给出 PASS，无 P0/P1/P2
或新发现。角色独立性没有外部 Provider 证明，结论保守标记
`correlated_review`。

## 证据与结论

- Evidence manifest：`evidence/TR-20260814-002/manifest.json`。
- Decision：GO，仅限把 WORK-2026-005 移入 prototype verification，并以
  当前 contract 作为后续回放/逆向补丁工作项的输入。
- 未完成/未授权：ADR/PRD 精确 owner 接受、持久 operation log、真正
  undo/redo、数据库、API、UI、resolver、真实 Provider/Web、用户数据和发布。
