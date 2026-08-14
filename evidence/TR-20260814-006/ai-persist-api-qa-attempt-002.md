# AI QA attempt 002 — local persistence API sidecar and web auto-save (WORK-2026-014)

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: graph_qa_fresh
decision: pass
reviewed_commit: e0a4c7212aa8be2aae1b2319968b3f75159bfba1
red_baseline_commit: 6c0c33c409a3fdb400fd9a2730b42dff7024960a
ready_commit: 31ce81486a643304e2d1acd0ef3442a20d3f9440
supersedes: 6c0c33c409a3fdb400fd9a2730b42dff7024960a (attempt 001)
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

PASS with no P0, P1, or new P2 finding. This superseding QA attempt re-reviews
frozen commit `e0a4c72` (fix(persist): reject backup of missing workspace),
which closes attempt 001's P2-1. The fix is semantically effective: `POST
/api/workspaces/{id}/backup` no longer calls `create_workspace`, so a missing
workspace returns `404 {"code":"workspace_missing"}` without creating any empty
directory or SQLite database under `data_root`, and a saved workspace still
backs up to `200 {"status":"backed_up","backup_path":...}` with a `.sha256`
sidecar. The P2-2 (mount-time race) and P2-3 (600 ms debounce unload flush)
observations from attempt 001 are confirmed still present and are treated as
known prototype boundaries, not findings.

Evidence boundary, stated up front: this QA environment has **no shell
executor at all** (neither this reviewer nor a delegated read-only sub-agent
has a bash tool; every command attempt is BLOCKED at the permission layer).
Consequently `git show --stat`, `git cat-file`, `git status`, and both pytest
invocations could **not** be executed, and are reported as such — nothing was
faked. Commit-chain verification relies on the authoritative `.git/logs`
(reflog) files, which are plain-text and were read directly. Behaviour claims
are line-by-line static execution tracing of the working tree (which points at
`e0a4c72`) against each required counter-example. See Limitations.

## Independent checks

### 1. Commit chain and frozen-point lineage — 静态推演 (reflog, no git binary)

- `.git/refs/heads/feature/WORK-2026-014-local-persist-api` contains exactly
  `e0a4c7212aa8be2aae1b2319968b3f75159bfba1`, i.e. the branch and HEAD point at
  the reviewed commit.
- `.git/logs/refs/heads/feature/WORK-2026-014-local-persist-api` lists, in
  order, the commits `31ce81486a643304e2d1acd0ef3442a20d3f9440` (ready),
  `4fe918bffde539c10ea69529df45ba854bbe1bb9` (red baseline),
  `6c0c33c409a3fdb400fd9a2730b42dff7024960a` (attempt 001 freeze point), and
  `e0a4c7212aa8be2aae1b2319968b3f75159bfba1`. The final reflog entry reads:
  `6c0c33c409a3fdb400fd9a2730b42dff7024960a e0a4c7212aa8be2aae1b2319968b3f75159bfba1 ... commit: fix(persist): reject backup of missing workspace`.
  In reflog commit records the left SHA is the parent, so **`e0a4c72`'s direct
  parent is `6c0c33c`** — confirmed. Chain `e0a4c72 -> 6c0c33c -> 4fe918b ->
  31ce814` matches the task statement.
- `git show --stat e0a4c72` (claimed: 2 files, `main.py` +12/−1, test +11)
  could **not** be executed. File-scope evidence instead: (a) `apps/api/main.py`
  in the working tree contains exactly the documented fix; (b)
  `tests/integration/test_persist_api.py` contains the new
  `test_backup_missing_workspace_returns_404` (8 `test_` functions, 105 lines);
  (c) every other WORK-2026-014 file matches the attempt-001 description of the
  `6c0c33c` freeze (`api.ts` 195 lines as attested for `6c0c33c`; `ci.yml`
  python job still gates `ruff format --check packages scripts tests apps`,
  strict mypy on `apps/api`, `uv run pytest`; `App.tsx` loadGraph/scheduleAutoSave
  code identical to the attempt-001 description; `workspace.py` backup_workspace
  unchanged). No sign of any third modified file. Exact ± line counts are
  quoted from the task statement only, not independently measured.

### 2. Test suites — NOT executed (permission layer has no shell at all)

Commands required by the task could not even be attempted, let alone executed;
the read-only sub-agent reported "no shell/bash execution tools", so every
`uv ...`/`git ...` invocation is BLOCKED:

```
uv run python -m pytest tests/integration/test_persist_api.py -q   → BLOCKED (no shell)
uv run python -m pytest -q                                         → BLOCKED (no shell)
```

These are **not** reported as passing. Local disk side-evidence (not a live
run): `.pytest_cache/v/cache/nodeids` lists **188** collected nodes, including
exactly **8** `tests/integration/test_persist_api.py` nodes — the 7 attested at
`6c0c33c` plus the new `test_backup_missing_workspace_returns_404`;
`.pytest_cache/v/cache/lastfailed` holds only one pre-existing calculus edge
case (`test_invalid_independent_review_mutations_fail[<lambda>-review coverage]`),
unrelated to this work item. The task's expected `8 passed` and `183 passed`
figures are therefore **not** independently reproduced.

### 3. P2-1 fix — static execution tracing

`post_backup` in `apps/api/main.py` now reads:

```python
workspace_root = _workspace_root(root, workspace_id)
try:
    layout = resolve_workspace(workspace_root)   # was: create_workspace(workspace_root)
    load_course_graph(layout)
    backup_path = backup_workspace(layout)
    return {"status": "backed_up", "backup_path": str(backup_path)}
except WorkspaceError as error:
    raise _http_error(error) from error
```

Traced counter-examples:

- **Missing workspace (nothing saved).** `_workspace_root` first enforces
  UUIDv7 (any non-UUID or non-v7 string → `404 workspace_missing` before any
  path join). For a valid v7 id, `resolve_workspace` checks `root.is_dir()` and
  `db_path.is_file()` and rejects with `workspace_missing` /
  `root_directory_absent` or `database_file_absent` before touching the
  filesystem for writes. `create_workspace` is never called, so **no directory
  and no empty `knowledge-tree.db` are created under `data_root`** — matches
  `test_backup_missing_workspace_returns_404` (fresh `tmp_path`, POST backup
  before any PUT → `404` + `code == "workspace_missing"`). PASS.
- **Workspace directory exists but no saved graph.** `resolve_workspace`
  passes (dir + db present) but `load_course_graph` returns no row →
  `_reject("workspace_corrupt", rule="course_graph_absent")`; `_http_error`
  maps `workspace_corrupt` + `course_graph_absent` to `404
  {"code":"workspace_missing"}` — the same "no saved graph == not found"
  semantics as GET. PASS.
- **Saved workspace.** PUT path (`create_workspace → migrate →
  save_course_graph`) is unchanged, so after a successful PUT,
  `resolve_workspace` and `load_course_graph` both pass and `backup_workspace`
  writes `<backup>.sqlite3` plus a `.sha256` sidecar (SHA-256 hex + newline),
  returning `200 {"status":"backed_up","backup_path":...}` — matches
  `test_backup_creates_checksummed_backup` (backup file and sidecar exist).
  No regression. PASS.
- **Error-path safety.** `backup_workspace` failures (e.g. source unreadable)
  still surface as `500 backup_failed`, not as a 200; `_http_error` is
  unchanged. No tamper-evasion vector is introduced: backup file + checksum
  sidecar are written together exactly as before.

### 4. No regression of attempt-001 PASS items — static tracing

- **CORS exact whitelist.** Middleware config in the working tree is byte-for-
  byte as attested: `CORSMiddleware(allow_origins=allowed_origins,
  allow_methods=["GET","PUT","POST","OPTIONS"], allow_headers=["*"],
  allow_credentials=False)`. Allowed origin echoed exactly; forbidden origin
  gets no `access-control-allow-origin` header. PASS.
- **Path traversal.** `_workspace_root` still gates on `_is_uuidv7` before any
  join; only strict `8-4-4-4-12` hex v7 ids can reach `data_root / id`. No read
  or write outside `data_root` reachable. PASS.
- **PUT invalid → 422, no overwrite.** `put_graph` order unchanged: `_read_json`
  (422 `graph_invalid` on non-JSON/non-object) → `validate_course_graph`
  (422 `graph_invalid` + rule) **before** `create_workspace`/`save_course_graph`,
  so invalid PUTs never touch the store; prior revision preserved. PASS.
- **PUT→GET round-trip & health.** Unchanged handlers; no semantic drift. PASS.

### 5. P2-2 / P2-3 status — confirmed unfixed, accepted prototype boundaries

- **P2-2 (mount-time race):** `App.tsx` `loadGraph()` effect (lines 202–232)
  still unconditionally calls `setPresent(saved)` when a saved graph resolves,
  with only a `cancelled` unmount flag — no "user already committed" guard.
  **Not fixed** in `e0a4c72`, and not in its 2-file scope (API side + test
  only). Not treated as a finding: loopback sidecar, small window, documented
  prototype boundary.
- **P2-3 (unload flush):** `scheduleAutoSave` (lines 240–250) still debounces
  600 ms and there is no `beforeunload`/`pagehide`/`visibilitychange` flush
  handler anywhere in `App.tsx` (grep confirms zero matches). **Not fixed.**
  Acceptable for demo scope; noted as a data-loss edge for future product work.

## Findings

No P0 or P1 finding. No reproducible semantic bypass, authorization escalation,
data corruption, CORS/path-traversal vulnerability, or tamper-evasion failure
was found in the reviewed fix. P2-1 is closed. P2-2 and P2-3 from attempt 001
remain intentionally unaddressed (out of scope of `e0a4c72`'s 2-file change)
and remain acceptable for the prototype. No new P2 is introduced.

## Limitations

- **No execution was possible.** This QA environment exposes no shell tool to
  this reviewer or to a delegated read-only sub-agent, so `git show --stat
  e0a4c72`, `git cat-file -p e0a4c72`, `git status`, `uv run python -m pytest
  tests/integration/test_persist_api.py -q` (expected 8 passed) and `uv run
  python -m pytest -q` (expected 183 passed) were **not** run. All commit-chain
  facts come from the plain-text `.git/logs/*` reflog files (authoritative git
  records), and all behaviour claims are static execution tracing of the
  working tree, which points at `e0a4c72`. The exact `--stat` +/− line counts
  and the `8 passed` / `183 passed` totals are quoted as task/commit
  declarations only; the pytest-cache node count (188 total, 8 persist nodes)
  and the single unrelated `lastfailed` entry are local, untracked side-evidence.
- Working-tree cleanliness was not verifiable without `git status`; the
  assumption that the working tree equals `e0a4c72` is supported by the branch
  ref, the reflog, and the file contents (fix present, new test present), but
  not by a live `git` check.
- This review covers only the `e0a4c72` delta over the `6c0c33c` freeze and
  the re-confirmed attempt-001 PASS items; it does not re-audit the
  domain/contracts layers wholesale, nor release readiness, encryption,
  multi-process safety, or cloud behaviour. The loopback API remains
  unauthenticated by design (accepted prototype premise).
- This correlated machine attestation is not a human signature, workspace-owner
  acceptance, release approval, or ADR acceptance. No network, real provider,
  or user data was used; no repository file was modified (the only write is
  this report under `evidence/`, as the workflow prescribes).
