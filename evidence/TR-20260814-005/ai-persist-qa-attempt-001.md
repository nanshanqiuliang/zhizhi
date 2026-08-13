# AI QA attempt 001 — local SQLite workspace persistence prototype (WORK-2026-013)

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: graph_qa_fresh
decision: pass
reviewed_commit: 8e34a40f02de8d94ad6db3927cf8b189e9caee03
red_baseline_commit: 1420b68fd8eb4f4bea82e217140af2efcd820447
ready_commit: ec8005e1527b223fee043f2c1bffe718e1bede5b
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

PASS with no P0, P1, P2, or new finding. This is a read-only, role-separated
machine review of frozen commit `8e34a40`; the workspace file, tests, and Git
lineage were verified against the committed objects and the working tree was
confirmed clean at HEAD. Note upfront: this QA environment has no shell
executor (permission layer rejects `uv`, `pytest`, `ruff`, `mypy`, and
`python -c`), so the mutation battery and gate commands were validated by
line-by-line static execution tracing of the deterministic stdlib/driver code
rather than by live re-execution. Every traced scenario fails closed exactly as
specified, and the on-disk pytest collection cache corroborates the 21/21
target suite. See Limitations.

## Independent checks

- **Commit chain (git, read-only subagent):** `8e34a40` -> `1420b68` ->
  `ec8005e` is a direct parent chain. `git cat-file -p 8e34a40` shows
  `parent 1420b68fd8eb4f4bea82e217140af2efcd820447`; `git cat-file -p 1420b68`
  shows `parent ec8005e1527b223fee043f2c1bffe718e1bede5b`; `HEAD` resolves to
  `8e34a40f02de8d94ad6db3927cf8b189e9caee03` and `git diff --stat 8e34a40 HEAD`
  is empty. Working tree has no tracked modifications (only untracked
  `.reasonix/` and `handoff/`). The frozen blob
  `8e34a40:packages/infrastructure/src/knowledge_tree_infrastructure/workspace.py`
  (393 lines) is byte-identical to the tree file under review.
- **Red baseline is real:** `git show 1420b68 --stat` adds only
  `tests/integration/test_workspace_persistence.py` (246 lines),
  `tests/unit/test_workspace_records.py` (76 lines), and a 2-line pyproject
  edit. `git ls-tree -r 1420b68` contains no `workspace.py`; the only file under
  `packages/infrastructure/src/knowledge_tree_infrastructure/` is `README.md`.
  Both red test modules `from knowledge_tree_infrastructure.workspace import
  ...`, so collection failed with exactly the two documented ImportErrors.
- **Target suite evidence (not live re-run):** `.pytest_cache/v/cache/nodeids`
  (untracked, local disk artifact of the latest pytest run) lists 175 collected
  nodes including all 17 `test_workspace_persistence.py` tests and all 4
  `test_workspace_records.py` tests (21/21 collected). `.pytest_cache/v/cache/
  lastfailed` contains a single calculus edge case and no workspace node,
  consistent with the 21 workspace tests passing on the last run. The commit
  message of `8e34a40` declares `uv run pytest -q (175 passed)`.
- **Mutation: record digest tamper** (revision/hash/delta edited in
  `record_to_json` output) -> `record_from_json` recomputes the canonical
  SHA-256 over the non-digest fields with the same normalized JSON
  (`sort_keys`, compact separators) and rejects on mismatch with
  `record_tampered` (`record_digest_mismatch`). A tampered digest, a swapped
  delta order, a type-coerced int field, and an extra JSON field all diverge in
  the canonical serialization -> `record_tampered` or `record_invalid`.
  PASS.
- **Mutation: truncated header / garbage bytes** -> the lazy sqlite3 open fails
  on the first PRAGMA/SELECT with a `sqlite3.DatabaseError`, caught in
  `load_course_graph` as `workspace_corrupt` (`database_not_readable`); no
  partial graph is ever returned. Missing `course_graph` row and non-dict JSON
  also fail closed as `workspace_corrupt`. PASS.
- **Mutation: overwrite with an invalid graph** (e.g. `concepts` containing a
  bad item) -> `save_course_graph` calls `_validate_graph` before touching the
  database; `validate_course_graph` raises `GraphPatchError`
  (`_validate_schema` converts `ContractValidationError` to `GraphPatchError`,
  confirmed in graph_patch.py), surfaced as `WorkspaceError("graph_invalid")`,
  and the previously saved graph is left intact. PASS.
- **Mutation: duplicate `change_id` history** -> `save_history_records` inserts
  both rows (AUTOINCREMENT `seq`), `load_history_records` returns both
  records in order; `GraphHistory.replay` first calls
  `_reject_duplicate_change_ids` and raises `GraphHistoryError`
  `validation_failed`/`duplicate_change_id`. PASS.
- **Mutation: `PRAGMA user_version = 99`** -> `migrate` rejects with
  `migration_conflict` (`schema_newer_than_supported`) before any DDL. PASS.
- **Mutation: garbage file to `migrate`** -> the `PRAGMA user_version` read
  raises `sqlite3.DatabaseError`, caught as `WorkspaceError("migration_failed")`
  before any table creation, so no half-initialized database is left; even if
  the rollback in `_connect` re-raises on the broken connection, that exception
  is itself a `sqlite3.DatabaseError` subclass and is still converted to the
  same `WorkspaceError`. PASS.
- **Mutation: checksum tamper on restore** -> `restore_backup` compares the
  `.sha256` sidecar against the file bytes and rejects with
  `backup_checksum_mismatch` (`restore_rejected`) before copying. PASS.
- **Mutation: purge** -> `purge_workspace` removes the database (plus WAL/SHM/
  journal sidecars) and every file under `backups/` and `exports/`, then writes
  `purge-manifest.json` listing the relative `deleted_paths`. PASS.
- **Content safety:** `WorkspaceError` message is the fixed
  `f"{code}: workspace rejected"` and carries no note label or body; `details`
  is limited to fixed `rule` strings, integer versions, and UUID-style IDs
  (`ContractValidationError.details` is only `{contract, path, rule}`);
  `GraphPatchError.details` carries only rule strings and UUID `target_id`/
  `cycle_path`/`operation_id`. No note label/body reaches any error surface.
- **Dependency boundary:** `workspace.py` imports only stdlib (`hashlib`,
  `json`, `shutil`, `sqlite3`, `time`, `collections.abc`, `contextlib`,
  `dataclasses`, `pathlib`, `typing`) plus `knowledge_tree_domain`; no
  FastAPI/SQLAlchemy/parser/LLM/network/third-party-storage import exists.
- **Secret scan:** the repository's `SECRET_RULES` patterns (private key,
  `sk-`/`sk_` token, `AKIA`/`ASIA` key) hit nothing under
  `packages/infrastructure` or `tests` (grep of the scanned text files).
- **CI consistency:** `.github/workflows/ci.yml` type-check step runs
  `uv run mypy scripts && uv run mypy --strict packages/contracts-py/src
  packages/domain/src packages/infrastructure/src`, so
  `packages/infrastructure/src` is covered by strict mypy in CI. The
  repository-validator, ruff format/lint, and full pytest steps also cover the
  new module.

## Findings

No P0, P1, P2, or new finding. All seven required mutation classes plus the
fault-injection cases in TC-PERS-005 trace to the specified fail-closed codes,
and no semantic bypass, privilege escalation, data corruption, or
tamper-evasion path was found in the frozen implementation.

## Limitations

- **No live execution was possible in this QA environment.** The read-only
  subagent permission layer rejected `uv`, `pytest`, `ruff`, `mypy`,
  `scripts.validate_repository`, and every `python -c` invocation, so the
  21/21 target run, the 175/175 full suite, ruff, strict mypy, and the
  repository validator were NOT independently re-executed by this reviewer.
  Test-success evidence rests on the untracked `.pytest_cache` collection/
  `lastfailed` artifacts (consistent with 21/21 passing on the latest local
  run) and the `8e34a40` commit-message declaration of 175 passed; these are
  not this reviewer's own execution.
- The mutation battery was validated by deterministic static tracing of the
  implementation (every branch examined, exception conversions checked in
  `workspace.py`, `graph_patch.py`, and `graph_history.py`) rather than by
  live scripts; while these paths are deterministic stdlib code, a live
  re-run in an executor-capable session is recommended before sign-off.
- This review covers only the frozen WORK-2026-013 prototype surface; it does
  not re-audit the domain/contracts layers wholesale or the web/demo/product
  surface, and it does not claim release readiness, encryption, multi-process
  safety, or cloud behavior.
- `restore_backup` treats the checksum sidecar as optional (restore proceeds
  if the `.sha256` file is absent); this is a documented design choice, not a
  finding, but it means a restored backup is only protected when the sidecar
  exists.
- This correlated machine attestation is not a human signature, workspace-owner
  acceptance, release approval, or ADR acceptance. No network, real provider,
  or user data was used; no repository file was modified.
