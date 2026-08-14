# TR-20260814-009：PDF 文本解析与 Anchor 来源跳转验证

> 本报告冻结 `267fb7e3e15670fed11a8727960eec738662cbaf`
> 的 PDF 文本解析与 Anchor 来源跳转（WORK-2026-017）。它证明已导入
> 的 PDF 可解析为页文本、页文本与锚点端点可用、漂移/缺失不误跳；
> 不代表 PDF.js 可视化渲染、bbox 区域高亮、Markdown/TXT 查看器已完成
> （这些属于第 5 步后续）。

```yaml
status: passed
test_level: integration_security_component_repository
owner: graph_qa_fresh
related_ids: [WORK-2026-017, REQ-2026-006, REQ-2026-010, NFR-2026-002, ADR-0001, WORK-2026-004, WORK-2026-005, WORK-2026-016, TR-20260814-005, TR-20260814-008]
build_id: 267fb7e3e15670fed11a8727960eec738662cbaf
started_at: 2026-08-14T09:30:00+08:00
finished_at: 2026-08-14T09:45:00+08:00
supersedes: null
```

## 目的与门槛

- 证明 PDF 可解析为页文本并存入 `resource_segment`（schema v3），解析幂等。
- 证明页文本端点正确返回/越界拒绝/未解析提示/缺失 404。
- 证明锚点注册（UPSERT 幂等、返回实际 id）、列表按页排序、缺失资源 404。
- 证明内容漂移（content_hash 变化）时返回 `source_changed` 而非旧定位。
- 证明金标 50 个页级锚点全部可定位。

## 方法与结果

| Test ID | 场景 | Actual | Result |
|---|---|---|---|
| TC-VIEW-001 | PDF 解析 → segment | 52 段、每页 text_hash，幂等 | PASS |
| TC-VIEW-002 | 页文本端点 | 正确文本/越界/未解析/404 | PASS |
| TC-VIEW-003 | anchors 端点 | 金标 50 锚点、UPSERT 幂等、缺失 404 | PASS |
| TC-VIEW-004 | 漂移/缺失定位 | source_changed/anchor_not_found，不误跳 | PASS |
| TC-VIEW-005 | Web 查看器与跳转 | 翻页、跳转、漂移提示 | PASS |
| TC-REPO-001 | 完整 Python/仓库门 | viewer 10/10、全仓 218/218、Ruff/mypy/validator | PASS |
| TC-REPO-002 | TS/Web/依赖/构建门 | frozen install、peers、Web 18/18、check、build | PASS |

职责隔离 QA 对冻结 `8c3c620` 返回 PASS（0 P0/P1，6 个非阻塞 P2），在
`53eb2cd` 确认红灯真实（parse/get_page_text/PageSegment 不存在）。P2-1
（anchor UPSERT 返回悬空 id）、P2-3（锚点端点缺失资源不 404）、P2-4
（storage_key 未校验在 workspace 内）、P2-6（migrate docstring 过时）由
`267fb7e` 修复并新增回归测试；P2-2（漂移读时检查非并发原子）与 P2-5
（前端把越界翻页误报为 drift）记录为原型已知边界。QA 为只读静态推演
（环境无法实跑，已如实披露）；本会话随后实跑全门（218/218、Web 18/18）
并做真实 uvicorn e2e（金标 PDF 解析 52 页、页 1 文本正确、越界 422）。
角色独立性无外部 Provider 证明，保守记录 `correlated_review`。

## 证据与结论

- Evidence manifest：`evidence/TR-20260814-009/manifest.json`。
- Decision：GO，仅限 WORK-2026-017 的 PDF 页文本解析与 Anchor 定位
  prototype verification；允许第 5 步后续工作项（PDF.js 渲染、bbox 高亮）。
- 未完成/未授权：PDF.js 可视化渲染、bbox 区域高亮、Markdown/TXT 查看器、
  OCR、中文分词、真实 Provider/Web、用户数据和发布。
