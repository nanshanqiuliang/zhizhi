# AI QA attempt 001 — local persistence API sidecar and web auto-save (WORK-2026-014)

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: graph_qa_fresh
decision: pass
reviewed_commit: 6c0c33c409a3fdb400fd9a2730b42dff7024960a
red_baseline_commit: 4fe918bffde539c10ea69529df45ba854bbe1bb9
ready_commit: 31ce81486a643304e2d1acd0ef3442a20d3f9440
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

PASS with no P0 or P1 finding. This is a read-only, role-separated machine
review of frozen commit `6c0c33c`; the Git lineage, the red-light baseline, the
working-tree state, and the frozen blobs were verified against committed
objects (via a read-only git subagent), and the QA report itself is the only
new file written (under `evidence/`, as required by the workflow).

Note upfront: this QA environment has no shell executor for mutating commands.
The permission layer rejected every `uv run ...`, `pnpm ...`, `ruff`, `mypy`,
and `scripts.validate_repository` invocation (exact rejection reason recorded
below), so the test suites were NOT independently re-executed by this reviewer.
All behaviour claims below are therefore either (a) live read-only git/grep
verification, or (b) line-by-line static execution tracing of the frozen
implementation against each required counter-example. Every traced scenario
fails closed exactly as specified; the three P2 observations listed in Findings
are non-blocking semantic/UX edges, not security, data-integrity, or
tamper-evasion defects. See Limitations for the full evidence boundary.

## Independent checks

### 1. Commit chain and red baseline (live git, read-only subagent)

- `git rev-parse HEAD` → `6c0c33c409a3fdb400fd9a2730b42dff7024960a`; the branch
  `feature/WORK-2026-014-local-persist-api` points at the same SHA and is the
  only branch head (`git log --oneline --all` is a single linear chain).
- `git cat-file -p 6c0c33c` → `parent 4fe918bffde539c10ea69529df45ba854bbe1bb9`;
  `git cat-file -p 4fe918b` → `parent 31ce81486a643304e2d1acd0ef3442a20d3f9440`.
  Direct parent chain `6c0c33c -> 4fe918b -> 31ce814` confirmed.
- `git diff --stat 6c0c33c HEAD` is empty (HEAD == frozen commit); `git status
  --porcelain` shows no tracked modifications (only untracked `.reasonix/` and
  `handoff/`).
- Red baseline is real: `git ls-tree -r 4fe918b -- apps/api` lists only
  `apps/api/README.md` — `apps/api/main.py` did **not** exist at `4fe918b`, so
  `tests/integration/test_persist_api.py` (added at `4fe918b`, 105 lines) could
  not collect (`from apps.api.main import create_app` → ImportError), exactly
  the documented red-light failure. `git show --stat 4fe918b` adds only
  `apps/web/src/App.persist.test.tsx` (88 lines) and
  `tests/integration/test_persist_api.py` (105 lines).
- Frozen blob matches the tree: `git show --stat 6c0c33c` is 8 files,
  +457/−33 (`apps/api/main.py` +143, `apps/web/src/api.ts` +195,
  `apps/web/src/App.tsx` +96/−x, `apps/web/src/main.tsx` 5±, `__init__.py` +37,
  `.github/workflows/ci.yml` 4±, `App.persist.test.tsx` 2±, `test_persist_api.py`
  −8); the file contents read from the working tree match the frozen diff
  (e.g. the −8 lines are the unused `knowledge_tree_infrastructure.workspace`
  import block removed from the test).

### 2. Test suites — NOT live-run (permission layer rejected execution)

Commands attempted (each returned the same permission-layer error, so no
result can be reported for any of them):

```
uv run python -m pytest tests/integration/test_persist_api.py -q        → blocked
uv run python -m pytest -q                                              → blocked
pnpm --filter @knowledge-tree/web test                                   → blocked
CI=true pnpm --filter @knowledge-tree/web test                           → blocked
uv run ruff check .                                                      → blocked
uv run ruff format --check packages scripts tests apps                   → blocked
uv run python -m mypy --strict packages/contracts-py/src packages/domain/src packages/infrastructure/src apps/api → blocked
uv run python -m scripts.validate_repository                             → blocked
```

Exact rejection: `blocked: read-only subagents can run only
permission-classified foreground read-only commands` (pytest/pnpm write
`.pytest_cache`/`.ruff_cache`/`.mypy_cache`/test temp files, so they are
classified as non-read-only). These are **not** reported as passing. Local
disk evidence only: `.pytest_cache/v/cache/nodeids` lists **187** collected
nodes, including all **7** `test_persist_api.py` nodes and all 17
`test_workspace_persistence.py` + 4 `test_workspace_records.py` nodes;
`.pytest_cache/v/cache/lastfailed` holds exactly one pre-existing calculus
edge case (`test_invalid_independent_review_mutations_fail[<lambda>-review
coverage]`), unrelated to this work item. The `6c0c33c` commit message
declares `pytest -q (182 passed)` and `pnpm ... check (10 passed)`, which is
**not** independently reproduced here (see Limitations for the 187-vs-182
count discrepancy).

### 3. Independent counter-examples (static execution tracing)

- **CORS (whitelist exactness).** `create_app(allowed_origins=[...])` feeds the
  list verbatim to `CORSMiddleware(allow_origins=allowed_origins,
  allow_methods=["GET","PUT","POST","OPTIONS"], allow_headers=["*"],
  allow_credentials=False)`. Starlette only emits `access-control-allow-origin`
  when the request `Origin` exactly matches an allowlist entry. Traced:
  `Origin: http://evil.example` on `GET /api/health` → no
  `access-control-allow-origin` header (plain 200), matching
  `test_cors_rejects_forbidden_origin`; `Origin: http://localhost:5173` →
  exact echo, matching `test_cors_allows_configured_origin`. `allow_credentials
  =False` (no cookies) plus `allow_headers=["*"]` reflects preflight headers
  without credentials — standard, no credential exposure. PASS.
- **Path traversal.** `_workspace_root` calls `_is_uuidv7` first: only strings
  that parse as a UUID with `version == 7` and RFC-4122 variant pass; `..`,
  `/`, `\`, `%2e`, or any non-UUID string → `HTTPException(404,
  {"code":"workspace_missing"})` before any path join. `data_root / workspace_id`
  therefore only ever joins a strict `8-4-4-4-12` hex string. Traced
  `/api/workspaces/../../etc/passwd/graph` and `/api/workspaces/not-a-uuid/graph`
  → 404 `workspace_missing`; no read or write outside `data_root` is reachable.
  PASS.
- **PUT invalid payloads (no overwrite).** `_read_json` rejects non-JSON bodies
  and non-object JSON with `422 graph_invalid`; `validate_course_graph` then
  rejects missing required fields / bad `concepts` items via `GraphPatchError`
  → `422 {"code":"graph_invalid","rule":<rule>,...}`. Crucially, validation
  runs **before** `create_workspace`/`migrate`/`save_course_graph`, so an
  invalid PUT never touches the store; the previously saved graph (revision_no)
  is preserved — matches `test_put_invalid_graph_rejected`. PASS.
- **PUT valid → GET semantics.** `save_course_graph` stores the validated graph
  (canonical JSON, sorted keys); `load_course_graph` revalidates and returns
  it. workspace_id/course_id/revision_no/concepts round-trip exactly — matches
  `test_put_then_get_round_trip`. PASS.
- **Backup + checksum.** `backup_workspace` writes `<backup>.sqlite3` and a
  `.sha256` sidecar (SHA-256 hex + newline) — matches
  `test_backup_creates_checksummed_backup`. Restore is **not exposed by the
  API** (`main.py` routes are only `GET/PUT /api/workspaces/{id}/graph`,
  `POST /api/workspaces/{id}/backup`, `GET /api/health`); the tampered-restore
  counter-example therefore does not apply at the API surface. At the
  workspace layer (`restore_backup`), the checksum sidecar is compared before
  any copy and a mismatch raises `backup_checksum_mismatch`/`restore_rejected`
  — this was already attested in TR-20260814-005 for the same frozen blob.
  PASS.
- **Web `graphToSnapshot(snapshotToGraph(s))`.** Node ids map to canonical
  UUIDv7 (stable per-session via `canonicalIds`; pre-existing UUIDv7 ids pass
  through unchanged, so reload→re-save keeps ids stable). title→`label`,
  note→`annotations[{kind:"note"}]`, edges→`source_concept_id`/`target_concept_id`
  all round-trip; `positionLocked`→layout `pinned`, x/y→layout; `tone` is
  re-derived from in/out degree as allowed. PASS.
- **uuidv7 format.** `uuidv7()` sets byte 6 = `0x70 | r&0x0f` (version nibble
  7) and byte 8 = `0x80 | r&0x3f` (RFC-4122 variant 10), 48-bit millisecond
  timestamp, and joins as 8-4-4-4-12 lowercase hex →
  `xxxxxxxx-xxxx-7xxx-[89ab]xxx-xxxxxxxxxxxx`, matching `isUuidV7`'s regex.
  PASS.

### 4. Content safety and dependency boundary

- `WorkspaceError` message is the fixed `f"{code}: workspace rejected"`;
  `GraphPatchError` is `f"{code}: graph patch rejected"`;
  `ContractValidationError` is `f"{code}: {contract} at {path} violates {rule}"`
  — no note label or body text ever reaches an error response. The flattened
  HTTP error payload contains only `code`/`rule`/`contract`/`path`/`target_id`
  (UUIDs), versions, and cycle paths. PASS.
- Secret scan: `SECRET_RULES` patterns (private key, `sk-`/`sk_` token,
  `AKIA`/`ASIA`) hit nothing under `apps/` (grep over `apps/api/main.py`,
  `apps/web/src/*.ts(x)`, all tests). PASS.
- Dependency boundary: `workspace.py` imports only stdlib (`hashlib`, `json`,
  `shutil`, `sqlite3`, `time`, `collections.abc`, `contextlib`, `dataclasses`,
  `pathlib`, `typing`) plus `knowledge_tree_domain`; `main.py` imports
  `fastapi`, `starlette`, `knowledge_tree_domain`, and the workspace adapter —
  `fastapi`/`uvicorn` were already declared in `pyproject.toml`. No new
  third-party or network dependency was introduced. PASS.
- Repository validator: `scripts/repository_validation.REQUIRED_PATHS` includes
  `apps/api`; all referenced paths exist in the tree. Not executed (see §2).

### 5. CI consistency

`.github/workflows/ci.yml` in `6c0c33c` extends `ruff format --check` to
`packages scripts tests apps` and strict `mypy` to `... apps/api` (diff
verified: both lines changed from the pre-frozen version). This matches the
frozen commit message's declared gate commands. The web job runs
`pnpm check` (`tsc -b && eslint . --max-warnings 0 && vitest run`) and covers
`apps/web/src` including the new `api.ts`. PASS.

## Findings

No P0 or P1 finding. No CORS bypass, path-traversal reach, invalid-payload
overwrite, semantic round-trip break, or tamper-evasion failure was found.
Three non-blocking P2 observations (none is a security, data-integrity, or
anti-tamper defect):

- **P2-1 (backup semantics):** `POST /api/workspaces/{id}/backup` calls
  `create_workspace` then `backup_workspace`, so backing up a workspace that
  has no database silently creates an empty SQLite file inside `data_root` and
  returns `200 backed_up`. This differs from `GET .../graph` (404
  `workspace_missing` for a missing workspace). Harmless (backup filenames are
  timestamp-unique, nothing is overwritten), but the endpoint does not
  distinguish "missing" from "backed up".
- **P2-2 (mount-time race):** in `App.tsx`, edits made before `loadGraph()`
  resolves can be overwritten by `setPresent(saved)`. The window is small for a
  loopback sidecar and the existing tests do not cover it; a guard (drop the
  resolved value if the user already committed) would harden it.
- **P2-3 (unload flush):** the 600 ms debounce in `scheduleAutoSave` means an
  edit made within the last 600 ms before page close is not persisted (no
  `beforeunload` flush). Acceptable for the demo scope, but worth noting as a
  data-loss edge for future product work.

## Limitations

- **No live execution was possible in this QA environment.** The permission
  layer rejected `uv`, `pytest`, `pnpm`, `ruff`, `mypy`, and
  `scripts.validate_repository` for the read-only subagent; therefore the
  `7 passed` API-suite run, the full `182 passed` run, `ruff check`,
  strict-mypy, the pnpm `10 passed` run, and the repository validator were NOT
  independently re-executed by this reviewer. Everything reported from those
  commands is static tracing plus local cache evidence, and the commit-message
  declarations (182 pytest / 10 web) are quoted as declarations only.
- **pytest count discrepancy:** the local `.pytest_cache/v/cache/nodeids`
  lists 187 collected nodes, while the `6c0c33c` commit message declares
  `182 passed`. The cache is an untracked local artifact (last-run state,
  including one pre-existing calculus `lastfailed` entry) and may predate or
  postdate the commit's own run; the exact collection/pass count cannot be
  confirmed without a live run.
- The web counter-examples rely on the vitest/jsdom harness (crypto,
  `fetch`) being available under `pnpm check`; the tests themselves are mock-
  based and do not exercise `snapshotToGraph`/`uuidv7` directly (the mock
  `PersistApi` short-circuits before serialization), so those two functions
  are verified by static tracing only.
- This review covers only the frozen WORK-2026-014 surface (API sidecar, web
  auto-save, CI wiring); it does not re-audit the domain/contracts layers
  wholesale, does not claim release readiness, encryption, multi-process
  safety, or cloud behaviour, and does not assess the sidecar's lack of
  authentication (loopback-only local app is an accepted design premise).
- This correlated machine attestation is not a human signature, workspace-
  owner acceptance, release approval, or ADR acceptance. No network, real
  provider, or user data was used; no repository file was modified (the only
  write is this report under `evidence/`, as the workflow prescribes).
