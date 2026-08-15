"""Local SQLite workspace persistence adapter (WORK-2026-013 prototype).

Pure stdlib `sqlite3` storage for a confirmed CourseGraph plus its trusted
GraphHistory change records. This adapter must never become the source of truth
for graph semantics: every read/write path reuses the canonical graph contract
via `knowledge_tree_domain.validate_course_graph`, and every record payload is
digest-checked on load so tampered history fails closed.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import time
from collections.abc import Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Never

from knowledge_tree_domain import (
    EntityDelta,
    GraphChangeRecord,
    GraphHistory,
    GraphHistoryError,
    GraphPatchError,
    semantic_graph_hash,
    validate_course_graph,
)

JsonObject = dict[str, Any]
SUPPORTED_SCHEMA_VERSION = 3
_GRAPH_KEY = "course_graph"
_INITIAL_GRAPH_KEY = "course_graph_initial"
_APPLIED_COUNT_KEY = "course_graph_applied"
_LOCAL_ACTOR = {"type": "user", "id": "local-user"}
_MAX_QUERY_LENGTH = 100
_SNIPPET_LENGTH = 60
_SEARCH_TABLE = "concept_search"
_MAX_IMPORT_BYTES = 25 * 1024 * 1024
_ALLOWED_MIME_BY_MAGIC: tuple[tuple[str, str], ...] = (("application/pdf", "%PDF-"),)
_TEXT_EXTENSIONS = {".md": "text/markdown", ".txt": "text/plain"}


class WorkspaceError(ValueError):
    """A stable, content-safe workspace rejection."""

    def __init__(self, code: str, *, details: Mapping[str, Any]) -> None:
        self.code = code
        self.details = dict(details)
        super().__init__(f"{code}: workspace rejected")


@dataclass(frozen=True, slots=True)
class ResourceInfo:
    """Metadata for an imported resource; never carries file content."""

    id: str
    display_name: str
    mime: str
    byte_size: int
    content_hash: str
    created_at: str


@dataclass(frozen=True, slots=True)
class PageSegment:
    """A single parsed page of text for a resource version."""

    resource_version_id: str
    page: int
    text: str
    text_hash: str


@dataclass(frozen=True, slots=True)
class AnchorRef:
    """A registered anchor binding a resource page to a payload."""

    id: str
    resource_id: str
    page: int
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class SearchResult:
    """A single concept match with a content-safe label and snippet."""

    id: str
    label: str
    snippet: str


@dataclass(frozen=True, slots=True)
class AnswerContext:
    """Citation-numbered context text plus the source refs it cites."""

    context: str
    sources: tuple[SearchResult, ...]


@dataclass(frozen=True, slots=True)
class WorkspaceLayout:
    """User-visible local workspace directory layout."""

    root: Path
    db_path: Path
    backups_dir: Path
    exports_dir: Path


def create_workspace(root: Path) -> WorkspaceLayout:
    """Create (or reuse) the local workspace directory layout."""

    root = Path(root)
    db_path = root / "knowledge-tree.db"
    backups_dir = root / "backups"
    exports_dir = root / "exports"
    root.mkdir(parents=True, exist_ok=True)
    backups_dir.mkdir(parents=True, exist_ok=True)
    exports_dir.mkdir(parents=True, exist_ok=True)
    return WorkspaceLayout(
        root=root, db_path=db_path, backups_dir=backups_dir, exports_dir=exports_dir
    )


def resolve_workspace(root: Path) -> WorkspaceLayout:
    """Resolve an existing workspace layout, failing closed if incomplete."""

    layout = WorkspaceLayout(
        root=Path(root),
        db_path=Path(root) / "knowledge-tree.db",
        backups_dir=Path(root) / "backups",
        exports_dir=Path(root) / "exports",
    )
    if not layout.root.is_dir():
        _reject("workspace_missing", rule="root_directory_absent")
    if not layout.db_path.is_file():
        _reject("workspace_missing", rule="database_file_absent")
    return layout


def migrate(db_path: Path) -> None:
    """Migrate a database to schema v3; reject unknown/future versions."""

    db_path = Path(db_path)
    try:
        with _connect(db_path) as conn:
            current = int(conn.execute("PRAGMA user_version").fetchone()[0])
            if current > SUPPORTED_SCHEMA_VERSION:
                _reject(
                    "migration_conflict",
                    rule="schema_newer_than_supported",
                    current_version=current,
                    supported_version=SUPPORTED_SCHEMA_VERSION,
                )
            if current == SUPPORTED_SCHEMA_VERSION:
                return
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS history_records ("
                "seq INTEGER PRIMARY KEY AUTOINCREMENT,"
                "change_id TEXT NOT NULL,"
                "payload TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS resource ("
                "id TEXT PRIMARY KEY,"
                "display_name TEXT NOT NULL,"
                "current_version_id TEXT,"
                "created_at TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS resource_version ("
                "id TEXT PRIMARY KEY,"
                "resource_id TEXT NOT NULL,"
                "version_no INTEGER NOT NULL,"
                "content_hash TEXT NOT NULL,"
                "mime TEXT NOT NULL,"
                "byte_size INTEGER NOT NULL,"
                "storage_key TEXT NOT NULL,"
                "created_at TEXT NOT NULL,"
                "UNIQUE(resource_id, content_hash))"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS resource_segment ("
                "id TEXT PRIMARY KEY,"
                "resource_version_id TEXT NOT NULL,"
                "page INTEGER NOT NULL,"
                "text TEXT NOT NULL,"
                "text_hash TEXT NOT NULL,"
                "content_hash TEXT NOT NULL,"
                "created_at TEXT NOT NULL,"
                "UNIQUE(resource_version_id, page))"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS anchor ("
                "id TEXT PRIMARY KEY,"
                "resource_id TEXT NOT NULL,"
                "page INTEGER NOT NULL,"
                "payload TEXT NOT NULL,"
                "created_at TEXT NOT NULL,"
                "UNIQUE(resource_id, page))"
            )
            conn.execute(f"PRAGMA user_version = {SUPPORTED_SCHEMA_VERSION}")
    except sqlite3.DatabaseError as error:
        raise WorkspaceError(
            "migration_failed", details={"rule": "database_not_readable"}
        ) from error


def save_course_graph(layout: WorkspaceLayout, graph: Mapping[str, Any]) -> None:
    """Validate and persist a CourseGraph, then rebuild the search index.

    On first save this is a whole-graph replacement (initialises the workspace).
    On subsequent saves the incoming graph is diffed against the current one and
    applied through the protected patch gate, so ordinary edits keep producing
    history records and remain cross-session undoable. Locked dimensions and
    revision conflicts are enforced by the patch gate itself.
    """

    _validate_graph(graph)
    current = _try_load_saved_graph(layout)
    if current is None:
        _whole_graph_replace(layout, graph)
        return
    if semantic_graph_hash(current) == semantic_graph_hash(graph):
        return
    patch = _build_diff_patch(current, graph)
    if not patch["operations"]:
        _whole_graph_replace(layout, graph)
        return
    apply_graph_patch(layout, patch, trusted_actor=_LOCAL_ACTOR)


def _whole_graph_replace(layout: WorkspaceLayout, graph: Mapping[str, Any]) -> None:
    """Overwrite the current/initial graph and clear history (first save)."""

    payload = json.dumps(graph, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    try:
        with _connect(layout.db_path) as conn:
            conn.execute(
                "INSERT INTO meta(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (_GRAPH_KEY, payload),
            )
            conn.execute(
                "INSERT INTO meta(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (_INITIAL_GRAPH_KEY, payload),
            )
            conn.execute("DELETE FROM history_records")
            conn.execute("DELETE FROM meta WHERE key=?", (_APPLIED_COUNT_KEY,))
            _rebuild_search_index(conn, graph)
    except sqlite3.DatabaseError as error:
        raise WorkspaceError("save_failed", details={"rule": "database_not_writable"}) from error


def search_course_graph(layout: WorkspaceLayout, query: str) -> list[SearchResult]:
    """Full-text search over saved concept labels and notes.

    FTS5 MATCH is used as the primary index (best for tokenized languages);
    a plain substring filter over label/note backs it up so CJK text that
    FTS5's unicode61 tokenizer would treat as one big token still matches.
    """

    if not isinstance(query, str) or not query.strip():
        _reject("search_invalid_query", rule="query_empty")
    if len(query) > _MAX_QUERY_LENGTH:
        _reject("search_invalid_query", rule="query_too_long")
    try:
        with _connect(layout.db_path) as conn:
            _ensure_search_table(conn)
            rows = conn.execute(f"SELECT concept_id, label, note FROM {_SEARCH_TABLE}").fetchall()
            match_ids: set[str] = set()
            try:
                for (concept_id,) in conn.execute(
                    f"SELECT concept_id FROM {_SEARCH_TABLE} WHERE {_SEARCH_TABLE} MATCH ?",
                    (query,),
                ):
                    match_ids.add(str(concept_id))
            except sqlite3.DatabaseError:
                _reject("search_invalid_query", rule="query_syntax_invalid")
    except sqlite3.DatabaseError as error:
        raise WorkspaceError(
            "workspace_corrupt", details={"rule": "search_not_readable"}
        ) from error

    needle = query.strip().casefold()
    results: list[SearchResult] = []
    for concept_id, label, note in rows:
        concept_id = str(concept_id)
        label = str(label)
        note = str(note)
        if (
            concept_id not in match_ids
            and needle not in label.casefold()
            and needle not in note.casefold()
        ):
            continue
        results.append(
            SearchResult(
                id=concept_id,
                label=label,
                snippet=_snippet(label, note, needle),
            )
        )
    results.sort(key=lambda result: result.label.casefold())
    return results


def build_answer_context(layout: WorkspaceLayout, question: str) -> AnswerContext:
    """Retrieve FTS5 matches and render them as citation-numbered context.

    Each matched concept is cited as `[n] label：snippet` in the context text and
    kept as a source ref (id = concept id, clickable in the Web). When a natural
    question does not literally appear in any label/note (e.g. "什么是极限" vs the
    label "极限"), a reverse substring fallback matches concepts whose label is
    contained in the question. No LLM call and no write; an empty result yields
    empty context and no sources.
    """

    results = search_course_graph(layout, question)
    if not results:
        results = _reverse_match_concepts(layout, question)
    if not results:
        return AnswerContext(context="", sources=())
    lines = [
        f"[{index}] {result.label}：{result.snippet}"
        for index, result in enumerate(results, start=1)
    ]
    return AnswerContext(context="\n".join(lines), sources=tuple(results))


def _reverse_match_concepts(layout: WorkspaceLayout, question: str) -> list[SearchResult]:
    """Match concepts whose label appears inside the question (best-effort)."""

    graph = load_course_graph(layout)
    needle = question.strip().casefold()
    matches: list[SearchResult] = []
    for concept in graph["concepts"]:
        label = str(concept["label"])
        if not label or label.casefold() not in needle:
            continue
        note = ""
        for annotation in concept.get("annotations", []):
            if isinstance(annotation, Mapping) and annotation.get("kind") == "note":
                note = str(annotation.get("value", ""))
                break
        matches.append(
            SearchResult(
                id=str(concept["id"]),
                label=label,
                snippet=_snippet(label, note, question.strip()),
            )
        )
    matches.sort(key=lambda result: result.label.casefold())
    return matches[:5]


def load_course_graph(layout: WorkspaceLayout) -> JsonObject:
    """Load and revalidate the persisted CourseGraph, failing closed on damage."""

    try:
        with _connect(layout.db_path) as conn:
            row = conn.execute("SELECT value FROM meta WHERE key=?", (_GRAPH_KEY,)).fetchone()
    except sqlite3.DatabaseError as error:
        raise WorkspaceError(
            "workspace_corrupt", details={"rule": "database_not_readable"}
        ) from error
    if row is None:
        _reject("workspace_corrupt", rule="course_graph_absent")
    try:
        parsed = json.loads(str(row[0]))
    except (TypeError, ValueError) as error:
        raise WorkspaceError(
            "workspace_corrupt", details={"rule": "course_graph_not_json"}
        ) from error
    if not isinstance(parsed, dict):
        _reject("workspace_corrupt", rule="course_graph_not_object")
    graph = parsed
    _validate_graph(graph)
    return graph


def apply_graph_patch(
    layout: WorkspaceLayout,
    patch: Mapping[str, Any],
    *,
    trusted_actor: Mapping[str, str],
    source: str = "manual",
) -> GraphChangeRecord:
    """Apply a confirmed user GraphPatch through the protected commit gate.

    Rebuilds the persisted history from the initial graph plus the recorded
    change log, applies the patch through `GraphHistory.apply_patch` (which
    enforces the confirmation gate, four-dimension locks, revision conflicts and
    duplicate change ids), then commits the new graph, the new record and the
    initial-graph marker in a single transaction.
    """

    history = _rebuild_history(layout)
    initial_graph = history.snapshot
    try:
        next_history = history.apply_patch(patch, trusted_actor=trusted_actor, source=source)
    except (GraphHistoryError, GraphPatchError) as error:
        raise _convert_domain_error(error) from error
    record = next_history.undo_records[-1]
    _atomic_commit_graph(
        layout,
        graph=next_history.snapshot,
        new_record=record,
        initial_graph=initial_graph,
        applied_count=len(next_history.undo_records),
    )
    return record


def accept_ai_draft(
    layout: WorkspaceLayout,
    patch: Mapping[str, Any],
    *,
    trusted_actor: Mapping[str, str],
    anchors: Sequence[Mapping[str, Any]],
    source: str = "ai_draft",
) -> GraphChangeRecord:
    """Apply a confirmed AI draft patch and materialize its source anchors.

    Anchors are `{id, resource_id, page, label}` and are inserted with their
    explicit ids so the patch's `evidence_ids` reference real `anchor` rows. The
    graph, its history record, the applied-count marker, the FTS index and the
    anchors commit in one transaction — an anchor failure rolls the whole
    acceptance back. Draft anchors use `page=0` as a resource-level sentinel
    (real page anchors are `page>=1`).
    """

    history = _rebuild_history(layout)
    initial_graph = history.snapshot
    try:
        next_history = history.apply_patch(patch, trusted_actor=trusted_actor, source=source)
    except (GraphHistoryError, GraphPatchError) as error:
        raise _convert_domain_error(error) from error
    record = next_history.undo_records[-1]
    _atomic_commit_graph(
        layout,
        graph=next_history.snapshot,
        new_record=record,
        initial_graph=initial_graph,
        applied_count=len(next_history.undo_records),
        anchors=anchors,
    )
    return record


def undo_graph(layout: WorkspaceLayout) -> JsonObject:
    """Undo the most recent persisted change in strict LIFO order."""

    history = _rebuild_history(layout)
    try:
        next_history = history.undo()
    except GraphHistoryError as error:
        raise _convert_domain_error(error) from error
    _atomic_commit_graph(
        layout,
        graph=next_history.snapshot,
        applied_count=len(next_history.undo_records),
    )
    return next_history.snapshot


def redo_graph(layout: WorkspaceLayout) -> JsonObject:
    """Redo the most recently undone change in strict LIFO order."""

    history = _rebuild_history(layout)
    try:
        next_history = history.redo()
    except GraphHistoryError as error:
        raise _convert_domain_error(error) from error
    _atomic_commit_graph(
        layout,
        graph=next_history.snapshot,
        applied_count=len(next_history.undo_records),
    )
    return next_history.snapshot


def _rebuild_history(layout: WorkspaceLayout) -> GraphHistory:
    """Rebuild an in-memory history from the persisted initial graph and log."""

    current = load_course_graph(layout)
    records = load_history_records(layout)
    if not records:
        return GraphHistory.start(current)
    initial = _load_initial_graph(layout)
    if initial is None:
        _reject("workspace_corrupt", rule="initial_graph_absent")
    applied = _read_applied_count(layout)
    if applied is None:
        applied = len(records)
    if applied < 0 or applied > len(records):
        _reject("history_conflict", rule="applied_count_invalid", applied_count=applied)
    active = records[:applied]
    try:
        history = GraphHistory.replay(initial, active)
    except GraphHistoryError as error:
        raise _convert_domain_error(error) from error
    if semantic_graph_hash(history.snapshot) != semantic_graph_hash(current):
        _reject("history_conflict", rule="saved_graph_history_mismatch")
    # Replay resets the revision counter to the deterministic replayed value;
    # preserve the runtime revision stored on the persisted graph so subsequent
    # apply/undo/redo keeps the revision strictly monotonic.
    snapshot = history.snapshot
    snapshot["revision_no"] = current["revision_no"]
    snapshot_json = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return GraphHistory(
        _snapshot_json=snapshot_json,
        undo_records=history.undo_records,
        redo_records=tuple(reversed(records[applied:])),
    )


def _read_applied_count(layout: WorkspaceLayout) -> int | None:
    try:
        with _connect(layout.db_path) as conn:
            row = conn.execute(
                "SELECT value FROM meta WHERE key=?", (_APPLIED_COUNT_KEY,)
            ).fetchone()
    except sqlite3.DatabaseError as error:
        raise WorkspaceError(
            "workspace_corrupt", details={"rule": "database_not_readable"}
        ) from error
    if row is None:
        return None
    try:
        return int(str(row[0]))
    except (TypeError, ValueError) as error:
        raise WorkspaceError(
            "workspace_corrupt", details={"rule": "applied_count_invalid"}
        ) from error


def _load_initial_graph(layout: WorkspaceLayout) -> JsonObject | None:
    try:
        with _connect(layout.db_path) as conn:
            row = conn.execute(
                "SELECT value FROM meta WHERE key=?", (_INITIAL_GRAPH_KEY,)
            ).fetchone()
    except sqlite3.DatabaseError as error:
        raise WorkspaceError(
            "workspace_corrupt", details={"rule": "database_not_readable"}
        ) from error
    if row is None:
        return None
    try:
        parsed = json.loads(str(row[0]))
    except (TypeError, ValueError) as error:
        raise WorkspaceError(
            "workspace_corrupt", details={"rule": "initial_graph_not_json"}
        ) from error
    if not isinstance(parsed, dict):
        _reject("workspace_corrupt", rule="initial_graph_not_object")
    _validate_graph(parsed)
    return parsed


def _atomic_commit_graph(
    layout: WorkspaceLayout,
    *,
    graph: Mapping[str, Any],
    new_record: GraphChangeRecord | None = None,
    initial_graph: Mapping[str, Any] | None = None,
    applied_count: int | None = None,
    anchors: Sequence[Mapping[str, Any]] = (),
) -> None:
    """Commit the graph, optional record/initial marker/applied count and any
    draft source anchors atomically (all-or-nothing)."""

    payload = json.dumps(graph, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    try:
        with _connect(layout.db_path) as conn:
            conn.execute(
                "INSERT INTO meta(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (_GRAPH_KEY, payload),
            )
            if initial_graph is not None:
                initial_payload = json.dumps(
                    initial_graph, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                )
                conn.execute(
                    "INSERT OR IGNORE INTO meta(key, value) VALUES(?, ?)",
                    (_INITIAL_GRAPH_KEY, initial_payload),
                )
            if new_record is not None:
                conn.execute(
                    "INSERT INTO history_records(change_id, payload) VALUES(?, ?)",
                    (new_record.change_id, record_to_json(new_record)),
                )
            if applied_count is not None:
                conn.execute(
                    "INSERT INTO meta(key, value) VALUES(?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (_APPLIED_COUNT_KEY, str(applied_count)),
                )
            created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            for anchor in anchors:
                conn.execute(
                    "INSERT INTO anchor(id, resource_id, page, payload, created_at) "
                    "VALUES(?, ?, ?, ?, ?) "
                    "ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
                    (
                        str(anchor["id"]),
                        str(anchor["resource_id"]),
                        int(anchor["page"]),
                        json.dumps(
                            {
                                "topic_zh": str(anchor.get("label", "AI 草案来源")),
                                "source": "ai_draft",
                            },
                            ensure_ascii=False,
                        ),
                        created_at,
                    ),
                )
            _rebuild_search_index(conn, graph)
    except sqlite3.DatabaseError as error:
        raise WorkspaceError("save_failed", details={"rule": "database_not_writable"}) from error


def _convert_domain_error(error: ValueError) -> WorkspaceError:
    """Map a domain graph error to a stable workspace error code."""

    code = str(getattr(error, "code", "patch_invalid"))
    details = dict(getattr(error, "details", {"rule": code}))
    mapped = {
        "revision_conflict": "patch_revision_conflict",
        "target_locked": "target_locked",
        "permission_denied": "permission_denied",
        "history_empty": "history_empty",
        "history_conflict": "history_conflict",
    }.get(code, "patch_invalid")
    return WorkspaceError(mapped, details=details)


def backup_workspace(layout: WorkspaceLayout) -> Path:
    """Create a consistent online backup plus a checksum sidecar file."""

    # Millisecond-precision stamp so two backups in the same second cannot
    # overwrite each other.
    stamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime()) + f"{int(time.time() * 1000) % 1000:03d}Z"
    backup_path = layout.backups_dir / f"backup-{stamp}.sqlite3"
    try:
        with _connect(layout.db_path) as source, _connect(backup_path) as target:
            source.backup(target)
    except sqlite3.DatabaseError as error:
        raise WorkspaceError("backup_failed", details={"rule": "source_not_readable"}) from error
    digest = hashlib.sha256(backup_path.read_bytes()).hexdigest()
    backup_path.with_suffix(backup_path.suffix + ".sha256").write_text(
        f"{digest}\n", encoding="utf-8"
    )
    return backup_path


def restore_backup(layout: WorkspaceLayout, backup_path: Path) -> None:
    """Restore the database from a checksummed backup file.

    A missing checksum sidecar is rejected: the workspace guarantees every
    backup is checksummed, so an unchecksummed file must not overwrite the
    live database silently.
    """

    backup_path = Path(backup_path)
    checksum_file = backup_path.with_suffix(backup_path.suffix + ".sha256")
    if not checksum_file.is_file():
        _reject("backup_invalid", rule="backup_checksum_missing")
    expected = checksum_file.read_text(encoding="utf-8").strip()
    actual = hashlib.sha256(backup_path.read_bytes()).hexdigest()
    if expected != actual:
        _reject("backup_checksum_mismatch", rule="restore_rejected")
    try:
        _remove_wal_sidecars(layout.db_path)
        shutil.copyfile(backup_path, layout.db_path)
    except OSError as error:
        raise WorkspaceError("restore_failed", details={"rule": "backup_not_readable"}) from error


def list_backups(layout: WorkspaceLayout) -> list[str]:
    """List backup filenames in newest-first order (checksum sidecars excluded)."""

    if not layout.backups_dir.is_dir():
        return []
    return sorted(
        (path.name for path in layout.backups_dir.glob("*.sqlite3") if path.is_file()),
        reverse=True,
    )


def restore_backup_by_name(layout: WorkspaceLayout, filename: str) -> None:
    """Restore a workspace backup by its filename, guarded to the backups dir."""

    if not filename or Path(filename).name != filename or "/" in filename or "\\" in filename:
        _reject("backup_invalid", rule="backup_name_invalid")
    backup_path = (layout.backups_dir / filename).resolve()
    try:
        backup_path.relative_to(layout.backups_dir.resolve())
    except ValueError:
        _reject("backup_invalid", rule="backup_outside_workspace")
    if not backup_path.is_file():
        _reject("backup_invalid", rule="backup_missing")
    restore_backup(layout, backup_path)


def export_course_graph(layout: WorkspaceLayout, out_path: Path) -> None:
    """Export the validated CourseGraph as human-readable JSON."""

    graph = load_course_graph(layout)
    out_path = Path(out_path)
    out_path.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")


def purge_workspace(layout: WorkspaceLayout) -> Path:
    """Delete workspace data, recording a purge manifest first."""

    manifest = layout.root / "purge-manifest.json"
    deleted: list[str] = []
    if layout.db_path.exists():
        deleted.append(str(layout.db_path.relative_to(layout.root)))
        _remove_wal_sidecars(layout.db_path)
        layout.db_path.unlink()
    for directory in (layout.backups_dir, layout.exports_dir):
        if directory.is_dir():
            for child in directory.iterdir():
                if child.is_file():
                    deleted.append(str(child.relative_to(layout.root)))
                    child.unlink()
    manifest.write_text(
        json.dumps(
            {
                "deleted_paths": sorted(deleted),
                "purged_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return manifest


def save_history_records(layout: WorkspaceLayout, records: Iterable[GraphChangeRecord]) -> None:
    """Persist trusted change records in insertion order (duplicates preserved)."""

    frozen = tuple(records)
    try:
        with _connect(layout.db_path) as conn:
            conn.executemany(
                "INSERT INTO history_records(change_id, payload) VALUES(?, ?)",
                [(record.change_id, record_to_json(record)) for record in frozen],
            )
    except sqlite3.DatabaseError as error:
        raise WorkspaceError("save_failed", details={"rule": "history_not_writable"}) from error


def load_history_records(layout: WorkspaceLayout) -> list[GraphChangeRecord]:
    """Load and digest-verify all persisted change records in order."""

    try:
        with _connect(layout.db_path) as conn:
            rows = conn.execute("SELECT payload FROM history_records ORDER BY seq").fetchall()
    except sqlite3.DatabaseError as error:
        raise WorkspaceError(
            "workspace_corrupt", details={"rule": "history_not_readable"}
        ) from error
    return [record_from_json(str(row[0])) for row in rows]


def record_to_json(record: GraphChangeRecord) -> str:
    """Serialize a change record without losing its trusted digest."""

    payload = {
        "change_id": record.change_id,
        "before_revision_no": record.before_revision_no,
        "after_revision_no": record.after_revision_no,
        "before_semantic_hash": record.before_semantic_hash,
        "after_semantic_hash": record.after_semantic_hash,
        "deltas": [
            {
                "collection": delta.collection,
                "entity_key": delta.entity_key,
                "before_json": delta.before_json,
                "after_json": delta.after_json,
                "before_index": delta.before_index,
                "after_index": delta.after_index,
            }
            for delta in record.deltas
        ],
    }
    if record.source != "manual":
        payload["source"] = record.source
    payload["record_digest"] = _digest(payload)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def record_from_json(payload: str) -> GraphChangeRecord:
    """Deserialize a change record, rejecting tampered or malformed payloads."""

    try:
        parsed = json.loads(payload)
    except ValueError as error:
        raise WorkspaceError("record_invalid", details={"rule": "payload_not_json"}) from error
    if not isinstance(parsed, dict):
        _reject("record_invalid", rule="payload_not_object")
    try:
        change_id = str(parsed["change_id"])
        before_revision_no = int(parsed["before_revision_no"])
        after_revision_no = int(parsed["after_revision_no"])
        before_semantic_hash = str(parsed["before_semantic_hash"])
        after_semantic_hash = str(parsed["after_semantic_hash"])
        declared_digest = str(parsed["record_digest"])
        raw_deltas = parsed["deltas"]
        if not isinstance(raw_deltas, list):
            _reject("record_invalid", rule="deltas_not_list")
        deltas: list[EntityDelta] = []
        for raw in raw_deltas:
            if not isinstance(raw, dict):
                _reject("record_invalid", rule="delta_not_object")
            deltas.append(
                EntityDelta(
                    collection=str(raw["collection"]),
                    entity_key=str(raw["entity_key"]),
                    before_json=(
                        str(raw["before_json"]) if raw.get("before_json") is not None else None
                    ),
                    after_json=(
                        str(raw["after_json"]) if raw.get("after_json") is not None else None
                    ),
                    before_index=(
                        int(raw["before_index"]) if raw.get("before_index") is not None else None
                    ),
                    after_index=(
                        int(raw["after_index"]) if raw.get("after_index") is not None else None
                    ),
                )
            )
    except (KeyError, TypeError, ValueError) as error:
        raise WorkspaceError(
            "record_invalid", details={"rule": "payload_fields_invalid"}
        ) from error

    verification = {
        "change_id": change_id,
        "before_revision_no": before_revision_no,
        "after_revision_no": after_revision_no,
        "before_semantic_hash": before_semantic_hash,
        "after_semantic_hash": after_semantic_hash,
        "deltas": parsed["deltas"],
    }
    source = str(parsed.get("source", "manual"))
    if "source" in parsed:
        verification["source"] = source
    if _digest(verification) != declared_digest:
        _reject("record_tampered", rule="record_digest_mismatch")
    return GraphChangeRecord(
        change_id=change_id,
        before_revision_no=before_revision_no,
        after_revision_no=after_revision_no,
        before_semantic_hash=before_semantic_hash,
        after_semantic_hash=after_semantic_hash,
        deltas=tuple(deltas),
        record_digest=declared_digest,
        source=source,
    )


@contextmanager
def _connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    """Open a connection that commits on success and always closes the handle.

    The plain `with sqlite3.connect(...)` context only commits the transaction;
    it does NOT close the connection, which leaves the file locked on Windows.
    """

    conn = sqlite3.connect(db_path)
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def _remove_wal_sidecars(db_path: Path) -> None:
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = Path(f"{db_path}{suffix}")
        sidecar.unlink(missing_ok=True)


def import_resource(
    layout: WorkspaceLayout,
    *,
    display_name: str,
    content: bytes,
) -> ResourceInfo:
    """Import a whitelisted file into the workspace and register it.

    Content is stored under a generated UUIDv7 filename inside
    `resources/`; the client-supplied name is metadata only. Identical
    content (same SHA-256) is idempotent and returns the existing resource.
    The file is written to disk first and the database row is committed only
    after a successful write, so a failed write never leaves an orphan record.
    """

    display_name = _safe_display_name(display_name)
    if len(content) > _MAX_IMPORT_BYTES:
        _reject("import_too_large", rule="size_limit_exceeded")
    detected = _detect_mime(display_name, content)
    if detected is None:
        _reject("import_type_rejected", rule="mime_not_in_whitelist")
    content_hash = f"sha256:{hashlib.sha256(content).hexdigest()}"
    storage_key = f"resources/{_uuid7()}/{_uuid7()}"
    storage_path = layout.root / storage_key
    try:
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        storage_path.write_bytes(content)
    except OSError as error:
        raise WorkspaceError("import_failed", details={"rule": "storage_not_writable"}) from error
    created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        with _connect(layout.db_path) as conn:
            existing = conn.execute(
                "SELECT resource_id, version_no FROM resource_version WHERE content_hash=?",
                (content_hash,),
            ).fetchone()
            if existing is not None:
                resource_id, version_no = existing
                storage_path.unlink(missing_ok=True)
                return _resource_info(conn, str(resource_id), int(version_no))
            resource_id = _uuid7()
            version_id = _uuid7()
            conn.execute(
                "INSERT INTO resource(id, display_name, current_version_id, created_at) "
                "VALUES(?, ?, ?, ?)",
                (resource_id, display_name, version_id, created_at),
            )
            conn.execute(
                "INSERT INTO resource_version("
                "id, resource_id, version_no, content_hash, mime, byte_size, "
                "storage_key, created_at) VALUES(?, ?, 1, ?, ?, ?, ?, ?)",
                (
                    version_id,
                    resource_id,
                    content_hash,
                    detected,
                    len(content),
                    storage_key,
                    created_at,
                ),
            )
            conn.execute(
                "UPDATE resource SET current_version_id=? WHERE id=?",
                (version_id, resource_id),
            )
        return ResourceInfo(
            id=resource_id,
            display_name=display_name,
            mime=detected,
            byte_size=len(content),
            content_hash=content_hash,
            created_at=created_at,
        )
    except sqlite3.DatabaseError as error:
        storage_path.unlink(missing_ok=True)
        raise WorkspaceError("import_failed", details={"rule": "database_not_writable"}) from error


def list_resources(layout: WorkspaceLayout) -> list[ResourceInfo]:
    """List imported resource metadata without any file content."""

    try:
        with _connect(layout.db_path) as conn:
            rows = conn.execute(
                "SELECT r.id, r.display_name, v.mime, v.byte_size, v.content_hash, "
                "r.created_at FROM resource r "
                "JOIN resource_version v ON v.resource_id = r.id "
                "AND v.id = r.current_version_id ORDER BY r.created_at"
            ).fetchall()
            return [
                ResourceInfo(
                    id=str(row[0]),
                    display_name=str(row[1]),
                    mime=str(row[2]),
                    byte_size=int(row[3]),
                    content_hash=str(row[4]),
                    created_at=str(row[5]),
                )
                for row in rows
            ]
    except sqlite3.DatabaseError as error:
        raise WorkspaceError(
            "workspace_corrupt", details={"rule": "resources_not_readable"}
        ) from error


def _resource_info(conn: sqlite3.Connection, resource_id: str, version_no: int) -> ResourceInfo:
    row = conn.execute(
        "SELECT r.id, r.display_name, v.mime, v.byte_size, v.content_hash, r.created_at "
        "FROM resource r JOIN resource_version v ON v.resource_id = r.id "
        "WHERE r.id=? AND v.version_no=?",
        (resource_id, version_no),
    ).fetchone()
    if row is None:
        _reject("import_failed", rule="resource_missing")
    return ResourceInfo(
        id=str(row[0]),
        display_name=str(row[1]),
        mime=str(row[2]),
        byte_size=int(row[3]),
        content_hash=str(row[4]),
        created_at=str(row[5]),
    )


def parse_pdf_resource(layout: WorkspaceLayout, resource_id: str) -> int:
    """Extract page text from an imported PDF into resource_segment rows."""

    from pypdf import PdfReader

    try:
        with _connect(layout.db_path) as conn:
            row = conn.execute(
                "SELECT v.id, v.content_hash, v.storage_key FROM resource_version v "
                "WHERE v.resource_id=? AND v.id = "
                "(SELECT current_version_id FROM resource WHERE id=?)",
                (resource_id, resource_id),
            ).fetchone()
    except sqlite3.DatabaseError as error:
        raise WorkspaceError(
            "workspace_corrupt", details={"rule": "resource_not_readable"}
        ) from error
    if row is None:
        _reject("parse_failed", rule="resource_missing")
    version_id, content_hash, storage_key = str(row[0]), str(row[1]), str(row[2])
    if not _storage_key_within(layout, storage_key):
        _reject("parse_failed", rule="storage_key_unsafe")
    pdf_path = layout.root / storage_key
    try:
        reader = PdfReader(pdf_path, strict=True)
        segments: list[tuple[str, int, str, str, str]] = []
        for page_index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            text_hash = f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"
            segments.append((_uuid7(), page_index, text, text_hash, content_hash))
    except Exception as error:  # pypdf raises various errors on malformed PDFs
        raise WorkspaceError("parse_failed", details={"rule": "pdf_not_parseable"}) from error
    created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        with _connect(layout.db_path) as conn:
            conn.execute("DELETE FROM resource_segment WHERE resource_version_id=?", (version_id,))
            conn.executemany(
                "INSERT INTO resource_segment("
                "id, resource_version_id, page, text, text_hash, content_hash, created_at) "
                "VALUES(?, ?, ?, ?, ?, ?, ?)",
                [
                    (segment_id, version_id, page, text, text_hash, parsed_hash, created_at)
                    for segment_id, page, text, text_hash, parsed_hash in segments
                ],
            )
    except sqlite3.DatabaseError as error:
        raise WorkspaceError("parse_failed", details={"rule": "database_not_writable"}) from error
    return len(segments)


def _storage_key_within(layout: WorkspaceLayout, storage_key: str) -> bool:
    """Return True only for a relative key that resolves inside the workspace."""

    candidate = (layout.root / storage_key).resolve()
    root = layout.root.resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return not Path(storage_key).is_absolute()


def get_page_text(layout: WorkspaceLayout, resource_id: str, page: int) -> PageSegment:
    """Return parsed text for a page, rejecting drift or out-of-range pages."""

    try:
        with _connect(layout.db_path) as conn:
            row = conn.execute(
                "SELECT v.id FROM resource_version v "
                "WHERE v.resource_id=? AND v.id = "
                "(SELECT current_version_id FROM resource WHERE id=?)",
                (resource_id, resource_id),
            ).fetchone()
            if row is None:
                _reject("workspace_missing", rule="resource_missing")
            version_id = str(row[0])
            max_page = conn.execute(
                "SELECT MAX(page) FROM resource_segment WHERE resource_version_id=?",
                (version_id,),
            ).fetchone()[0]
            if max_page is None:
                _reject("parse_pending", rule="resource_not_parsed")
            segment_row = conn.execute(
                "SELECT page, text, text_hash, content_hash FROM resource_segment "
                "WHERE resource_version_id=? AND page=?",
                (version_id, page),
            ).fetchone()
    except sqlite3.DatabaseError as error:
        raise WorkspaceError(
            "workspace_corrupt", details={"rule": "resource_not_readable"}
        ) from error
    if segment_row is None:
        _reject("page_out_of_range", rule="page_not_in_range")
    segment = PageSegment(
        resource_version_id=version_id,
        page=int(segment_row[0]),
        text=str(segment_row[1]),
        text_hash=str(segment_row[2]),
    )
    _check_drift(layout, version_id, str(segment_row[3]))
    return segment


def _check_drift(layout: WorkspaceLayout, version_id: str, parsed_hash: str) -> None:
    # Compare the hash recorded at parse time against the resource_version's
    # current hash; a change means the source content drifted and any anchor
    # located on the old content must not be trusted.
    try:
        with _connect(layout.db_path) as conn:
            row = conn.execute(
                "SELECT content_hash FROM resource_version WHERE id=?",
                (version_id,),
            ).fetchone()
    except sqlite3.DatabaseError as error:
        raise WorkspaceError(
            "workspace_corrupt", details={"rule": "resource_not_readable"}
        ) from error
    if row is None or str(row[0]) != parsed_hash:
        _reject("source_changed", rule="content_hash_mismatch")


def register_anchor(
    layout: WorkspaceLayout,
    *,
    resource_id: str,
    page: int,
    payload: Mapping[str, Any],
) -> AnchorRef:
    """Register a page anchor for a resource (idempotent per resource+page).

    Validates the resource exists and returns the id actually stored, so an
    upsert on the same resource+page never returns a dangling reference.
    """

    created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        with _connect(layout.db_path) as conn:
            exists = conn.execute("SELECT 1 FROM resource WHERE id=?", (resource_id,)).fetchone()
            if exists is None:
                _reject("workspace_missing", rule="resource_missing")
            conn.execute(
                "INSERT INTO anchor(id, resource_id, page, payload, created_at) "
                "VALUES(?, ?, ?, ?, ?) "
                "ON CONFLICT(resource_id, page) DO UPDATE SET payload=excluded.payload",
                (
                    _uuid7(),
                    resource_id,
                    page,
                    json.dumps(dict(payload), ensure_ascii=False),
                    created_at,
                ),
            )
            stored = conn.execute(
                "SELECT id FROM anchor WHERE resource_id=? AND page=?",
                (resource_id, page),
            ).fetchone()
            if stored is None:
                _reject("import_failed", rule="anchor_missing")
            return AnchorRef(
                id=str(stored[0]),
                resource_id=resource_id,
                page=page,
                payload=dict(payload),
            )
    except sqlite3.DatabaseError as error:
        raise WorkspaceError("import_failed", details={"rule": "database_not_writable"}) from error


def list_anchors(layout: WorkspaceLayout, resource_id: str) -> list[AnchorRef]:
    """List registered anchors for a resource ordered by page."""

    try:
        with _connect(layout.db_path) as conn:
            exists = conn.execute("SELECT 1 FROM resource WHERE id=?", (resource_id,)).fetchone()
            if exists is None:
                _reject("workspace_missing", rule="resource_missing")
            rows = conn.execute(
                "SELECT id, resource_id, page, payload FROM anchor "
                "WHERE resource_id=? ORDER BY page",
                (resource_id,),
            ).fetchall()
            return [
                AnchorRef(
                    id=str(row[0]),
                    resource_id=str(row[1]),
                    page=int(row[2]),
                    payload=json.loads(str(row[3])),
                )
                for row in rows
            ]
    except sqlite3.DatabaseError as error:
        raise WorkspaceError(
            "workspace_corrupt", details={"rule": "anchors_not_readable"}
        ) from error


def get_resource_file_path(layout: WorkspaceLayout, resource_id: str) -> Path:
    """Resolve the controlled storage path for a resource's current version."""

    try:
        with _connect(layout.db_path) as conn:
            row = conn.execute(
                "SELECT v.storage_key FROM resource_version v "
                "WHERE v.resource_id=? AND v.id = "
                "(SELECT current_version_id FROM resource WHERE id=?)",
                (resource_id, resource_id),
            ).fetchone()
    except sqlite3.DatabaseError as error:
        raise WorkspaceError(
            "workspace_corrupt", details={"rule": "resource_not_readable"}
        ) from error
    if row is None:
        _reject("workspace_missing", rule="resource_missing")
    storage_key = str(row[0])
    if not _storage_key_within(layout, storage_key):
        _reject("file_not_found", rule="storage_key_unsafe")
    file_path = layout.root / storage_key
    if not file_path.is_file():
        _reject("file_not_found", rule="file_absent")
    return file_path


def get_resource_mime(layout: WorkspaceLayout, resource_id: str) -> str:
    """Return the mime type of a resource's current version."""

    try:
        with _connect(layout.db_path) as conn:
            row = conn.execute(
                "SELECT v.mime FROM resource_version v "
                "WHERE v.resource_id=? AND v.id = "
                "(SELECT current_version_id FROM resource WHERE id=?)",
                (resource_id, resource_id),
            ).fetchone()
    except sqlite3.DatabaseError as error:
        raise WorkspaceError(
            "workspace_corrupt", details={"rule": "resource_not_readable"}
        ) from error
    if row is None:
        _reject("workspace_missing", rule="resource_missing")
    return str(row[0])


def read_resource_text(layout: WorkspaceLayout, resource_id: str) -> str:
    """Return the current version's full text for AI draft generation.

    Markdown/TXT resources are read as raw UTF-8 text; PDF resources require a
    prior `parse_pdf_resource` and are returned as page texts joined in page
    order (drift-checked). Any other mime fails closed: the draft pipeline must
    not silently invent text for a source it cannot read.
    """

    mime = get_resource_mime(layout, resource_id)
    if mime.startswith("text/"):
        file_path = get_resource_file_path(layout, resource_id)
        try:
            return file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            _reject("parse_failed", rule="resource_not_decodable")
    if mime == "application/pdf":
        try:
            with _connect(layout.db_path) as conn:
                row = conn.execute(
                    "SELECT v.id FROM resource_version v "
                    "WHERE v.resource_id=? AND v.id = "
                    "(SELECT current_version_id FROM resource WHERE id=?)",
                    (resource_id, resource_id),
                ).fetchone()
                if row is None:
                    _reject("workspace_missing", rule="resource_missing")
                version_id = str(row[0])
                segment_rows = conn.execute(
                    "SELECT text, content_hash FROM resource_segment "
                    "WHERE resource_version_id=? ORDER BY page",
                    (version_id,),
                ).fetchall()
        except sqlite3.DatabaseError as error:
            raise WorkspaceError(
                "workspace_corrupt", details={"rule": "resource_not_readable"}
            ) from error
        if not segment_rows:
            _reject("parse_pending", rule="resource_not_parsed")
        # Drift-check against the segments' parse-time content hash (the same
        # wiring as `get_page_text`); comparing the version's own hash to
        # itself would make `source_changed` unreachable.
        _check_drift(layout, version_id, str(segment_rows[0][1]))
        return "\n\n".join(str(segment_row[0]) for segment_row in segment_rows)
    _reject("draft_unsupported_resource", rule="unsupported_mime", mime=mime)


def _safe_display_name(name: str) -> str:
    base = Path(name).name
    if not base or base in {".", ".."} or "/" in name or "\\" in name:
        _reject("import_type_rejected", rule="invalid_name")
    return base


def _detect_mime(display_name: str, content: bytes) -> str | None:
    suffix = Path(display_name).suffix.lower()
    if content.startswith(b"%PDF-"):
        return "application/pdf"
    if suffix in _TEXT_EXTENSIONS:
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            return None
        return _TEXT_EXTENSIONS[suffix]
    return None


def _uuid7() -> str:
    """Generate a UUIDv7 string (48-bit ms timestamp + version/variant bits)."""

    import uuid as _uuid

    now = int(time.time() * 1000)
    # Build a v7-compatible UUID: timestamp in top 48 bits.
    value = (now << 80) | (0x70 << 72) | (0x80 << 64) | _uuid.uuid4().int & ((1 << 64) - 1)
    return str(_uuid.UUID(int=value))


def _digest(payload: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    return f"sha256:{digest}"


def _ensure_search_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS {_SEARCH_TABLE} "
        "USING fts5(concept_id UNINDEXED, label, note)"
    )


def _rebuild_search_index(conn: sqlite3.Connection, graph: Mapping[str, Any]) -> None:
    _ensure_search_table(conn)
    conn.execute(f"DELETE FROM {_SEARCH_TABLE}")
    concepts = graph.get("concepts")
    if not isinstance(concepts, list):
        return
    rows: list[tuple[str, str, str]] = []
    for concept in concepts:
        if not isinstance(concept, dict):
            continue
        concept_id = str(concept.get("id", ""))
        label = str(concept.get("label", ""))
        annotations = concept.get("annotations")
        note = ""
        if isinstance(annotations, list):
            for annotation in annotations:
                if isinstance(annotation, dict) and annotation.get("kind") == "note":
                    note = str(annotation.get("value", ""))
                    break
        rows.append((concept_id, label, note))
    if rows:
        conn.executemany(
            f"INSERT INTO {_SEARCH_TABLE}(concept_id, label, note) VALUES(?, ?, ?)",
            rows,
        )


def _snippet(label: str, note: str, needle: str) -> str:
    """Return a bounded snippet centred on the first match, never full text."""

    combined = f"{label}：{note}" if note else label
    index = combined.casefold().find(needle)
    if index < 0:
        index = 0
    start = max(0, index - _SNIPPET_LENGTH // 2)
    snippet = combined[start : start + _SNIPPET_LENGTH]
    if start > 0:
        snippet = f"…{snippet}"
    if start + _SNIPPET_LENGTH < len(combined):
        snippet = f"{snippet}…"
    return snippet


def _validate_graph(graph: Mapping[str, Any]) -> None:
    try:
        validate_course_graph(graph)
    except GraphPatchError as error:
        raise WorkspaceError(
            "graph_invalid", details={"rule": error.code, **error.details}
        ) from error


_LOCK_DIMENSIONS = ("content", "relations", "position", "annotations")


def _try_load_saved_graph(layout: WorkspaceLayout) -> JsonObject | None:
    """Return the currently saved graph, or None when nothing was saved yet."""

    try:
        with _connect(layout.db_path) as conn:
            row = conn.execute("SELECT value FROM meta WHERE key=?", (_GRAPH_KEY,)).fetchone()
    except sqlite3.DatabaseError as error:
        raise WorkspaceError(
            "workspace_corrupt", details={"rule": "database_not_readable"}
        ) from error
    if row is None:
        return None
    try:
        parsed = json.loads(str(row[0]))
    except (TypeError, ValueError) as error:
        raise WorkspaceError(
            "workspace_corrupt", details={"rule": "course_graph_not_json"}
        ) from error
    if not isinstance(parsed, dict):
        _reject("workspace_corrupt", rule="course_graph_not_object")
    _validate_graph(parsed)
    return parsed


def _note_value(concept: Mapping[str, Any]) -> str:
    annotations = concept.get("annotations")
    if not isinstance(annotations, list):
        return ""
    for annotation in annotations:
        if isinstance(annotation, dict) and annotation.get("kind") == "note":
            return str(annotation.get("value", ""))
    return ""


def _build_diff_patch(current: JsonObject, incoming: Mapping[str, Any]) -> JsonObject:
    """Diff two graphs into a confirmed user GraphPatch of ordered operations."""

    cur_concepts = {str(c["id"]): c for c in current["concepts"]}
    inc_concepts = {str(c["id"]): c for c in incoming["concepts"]}
    cur_edges = {str(e["id"]): e for e in current["edges"]}
    inc_edges = {str(e["id"]): e for e in incoming["edges"]}
    operations: list[JsonObject] = []

    def _rev(concept_id: str) -> int:
        concept = cur_concepts.get(concept_id)
        return int(concept["revision_no"]) if concept is not None else 0

    # 1. delete edges whose endpoints both survive (others are cascaded).
    for edge_id in sorted(set(cur_edges) - set(inc_edges)):
        edge = cur_edges[edge_id]
        if (
            str(edge["source_concept_id"]) in inc_concepts
            and str(edge["target_concept_id"]) in inc_concepts
        ):
            operations.append(
                {
                    "op_id": _uuid7(),
                    "op": "delete_edge",
                    "target": {"type": "edge", "id": edge_id},
                }
            )

    # 2. delete concepts (cascades their remaining edges and layout).
    for concept_id in sorted(set(cur_concepts) - set(inc_concepts)):
        operations.append(
            {
                "op_id": _uuid7(),
                "op": "delete_concept",
                "target": {"type": "concept", "id": concept_id},
                "expected_updated_revision_no": _rev(concept_id),
            }
        )

    # 3. create concepts.
    for concept_id in sorted(set(inc_concepts) - set(cur_concepts)):
        concept = json.loads(json.dumps(inc_concepts[concept_id]))
        concept["revision_no"] = 0
        operations.append({"op_id": _uuid7(), "op": "create_concept", "concept": concept})

    # 4. create edges.
    for edge_id in sorted(set(inc_edges) - set(cur_edges)):
        edge = json.loads(json.dumps(inc_edges[edge_id]))
        edge["revision_no"] = 0
        operations.append(
            {
                "op_id": _uuid7(),
                "op": "create_edge",
                "expected_source_revision_no": _rev(str(edge["source_concept_id"])),
                "expected_target_revision_no": _rev(str(edge["target_concept_id"])),
                "edge": edge,
            }
        )

    # 5. update concept content, note, locks and review fields.
    for concept_id in sorted(set(cur_concepts) & set(inc_concepts)):
        cur = cur_concepts[concept_id]
        inc = inc_concepts[concept_id]
        revision = _rev(concept_id)
        target = {"type": "concept", "id": concept_id}
        changes: JsonObject = {}
        if cur.get("label") != inc.get("label"):
            changes["label"] = inc["label"]
        for field in ("review_state", "confidence", "evidence_ids"):
            if cur.get(field) != inc.get(field):
                changes[field] = inc.get(field)
        if changes:
            operations.append(
                {
                    "op_id": _uuid7(),
                    "op": "update_concept",
                    "target": target,
                    "expected_updated_revision_no": revision,
                    "evidence_ids": [],
                    "changes": changes,
                }
            )
        if _note_value(cur) != _note_value(inc):
            operations.append(
                {
                    "op_id": _uuid7(),
                    "op": "upsert_annotation",
                    "target": target,
                    "expected_updated_revision_no": revision,
                    "annotation": {"kind": "note", "value": _note_value(inc)},
                }
            )
        for dimension in _LOCK_DIMENSIONS:
            if cur["locks"][dimension] != inc["locks"][dimension]:
                operations.append(
                    {
                        "op_id": _uuid7(),
                        "op": "set_lock",
                        "target": target,
                        "expected_updated_revision_no": revision,
                        "dimension": dimension,
                        "value": inc["locks"][dimension],
                    }
                )

    # 6. move layout items (including newly created concepts' layout).
    cur_layout = {(str(li["view_id"]), str(li["concept_id"])): li for li in current["layout_items"]}
    inc_layout = {
        (str(li["view_id"]), str(li["concept_id"])): li for li in incoming["layout_items"]
    }
    for key in sorted(set(inc_layout)):
        inc_li = inc_layout[key]
        concept_id = key[1]
        if concept_id not in inc_concepts:
            continue
        cur_li = cur_layout.get(key)
        if cur_li is None or (
            cur_li.get("x") != inc_li.get("x")
            or cur_li.get("y") != inc_li.get("y")
            or cur_li.get("pinned") != inc_li.get("pinned")
        ):
            operations.append(
                {
                    "op_id": _uuid7(),
                    "op": "set_layout_item",
                    "target": {"type": "concept", "id": concept_id},
                    "expected_updated_revision_no": _rev(concept_id),
                    "layout_item": json.loads(json.dumps(inc_li)),
                }
            )

    return {
        "schema_version": 1,
        "patch_id": _uuid7(),
        "workspace_id": incoming["workspace_id"],
        "course_id": incoming["course_id"],
        "base_revision_no": current["revision_no"],
        "actor": dict(_LOCAL_ACTOR),
        "reason": "自动保存",
        "requires_confirmation": True,
        "confirmed": True,
        "operations": operations,
    }


def _reject(code: str, *, rule: str, **safe_details: Any) -> Never:
    raise WorkspaceError(code, details={"rule": rule, **safe_details})
