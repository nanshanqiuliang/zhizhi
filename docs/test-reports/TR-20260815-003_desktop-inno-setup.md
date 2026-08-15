# TR-20260815-003：Inno Setup 安装器验证（WORK-2026-035，第 10 步切片 3b）

> 本报告密封 `c0cd6a98c0911b43a57fc399fc6459dfb5203445` 的 WORK-2026-035（第 10 步切片 3b：
> Inno Setup 安装器 + 应用图标）。它证明安装器可静默安装（开始菜单/卸载器/注册表）、覆盖安装
> 升级、静默卸载且用户数据始终保留；超集修复 `cb46909` 关闭 1 P2 + 3 P3 并瘦身冻结产物
> （排除 PIL/mypy/hypothesis 等开发依赖，安装器 22.6→18.4 MB）。

```yaml
status: passed
test_level: unit_repository_build_e2e
owner: ai_qa_auditor
related_ids: [WORK-2026-035, WORK-2026-033, WORK-2026-034, REQ-2026-001, NFR-2026-001]
build_id: c0cd6a98c0911b43a57fc399fc6459dfb5203445
started_at: 2026-08-15T22:00:00+08:00
finished_at: 2026-08-15T22:20:00+08:00
supersedes: null
```

## 目的与门槛

- 证明 `installer.iss` 固定 AppId、按用户安装、开始菜单/桌面快捷方式、卸载器注册。
- 证明 `build_installer.py` 产出 `dist/zhizhi-<version>-setup.exe`。
- 证明静默安装 → 文件/快捷方式/卸载器正确；静默卸载 → 全部移除、数据保留。
- 证明覆盖安装升级后用户数据仍在。
- 证明全仓门全绿。

## 方法与结果

| Test ID | 场景 | Actual | Result |
|---|---|---|---|
| TC-INST-001 | installer.iss 存在 + 关键节 | AppId/PrivilegesRequired/Icons/Run 齐备 | PASS |
| TC-INST-002 | build_installer 产出 setup.exe | 23,675,549 B，exit 0 | PASS |
| TC-INST-003 | 静默安装/卸载 + 数据保留 | exe/开始菜单/卸载器/HKCU 正确；卸载后全移除、数据保留 | PASS |
| TC-INST-004 | 覆盖安装升级数据保留 | 标记文件内容不变 | PASS |
| TC-REPO-001 | 完整门 | pytest 448/448 + 5 skipped；Ruff；strict mypy（39）；validator；Web 42/42 | PASS |
| QA-001 | 职责隔离对抗审查 | 红灯重跑 + 安装/升级/卸载冒烟 + ISCC 缺失路径 + 图标可复现 | PASS（0 P0/P1，1 P2 + 3 P3） |

职责隔离 QA 对冻结 `c0cd6a9` 返回 **PASS**（0 P0/P1；1 P2 + 3 P3 均非阻塞，`cb46909` 关闭）。
QA 独立执行完整静默安装/升级/卸载循环（含 HKCU 注册表 + 数据标记检查），复现红灯真值，验证
ISCC 缺失 fail-closed 与图标字节可复现；静态追踪 AppId/免管理员/`uninsdelete` 语义与
`[Files]` 仅本地来源。

## 证据

- `evidence/TR-20260815-003/`：QA attempt 001、manifest、checksums、commands、environment、
  gate-summary。
- 本报告 `docs/test-reports/TR-20260815-003_desktop-inno-setup.md`。

职责隔离 QA 为 `correlated_review`（机器审查），非人类签名、非 owner 接受；最终残余风险接受属于
workspace owner。
