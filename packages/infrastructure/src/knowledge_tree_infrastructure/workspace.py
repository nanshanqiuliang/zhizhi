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
SUPPORTED_SCHEMA_VERSION = 1
_GRAPH_KEY = "course_graph"


class WorkspaceError(ValueError):
    """A stable, content-safe workspace rejection."""

    def __init__(self, code: str, *, details: Mapping[str, Any]) -> None:
        self.code = code
        self.details = dict(details)
        super().__init__(f"{code}: workspace rejected")


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
    """Migrate an empty database to schema v1; reject unknown/future versions."""

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
            conn.execute(f"PRAGMA user_version = {SUPPORTED_SCHEMA_VERSION}")
    except sqlite3.DatabaseError as error:
        raise WorkspaceError(
            "migration_failed", details={"rule": "database_not_readable"}
        ) from error


def save_course_graph(layout: WorkspaceLayout, graph: Mapping[str, Any]) -> None:
    """Validate and persist a CourseGraph inside one atomic transaction."""

    _validate_graph(graph)
    payload = json.dumps(graph, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    try:
        with _connect(layout.db_path) as conn:
            conn.execute(
                "INSERT INTO meta(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (_GRAPH_KEY, payload),
            )
    except sqlite3.DatabaseError as error:
        raise WorkspaceError("save_failed", details={"rule": "database_not_writable"}) from error


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


def _digest(payload: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    return f"sha256:{digest}"


def _validate_graph(graph: Mapping[str, Any]) -> None:
    try:
        validate_course_graph(graph)
    except GraphPatchError as error:
        raise WorkspaceError(
            "graph_invalid", details={"rule": error.code, **error.details}
        ) from error


def _reject(code: str, *, rule: str, **safe_details: Any) -> Never:
    raise WorkspaceError(code, details={"rule": rule, **safe_details})
