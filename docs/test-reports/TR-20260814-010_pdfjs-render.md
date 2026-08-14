# TR-20260814-010：PDF.js 可视化渲染与 bbox 区域高亮验证

> 本报告冻结 `d56e7ef07e463b114b55f749f621f11f93d80ebf`
> 的 PDF.js 可视化渲染与 bbox 区域高亮（WORK-2026-018）。它证明已导入
> PDF 可在浏览器以 canvas 渲染、锚点目录跳转后按 `bbox_norm` 高亮区域、
> 窄视口下高亮与页面内容对齐、file/anchors 端点安全；第 5 步最后一个
> 主要产物完成。

```yaml
status: passed
test_level: integration_security_component_repository_browser
owner: graph_qa_fresh
related_ids: [WORK-2026-018, REQ-2026-006, REQ-2026-010, NFR-2026-002, ADR-0001, WORK-2026-016, WORK-2026-017, TR-20260814-005, TR-20260814-008, TR-20260814-009]
build_id: d56e7ef07e463b114b55f749f621f11f93d80ebf
started_at: 2026-08-14T10:00:00+08:00
finished_at: 2026-08-14T11:40:00+08:00
supersedes: null
```

## 目的与门槛

- 证明 PDF.js 以 canvas 渲染指定页（public worker 规避 Windows dev `@fs` 空格问题）。
- 证明锚点目录点击后渲染页并按 `bbox_norm` 高亮区域；窄视口下高亮与内容对齐。
- 证明 file 端点返回 PDF 二进制、缺失资源/文件 404、storage_key 越界拒绝。
- 证明 anchors POST 注册/列表、无效载荷 422。
- 证明 build 产物含 worker，dev/build 均可渲染。

## 方法与结果

| Test ID | 场景 | Actual | Result |
|---|---|---|---|
| TC-RENDER-001 | file 端点 | 二进制/404/source_changed/越界拒绝/文件缺失 404 | PASS |
| TC-RENDER-002 | PDF.js 渲染页 | canvas 生成、翻页/跳锚点 | PASS |
| TC-RENDER-003 | bbox 高亮 | 位置正确（10%/20%/50%/15%）、无 bbox 不画框、窄视口对齐 | PASS |
| TC-RENDER-004 | 漂移/缺失/越界 | 稳定错误，不误跳不泄漏 | PASS |
| TC-REPO-001 | 完整 Python/仓库门 | viewer 12/12、file 4/4、全仓 224/224、Ruff/mypy/validator | PASS |
| TC-REPO-002 | TS/Web/依赖/构建门 | frozen install、peers、Web 20/20、check、build（含 worker） | PASS |
| TC-BROWSER-001 | 真实浏览器（CDP headless） | 查看器/文本/渲染/canvas 979×1267/翻页/锚点跳转/bbox 高亮 | PASS |
| TC-BROWSER-002 | 窄视口 800px | bbox top 20%/left 10%/height 15%/width 50%，aligned | PASS |

职责隔离 QA 对冻结 `2601215` 返回 **FAIL（1 P1：窄视口下 bbox 纵向错位，
7 P2）**——`.pdf-page` 固定内联高度而 canvas 等比收缩导致高亮百分比错位。
P1 由 `d56e7ef` 修复（容器高度由 canvas 撑开），本会话以真实 800px
headless 视口验证 `aligned: true`（此前偏移约 8% 页高），并新增位置断言
测试；P2-1（文件缺失 404 file_not_found）与 P2-4（drift 清 activeAnchor）
一并关闭，其余 P2 记录为原型边界。QA 为只读静态推演（P1 为 CSS 规范级，
环境无法实跑，已如实披露）；本会话实跑全门（224/224、Web 20/20）、真实
uvicorn file 端点 e2e、真实浏览器（CDP）完整渲染/高亮/窄视口验证。
角色独立性无外部 Provider 证明，保守记录 `correlated_review`。

## 证据与结论

- Evidence manifest：`evidence/TR-20260814-010/manifest.json`。
- Decision：GO，仅限 WORK-2026-018 的 PDF.js 渲染与 bbox 高亮 prototype
  verification。第 5 步最后一个主要产物完成，第 5 步标记 100%。
- 未完成/未授权：文本层与页面文本高亮联动、多页连续滚动渲染、Markdown/TXT
  可视化渲染、OCR、中文分词、真实 Provider/Web、用户数据和发布。
