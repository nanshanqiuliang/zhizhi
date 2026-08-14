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
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Never

from knowledge_tree_domain import (
    EntityDelta,
    GraphChangeRecord,
    GraphPatchError,
    validate_course_graph,
)

JsonObject = dict[str, Any]
SUPPORTED_SCHEMA_VERSION = 2
_GRAPH_KEY = "course_graph"
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
class SearchResult:
    """A single concept match with a content-safe label and snippet."""

    id: str
    label: str
    snippet: str


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
    """Migrate a database to schema v2; reject unknown/future versions."""

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
            conn.execute(f"PRAGMA user_version = {SUPPORTED_SCHEMA_VERSION}")
    except sqlite3.DatabaseError as error:
        raise WorkspaceError(
            "migration_failed", details={"rule": "database_not_readable"}
        ) from error


def save_course_graph(layout: WorkspaceLayout, graph: Mapping[str, Any]) -> None:
    """Validate and persist a CourseGraph, then rebuild the search index."""

    _validate_graph(graph)
    payload = json.dumps(graph, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    try:
        with _connect(layout.db_path) as conn:
            conn.execute(
                "INSERT INTO meta(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (_GRAPH_KEY, payload),
            )
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


def backup_workspace(layout: WorkspaceLayout) -> Path:
    """Create a consistent online backup plus a checksum sidecar file."""

    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
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
    """Restore the database from a checksummed backup file."""

    backup_path = Path(backup_path)
    checksum_file = backup_path.with_suffix(backup_path.suffix + ".sha256")
    if checksum_file.is_file():
        expected = checksum_file.read_text(encoding="utf-8").strip()
        actual = hashlib.sha256(backup_path.read_bytes()).hexdigest()
        if expected != actual:
            _reject("backup_checksum_mismatch", rule="restore_rejected")
    try:
        _remove_wal_sidecars(layout.db_path)
        shutil.copyfile(backup_path, layout.db_path)
    except OSError as error:
        raise WorkspaceError("restore_failed", details={"rule": "backup_not_readable"}) from error


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
    mime: str | None,
) -> ResourceInfo:
    """Import a whitelisted file into the workspace and register it.

    Content is stored under a generated UUIDv7 filename inside
    `resources/`; the client-supplied name is metadata only. Identical
    content (same SHA-256) is idempotent and returns the existing resource.
    """

    display_name = _safe_display_name(display_name)
    if len(content) > _MAX_IMPORT_BYTES:
        _reject("import_too_large", rule="size_limit_exceeded")
    detected = _detect_mime(display_name, content)
    if detected is None:
        _reject("import_type_rejected", rule="mime_not_in_whitelist")
    content_hash = f"sha256:{hashlib.sha256(content).hexdigest()}"
    storage_key = f"resources/{_uuid7()}/{_uuid7()}"
    created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        with _connect(layout.db_path) as conn:
            existing = conn.execute(
                "SELECT resource_id, version_no, content_hash, mime, byte_size, created_at "
                "FROM resource_version WHERE content_hash=?",
                (content_hash,),
            ).fetchone()
            if existing is not None:
                resource_id, version_no, *_ = existing
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
        storage_path = layout.root / storage_key
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        storage_path.write_bytes(content)
        return ResourceInfo(
            id=resource_id,
            display_name=display_name,
            mime=detected,
            byte_size=len(content),
            content_hash=content_hash,
            created_at=created_at,
        )
    except sqlite3.DatabaseError as error:
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


def _reject(code: str, *, rule: str, **safe_details: Any) -> Never:
    raise WorkspaceError(code, details={"rule": rule, **safe_details})
