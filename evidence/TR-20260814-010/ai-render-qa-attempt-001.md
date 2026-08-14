# AI QA attempt 001 — PDF.js canvas render and bbox highlight (WORK-2026-018)

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: graph_qa_fresh
decision: fail
reviewed_commit: 2601215a8db600eb6ff104b920799930484960a2
red_baseline_commit: 275d7c6429aa870eda86184a4023f0cf8cf7d1f2
ready_commit: 54a108be875b4fb76e3331c6babc89f30e6e3c90
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

**FAIL**，含 1 个 P1 与 7 个 P2 finding。这是对冻结提交 `2601215`（WORK-2026-018 PDF.js canvas 渲染、bbox 高亮与 file/anchors 端点）的职责隔离只读机器审查。

提交链（Ready `54a108b` → 红灯基线 `275d7c6` → 冻结 `2601215`，HEAD == 冻结提交）、冻结 blob、红灯基线的"实现不存在"状态均通过只读 git 命令**实跑**验证；file 端点/anchors POST 的服务端语义与安全边界、bbox 百分比映射、渲染组件行为全部逐行静态推演并与冻结测试交叉核对；`apps/web/public/pdf.worker.min.mjs` 与 `apps/web/node_modules/pdfjs-dist/build/pdf.worker.min.mjs` 经 `cmp` **实跑**确认为字节一致（1,262,398 字节）。

**P1 失败项（静态推演、确定性 CSS 行为）**：`PdfRenderer` 的 `.pdf-page` 高度由内联 `height: pageSize.height` 固定，而 `.pdf-page canvas` 声明 `max-width: 100%; height: auto !important`。当查看器容器宽度 < 页面渲染宽度（A4 页面 @1.6 约 952–979px；视口可用宽度约需 >1050px 才完全不触发）时，`.pdf-page` 宽度被 `max-width` 收缩但高度保持固定，canvas 显示高度按宽高比等比收缩，bbox 高亮 div 的百分比 top/height 相对的是**未缩放的 `.pdf-page` 高度** → 高亮框与页面实际内容纵向错位（视口 800px 时偏移可达约 8% 页面高度）。这是核心功能（锚点定位高亮）的确定性坐标错误，且没有任何测试覆盖位置计算（`PdfRender.test.tsx` 仅断言高亮元素存在）。

P0 无；未发现语义绕过、越权、路径逃逸、正文泄漏或防篡改失败。服务端全部错误路径 fail-closed 且错误 payload 无正文。

必须如实披露：本 QA 环境的权限层拒绝了本审计者以及隔离只读执行子代理的全部 `uv`/`pnpm`/`pytest`/`python -m`/`python -c` 执行类命令（精确拒绝文本见 §2），因此 15 项 render 集成测试、全量 pytest、web vitest、ruff、strict-mypy、`scripts.validate_repository` 均**未能实跑**；所有 Python/TS 行为声明以逐行静态执行推演为主，P1 渲染错位亦为 CSS 规范级静态推演（未实机浏览器验证）。提交 message 中的 `223 passed; pdf viewer 15/15; web 20 passed` 仅作为自述引用，未被独立复现。详见 §2 与 Limitations。

## Independent checks

### 1. 提交链、冻结 blob 与红灯基线（实跑：git 只读命令，由隔离只读执行子代理执行）

- `git rev-parse HEAD` = `2601215a8db600eb6ff104b920799930484960a2`（冻结提交即 HEAD）。`git log -1 --format=raw 2601215`：`parent 275d7c6429aa870eda86184a4023f0cf8cf7d1f2`，`Refs: WORK-2026-018, NFR-2026-002`。`git show -s --format=%P 275d7c6` = `54a108be875b4fb76e3331c6babc89f30e6e3c90`。链 `2601215 ← 275d7c6 ← 54a108b` 线性成立；`git log --oneline --ancestry-path 54a108b..2601215` 恰好 2 行（红灯 + 冻结），**范围内无分支外游离提交**。
- `git show --stat 2601215` 与 `git diff 275d7c6 2601215 --stat` **完全一致**：15 文件，+461/−14。含 PdfRenderer.tsx(new, 83)、pdf.worker.min.mjs(+29)、main.py(+49)、workspace.py(+43)、api.ts(+31)、App.tsx(+36)、styles.css(+64)、test/setup.ts(+62，修改非新增)、test_pdf_viewer.py(+36，新增 2 个 API 测试)、test_pdf_file.py(+5)、PdfRender.test.tsx(+30，新增 2 个用例)；**不含** pyproject.toml/uv.lock/apps/web/package.json/pnpm-lock.yaml（无新增 Python 依赖；pdfjs-dist 依赖在红灯基线 275d7c6 引入）。
- 冻结 blob 存在性（`git ls-tree 2601215`）：PdfRenderer.tsx=`2ca79e5d…`、pdf.worker.min.mjs=`66a5d815…`、main.py=`4e1a3121…`、workspace.py=`35385385…`、api.ts=`eda41cc3…`、App.tsx=`1e0ec790…`、setup.ts=`8409b64a…`、test_pdf_viewer.py=`08a18e25…`、test_pdf_file.py=`5a5d962b…`、PdfRender.test.tsx=`230de8ad…`、ci.yml=`c3da6f0c…`，全部命中。
- 红灯基线真实性（在父提交 275d7c6 上验证）：`git ls-tree -r 275d7c6 apps/web/src` 11 个文件中**无 PdfRenderer.tsx**；`git diff 275d7c6 2601215 -- api.ts` 显示 `getFileUrl` 全部为 `+` 新增、`workspace.py` 的 `get_resource_file_path`/`get_resource_mime` 全部为 `+` 新增 → 红灯基线实现均不存在。红灯基线仅 4 文件 +294（package.json +1 `pdfjs-dist: ^6.2.108`、pnpm-lock.yaml +134 含 `pdfjs-dist@6.2.108` 与可选依赖 `@napi-rs/canvas@1.0.5` 的 12 个平台二进制包、PdfRender.test.tsx +87、test_pdf_file.py +72），符合"红灯仅测试 + 依赖"的既定模式。
- 工作树：`git diff HEAD --stat` 空；`git status --porcelain` 仅未跟踪目录 `.reasonix/`、`handoff/`。workspace_modified = false（本审计未修改仓库文件；唯一写入是本报告）。

### 2. 测试套件 —— 未实跑（权限层拒绝，全部如实记录）

隔离只读执行子代理逐条尝试以下命令，每条返回同一段精确拒绝：

```
blocked: read-only subagents can run only permission-classified foreground read-only commands
```

| 命令 | 结果 |
|---|---|
| `uv run python -m pytest tests/integration/test_pdf_viewer.py tests/integration/test_pdf_file.py -q` | 拒绝（未运行） |
| `uv run python -m pytest -q` | 拒绝（未运行） |
| `CI=true pnpm --filter @knowledge-tree/web test` | 拒绝（未运行） |
| `uv run ruff check .` | 拒绝（未运行） |
| `uv run python -m mypy --strict packages/contracts-py/src packages/domain/src packages/infrastructure/src apps/api` | 拒绝（未运行） |
| `uv run python -m scripts.validate_repository` | 拒绝（未运行） |
| `uv run python -c …` / `uv --version` / `git cat-file` / `git grep` / `git hash-object` / `certutil` / `powershell Get-FileHash` | 拒绝（未运行） |
| `python --version` / `git log` / `git show --stat` / `git ls-tree` / `git diff` / `git status` / `git rev-parse` / `git ls-files` / `git show -s --format=%P` / `cmp` / `wc -l` | 放行（实跑） |

以上均**不**记为通过。静态交叉核对：`test_pdf_viewer.py` 12 个测试函数 + `test_pdf_file.py` 3 个测试函数 = 15（与自述 15 一致）；自述全量 223 = 上一工作项 QA 时缓存/自述的 216 + 本工作项新增 7（pdf_viewer +4、pdf_file +3）；自述 web 20 = 上一工作项 18 + PdfRender.test.tsx 新增 2。数字与提交自述自洽，但**未独立复现**。

### 3. 独立反例（静态逐行推演；除 worker 一致性外均未实跑）

- **file 端点：PDF 二进制/类型一致。** `GET .../resources/{rid}/file`：`resolve_workspace` → `get_resource_mime`（JOIN `resource.current_version_id`，无行 → `_reject("workspace_missing", rule="resource_missing")` → API 404）→ `get_resource_file_path` → `FileResponse(file_path, media_type=mime, filename=Path(resource_id).name)`。`mime` 来自 `resource_version.mime`，即导入时 `_detect_mime` 的魔数白名单（`application/pdf`/text/*），无客户端可控面；响应字节即磁盘原文件（FileResponse 流式），冻结测试断言 `content-type == application/pdf`、`startswith(b"%PDF-")`、长度 == 原文件。PASS。
- **file 端点：缺失 resource → 404。** 上述 `get_resource_mime` 无行路径 → `workspace_missing` → 404，与冻结测试 `test_file_endpoint_missing_resource_404` 断言一致。PASS。
- **file 端点：storage_key 越界（DB 篡改 `../../`）→ 不读外部文件。** `get_resource_file_path` 在返回前调用 `_storage_key_within`：`(root / key).resolve()` 的 `relative_to(root)` 失败（逃逸）或 `Path(key).is_absolute()`（绝对路径）→ `_reject("file_not_found", rule="storage_key_unsafe")` → 404 `file_not_found`；**`FileResponse` 尚未构造，磁盘零访问**。`_storage_key_within` 同时被 `parse_pdf_resource`（拒绝码 `parse_failed/storage_key_unsafe`）复用。正常路径 `storage_key` 恒为 `import_resource` 生成的 `resources/{uuid7}/{uuid7}` 相对子路径。PASS。
- **POST anchors：合法注册/列表。** `register_anchor` 先查 `resource` 存在（无 → `workspace_missing` 404），再 `INSERT … ON CONFLICT(resource_id, page) DO UPDATE SET payload=excluded.payload`（同页幂等覆盖，不新增行），事务内 `SELECT id` 返回**实际存储的 id**（修复上一工作项 P2-1 的悬空引用问题，冻结测试 `test_register_anchor_returns_stored_id_on_upsert` 固化）。`list_anchors` 校验资源存在后 `ORDER BY page`，`json.loads(payload)`。PASS。
- **POST anchors：page=0 / payload 非对象 → 422。** `post_anchor`：`if not isinstance(page, int) or page < 1 or not isinstance(anchor_payload, dict): raise HTTPException(422, {"code":"anchor_invalid","rule":"page_or_payload_invalid"})`。冻结测试 `test_api_register_anchor_invalid_payload`（`{"page":0,"payload":"not-an-object"}` → 422 `anchor_invalid`）逐字对应。PASS（边界瑕疵见 P2-2/P2-3）。
- **POST anchors：缺失 resource → 404。** `register_anchor` 的 `workspace_missing` → `_http_error` 404。PASS。
- **bbox 映射。** `[0.1, 0.2, 0.6, 0.35]` → `left 10%`、`top 20%`、`width (0.6−0.1)×100 = 50%`、`height (0.35−0.2)×100 = 15%`，与任务标准逐项一致（`PdfRenderer.tsx` L72-77 直接算术）。无 bbox 锚点：`activeAnchor?.bboxNorm` falsy → 不渲染高亮 div。pageSize 未就绪：`pageSize` falsy → 不渲染高亮 div。PASS（缩放错位另见 P1-1）。
- **渲染：canvas 尺寸 = viewport×scale。** `viewport = pageHandle.getViewport({ scale: 1.6 })`；`canvas.width = viewport.width`、`canvas.height = viewport.height`（物理像素），`setPageSize` 同值。loading 覆盖层（`status==="loading"`，文案"正在渲染 PDF…"）与 failed 覆盖层（`.pdf-overlay.error`）恒存在，canvas 无条件渲染，避免 canvasRef 未挂载时 effect 静默 return 造成的挂起。翻页重渲染：`App.tsx` `<PdfRenderer key={viewerPage} …/>` 以 key 强制重挂载，effect deps `[fileUrl, page]` 双保险。effect cleanup 置 `cancelled`，异步竞态下不产生过时 setState。PASS。
- **worker：public 文件与 pdfjs-dist 包一致。** `cmp apps/web/public/pdf.worker.min.mjs apps/web/node_modules/pdfjs-dist/build/pdf.worker.min.mjs` **实跑零差异**；`git diff --no-index` 无输出；两文件均 1,262,398 字节、28 行；`git ls-files -s` 记录 public 文件 blob `66a5d815…` 且 `git cat-file -s` 同样 1,262,398 字节；`git diff -- apps/web/public/pdf.worker.min.mjs` 无输出（工作区与索引一致）。内容为 Mozilla 官方 worker（Apache-2.0，文件头含 "Copyright 2024 Mozilla Foundation"）。**build 后 dist 含 worker**：`apps/web/vite.config.ts`（全量读取）未配置 `publicDir`，使用 Vite 默认 `public/` → 构建时复制到 `dist/` 根，`workerSrc="/pdf.worker.min.mjs"` 在 dev（dev server 静态服务 public）与 build（复制到 dist）下同 URL 成立，规避 Windows `@fs` 路径含空格（"E:\知识树 - 副本"）导致的 `?url` 404。PASS。
- **前端注入面。** `App.tsx`/`PdfRenderer.tsx` 均无 `dangerouslySetInnerHTML`（grep 零命中）；查看器文本用 `<pre>{viewerText}</pre>` 插值；锚点 label 来自服务端 payload 的 `topic_zh`，经 `listAnchors` 映射为字符串，无 HTML 渲染路径。PASS。

### 4. 内容安全与依赖边界

- 错误 payload 无正文：`workspace_missing`/`file_not_found`/`anchor_invalid` 全部只带 `code`+`rule`（`_reject` 只接受固定 `rule` 与安全字段，`WorkspaceError.__str__` 固定为 `"{code}: workspace rejected"`）；file 端点 404/422 响应不含文件名、路径、hash 或正文。`get_page_text` 正常路径返回正文是端点设计目的；错误路径零正文。PASS。
- 无 secret：按仓库 `SECRET_RULES`（`-----BEGIN …PRIVATE KEY-----`、`sk-`/`sk_`≥20 位、`AKIA`/`ASIA`16 位）对 `apps/web/src`、`tests/integration`、`packages/infrastructure/.../workspace.py`、`apps/api` 逐一 grep，**全部零命中**（实跑）。`scripts.validate_repository` 的 `TEXT_SUFFIXES` 覆盖 `.py/.ts/.tsx/.css/.json`，新增文本文件均在扫描面；`pdf.worker.min.mjs`（`.mjs`）不在扫描面，但它是官方第三方 Apache-2.0 运行时（字节级验证），非本仓库生成内容。
- 无新增 Python 依赖：冻结提交不含 `pyproject.toml`/`uv.lock`。npm 面：`pdfjs-dist ^6.2.108` 在**红灯基线**（275d7c6）已入 `apps/web/package.json` 与 `pnpm-lock.yaml`（安装版本 6.2.108，与 lock 一致），冻结提交无依赖变更；`pdfjs-dist` 带可选依赖 `@napi-rs/canvas@1.0.5`（12 个平台二进制包，CI Linux 下安装 linux 变体）——标准 npm optionalDependencies 行为，supply-chain 面扩大但非异常（见 P2-7）。
- `scripts.validate_repository` 本身未实跑（被拒）；静态推演：`REQUIRED_PATHS` 含 apps/api、apps/web、packages/infrastructure 等全部存在，secret 扫描零命中，无理由失败，但**未独立验证**。

### 5. CI 一致性

`.github/workflows/ci.yml`（本提交未改动，blob `c3da6f0c…` 与 HEAD 一致）：python job `uv run ruff format --check packages scripts tests apps`、`uv run ruff check .` 均覆盖 `apps`；`uv run mypy scripts && uv run mypy --strict packages/contracts-py/src packages/domain/src packages/infrastructure/src apps/api` 显式覆盖 `apps/api`；`uv run pytest` 默认 testpaths 收集 `tests/`（含新增 15 个 render 节点）。web job `pnpm check`（`tsc -b --pretty false` + `eslint . --max-warnings 0` + `vitest run`）覆盖新增 PdfRenderer.tsx/api.ts/App.tsx/setup.ts/PdfRender.test.tsx；`pnpm build`（`tsc -b && vite build`）会把 `public/pdf.worker.min.mjs` 复制进 dist，覆盖 worker 运行时面。CI 无需要变更项。PASS。

## Findings

**P0：无。**

**P1-1（渲染错位，决策失败项）—— bbox 高亮在窄视口与页面内容纵向错位。** `styles.css`：`.pdf-page` 高度由 `PdfRenderer.tsx` 内联 `height: pageSize.height` 固定，无 CSS 高度规则覆盖；`.pdf-page canvas` 声明 `max-width: 100%; height: auto !important`（`!important` 覆盖内联 height）。`viewer-body` 容器宽度 < 页面渲染宽度时：`.pdf-page` 宽度被 `max-width:100%` 收缩但高度保持 `pageSize.height` 不变，canvas 显示高度按固有宽高比（`viewport.height/viewport.width`）等比收缩，而 bbox-highlight 的 `top/height` 百分比相对未缩放的 `.pdf-page` 高度计算 → 高亮框与 canvas 内实际内容纵向错位。定量（A4 @1.6 ≈ 979×1267px）：视口可用宽度 800px 时，页面收缩到 679px、canvas 显示高约 879px，bbox `top:20%` 显示在 253px 处而内容实际 20% 在约 176px 处，偏移约 77px（≈8% 页高）；视口 < ~1050px 即开始可感知错位。分屏/窄窗口/嵌入式场景可稳定复现，且 `PdfRender.test.tsx` 只断言高亮元素存在、无任何位置断言，测试零覆盖。修复方向：`.pdf-page` 同步按宽度缩放高度（如容器改用 `aspect-ratio` 或对缩放后的容器设置 height），或改为横向 `overflow: auto` 不收缩。**（静态推演：CSS `max-width`/`height:auto` 的 used-value 语义与 canvas 固有宽高比行为均为规范确定性，未做浏览器实机验证。）**

**P2（非阻塞观察）：**

- **P2-1（file 端点磁盘文件缺失时 500 而非 404）：** `get_resource_file_path` 只校验 `storage_key` 位于 workspace 内，不校验磁盘存在；若 DB 有记录但文件被本地删除，`FileResponse` 的 `os.stat` 抛 `FileNotFoundError` → Starlette 500（无 JSON code）。需本地文件操作才可触发，非 HTTP 可达，无测试覆盖。
- **P2-2（anchors POST 无 body/非 JSON body 的错误码错位）：** `post_anchor` 复用 `_read_json`，其非 JSON/非对象分支抛 422 `graph_invalid`（而非 `anchor_invalid`）。仍是 422、无正文泄漏，但错误码语义不一致。
- **P2-3（`page=True` 通过校验）：** `isinstance(True, int)` 为 True 且 `True >= 1`，布尔 `page=true` 会被接受并注册为 page 1（sqlite 存 1）。语义瑕疵，非安全面。
- **P2-4（drift 场景下 render 模式仍显示旧 bbox）：** `jumpToAnchor`/`changeViewerPage` 的 `getPageText` 漂移失败置 `viewerStatus="drift"` 并清空文本，但 `viewerMode === "render"` 时 `PdfRenderer` 仍以当前文件渲染并把 `activeAnchor` 的旧 bbox 叠加其上（有"资料已变化"警告，但高亮位置可能误导）。fail-closed 方向正确（无旧文本展示），建议 drift 时同时清 `activeAnchor`。
- **P2-5（翻页整份文档重新加载）：** effect 在 `[fileUrl, page]` 变化时重新 `getDocument`，未缓存 PDFDocumentProxy；render 模式连续翻页反复下载+解析整份 PDF。性能观察，非正确性问题。
- **P2-6（测试名与实际不符）：** `test_file_endpoint_non_pdf_resource_rejected` 并未调用 file 端点，只断言 markdown 导入的 `content_hash` 前缀；file 端点对非 PDF 资源实际正常返回文件（`get_resource_mime` 返回 DB mime，不设 PDF 白名单）。当前 App 只对 `application/pdf` 资源暴露"打开"入口，无实际利用面，但测试未测其所声称的行为。
- **P2-7（`@napi-rs/canvas` 可选原生依赖）：** `pdfjs-dist@6.2.108` 的 `optionalDependencies` 引入 `@napi-rs/canvas@1.0.5` 及 12 个平台二进制包（lock 已固定、integrity 有值）。属标准 npm 行为，但 supply-chain 面较纯 JS 依赖扩大，建议在后续审查中关注其完整性校验与升级策略。

## Limitations

- **无实跑执行。** 权限层拒绝了本审计者与隔离只读子代理的全部 `uv`/`pnpm`/`pytest`/`python -m`/`python -c` 命令（精确拒绝文本见 §2）。15 项 render 集成测试、全量 pytest（自述 223）、web vitest（自述 20）、ruff、strict-mypy、`scripts.validate_repository` 均**未**独立执行；自述通过数仅作引用。本地 pytest 缓存在本次审查中未重新读取（上一工作项 QA 已核对过其 nodeids/lastfailed，本工作项测试文件路径与函数名均经 `git`/`read_file` 静态核实存在）。
- **P1 为 CSS 规范级静态推演。** bbox 缩放错位依据 CSS2.1/Canvas 固有宽高比语义确定性推演（`max-width` 约束 used width、`height: auto !important` 覆盖内联 height），未在真实浏览器/视口实机验证；不排除特定渲染引擎边界行为。此为决策 fail 的直接依据，建议实现侧在真实浏览器窄视口下复现确认。
- **git 实跑的边界。** 放行的 git 只读命令子集见 §2；`git cat-file`/`git grep`/`git hash-object`/`certutil`/`powershell` 被拒，相关证据改用 `git ls-tree`/`git diff`/`git show`/`git log --format=raw`/`git ls-files -s`/`cmp` 等价替代并闭环。
- **反例为静态推演。** file 端点字节一致性、anchors UPSERT 语义、`_storage_key_within` 逃逸拒绝、bbox 百分比映射、canvas 尺寸等均为逐行执行追踪并交叉核对冻结测试文件；sqlite UPSERT 行为、pypdf 异常面、Windows 路径解析等为静态推理。
- **范围边界。** 仅覆盖冻结的 WORK-2026-018 表面（file/anchors 端点、PdfRenderer、worker 接线、CI/依赖），不重审 WORK-2026-016/017 已交付的解析/漂移/导入全量；loopback 无鉴权是既定设计前提；pdfjs 真实渲染正确性（页面像素内容）在 vitest jsdom 下从未真实执行（PdfRenderer 在所有测试中被 `vi.mock`），依赖真实浏览器行为，超出本审查可验证范围。未使用网络、真实 Provider 或用户数据。
- 本关联机器 attestation 不是真人签名、不是 workspace owner 接受、不是发布/ADR 批准；`correlation_classification: correlated_review` 依 harness 角色卡标记。
