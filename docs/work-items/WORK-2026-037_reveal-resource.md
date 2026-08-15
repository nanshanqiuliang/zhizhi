# WORK-2026-037：打开本地资料目录（第 10 步后用户反馈）

```yaml
status: ready
type: feature
owner: Codex (api + web role)
reviewers: [ai_qa_auditor, workspace_owner]
related_ids: [WORK-2026-016, REQ-2026-001, NFR-2026-001]
target_stage: "阶段 1 / 第 10 步后使用反馈修复"
risk: low
created_at: 2026-08-15T22:40:00+08:00
updated_at: 2026-08-15T22:40:00+08:00
```

## 问题与结果

- 用户/工程问题：使用反馈——「本地资料的打开按钮没有反应，不能一键打开本地目录」。当前
  「打开」只打开应用内查看器；没有一键在资源管理器中打开资料所在目录的能力。
- 期望结果：本地资料区提供「打开资料目录」（打开当前工作区 `resources/` 目录）与每个资源的
  「在文件夹中显示」（explorer 选中该文件）；由本地 sidecar 调用 Explorer，浏览器/窗口模式均可。
- 成功如何被观察：红灯测试（端点缺失 404）→ 实现；`open-dir`/`reveal` 端点返回 200 且路径在
  工作区内；资源/工作区缺失 404；Web 按钮出现并可调用。

## 范围

- In scope：
  - `apps/api/main.py`：`POST /api/workspaces/{id}/resources/open-dir`（打开 `layout.root/resources`）
    与 `POST /api/workspaces/{id}/resources/{rid}/reveal`（`explorer /select, <file>`）；
    `_reveal_in_explorer(path)` 用 `subprocess.Popen(["explorer","/select,",...])`（非 Windows
    优雅 no-op）；路径经 `_storage_key_within`/`get_resource_file_path` 守卫。
  - `apps/web/src/api.ts`：`openResourcesDir()` + `revealResource(rid)`。
  - `apps/web/src/App.tsx`：本地资料区「打开资料目录」按钮 + 每资源「在文件夹中显示」。
  - 测试：`tests/integration/test_resource_reveal.py`（mock `_reveal_in_explorer`：open-dir 200、
    reveal 200、缺失 404、路径在工作区内）；Web 组件测试。
- Out of scope：打开 PDF/文档的关联程序；文件系统级导入（第 11 步）；多工作区切换（WORK-2026-039）。
- 受影响模块：`apps/api/main.py`、`apps/web/src/api.ts`、`apps/web/src/App.tsx`、相关测试。
- 依赖和假设：本地 sidecar 与 UI 同机（桌面/浏览器模式均成立）；Explorer 在 Windows 可用。

## 风险影响

- 数据/schema/migration：无。
- 安全/隐私：仅暴露/打开工作区内已注册资源路径（`_storage_key_within` 守卫）；不暴露任意路径。
- 并发/幂等/恢复：无。
- 性能/容量/成本：无。
- 可观测性/诊断：无。
- 用户文档：手册本地资料区描述更新。

## 验收标准

- [ ] AC-1：`open-dir` 打开工作区 `resources/` 目录（mock 断言路径）。
- [ ] AC-2：`reveal` 用 `explorer /select,` 选中该资源文件（mock 断言）。
- [ ] AC-3：资源/工作区缺失 → 404 `workspace_missing`/`file_not_found`；非 Windows no-op 不报错。
- [ ] AC-4：Web 资料区出现「打开资料目录」与每资源「在文件夹中显示」并调用端点。
- [ ] AC-5：全仓门（validator/Ruff/mypy/pytest/Web）全绿。
- [ ] 错误和恢复路径：目录不存在明确报错；explorer 启动失败不崩溃。
- [ ] 回滚/禁用方法：回退本提交即回无此按钮。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-REVEAL-001 | integration | open-dir 200 + mock 断言路径 | resources 目录 | 待实现 |
| TC-REVEAL-002 | integration | reveal 200 + mock 断言 /select | 资源文件 | 待实现 |
| TC-REVEAL-003 | integration | 缺失 404 + 路径守卫 | workspace_missing/file_not_found | 待实现 |
| TC-REVEAL-004 | component | Web 按钮出现并调用 | openResourcesDir/revealResource | 待实现 |
| TC-REPO-001 | repository | 全仓门 | validator/Ruff/mypy/pytest/Web | 待实现 |

## 交付物与关闭

- Commit/PR：分支 `feature/WORK-2026-037-reveal-resource`；Ready → 红灯 → 实现。
- Contract/ADR/migration/prompt：无新 canonical contract；新增 2 个端点（本地只读操作）。
- Test Run：TC-REVEAL-001..004 + 全仓门。
- Release：随下一个桌面构建。
- 观察结果：职责隔离 QA `TR-20260815-004` PASS；可一键打开资料目录/在文件夹中显示（仅守卫路径）。
- 未完成项的新 ID：无。
