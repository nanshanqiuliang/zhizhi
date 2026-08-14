# TR-20260814-008：安全文件导入与资源注册验证

> 本报告冻结 `eee15d0e5127bd91d7e21124282107a4e02c1f25`
> 的安全文件导入（WORK-2026-016）。它证明 Markdown/TXT/PDF 可被安全
> 导入本地工作区并注册为 resource/resource_version（schema v2）；不代表
> PDF 解析、Markdown 渲染、PDF viewer、Anchor 生成与来源跳转已完成
> （这些属于第 5 步后续工作项）。

```yaml
status: passed
test_level: integration_security_component_repository
owner: graph_qa_fresh
related_ids: [WORK-2026-016, REQ-2026-006, REQ-2026-010, NFR-2026-001, NFR-2026-002, ADR-0001, WORK-2026-004, WORK-2026-005, WORK-2026-013, WORK-2026-014, TR-20260814-005, TR-20260814-006]
build_id: eee15d0e5127bd91d7e21124282107a4e02c1f25
started_at: 2026-08-14T08:55:00+08:00
finished_at: 2026-08-14T09:15:00+08:00
supersedes: null
```

## 目的与门槛

- 证明 schema v2 migration（resource/resource_version）可把 v1 库升级且保留既有数据；未知版本冲突失败。
- 证明 MD/TXT/PDF 受控导入（UUIDv7 磁盘文件名、SHA-256 去重幂等、元数据正确）。
- 证明白名单外类型/伪造扩展名/超大文件/路径逃逸均拒绝且不落盘。
- 证明先落盘后提交 DB，写失败不留孤儿记录；列表端点只返回元数据。

## 方法与结果

| Test ID | 场景 | Actual | Result |
|---|---|---|---|
| TC-IMPORT-001 | migration v1→v2 | 表存在、版本 2、未知版本冲突失败、旧数据保留 | PASS |
| TC-IMPORT-002 | 导入 MD/TXT/PDF | 受控副本 + 元数据正确；重复幂等 | PASS |
| TC-IMPORT-003 | 白名单外/伪造/超大/路径逃逸 | 稳定拒绝且不落盘；写失败无孤儿 | PASS |
| TC-IMPORT-004 | resources 列表 | 元数据不含内容；404 | PASS |
| TC-IMPORT-005 | Web 导入控件与列表 | 导入成功/失败提示可见 | PASS |
| TC-REPO-001 | 完整 Python/仓库门 | import 15/15、全仓 208/208、Ruff/mypy/validator | PASS |
| TC-REPO-002 | TS/Web/依赖/构建门 | frozen install、peers、Web 15/15、check、build | PASS |

职责隔离 QA 对冻结 `10e104f` 返回 PASS（0 P0/P1，5 个非阻塞 P2），在
`50b3245` 确认红灯真实（import 实现不存在）。P2-1（DB 提交与落盘非原子，
写失败留孤儿记录）与 P2-3（mime 死参数）由 `eee15d0` 修复并新增孤儿回归
测试；P2-2（幂等非并发安全）、P2-4（POST 隐式建 workspace，与 PUT /graph
一致）、P2-5（前端错误映射粗糙）记录为原型已知边界。QA 为只读静态推演
（环境无法实跑，已如实披露）；本会话随后实跑全门（208/208、Web 15/15）
并做真实 uvicorn e2e（MD/PDF 导入、同 hash 幂等、exe 拒绝、列表无内容）。
角色独立性无外部 Provider 证明，保守记录 `correlated_review`。

## 证据与结论

- Evidence manifest：`evidence/TR-20260814-008/manifest.json`。
- Decision：GO，仅限 WORK-2026-016 的安全文件导入 prototype verification；
  允许第 5 步后续工作项（PDF 解析/查看器、Anchor 来源跳转）。
- 未完成/未授权：PDF 文本解析与查看器、Markdown 渲染、Anchor 生成与来源
  跳转、url/note 资源、真实 Provider/Web、用户数据和发布。
