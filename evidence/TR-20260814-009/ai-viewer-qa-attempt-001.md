# AI QA attempt 001 — PDF parsing, page text and anchor endpoints (WORK-2026-017)

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: graph_qa_fresh
decision: pass
reviewed_commit: 8c3c62071df1a297cbfb6ae8bd9ec2abef2925dc
red_baseline_commit: 53eb2cd0effde49bf00b5347e03cf287131ceffa
ready_commit: 2829ff22dc5d312df7bb6aeac4c74db53cb9e7f8
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

PASS，无 P0/P1 finding。这是对冻结提交 `8c3c620`（WORK-2026-017 PDF 页文本解析、页文本/锚点端点与 Web 查看器）的职责隔离的只读机器审查。

提交链（Ready `2829ff2` → 红灯基线 `53eb2cd` → 冻结 `8c3c620`，HEAD == 冻结提交）、冻结 blob、红灯基线的"实现不存在"状态均通过只读 git 命令**实跑**验证；冻结实现（`parse_pdf_resource`/`get_page_text`/`_check_drift`/`register_anchor`/`list_anchors`/schema v3 迁移/API 三端点/Web 查看器）全部逐行静态推演，与冻结测试文件交叉核对。

核心安全与语义声明逐条成立：重复 parse 幂等（同事务 DELETE+INSERT + `UNIQUE(resource_version_id, page)`）；越界页/未解析/缺失资源分别 fail-closed（`page_out_of_range`/`parse_pending`/404 `workspace_missing`）；**漂移检测在返回任何文本之前执行，篡改 `resource_version.content_hash` 后 `get_page_text` 只抛 `source_changed`，不存在返回旧定位文本的路径**；锚点同页 UPSERT 覆盖、列表按页排序、payload 无正文；schema v3 迁移以 `CREATE TABLE IF NOT EXISTS` 保留 v2 既有表与数据，`user_version=99` 拒绝；错误 payload 无正文、无 secret、无 `dangerouslySetInnerHTML`；无新增依赖（pypdf 在 WORK-2026-016 已引入且带 PEP 561 类型标注）；CI 的 ruff/mypy 均覆盖 `apps` 且 ci.yml 无需变更。

必须如实披露：本 QA 环境的权限层拒绝了本审计者（以及隔离的只读执行子代理）的全部 `uv`/`pnpm`/`pytest`/`python -m`/`python -c` 执行类命令（精确拒绝文本见 §2），因此 pdf-viewer 集成测试 8 项、全量 pytest、web vitest、ruff、strict-mypy、`scripts.validate_repository` 均**未能实跑**；所有行为声明以逐行静态执行推演为主，并交叉核对冻结测试文件与本地 pytest 缓存（缓存列出全部 8 个 pdf_viewer 节点、无 pdf_viewer 相关 lastfailed）。提交 message 中的 `216 passed; pdf viewer 8/8; web 18 passed` 仅作为自述引用，未被独立复现。详见 §2 与 Limitations。

## Independent checks

### 1. 提交链、冻结 blob 与红灯基线（实跑：隔离只读子代理执行 git 只读命令）

- `git rev-parse`：`HEAD = 8c3c62071df1a297cbfb6ae8bd9ec2abef2925dc`（冻结提交即 HEAD）；`53eb2cd0effde49bf00b5347e03cf287131ceffa`（红灯）；`2829ff22dc5d312df7bb6aeac4c74db53cb9e7f8`（Ready）。
- `git log --oneline -6` 最近三条为 `8c3c620 feat(viewer)…` ← `53eb2cd test(viewer): establish pdf viewer red baseline` ← `2829ff2 docs(viewer): ready pdf viewer and anchor jump work item`；`git log --oneline --ancestry-path 2829ff2..8c3c620` 恰好两行；`git cat-file -p 8c3c620` 显示 `parent 53eb2cd…` 与 `Refs: WORK-2026-017, NFR-2026-002, ADR-0001`；`git log --all 2829ff2..8c3c620` 只有这两个提交，**范围内无分支外游离提交**。链成立。
- `git show --stat 8c3c620` = `git diff 53eb2cd 8c3c620 --stat`：11 文件 +601/−17，含 `workspace.py`(+206)、`apps/api/main.py`(+50)、`apps/web/src/App.tsx`(+105/−)、`apps/web/src/api.ts`(+51)、`styles.css`(+121)、`PdfViewer.test.tsx`(+47/−)、`App.persist.test.tsx`(+8)、`ResourceImport.test.tsx`(+8)、`__init__.py`(+12)、`test_pdf_viewer.py`(±清理)、`test_resource_import.py`(+1/−1)。
- 冻结 blob 存在性（`git ls-tree 8c3c620`）：`workspace.py`=`5b7701da…86e`、`apps/api/main.py`=`a310bbc4…b9`、`api.ts`=`55ba7173…49`、`App.tsx`=`b641e09e…a8`、`PdfViewer.test.tsx`=`bd37e44a…76`、`test_pdf_viewer.py`=`fa1efe1a…ae`、`ci.yml`=`c3da6f0c…b7`，全部命中。
- 红灯真实性（直接在父提交 `53eb2cd` 上验证）：`git grep -n parse_pdf_resource 53eb2cd` 的 5 处命中全部在 `tests/integration/test_pdf_viewer.py`；`git grep -n get_page_text 53eb2cd -- packages apps tests` 的 5 处同样全部在测试文件；`git show 53eb2cd:…/workspace.py` 无 `parse_pdf_resource`/`get_page_text` 定义、无 `resource_segment`/`anchor` 表。`git grep -n parsePdf|getPageText|listAnchors|PageText|AnchorRef 53eb2cd -- apps/web/src` 的 9 处命中全部在 `PdfViewer.test.tsx`，`api.ts` 中 `PersistApi` 仅 5 个方法、无这些类型/方法。红灯基线真实成立（Python 侧 collection 时 `from knowledge_tree_infrastructure.workspace import (…PageSegment, get_page_text…)` 必然 ImportError；Web 侧 TS 编译必然失败）。
- 红→绿测试变更核查：`test_pdf_viewer.py` 绿灯仅做清理（删 `import hashlib`、调整 import 顺序、压缩 GOLD_JSON），断言逻辑与红灯基线一致；`PdfViewer.test.tsx` 绿灯把打开方式改为点击"打开"按钮、`getPageText` mock 补 `resource_version_id`、漂移用例改为 `page === 3` 抛错——与 `App.tsx` 实现的 `openViewer`/`jumpToAnchor` 行为一一对应。`test_resource_import.py` 绿灯仅把 `assert version == 2` 改为 `assert version == 3`（与 `SUPPORTED_SCHEMA_VERSION = 3` 一致）。
- 工作树：`git diff HEAD --stat` 为空；`git status --porcelain` 仅两个未跟踪目录 `.reasonix/`、`handoff/`。workspace_modified = false（本审计未修改任何仓库文件；唯一写入是本报告本身，为流程规定）。

### 2. 测试套件 —— 未实跑（权限层拒绝，全部如实记录）

隔离只读执行子代理逐条尝试以下命令，每条返回同一段精确拒绝：

```
blocked: read-only subagents can run only permission-classified foreground read-only commands
```

| 命令 | 结果 |
|---|---|
| `uv run python -m pytest tests/integration/test_pdf_viewer.py -q` | 拒绝（未运行） |
| `uv run python -m pytest -q` | 拒绝（未运行） |
| `CI=true pnpm --filter @knowledge-tree/web test` | 拒绝（未运行） |
| `uv run ruff check .` | 拒绝（未运行） |
| `uv run python -m mypy --strict packages/contracts-py/src packages/domain/src packages/infrastructure/src apps/api` | 拒绝（未运行） |
| `uv run python -m scripts.validate_repository` | 拒绝（未运行） |
| `uv run python -c "import pypdf; print(pypdf.__version__)"` 及 `python -m pytest …`/`python -m ruff check .`/`uv --version`/`git status` 等 | 拒绝（未运行） |

对照探测：`python --version` 放行（Python 3.12.6）；`uv`/`pnpm`/`python -m`/`python -c`/`git` 均在白名单之外被硬拦截。以上均**不**记为通过。

本地磁盘旁证（非执行结果）：`.pytest_cache/v/cache/nodeids`（222 行）包含**全部 8 个** `tests/integration/test_pdf_viewer.py` 节点（`test_parse_pdf_creates_segments`、`test_parse_pdf_is_idempotent`、`test_page_text_out_of_range`、`test_page_text_unparsed_resource`、`test_register_and_list_anchors`、`test_page_text_drift_detected`、`test_api_page_text`、`test_api_page_text_missing_resource_404`）；`.pytest_cache/v/cache/lastfailed` 仅含既有计算题边缘用例 `test_invalid_independent_review_mutations_fail[<lambda>-review coverage]`（与 WORK-2026-016 QA 时观察一致，与本工作项无关），**无 pdf_viewer 相关 lastfailed**。pypdf 实际安装版本为 6.15.0（`pypdf-6.15.0.dist-info/METADATA`，含 `Typing :: Typed` classifier 与 `py.typed`），满足 `pypdf>=6.10,<7`。

### 3. 独立反例（静态逐行推演；每条未实跑）

- **解析幂等（UNIQUE 生效）。** `parse_pdf_resource` 第 2 个事务内先 `DELETE FROM resource_segment WHERE resource_version_id=?` 再 `executemany INSERT`，同 `with _connect` 上下文（正常退出 commit、异常 rollback）。重复解析：页数 = `len(reader.pages)` 恒为 52，`UNIQUE(resource_version_id, page)` 结构性保证同页不重复；写入失败时整个事务 rollback，旧 segment 原样保留（不产生半删/半写）。PASS。
- **页文本端点。** `get_page_text`：(a) 页 1 命中解析时写入的真实金标文本（`extract_text() or ""`），`PageSegment.text` 即该页文本；(b) 越界页 99：`SELECT MAX(page)` 非 NULL（已解析）→ 查 `page=99` 无行 → `_reject("page_out_of_range", rule="page_not_in_range")` → API 422；(c) 未解析资源（仅 `%PDF-1.7` 头、无 segment）：`MAX(page)` 为 NULL → `_reject("parse_pending", rule="resource_not_parsed")` → 422；(d) 缺失资源：JOIN `resource` 的 `current_version_id` 子查询无行 → `_reject("workspace_missing", rule="resource_missing")` → API 404 `{"code":"workspace_missing"}`（冻结测试 `test_api_page_text_missing_resource_404` 断言 status 404 + code，与 `_http_error` 的 `workspace_missing→404` 分支一致）。PASS。
- **漂移（绝不返回旧定位）。** 解析时 segment 记录当时的 `content_hash`；`get_page_text` 在组装完 `PageSegment` 后、`return` **之前**调用 `_check_drift(version_id, parsed_hash)`：单独查询当前 `resource_version.content_hash`，不等（含行缺失）→ `_reject("source_changed", rule="content_hash_mismatch")`。篡改 `content_hash` 为 `sha256:000…0` 后调用页 1 → 抛 `source_changed`；调用链中不存在任何绕过 `_check_drift` 的返回路径。与冻结测试 `test_page_text_drift_detected`（UPDATE 后再 get）逐字对应。PASS（并发边界见 P2-2）。
- **锚点注册/覆盖与排序。** `register_anchor`：`INSERT … ON CONFLICT(resource_id, page) DO UPDATE SET payload=excluded.payload`；同页二次注册不新增行、payload 被覆盖，`UNIQUE(resource_id, page)` 兜底。`list_anchors`：`WHERE resource_id=? ORDER BY page` 返回 `json.loads(payload)`。金标 50 锚点注册后列表长度 50、pages == `range(1,51)`（冻结测试断言一致）。payload 仅 `topic_zh`/`concept_ids`，无正文。PASS（两处 P2 观察见 P2-1/P2-3）。
- **schema v3 迁移。** `migrate`：`current > 3` → `migration_conflict/schema_newer_than_supported`（`user_version=99` 命中）；`current == 3` → 幂等返回；`current < 3`（含 v2 与全新 0）→ 全部 `CREATE TABLE IF NOT EXISTS`（`meta`/`history_records`/`resource`/`resource_version` 已存在则跳过保留，新加 `resource_segment`/`anchor`），`PRAGMA user_version = 3`。v2 库（WORK-2026-016 建成）升 v3：既有 resource/resource_version/meta 数据零改动（DDL 全静态、IF NOT EXISTS 不触碰已有表），新增两张表。与冻结测试 `test_migrate_creates_resource_tables`（`version == 3`）一致。PASS。
- **安全边界。** 页文本端点只读 `resource_segment` 表，全程不触碰磁盘文件，无"读取 workspace 外文件"面；`parse_pdf_resource` 读 `layout.root / storage_key`，而 `storage_key` 恒为 `resources/{uuid7}/{uuid7}`（`import_resource` 内部生成、无客户端输入面），正常路径不可逃逸（DB 篡改前提见 P2-4）。所有错误 `_reject` 只带 `rule` 与固定安全字段，`WorkspaceError.__str__` 固定为 `f"{code}: workspace rejected"`，HTTP detail 为 `code`+`rule`，无正文、无 `text_hash`/`content_hash`/`display_name`。`get_page_text` 正常返回含正文是端点设计目的；错误路径无正文。PASS。

### 4. 内容安全与依赖边界

- 错误 payload 无正文：`parse_failed`/`parse_pending`/`page_out_of_range`/`source_changed` 全部只带 `rule`；无正文、无 hash、无文件名。PASS。
- 无 secret：按仓库 `SECRET_RULES`（`-----BEGIN …PRIVATE KEY-----`、`sk-`/`sk_`、`AKIA`/`ASIA`）对 6 个被审文件（workspace.py、apps/api/main.py、api.ts、App.tsx、test_pdf_viewer.py、PdfViewer.test.tsx）逐一 grep，全部零命中。PASS。
- 无新增依赖：`git show --stat 8c3c620` 不含 `pyproject.toml`/`uv.lock`/`apps/web/package.json`/`pnpm-lock.yaml`；pypdf 在 WORK-2026-016 已声明（`pypdf>=6.10,<7`）且本机安装 6.15.0 带 PEP 561 类型标注（`py.typed` + `Typing :: Typed`），mypy strict 下第三方 typed 包可正常类型化。Web 侧仅用 `fetch`，无新 npm 依赖。PASS。
- Web 注入面：`App.tsx` 无 `dangerouslySetInnerHTML`；查看器用 `<pre>{viewerText}</pre>` 文本插值渲染，锚点标签来自 `payload.topic_zh`（服务端 JSON 反序列化后字符串化），无 HTML 注入。`api.ts` `listAnchors` 把 `payload.topic_zh` 映射为 `label`、缺省 `第 N 页`，类型断言 `{ topic_zh?: string }`，异常 payload 结构不会抛错。PASS。
- `scripts.validate_repository` 的 `TEXT_SUFFIXES` 覆盖 `.py/.ts/.tsx/.md/.json` 等，冻结新增文件（`__init__.py`、api.ts、App.tsx、两个测试文件、styles.css）均在 secret 扫描范围；`REQUIRED_PATHS` 含 apps/api、apps/web、packages/infrastructure。该脚本本身未实跑（§2）。

### 5. CI 一致性

`.github/workflows/ci.yml` 冻结版（本提交未改动，blob 与 HEAD 一致）：python job 的 `uv run ruff format --check packages scripts tests apps`、`uv run ruff check .` 覆盖 apps；`uv run mypy scripts && uv run mypy --strict packages/contracts-py/src packages/domain/src packages/infrastructure/src apps/api` 显式覆盖 `apps/api`；`uv run pytest` 默认 testpaths 收集 `tests/`（含新增 8 个 pdf_viewer 节点）。web job 的 `pnpm check`（`tsc -b` + `eslint . --max-warnings 0` + `vitest run`）覆盖新增 `api.ts`/`App.tsx`/`PdfViewer.test.tsx`。CI 无需要变更项。PASS。

## Findings

无 P0/P1 finding。未发现任何可复现的语义绕过、越权、正文泄漏、数据损坏或防篡改失败。漂移检测在返回文本前执行、错误细节无正文、解析幂等、迁移保留数据等核心声明全部静态成立。六个非阻塞 P2 观察：

- **P2-1（`register_anchor` UPSERT 覆盖时返回的 id 与库中实际 id 不一致）：** `ON CONFLICT(resource_id, page) DO UPDATE SET payload=excluded.payload` 不更新 `id` 列，库中保留旧锚点 id；但函数返回值使用新生成的 `anchor_id`（`AnchorRef(id=anchor_id, …)`）。即覆盖注册后，`register_anchor` 返回的 id 与 `list_anchors` 返回的实际 id 不同。当前 Web 端只用 `list_anchors` 的 id 作 key，未受影响；但任何"保存注册返回值 id"的调用方会拿到不存在的行引用。
- **P2-2（漂移检测为读时检查，非并发原子）：** `get_page_text` 与 `_check_drift` 分属两个独立连接/事务，二者之间若 `resource_version.content_hash` 被并发更新，`_check_drift` 读到的仍是新值——fail-closed 方向正确（只会多抛 `source_changed`，不会漏报已提交的篡改）。反之若篡改发生在 `_check_drift` 之后，下次读取必然命中。单用户本地场景无实际并发，但"读文本与读 hash 非同一快照"不是最强原子形式。
- **P2-3（锚点端点对缺失资源不报 404）：** `list_anchors` 按 `resource_id` 过滤返回，对不存在的资源返回 `[]`（200），与页文本端点（404 `workspace_missing`）语义不一致；`register_anchor` 也不校验资源存在（可对幽灵资源注册锚点，无外键约束）。不构成安全或数据完整性问题，但 API 语义不对称。
- **P2-4（`parse_pdf_resource` 未显式校验 `storage_key` 位于 workspace 内）：** `pdf_path = layout.root / storage_key`，`storage_key` 来自 DB。正常路径恒为代码生成的相对子路径；但若 DB 被本地篡改写入 `../../…` 形式的 `storage_key`，`Path` 拼接可越过 workspace 根目录指向任意文件，pypdf 会尝试解析并提取文本入库。威胁前提是攻击者已能写本地 DB（本地单用户模型下等同已有文件写权限），故为纵深防御观察而非可利用越权。
- **P2-5（`changeViewerPage`/`jumpToAnchor` 把一切 `getPageText` 失败映射为 drift）：** 前端 catch 不区分 `page_out_of_range`（用户翻页越界）与 `source_changed`（内容漂移），越界翻页也显示"资料已变化，无法定位：请重新导入或查看最新版本"并清空文本。fail-closed 方向正确（不会展示错误文本），但诊断信息误导，且 `viewerPage` 已推进到越界页、文本被清空，用户需点"上一页"恢复。`openViewer` 失败则一律显示"无法读取该资料，请确认文件已解析"，同样无法区分未解析与漂移。
- **P2-6（`migrate` docstring 过时）：** `migrate` 的 docstring 仍写 "Migrate a database to schema v2"，而 `SUPPORTED_SCHEMA_VERSION = 3`；行为正确，注释需同步。

## Limitations

- **无实跑执行。** 权限层拒绝了本审计者与隔离只读子代理的全部 `uv`/`pnpm`/`pytest`/`python -m`/`python -c` 命令（精确拒绝文本见 §2）。8 项 pdf-viewer 集成测试、全量 pytest、web vitest、ruff、strict-mypy、`scripts.validate_repository` 均**未**独立执行；提交 message 的 `216 passed; pdf viewer 8/8; web 18 passed` 仅作为自述引用，未验证。
- **收集计数差异：** `.pytest_cache/v/cache/nodeids` 有 222 行（含参数化用例变体），与自述 216 passed 及 `lastfailed` 仅 1 条（既有计算题边缘用例）无法在无执行环境下精确调和；全部 8 个 pdf_viewer 节点确在缓存中且无 pdf_viewer 相关 lastfailed。pypdf 实际从 PDF 提取"Derivative"文本、52 页逐页提取的准确性依赖 pypdf 6.15 的渲染行为，未经实机验证（冻结测试自身断言该行为）。
- **git 实跑的边界：** 只读子代理成功执行的仅限单条 git 只读命令与目录/文件读取；`git show --stat`、`git cat-file`、`git ls-tree`、`git grep` 结果如上。工作树存在两个未跟踪目录 `.reasonix/`、`handoff/`（非冻结内容，不影响已跟踪文件）。
- **反例为静态推演：** 所有行为声明基于对冻结 blob 的逐行执行追踪并交叉核对冻结测试文件；sqlite UPSERT 的 id 保留语义、pypdf `strict=True` 的异常面、`Path /` 拼接对绝对路径的行为、Windows 下 sqlite 连接锁等均为静态推理，未经实机验证。
- **范围边界：** 本审查仅覆盖冻结的 WORK-2026-017 表面（PDF 解析、页文本/锚点端点、Web 查看器、CI/依赖接线），不重审 contracts/domain/import 全量（后者已在 WORK-2026-016 QA 覆盖），不声称发布就绪、加密、多进程安全或云行为；loopback 无鉴权是既定设计前提，锚点 payload 的内容安全依赖调用方（当前仅 topic_zh/concept_ids）。未使用网络、真实 Provider 或用户数据。
- 本关联机器 attestation 不是真人签名、不是 workspace owner 接受、不是发布/ADR 批准；`correlation_classification: correlated_review` 依 harness 角色卡标记。
