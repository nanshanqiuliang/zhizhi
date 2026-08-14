# WORK-2026-018：PDF.js 可视化渲染与 bbox 区域高亮

```yaml
status: verified_prototype
type: feature
owner: Codex (viewer-render role)
reviewers: [ai_qa_auditor, workspace_owner]
related_ids: [REQ-2026-006, REQ-2026-010, NFR-2026-002, ADR-0001, WORK-2026-004, WORK-2026-005, WORK-2026-016, WORK-2026-017, TR-20260814-005, TR-20260814-008, TR-20260814-009, TR-20260814-010]
target_stage: "阶段 1 / 自然语言第 5 步"
risk: high
created_at: 2026-08-14T10:00:00+08:00
updated_at: 2026-08-14T11:40:00+08:00
```

## 问题与结果

- 用户/工程问题：WORK-2026-017 已交付 PDF 页文本查看器与锚点目录跳转（从节点可跳到对应页），但用户看到的是纯文本而非 PDF 原貌；`PageBboxSelector`（bbox_norm 0-1 归一化区域）尚未可视化，无法做"从锚点区域高亮原文"的体验。
- 期望结果：新增基于 PDF.js 的可视化渲染：Web 端用 `pdfjs-dist` 渲染 PDF 页面为画布，叠加 `bbox_norm` 高亮框（页级锚点定位到页、bbox 锚点高亮区域）；"从节点跳回原文"升级为可视化定位。
- 成功如何被观察：导入金标 PDF 后，Web 查看器以 PDF.js 渲染页面图像（非纯文本）；点击锚点目录项或节点锚点后跳到对应页并在 bbox 区域显示高亮；漂移/缺失仍明确提示不误跳。

## 范围

- In scope：`apps/web` 用 `pdfjs-dist` 渲染 PDF 页面（canvas）；bbox 高亮叠加层（按 `PageBboxSelector.bbox_norm` 绘制）；API 新增 PDF 文件内容端点（`GET .../resources/{rid}/file`，仅已注册资源、受控副本）；查看器把页文本视图与 PDF.js 渲染视图切换/并列；锚点目录项点击后在渲染页高亮；金标 50 页级锚点验收 + 合成 bbox 锚点验收。
- Out of scope：OCR、文本层与页面文本高亮联动、多页连续滚动渲染（先单页视图）、云同步、加密、真实 AI/Provider、Markdown/TXT 可视化渲染。
- 受影响模块/接口/数据：`apps/web`（pdfjs-dist 依赖、渲染组件）、`apps/api`（file 端点）；复用 schema v3 resource_version.storage_key 与 anchor 表；无新 canonical contract/migration/prompt。
- 依赖和假设：pdfjs-dist 6.x 已锁定；`GET .../file` 返回 `application/pdf` 二进制（Content-Disposition inline），只允许已注册资源且校验 workspace 内路径；bbox_norm 为 [x0,y0,x1,y1] 归一化（左上→右下），渲染时乘页面尺寸。

## 安全与边界

- file 端点只读受控资源副本，复用 `_storage_key_within` 守卫；错误不含正文。
- PDF.js 渲染在浏览器本地执行，不把文件内容发往网络；无 CSP 放宽或远程 worker 需求（用本地 worker 或主线程）。
- 高亮只读，不修改资源；漂移时 file 端点同样返回 `source_changed`。

## 风险影响

- 数据/schema/migration：无 schema 变化；file 端点读既有 storage_key。
- 安全/隐私：受控读取 + 路径守卫；无网络出站；错误不含正文。
- 并发/幂等/恢复：渲染无写；file 端点幂等。
- 性能/容量/成本：单页 canvas 渲染；≤25 MiB 导入上限；无模型费用。
- 可观测性/诊断：稳定错误码（`source_changed`/`file_not_found`）；不落正文。
- 用户文档：更新 USER_MANUAL 与路线第 5 步完成状态（100%）。

## 验收标准

- [x] AC-1：`GET .../resources/{rid}/file` 返回 PDF 二进制（正确 Content-Type），缺失资源 404、漂移 `source_changed`、storage_key 越界拒绝、文件缺失 404。
- [x] AC-2：Web 用 PDF.js 渲染指定页为 canvas；翻页/跳锚点页切换渲染。
- [x] AC-3：带 `page_bbox` 的锚点在被跳转页显示高亮框（位置按 bbox_norm × 页面尺寸）；无 bbox 锚点只定位页不画框；窄视口对齐。
- [x] AC-4：锚点目录点击 → 渲染页 + 高亮；漂移/缺失明确提示不误跳。
- [x] AC-5：集成/组件/安全测试覆盖正/负路径；全仓门通过。
- [x] 错误和恢复路径：PDF 加载失败显示可见错误，不影响既有编辑；file 端点失败不污染数据。
- [x] 回滚/禁用方法：回退本工作项提交可回到页文本查看器；不影响既有持久化/导入/跳转证据。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-RENDER-001 | integration | file 端点 | 二进制/404/source_changed/越界拒绝/文件缺失 404 | 4/4 PASS / TR-010 |
| TC-RENDER-002 | component | PDF.js 渲染页 | canvas 生成、翻页/跳锚点 | Web 20/20 PASS / TR-010 |
| TC-RENDER-003 | component | bbox 高亮 | 高亮框位置正确、无 bbox 不画框、窄视口对齐 | Web 20/20 PASS / TR-010 |
| TC-RENDER-004 | security | 漂移/缺失/越界 | 稳定错误，不误跳不泄漏 | 4/4 PASS / TR-010 |
| TC-REPO-001 | repository | 全仓门 | validator/Ruff/mypy/pytest/Web | 224/224、20/20 PASS / TR-010 |
| TC-BROWSER-001 | browser | CDP 完整渲染/高亮 | 查看器/文本/渲染/canvas/翻页/锚点/bbox | ALL PASS / TR-010 |
| TC-BROWSER-002 | browser | 窄视口 800px | bbox 10%/20%/50%/15% aligned | PASS / TR-010 |

## 交付物与关闭

- Commit/PR：分支 `feature/WORK-2026-018-pdfjs-render`；Ready `54a108b`，红灯 `275d7c6`，实现 `2601215`，P1/P2 修复 `d56e7ef`。
- Contract/ADR/migration/prompt：无新 canonical contract/migration；file/anchors 端点；public worker 运行时资源；无 prompt。
- Test Run：viewer 12/12、file 4/4、全仓 Python 224/224、Web 20/20、Ruff、strict mypy、repository validator、frozen installs/peers/check/build（含 worker）全通过；QA attempt 001 FAIL（1 P1）→ 修复后浏览器验证；真实浏览器（CDP）完整渲染/高亮/窄视口 aligned；证据为 `TR-20260814-010`。
- Release：无托管发布；本地 API + Web 可演示 PDF.js 渲染与高亮。
- 观察结果：PDF.js 可视化渲染与 bbox 高亮已验证，第 5 步最后一个主要产物完成；第 5 步标记 100%。
- 未完成项的新 ID：文本层与页面文本高亮联动、多页连续滚动渲染、Markdown/TXT 可视化渲染、OCR、中文分词分别后续建项。

## 决策记录

- 用 `pdfjs-dist` 官方 npm 包（v6.2.108）；渲染用主线程 worker（`GlobalWorkerOptions.workerSrc` 指向包内 worker），本地执行无网络。
- 高亮层用绝对定位 div 叠加在 canvas 上，坐标 = `bbox_norm` × canvas CSS 尺寸。
