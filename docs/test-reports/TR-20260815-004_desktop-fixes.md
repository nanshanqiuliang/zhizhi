# TR-20260815-004：第 10 步后使用反馈修复验证（WORK-2026-036..039）

> 本报告密封四项修复（拖拽 `69d0de9`、打开本地目录 `1f01795`、AI 接入设置 `abf2d9a`、
> 多课程 `e0fc05f`）。它证明：拖拽仅左键按住时进行且松键即停；可一键打开资料目录/在文件夹中
> 显示；应用内可配置 DeepSeek Key（草案/问答/指令即时可用）；可新建并切换多门课程。超集修复
> `c577928` 关闭 1 P2（ruff 格式）与 1 P3（右键过滤）。

```yaml
status: passed
test_level: unit_integration_component_repository_e2e
owner: ai_qa_auditor
related_ids: [WORK-2026-036, WORK-2026-037, WORK-2026-038, WORK-2026-039, REQ-2026-001, NFR-2026-001]
build_id: abf2d9a6f6ef03159f3e140c74c92cdcb9f1f4eb
started_at: 2026-08-15T23:00:00+08:00
finished_at: 2026-08-15T23:40:00+08:00
supersedes: null
```

## 目的与门槛

- 证明拖拽仅左键按住（`buttons & 1`）时进行；松键/pointercancel 即结束（036）。
- 证明 `open-dir`/`reveal` 打开本地目录且仅限工作区内守卫路径（037）。
- 证明 `/api/settings/ai` 保存/清除 key（配置文件优先、env 兜底、不回显），保存后 AI 可用、
  无 key 仍 503（038）。
- 证明 `GET/POST /api/workspaces` 列出/新建课程，Web 可切换（039）。
- 证明全仓门全绿。

## 方法与结果

| Test ID | 场景 | Actual | Result |
|---|---|---|---|
| TC-DRAG-001/002 | 按住左键拖拽 / 松键后不再拖 | 移动 vs 不动（App.test 新用例） | PASS |
| TC-REVEAL-001..003 | open-dir/reveal 200 + 守卫 + 404/422 | explorer spy 参数正确、篡改路径拒绝 | PASS |
| TC-AI-001..003 | load/save_api_key + GET/PUT/DELETE + 503 | 配置文件优先/env 兜底、不回显、fail-closed | PASS |
| TC-WS-001..003 | 列表/创建/名称 422 | 新课程可列出可载图、隔离 | PASS |
| TC-REPO-001 | 完整门 | pytest 454/454 + 5 skipped；ruff；mypy 40；validator；Web 47/47 | PASS |
| QA-001 | 职责隔离对抗审查 | 45 API 探针 + 冻结 exe 探针 + 红灯重跑 | PASS（0 P0/P1，1 P2 + 3 P3） |

职责隔离 QA 对四项修复返回 **PASS**（0 P0/P1；1 P2 + 3 P3）。QA 执行 45 个对抗 API 探针
（含篡改 storage_key 拒绝、非 Windows no-op、env-DELETE 边界、损坏 ai.json），冻结 exe 探针
12/12 证明四项修复均在重建产物中生效；红灯 037/038/039 真值实际重跑。

P2/P3 处置：P2（ruff 格式，`test_resource_reveal.py`）+ P3（右键过滤）由 `c577928` 修复；
P2*（非默认课程图内部 workspace id 为默认值，目录隔离完好）与 P3（env key 在 DELETE 后仍为
configured:true）记录为文档化 MVP 边界。

## 证据

- `evidence/TR-20260815-004/`：QA attempt 001、manifest、checksums、commands、environment、
  gate-summary。
- 本报告 `docs/test-reports/TR-20260815-004_desktop-fixes.md`。

职责隔离 QA 为 `correlated_review`（机器审查），非人类签名、非 owner 接受；最终残余风险接受属于
workspace owner。
