# WORK-2026-013：本地 SQLite 持久化工作区 prototype

```yaml
status: ready
type: feature
owner: Codex (local persistence role)
reviewers: [ai_qa_auditor, workspace_owner]
related_ids: [REQ-2026-006, REQ-2026-008, NFR-2026-001, ADR-0005, WORK-2026-005, WORK-2026-011, WORK-2026-012]
target_stage: "阶段 1 / 自然语言第 4 步"
risk: high
created_at: 2026-08-14T07:24:00+08:00
updated_at: 2026-08-14T07:24:00+08:00
```

## 问题与结果

- 用户/工程问题：Web Demo（WORK-2026-012）所有数据只存在于会话内存，刷新/关闭即丢失；GraphPatch v1（WORK-2026-005）与纯领域回放/撤销（WORK-2026-011）已验证，但没有任何落盘能力，无法兑现“关闭并重新打开后内容仍在；数据可导出、备份和恢复”的第 4 步完成标志。
- 期望结果：新增一个纯 Python + 标准库 `sqlite3` 的本地工作区持久化 prototype：数据目录、版本化 SQLite schema/migration、CourseGraph 保存/加载、重启存活、备份/导出/删除、迁移回滚，以及断电/损坏/重复 replay 的失败证据。
- 成功如何被观察：把已确认的 CourseGraph 写入本地 SQLite 后关闭进程，重新打开能按 revision 语义恢复同一图；导出为校验过的 JSON；备份文件可恢复；迁移失败或数据库损坏时以稳定错误失败关闭，不产生部分写入。

## 范围

- In scope：数据目录布局与校验；SQLite schema v1 + 版本化 migration 框架；CourseGraph 保存/加载（复用 `validate_course_graph`/`validate_contract`）；重启存活；备份（SQLite 在线备份或文件复制 + 校验和）、导出（JSON）、删除（purge manifest 语义）；迁移回滚；损坏/断电/重复 replay 故障注入测试。
- Out of scope：Web API/UI 接入（自动保存、工作区选择界面）、FTS5 全文搜索、文件导入、PDF viewer、真实 AI/Provider、多进程并发、云端同步、数据加密、内存 Demo 的自动持久化改写。
- 受影响模块/接口/数据：新增 `packages/infrastructure` 的 SQLite adapter 与 `docs/contracts` 的 workspace schema（如需要）；复用 `knowledge-tree-graph.v1` canonical schema 与 `GraphHistory` 记录语义；不修改既有 domain/contract 公共 API 的语义。
- 依赖和假设：Python 3.12 标准库 `sqlite3` 可用，不新增第三方依赖；`sqlite3` 模块原生支持 WAL、事务与备份；schema 用 `PRAGMA user_version` 或专用 meta 表做版本化迁移；历史记录沿用 WORK-2026-011 的 `GraphChangeRecord` JSON 表示。

## 风险影响

- 数据/schema/migration：新增 SQLite schema v1 与 migration 框架；迁移必须版本化、可回滚、防重复执行；不得以删除既有测试替代关键不变量。
- 安全/隐私：只写测试目录或显式传入的数据目录；不读取网络/secret；错误 details 不含笔记正文；导出/备份内容不含 secret。
- 并发/幂等/恢复：单进程本地写入；WAL 模式；写操作在单个事务内原子提交；损坏/截断文件与重复 replay 必须失败关闭；不声明崩溃后自动恢复。
- 性能/容量/成本：目标单课程数百节点规模；SQLite 默认参数足够；无模型费用。
- 可观测性/诊断：稳定 `snake_case` 错误码（如 `workspace_corrupt`、`migration_conflict`、`purge_incomplete`）；诊断不落正文。
- 用户文档：更新 USER_MANUAL 与路线的“持久化仍未接入 UI”边界；不把 prototype 写成产品已保存。

## 验收标准

- [ ] AC-1：数据目录可创建/复用，非法目录或缺失必要文件时稳定失败；目录内布局（db 文件、backups/、exports/）与文档一致。
- [ ] AC-2：已确认 CourseGraph 保存后可重新加载，语义等价且 revision 保留；加载时先做 canonical schema 校验。
- [ ] AC-3：版本化 migration 可从空库按序建到 v1；重复/乱序迁移稳定失败；迁移失败可回滚且不留半初始化状态。
- [ ] AC-4：备份生成校验和，可从备份恢复库；导出 JSON 通过 graph contract 校验；删除走 purge manifest 语义，删除后数据库与目录状态一致。
- [ ] AC-5：故障注入（截断 db、垃圾字节、断电式中断写入、重复 replay 历史）均以稳定错误失败关闭，不产生部分图或伪成功。
- [ ] 错误和恢复路径：损坏库可被检测并提示重新创建/恢复备份；调用方基于 code/details 决定处理，不自动猜测。
- [ ] 回滚/禁用方法：回退本工作项提交即可禁用持久化；不得复用内存 Demo 冒充保存能力。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-PERS-001 | integration | 目录创建/复用/校验 | 布局正确，非法路径失败 | 红灯→绿灯 |
| TC-PERS-002 | integration | save→close→reopen | 语义等价、revision 保留 | 红灯→绿灯 |
| TC-PERS-003 | integration | migration v1 建库/重复/乱序/回滚 | 版本正确，冲突失败 | 红灯→绿灯 |
| TC-PERS-004 | integration | backup/export/delete | 校验和匹配、契约校验通过、purge 一致 | 红灯→绿灯 |
| TC-PERS-005 | security/integration | 截断/垃圾字节/中断写入/重复 replay | 稳定错误，无部分状态 | 红灯→绿灯 |
| TC-PERS-006 | unit | history record JSON 往返 | 与 WORK-2026-011 语义一致 | 红灯→绿灯 |

## 交付物与关闭

- Commit/PR：分支 `feature/WORK-2026-013-local-sqlite-workspace`；先提交失败 persistence/restart 测试，再实现最小 adapter。
- Contract/ADR/migration/prompt：新增 workspace 相关 schema（如需要）；无 prompt 变化。
- Test Run：全仓门（repository validator、Ruff、mypy、pytest、pnpm）按 DoD 执行；职责隔离 QA 对冻结 SHA 复核。
- Release：无托管发布；本地 CLI/测试可演示。
- 观察结果：本轮只交付持久化 prototype，不接入浏览器；重启存活与备份/导出/删除必须可重复验证。
- 未完成项的新 ID：UI/API 接入、自动保存、FTS5 搜索、文件导入、加密与多进程分别后续建项。
