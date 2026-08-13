# TR-20260814-003：纯领域修改回放与 LIFO 撤销/重做验证

> 本报告冻结 `4fc8e60a392d1442f7475aa3f8082e31a1469cde`
> 的内存 history prototype。它证明领域语义可回放/撤销/重做，不代表
> SQLite 持久化、跨进程恢复、API、UI 或产品级撤销已经完成。

```yaml
status: passed
test_level: domain_property_security
owner: graph_qa_fresh
related_ids: [WORK-2026-011, REQ-2026-008, NFR-2026-001, NFR-2026-003, ADR-0004, ADR-0005]
build_id: 4fc8e60a392d1442f7475aa3f8082e31a1469cde
started_at: 2026-08-14T01:36:00+08:00
finished_at: 2026-08-14T01:54:40+08:00
supersedes: null
```

## 目的与门槛

- 证明 confirmed user GraphPatch 可以形成内容绑定的最小内部变更记录。
- 证明顺序 replay、LIFO undo/redo、redo 分支失效和 revision 单调语义。
- 证明非用户/未确认/身份伪造、篡改、乱序、重复、空栈和漂移均失败关闭。
- 证明 history 不扩大公开 GraphPatch/AI 权限、不依赖文件/网络/数据库。

## 方法与结果

| Test ID | 场景 | Actual | Result |
|---|---|---|---|
| TC-HIST-001 | confirmed user apply/record | 只记录变化实体、revision/hash/digest | PASS |
| TC-HIST-002 | 两条记录顺序 replay | 重建同一 snapshot/业务语义 | PASS |
| TC-HIST-003 | 六类 operation undo/redo | 语义往返相等，revision 单调 | PASS |
| TC-HIST-004 | non-user/unconfirmed/spoof | 不产生 record，稳定拒绝 | PASS |
| TC-HIST-005 | tamper/order/duplicate/empty/drift | 全部失败关闭，无部分状态 | PASS |
| TC-HIST-006 | 禁用常见 I/O 入口 | 内存 apply/undo 正常完成 | PASS |
| TC-REPO-001 | 完整 Python/仓库门 | history 18/18、既有 graph 50/50、全仓 154/154、Ruff/mypy/validator | PASS |
| TC-REPO-002 | TS/Web/依赖/构建门 | frozen install、peers、generation/tsc、Web 1/1、build | PASS |

独立 QA 对冻结提交主动变异 record delta/digest/hash/revision/顺序/重复 ID，
并复核两层 LIFO、分支清空、六 operation、caller isolation 与无 I/O，未发现
P0/P1/P2 或新问题。角色独立性没有外部 Provider 证明，保守记录
`correlated_review`。

## 证据与结论

- Evidence manifest：`evidence/TR-20260814-003/manifest.json`。
- Decision：GO，仅限 WORK-2026-011 的 pure-domain prototype verification，
  并允许下一工作项设计可见知识树网页的内存 demo 边界。
- 未完成/未授权：ADR-0005 owner 接受、持久 operation log/periodic snapshot、
  crash recovery、SQLite、API、UI history 面板、真实 Provider/Web、用户数据和发布。
