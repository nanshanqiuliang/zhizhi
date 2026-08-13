# TR-20260814-005：本地 SQLite 持久化工作区 prototype 验证

> 本报告冻结 `8e34a40f02de8d94ad6db3927cf8b189e9caee03`
> 的本地 SQLite 持久化 prototype。它证明数据目录、schema/migration、
> save/load 重启存活、备份/导出/删除与故障注入失败关闭语义；
> 不代表浏览器自动保存、API/UI 接入、FTS5 搜索、导入、加密、
> 多进程或云同步已经完成。

```yaml
status: passed
test_level: integration_security_unit
owner: graph_qa_fresh
related_ids: [WORK-2026-013, REQ-2026-006, REQ-2026-008, NFR-2026-001, ADR-0005, WORK-2026-005, WORK-2026-011, WORK-2026-012]
build_id: 8e34a40f02de8d94ad6db3927cf8b189e9caee03
started_at: 2026-08-14T07:24:00+08:00
finished_at: 2026-08-14T07:45:00+08:00
supersedes: null
```

## 目的与门槛

- 证明本地数据目录可创建/复用/校验，缺库文件时稳定失败。
- 证明已确认 CourseGraph 保存后可重新加载，语义等价且 revision 保留。
- 证明版本化 migration v1 可建库、幂等、拒绝未知版本并失败回滚。
- 证明备份（校验和）、导出（契约 JSON）、删除（purge manifest）一致。
- 证明截断/垃圾字节/非法图/重复 replay 等故障注入均失败关闭，无部分状态。
- 证明 history record JSON 往返保持 WORK-2026-011 语义且 digest 防篡改。

## 方法与结果

| Test ID | 场景 | Actual | Result |
|---|---|---|---|
| TC-PERS-001 | 目录创建/复用/校验 | 布局正确；缺库 `workspace_missing` | PASS |
| TC-PERS-002 | save→close→reopen | 语义等价、revision 保留 | PASS |
| TC-PERS-003 | migration v1 建库/幂等/未知版本/回滚 | `migration_conflict`；无半初始化 | PASS |
| TC-PERS-004 | backup/restore/export/purge | 校验和匹配、契约 JSON、purge manifest 一致 | PASS |
| TC-PERS-005 | 截断/垃圾/非法图/重复 replay | `workspace_corrupt`/`graph_invalid`/`validation_failed` | PASS |
| TC-PERS-006 | record JSON 往返 | 字段/digest 一致；篡改 `record_tampered` | PASS |
| TC-REPO-001 | 完整 Python/仓库门 | 目标 21/21、全仓 175/175、Ruff/mypy/validator | PASS |
| TC-REPO-002 | TS/Web/依赖/构建门 | frozen install、peers、Web 6/6、check、build | PASS |

职责隔离 QA（`graph_qa_fresh`，只读机器审查）对冻结提交 `8e34a40` 返回
PASS，0 P0/P1/P2、无新发现；独立核验提交链（`ec8005e ← 1420b68 ←
8e34a40`）、红灯真实性、内容安全、依赖边界、secret 扫描与 CI mypy 覆盖。
QA 环境无 shell 执行器，其变异为确定性静态推演；本会话随后对全部八类
变异（digest 篡改、截断/垃圾 db、migration 冲突、重复 replay、checksum
篡改、非法图覆盖、purge）做了 live 重放，全部失败关闭，与 QA 结论一致。
角色独立性没有外部 Provider 证明，保守记录 `correlated_review`。

## 证据与结论

- Evidence manifest：`evidence/TR-20260814-005/manifest.json`。
- Decision：GO，仅限 WORK-2026-013 的本地 SQLite persistence prototype
  verification；允许下一工作项接入 Web/API 持久化边界。
- 未完成/未授权：浏览器自动保存与工作区 UI、API/UI 接入、FTS5 全文搜索、
  文件导入/PDF viewer、数据加密、多进程并发、云端同步、真实 Provider/Web、
  用户数据和发布。
