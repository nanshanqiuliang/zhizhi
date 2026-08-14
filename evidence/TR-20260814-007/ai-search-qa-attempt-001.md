# AI QA attempt 001 — FTS5 full-text search over saved concepts (WORK-2026-015)

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: graph_qa_fresh
decision: pass
reviewed_commit: eeba07368b0f2d1f47ebfd893ef2675aca194656
red_baseline_commit: e451057b17eedeec5180d1ac5a41490021ea6236
ready_commit: e451057b17eedeec5180d1ac5a41490021ea6236
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

PASS with no P0 or P1 finding. This is a read-only, role-separated machine
review of frozen commit `eeba073` (WORK-2026-015 FTS5 search). Git lineage,
frozen blobs, working-tree state, and the red-light baseline were verified
against committed objects via live read-only git commands; every required
counter-example was re-derived independently (MATCH + substring fallback for
CJK, empty/overlong/invalid-syntax rejection, empty-result 200, missing
workspace 404, bounded snippet, save-time index rebuild, corrupt-index
fail-closed behaviour, and the two web tests). Three P2 observations are
non-blocking UX/error-classification edges, not security, data-integrity, or
anti-tamper defects.

Note upfront: this QA environment's permission layer rejected every `uv`/
`pnpm` invocation for a read-only subagent (exact rejection recorded in §2),
so the Python and web test suites were NOT independently re-executed here.
All behavioural claims in §3 are line-by-line static execution tracing of the
frozen implementation, cross-checked against the frozen test files and the
local pytest cache (which lists exactly the 10 `test_search_api.py` nodes with
no search-related `lastfailed` entry). See Limitations for the full boundary.

## Independent checks

### 1. Commit chain, frozen blob, and working tree (live git, read-only subagent)

- `git rev-parse HEAD` → `eeba07368b0f2d1f47ebfd893ef2675aca194656`; branch
  `feature/WORK-2026-015-fts5-search` is the only head and `HEAD ==` the frozen
  commit (`git diff --stat eeba073 HEAD` is empty).
- `git cat-file -p eeba073` → `parent e451057b17eedeec5180d1ac5a41490021ea6236`;
  `git log --oneline --ancestry-path e451057..eeba073` yields only `eeba073`
  itself — `eeba073` is the **direct child** of the Ready boundary `e451057`
  (chain: `eeba073 → e451057 → 607a443 → e0a4c72 → 6c0c33c → 4fe918b →
  31ce814`).
- **Lineage correction:** the task brief called `31ce814` "eeba073's
  grandparent". It is in fact the 6th ancestor; the direct grandparent is
  `607a443`. The red-light evidence does not depend on which ancestor — see
  the stronger check below.
- `git show --stat eeba073`: 8 files, +481/−5 (`apps/api/main.py` +18,
  `apps/web/src/App.tsx` +65, `apps/web/src/api.ts` +16,
  `apps/web/src/styles.css` +102, `apps/web/src/App.persist.test.tsx` +45/−x,
  `workspace.py` +118, `__init__.py` +4, `tests/integration/test_search_api.py`
  +118). `git cat-file -t` confirms both commits are commit objects.
- Working tree matches the frozen blob: `git diff eeba073 -- apps/api/main.py
  apps/web/src/api.ts packages/.../workspace.py tests/integration/test_search_api.py`
  is empty; `git status --porcelain` shows only untracked `.reasonix/`,
  `handoff/` (no tracked-file modification).
- **Red baseline (stronger than the brief's worktree note):** on the Ready
  boundary `e451057` (eeba073's direct parent) there is *no* `SearchResult`,
  *no* `search_course_graph` (git grep: no matches in workspace.py), *no*
  `/api/workspaces/{workspace_id}/search` route (git grep: no matches in
  main.py), and *no* `tests/integration/test_search_api.py` (git ls-tree:
  only `test_persist_api.py` + `test_workspace_persistence.py` exist). Adding
  the frozen test file to `e451057` therefore fails collection with
  `ImportError: cannot import name 'SearchResult'` — the documented red light
  is real, and already at the direct parent (no need to reach back to
  `31ce814`).

### 2. Test suites — NOT live-run (permission layer rejected execution)

Every execution command was attempted through a read-only subagent and each
returned the same permission-layer rejection, so no result can be reported for
any of them:

```
uv run python -m pytest tests/integration/test_search_api.py -q   → blocked
uv run python -m pytest -q                                         → blocked
CI=true pnpm --filter @knowledge-tree/web test                     → blocked
uv run ruff check .                                                → blocked
uv run python -m mypy --strict ... apps/api                        → blocked
uv run python -m scripts.validate_repository                       → blocked
```

Exact rejection: `blocked: read-only subagents can run only
permission-classified foreground read-only commands`. (`python --version` →
Python 3.12.6 and `node --version` → v24.14.1 ran fine, but `uv` itself is
outside the allowed list.) These are **not** reported as passing.

Local disk evidence only: `.pytest_cache/v/cache/nodeids` lists **198**
collected nodes including **all 10** `test_search_api.py` nodes
(`test_search_hits_label`, `test_search_hits_note`, `test_search_result_shape`,
`test_search_no_match_returns_empty`, and the six `test_search_endpoint_*`
tests) — i.e. the suite was collected on a recent run of this exact tree.
`.pytest_cache/v/cache/lastfailed` holds exactly one pre-existing calculus
edge case (`test_invalid_independent_review_mutations_fail[<lambda>-review
coverage]`), unrelated to search. The `eeba073` commit message declares
`pytest -q (193 passed; search 10/10)` and `pnpm check (12 passed)`; the web
count is structurally consistent (6 existing `App.test.tsx` + 6
`App.persist.test.tsx` = 12, with the two new search tests present), but
neither count was independently reproduced here.

### 3. Independent counter-examples (static execution tracing)

- **CJK label/note hit via substring fallback.** `_rebuild_search_index`
  stores `(concept_id, label, note)` (first `kind=="note"` annotation) into
  FTS5 `concept_search(concept_id UNINDEXED, label, note)`. Search computes
  `match_ids` from `MATCH ?` (parameterised — no SQL injection), then falls
  back to `needle = query.strip().casefold() in label.casefold()/note.casefold()`
  for every row. `graph_with_notes()` sets note = `"<label>的笔记内容"`; query
  `"极限"` hits via MATCH on label token AND via substring on label/note;
  query `"连续"` (present only inside the concatenated CJK token
  `"连续的笔记内容"`, which unicode61 tokenizes as one token and MATCH misses)
  still hits via the substring fallback — the known CJK tokenization edge the
  work item declared out of scope is explicitly covered by the fallback.
  English queries (`limit`) go through MATCH (case-insensitive) and are also
  substring-covered. PASS.
- **Empty / overlong / invalid-syntax queries.** `""` or whitespace →
  `_reject("search_invalid_query", rule="query_empty")`; `len(query) > 100`
  (101-char string) → `rule="query_too_long"`; FTS5 syntax error from
  `"极限 AND ("` raises `sqlite3.DatabaseError` inside the inner try, caught
  and re-raised as `rule="query_syntax_invalid"`. All three map through
  `_http_error` to **422 `{"code":"search_invalid_query","rule":...}`**, and
  because `WorkspaceError` is not a `sqlite3.DatabaseError` it is not swallowed
  by the outer corrupt-handler. Matches `test_search_endpoint_empty/
  overlong/invalid_syntax_rejected`. PASS.
- **No match → empty 200; missing workspace → 404.** `"不存在的关键词"` →
  empty `results` → `200 {"results": []}`. A workspace whose root directory
  or `knowledge-tree.db` is absent → `resolve_workspace` raises
  `workspace_missing` → **404**, and `_workspace_root` still requires UUIDv7
  first (path traversal from WORK-2026-014 re-verified as blocked before any
  join). Matches `test_search_no_match_returns_empty`,
  `test_search_endpoint_no_match_empty_list`, and
  `test_search_endpoint_missing_workspace_404`. PASS.
- **Snippet bounded and body-leak-free.** `_snippet` finds the first
  `needle` in `f"{label}：{note}"`, takes a 60-char window centred on it
  (`_SNIPPET_LENGTH=60`), and adds at most `…` prefix + `…` suffix → max length
  62. Errors carry no body: `WorkspaceError.__str__` is the fixed
  `f"{code}: workspace rejected"` and HTTP `detail` contains only
  `code`/`rule`/fixed keys — never the query, label, or note text. PASS.
- **Save-time index consistency.** `save_course_graph` writes the graph to
  `meta` and calls `_rebuild_search_index` inside the **same** `_connect`
  transaction (DELETE all + INSERT new rows), so changing a label/note and
  re-saving atomically replaces the index: the old token stops matching and
  the new one matches; a mid-rebuild failure rolls back both meta and index.
  PASS.
- **Corrupt index fails closed.** Deleting `concept_search` → next search
  recreates an empty table (`CREATE VIRTUAL TABLE IF NOT EXISTS`) and returns
  `[]` (stable, non-crashing); re-saving rebuilds it. A table that exists but
  is broken → SELECT/MATCH raises `DatabaseError` → outer handler →
  `workspace_corrupt` (500) or inner handler → 422; never a crash or partial
  graph read. See P2-3 for the one misclassification edge. PASS.
- **Web search/locate/fail.** `runSearch` (empty query clears; success →
  `done` + results; any error → `failed` + cleared) and `jumpToResult`
  (`present.nodes.find` → `selectNode` + viewport `scrollLeft` centring) match
  the two new tests: "searches and locates a matching concept" (fires change,
  awaits `定位到概念：极限`, clicks, asserts node button appears) and
  "shows no-match feedback and a failed-search state" (`没有匹配的概念`,
  then `搜索失败`). `httpPersistApi.searchGraph` encodes the query with
  `encodeURIComponent` and maps non-OK to `throw`. PASS.

### 4. Content safety and dependency boundary

- Error payloads never contain note/label/query text (see §3 snippet item).
- Secret scan: `SECRET_RULES` patterns (private key, `sk-`/`sk_` token,
  `AKIA`/`ASIA`) hit nothing under `apps/`, `packages/`, `tests/`, `scripts/`
  (grep over the tree). PASS.
- Dependency boundary: `workspace.py` adds only stdlib usage (`sqlite3` FTS5
  is built into Python 3.12; `_ensure_search_table` uses a fixed table name —
  no new import); `main.py` reuses existing `fastapi`/`starlette`;
  `pyproject.toml` is unchanged in `eeba073`; web uses `fetch` with no new
  package. No third-party or network dependency was introduced. PASS.
- Repository validator: `scripts/repository_validation.REQUIRED_PATHS`
  includes `apps/api`, `apps/web`, `packages/infrastructure/...`; all listed
  paths exist at `eeba073` (verified via `git ls-tree`). Not executed (§2).

### 5. CI consistency

`.github/workflows/ci.yml` at `eeba073` runs `ruff format --check packages
scripts tests apps`, `ruff check .`, `mypy scripts` + `mypy --strict ... apps/api`
(so `apps/api/main.py` IS covered), `uv run pytest` (testpaths `tests`,
pythonpath includes `apps`), and the web job runs `pnpm check`
(`tsc -b && eslint . --max-warnings 0 && vitest run`), which covers the new
`App.tsx` search UI and `api.ts`. This matches the commit message's declared
gate set. PASS.

## Findings

No P0 or P1 finding. No semantic bypass, privilege escalation, data
corruption, index inconsistency, note-body leak, or tamper-evasion failure was
found. Three non-blocking P2 observations:

- **P2-1 (search request race):** `App.tsx` `runSearch` fires on every
  keystroke with no debounce and no request sequencing/abort, so a slow older
  response can overwrite newer results in the dropdown. Local loopback latency
  makes this rare; the existing tests use sequential mock promises. UX edge,
  not a correctness or security defect.
- **P2-2 (front-end length/no-match UX):** the search input has no `maxLength`
  and non-OK responses are all mapped to `搜索失败`, so an overlong (>100)
  or invalid-syntax query surfaces as a generic failure rather than the
  work-item's stated `搜索词无效` hint. Server-side rejection is correct; the
  message mapping is coarse.
- **P2-3 (corrupt-table error classification):** if `concept_search` is
  replaced by an ordinary table with the same name (not a FTS5 virtual table),
  `MATCH` raises `DatabaseError` which the inner handler classifies as
  `query_syntax_invalid` (422) rather than `workspace_corrupt` (500). Still a
  stable, non-crashing, non-leaking failure; only the reported rule is
  misleading in a hand-tampered store.

## Limitations

- **No live execution in this QA environment.** The permission layer rejected
  `uv`, `pytest`, `pnpm`, `ruff`, `mypy`, and `scripts.validate_repository`
  for the read-only subagent (exact rejection recorded in §2). The 10-test
  search suite, the full pytest run, `pnpm check`, ruff, strict-mypy, and the
  repository validator were NOT independently re-executed. Everything reported
  from them is static tracing plus local cache evidence; the commit message's
  `193 passed` / `12 passed` declarations are quoted as declarations only.
- **Node-count discrepancy:** local `.pytest_cache/v/cache/nodeids` lists 198
  collected nodes while the commit declares `193 passed`; the cache is an
  untracked local artifact (last-run state) and the one `lastfailed` entry is
  a pre-existing calculus edge case unrelated to search. Exact pass counts
  cannot be confirmed without a live run.
- **Lineage correction:** `31ce814` is the 6th ancestor of `eeba073`, not its
  grandparent (`607a443` is); the red-light claim was verified directly at the
  parent `e451057`, which is stronger.
- **FTS5 semantics under Python 3.12.6** (unicode61 tokenization, syntax
  error surface, `MATCH ?` parameter binding) are reasoned statically; a live
  sqlite3 run would independently confirm the tokenization assumptions behind
  the CJK fallback.
- This review covers only the frozen WORK-2026-015 surface (FTS5 index,
  search endpoint, web search UI, CI wiring). It does not re-audit the domain/
  contracts layers wholesale, does not claim release readiness, encryption,
  multi-process safety, or cloud behaviour, and does not assess the sidecar's
  lack of authentication (loopback-only local app is an accepted design
  premise).
- This correlated machine attestation is not a human signature, workspace-
  owner acceptance, release approval, or ADR acceptance. No network, real
  provider, or user data was used; no repository file was modified (the only
  write is this report under `evidence/`, as the workflow prescribes).
