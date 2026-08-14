# AI QA attempt 001 — safe file import and resource registration (WORK-2026-016)

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: graph_qa_fresh
decision: pass
reviewed_commit: 10e104f2961e93813f2ce477c52e50b29aa0081e
red_baseline_commit: 50b324528ec594876f2949b0de9d76fc7a6fce61
ready_commit: 293c0ef6eec2250ef8780f4089d2384fb9597762
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

PASS，无 P0/P1 finding。这是对冻结提交 `10e104f`（WORK-2026-016 安全文件导入）的职责隔离的只读机器审查。提交链（Ready `293c0ef` → 红灯基线 `50b3245` → 冻结 `10e104f`，HEAD == 冻结提交）、冻结 blob、红灯基线的"无实现"状态均通过只读 git 命令实跑验证；全部反例（路径逃逸、伪造扩展名、非法 UTF-8、白名单外类型、超大文件、内容幂等、v1→v2 迁移、user_version=99 冲突、元数据列表、缺失 workspace 404、类型拒绝零写入）以逐行静态执行推演独立复核，结论全部符合预期；错误 payload 无正文/无 secret；`python-multipart` 为唯一新增 Python 依赖；CI 的 ruff/mypy 均覆盖 `apps/api` 且 `uv.lock` 已包含 `python-multipart`。

必须如实披露：本 QA 环境的权限层拒绝了本审计者（以及隔离的只读执行子代理）的全部 `uv`/`pnpm`/`pytest`/`python` 执行类命令（精确拒绝文本见 §2），因此 14 项 import 集成测试、全量 pytest、web vitest、ruff、strict-mypy、`scripts.validate_repository` 均**未能实跑**，所有行为声明均为静态推演，并交叉核对冻结测试文件与本地 pytest 缓存（缓存列出全部 14 个 import 节点、无 import 相关 lastfailed）。详见 §2 与 Limitations。

## Independent checks

### 1. 提交链、冻结 blob 与红灯基线（实跑：隔离只读子代理执行 git 只读命令）

- `git rev-parse`：`HEAD = 10e104f2961e93813f2ce477c52e50b29aa0081e`（冻结提交即 HEAD）；`50b324528ec594876f2949b0de9d76fc7a6fce61`（红灯）；`293c0ef6eec2250ef8780f4089d2384fb9597762`（Ready）。
- `git log --oneline -15` 最近三条依次为 `10e104f feat(import): add safe resource import and registration` ← `50b3245 test(import): establish resource import red baseline` ← `293c0ef docs(import): ready safe file import work item`；`git log --oneline --ancestry-path 293c0ef..10e104f` 恰好两行；`git cat-file -p 10e104f` 显示 `parent 50b3245…` 与 `Refs: WORK-2026-016`。链成立。
- `git show --stat 10e104f` = `git diff 50b3245 10e104f --stat`：11 文件，+460/−21，含 `workspace.py`(+189)、`apps/api/main.py`(+59)、`apps/web/src/App.tsx`(+65/−)、`apps/web/src/api.ts`(+33)、`styles.css`(+81)、`ResourceImport.test.tsx`(+8/−)、`App.persist.test.tsx`(+9)、`__init__.py`(+6)、`pyproject.toml`(+1)、`uv.lock`(+11)、`tests/integration/test_resource_import.py`(+19/−)。
- 冻结 blob 存在性（`git ls-tree 10e104f`）：`workspace.py`=`d150199a…8d59`、`apps/api/main.py`=`6422a810…c71c6`、`api.ts`=`ea39c0f4…84a3`、`App.tsx`=`d9259e1c…95ca`、`ResourceImport.test.tsx`=`2e2b0f6a…0f1c`、`test_resource_import.py`=`d5793dab…73a`，全部命中。
- 红灯真实性（比任务说明更强，直接在直接父提交 `50b3245` 上验证）：`git grep -n import_resource 50b3245` 的 12 处匹配全部位于测试文件；`git grep -n import_resource 50b3245 -- packages apps` 零匹配（exit 1）；`git grep -n ResourceInfo 50b3245` 仅测试文件 5 处；`git show 50b3245:…/workspace.py` 中 `SUPPORTED_SCHEMA_VERSION = 1`、无 `import_resource`、无 `resource`/`resource_version` 表。红灯基线真实成立。
- 工作树：`git diff HEAD --stat` 为空（无已跟踪修改）；`git status --porcelain` 仅两个未跟踪目录 `.reasonix/`、`handoff/`。workspace_modified = false（本审计未修改任何仓库文件；唯一写入是本报告本身，为流程规定）。

### 2. 测试套件 —— 未实跑（权限层拒绝，全部如实记录）

本审计者无 shell 工具；隔离只读执行子代理尝试了以下每条命令，全部返回同一段精确拒绝：

```
blocked: read-only subagents can run only permission-classified foreground read-only commands
```

| 命令 | 结果 |
|---|---|
| `uv run python -m pytest tests/integration/test_resource_import.py -q` | 拒绝（未运行） |
| `uv run python -m pytest -q` | 拒绝（未运行） |
| `CI=true pnpm --filter @knowledge-tree/web test` | 拒绝（未运行） |
| `uv run ruff check .` | 拒绝（未运行） |
| `uv run python -m mypy --strict packages/contracts-py/src packages/domain/src packages/infrastructure/src apps/api` | 拒绝（未运行） |
| `uv run python -m scripts.validate_repository` | 拒绝（未运行） |
| 免 uv 的 `python -c`（版本探测/import/临时 sqlite 反例脚本） | 拒绝（未运行） |

以上均**不**记为通过。本地磁盘证据仅：`.pytest_cache/v/cache/nodeids` 列出 **213** 个收集节点，其中包含 **全部 14 个** `tests/integration/test_resource_import.py` 节点（`test_migrate_creates_resource_tables`、`test_migrate_rejects_unknown_version`、`test_import_markdown`、`test_import_txt`、`test_import_pdf`、`test_import_duplicate_is_idempotent`、`test_list_resources_metadata_only`、`test_import_rejects_out_of_whitelist`、`test_import_rejects_forged_extension`、`test_import_rejects_too_large`、`test_import_rejects_traversal_name`、`test_api_import_and_list`、`test_api_import_rejects_bad_type`、`test_api_resources_missing_workspace_404`）；`.pytest_cache/v/cache/lastfailed` 仅有既有的 `test_invalid_independent_review_mutations_fail[<lambda>-review coverage]` 一条（计算题包边缘用例，与 import 无关）。提交 message 声明的 `207 passed; import 14/14; web check 15 passed` 是提交自述，未被独立复现（web 15 的结构可静态核对：`App.test.tsx` 6 + `App.persist.test.tsx` 6 + `ResourceImport.test.tsx` 3 = 15，见 §3）。

### 3. 独立反例（静态逐行推演；每条未实跑）

- **路径逃逸 → 拒绝且不落盘。** `import_resource` 第一行即 `_safe_display_name`：`Path(name).name` 后，若 base 为空、为 `"."`/`".."`、或原名含 `/`、`\` → `WorkspaceError("import_type_rejected", rule="invalid_name")`。逐例推演：`"../../evil.md"`（base=`evil.md` 但含 `/`）、`"C:\\evil.md"`（Windows base=`evil.md` 但含 `\`；POSIX base=原串仍含 `\`）、`"/etc/evil.md"`（含 `/`）、`""`（base 空）、`".."`（base=`..`）全部被拒，且发生在任何 DB/磁盘写入之前。磁盘文件名完全生成：`storage_key = f"resources/{_uuid7()}/{_uuid7()}"`，客户端名仅作为 `display_name` 元数据，不存在把客户端名拼进路径的写入面。PASS。
- **UUIDv7 有效性（防格式绕过）。** `_uuid7()`：`(now<<80)|(0x70<<72)|(0x80<<64)|(uuid4().int & ((1<<64)-1))`。按位推演：48 位毫秒时间戳占 MSB 位 0–47；`0x70<<72` 的 `0111` 落在 MSB 位 48–51（版本=7）；`&` 优先级高于 `|` 故随机部分正确掩到 64 位；variant 位（MSB 位 64–65）由 uuid4 低 64 位的最高两位继承（RFC 4122 的 `10`），故 `.version==7` 且 `.variant=="specified in RFC 4122"`，能被 API 层 `_is_uuidv7` 接受。合法 v7。PASS。
- **类型伪造与白名单。** `_detect_mime`：magic `b"%PDF-"` 命中 → `application/pdf`（magic 优先，强信号）；否则后缀在 `{".md","text/markdown",".txt","text/plain"}` 且 `content.decode("utf-8")` 成功 → 文本类型；否则 `None` → `import_type_rejected/mime_not_in_whitelist`。逐例：内容非 PDF 但叫 `.pdf`（magic 不匹配、`.pdf` 不在文本表）→ 拒绝；`.md` 含非法 UTF-8（`UnicodeDecodeError` → `None`）→ 拒绝；`.exe` 内容 `MZ\x90\x00` → 拒绝。全部在 `_connect` 事务之前触发，**不产生 resource 记录、不写磁盘**。PASS。
- **大小上限。** `len(content) > 25*1024*1024` → `import_too_large/size_limit_exceeded`，位于类型检测与一切写入之前；边界 `== 25MiB` 通过、`25MiB+1` 拒绝（与测试用 `b"x"*(25*1024*1024+1)` 一致）。PASS。
- **内容幂等。** 同 content_hash 二次导入：事务内 `SELECT … FROM resource_version WHERE content_hash=?` 命中即 `_resource_info` 返回既有资源（display_name 取已存记录的，不更新）；磁盘仅第一份副本，无重复写。`test_import_duplicate_is_idempotent` 断言 `first.content_hash == second.content_hash` 且 `len(list_resources)==1`，与实现一致。PASS（并发边界见 P2-2）。
- **迁移。** `migrate`：`current > 2` → `migration_conflict/schema_newer_than_supported`（`user_version=99` 命中，与测试一致）；`current == 2` → 幂等返回；`current < 2`（含 v1 与全新 0）→ `CREATE TABLE IF NOT EXISTS` 建 `resource`/`resource_version`（既有 `meta`/`history_records` 跳过保留），`PRAGMA user_version = 2`。v1 库既有 graph/meta/history 数据不受影响；表 DDL 全部静态、无拼接注入（仅常量 2 入 PRAGMA）。PASS。
- **列表与 404。** `list_resources` JOIN `v.id = r.current_version_id`，只返回 id/display_name/mime/byte_size/content_hash/created_at——**无 content 字段**；API 返回体同样仅这 6 个键。缺失 workspace 时 GET 走 `resolve_workspace` → `workspace_missing` → 404 `{"code":"workspace_missing"}`。PASS。
- **并发/事务：类型拒绝零写入。** 名字/大小/类型三类拒绝全部发生在 `with _connect(...)` 之前，DB 无记录、磁盘无文件（任务要求的核心反例成立）。`sqlite3.DatabaseError` 事务内异常由 `_connect` rollback 并包装为 `import_failed`(422)。（DB 提交与磁盘落盘非原子，见 P2-1。）
- **API 语义。** POST multipart 缺 `file` 字段或无 `read`/`filename` 属性 → 422 `{"code":"import_type_rejected","rule":"file_missing"}`；`str(upload.filename or "upload")` 缺省文件名安全；返回体仅元数据。Web 端 `handleImport`：无文件直接返回、成功去重追加、失败置 `failed` 并提示、`finally` 清空 file input；三个 `ResourceImport.test.tsx` 用例（列表渲染、导入成功追加、失败提示）与实现逐一对应。PASS。

### 4. 内容安全与依赖边界

- 错误 details 不含文件正文：所有 `_reject` 只携带 `rule` 与固定安全字段（如 `current_version`/`supported_version`），`WorkspaceError.__str__` 为固定 `f"{code}: workspace rejected"`；HTTP detail 仅 `code`+`rule`+固定值，文件内容、display_name、content_hash 均不出现。列表/导入返回也仅元数据。PASS。
- 无 secret：按仓库 `SECRET_RULES`（private key / `sk-`/`sk_` / `AKIA`/`ASIA`）grep `apps/`、`packages/`、`tests/`、`scripts/` 全部零命中。PASS。
- 依赖边界：`pyproject.toml` 冻结提交仅 +1 行（`python-multipart>=0.0.32`），`uv.lock` +11 行且已含 `python-multipart`（包定义、specifier、依赖边均存在）；`workspace.py` 只新增 stdlib 用法（`hashlib`/`pathlib`/`time`/`uuid` 均为既有 import 风格），`apps/api/main.py` 复用既有 fastapi/starlette；Web 侧 `api.ts` 仅用 `fetch` + `FormData`，无新 npm 依赖（`apps/web/package.json` 无变化）。PASS。
- `scripts/validate_repository`：`REQUIRED_PATHS` 含 `apps/api`、`apps/web`、`packages/infrastructure/...`，全部存在（`git ls-tree` 已核）；`TEXT_SUFFIXES` 覆盖 `.py/.tsx/.ts/.md`，冻结新增文件均会被 secret 扫描覆盖。该脚本本身未实跑（§2）。

### 5. CI 一致性

`.github/workflows/ci.yml`（冻结版本）：python job 的 `uv run mypy --strict packages/contracts-py/src packages/domain/src packages/infrastructure/src apps/api` 显式覆盖 `apps/api`；`ruff format --check packages scripts tests apps` 与 `ruff check .` 覆盖 apps；`uv sync --locked` 依赖锁含 `python-multipart`（见 §4）。web job 的 `pnpm check`（`tsc -b --pretty false && eslint . --max-warnings 0 && vitest run`）覆盖新增 `App.tsx`/`api.ts`/`ResourceImport.test.tsx`；`pnpm peers check` 无新 peer。CI 无需要变更项，与提交自述的 gate 集合一致。PASS。

## Findings

无 P0/P1 finding。未发现任何可复现的语义绕过、越权、路径逃逸、数据损坏、类型绕过、正文泄漏或防篡改失败。五个非阻塞 P2 观察：

- **P2-1（DB 提交与磁盘落盘非原子）：** `import_resource` 在 `_connect` 事务提交之后才 `mkdir` + `write_bytes`，且 `except` 只捕 `sqlite3.DatabaseError`。若落盘抛 `OSError`（磁盘满/权限/IO 中断），会留下已提交的孤儿 `resource`/`resource_version` 记录（或半文件），且异常不被包装为 `WorkspaceError`，API 层 500。类型/大小/名字拒绝路径不受影响（发生在事务前）。本地单用户场景概率低，但不满足"导入失败绝不留半记录"的字面最强形式。
- **P2-2（幂等检查非并发安全）：** 幂等靠事务内 `SELECT content_hash` + `UNIQUE(resource_id, content_hash)`；该唯一约束不阻止跨 resource 的重复内容。两个并发请求对同一文件可能各自 INSERT（resource_id 不同），产生 2 条资源与 2 份磁盘副本。FastAPI 单事件循环内同步函数不会交错，实际只在多请求/多线程并发下出现，概率极低。
- **P2-3（`mime` 死参数）：** `import_resource(..., mime: str | None)` 接收但从不使用该参数（API 传 `None`，类型由 magic/后缀内部决定）。行为正确、参数有误导性，建议后续移除或改为只读校验。
- **P2-4（POST 隐式创建 workspace）：** `POST /resources` 对不存在的 workspace 会 `create_workspace`+`migrate` 静默建库（与既有 `PUT /graph` 语义一致）；`GET /resources` 则 404。若产品期望"导入必须先有工作区"，这是行为分叉，但不构成安全或数据完整性问题。
- **P2-5（前端错误映射粗糙）：** `importResource` 将一切非 OK 响应映射为"导入失败，请检查文件类型与大小"，无法区分 422（类型/大小/名字）与 500（DB/IO），与 WORK-2026-015 的搜索失败映射同类 UX 边角。

## Limitations

- **无实跑执行。** 权限层拒绝了本审计者与隔离只读子代理的全部 `uv`/`pnpm`/`pytest`/`python`/`ruff`/`mypy` 命令（精确拒绝文本见 §2）。14 项 import 集成测试、全量 pytest、web vitest、ruff、strict-mypy、`scripts.validate_repository` 均**未**独立执行；提交 message 的 `207 passed; import 14/14; web 15 passed` 仅作为自述引用，未验证。
- **收集计数差异：** 本地 `.pytest_cache/v/cache/nodeids` 有 213 个节点而提交自述为 207 passed，二者相差 6 且 `lastfailed` 仅 1 条（既有计算题边缘用例）；缓存是未跟踪的本地最后运行状态，仓库无 skip/xfail 标记，无法在无执行环境下调和精确计数。全部 14 个 import 节点均确在缓存中且无 import 相关 lastfailed。
- **git 实跑的边界：** 只读子代理成功执行的仅限单条 git 只读命令（`&&` 串联与管道被权限层拒绝）；`git show --stat`、`git cat-file`、`git ls-tree`、`git grep` 结果如上。工作树存在两个未跟踪目录 `.reasonix/`、`handoff/`（非冻结内容，不影响已跟踪文件）。
- **反例为静态推演：** 所有行为声明基于对冻结 blob 的逐行执行追踪，交叉核对冻结测试文件；`_uuid7` 的位布局、`Path.name` 的平台差异、sqlite `PRAGMA user_version` 的可回滚性、python-multipart 的 `UploadFile` 属性均为静态推理，未经实机验证。
- 本审查仅覆盖冻结的 WORK-2026-016 表面（导入/注册/列表 API、Web 控件、CI/依赖接线），不重审 contracts/domain 全量，不声称发布就绪、加密、多进程安全或云行为；loopback 无鉴权是既定设计前提。未使用网络、真实 Provider 或用户数据。
- 本关联机器 attestation 不是真人签名、不是 workspace owner 接受、不是发布/ADR 批准；`correlation_classification: correlated_review` 依 harness 角色卡标记。
