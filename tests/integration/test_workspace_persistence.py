"""Red-light persistence/restart tests for the local SQLite workspace prototype.

These tests target the WORK-2026-013 public API
(`knowledge_tree_infrastructure.workspace`) which does not exist yet, so the
collection phase is expected to fail with ImportError until the adapter is
implemented.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from knowledge_tree_domain import GraphHistory, GraphHistoryError
from knowledge_tree_infrastructure.workspace import (
    WorkspaceError,
    WorkspaceLayout,
    backup_workspace,
    create_workspace,
    export_course_graph,
    load_course_graph,
    load_history_records,
    migrate,
    purge_workspace,
    resolve_workspace,
    restore_backup,
    save_course_graph,
    save_history_records,
)

from tests.contract.test_graph_contracts import COURSE_ID, WORKSPACE_ID, valid_graph, valid_patch

JsonObject = dict[str, Any]
TRUSTED_USER = {"type": "user", "id": "local-user"}


def confirmed_patch() -> JsonObject:
    patch = valid_patch()
    patch["confirmed"] = True
    return patch


def history_with_one_record() -> tuple[JsonObject, JsonObject]:
    """Return (initial_graph, record_payload) from a confirmed patch replay."""

    graph = valid_graph()
    history = GraphHistory.start(graph).apply_patch(
        confirmed_patch(), trusted_actor=TRUSTED_USER
    )
    record = history.undo_records[-1]
    return graph, record


# TC-PERS-001: 目录创建/复用/校验
def test_create_workspace_layout(tmp_path: Path) -> None:
    layout = create_workspace(tmp_path / "ws")
    assert isinstance(layout, WorkspaceLayout)
    assert layout.root == (tmp_path / "ws")
    assert layout.root.is_dir()
    assert layout.db_path.parent == layout.root
    assert layout.backups_dir.is_dir()
    assert layout.exports_dir.is_dir()


def test_create_workspace_reuse_existing(tmp_path: Path) -> None:
    first = create_workspace(tmp_path / "ws")
    second = create_workspace(tmp_path / "ws")
    assert first.root == second.root == (tmp_path / "ws")


def test_resolve_workspace_missing(tmp_path: Path) -> None:
    with pytest.raises(WorkspaceError) as excinfo:
        resolve_workspace(tmp_path / "absent")
    assert excinfo.value.code == "workspace_missing"


def test_resolve_workspace_incomplete(tmp_path: Path) -> None:
    layout = create_workspace(tmp_path / "ws")
    layout.db_path.unlink(missing_ok=True)
    with pytest.raises(WorkspaceError) as excinfo:
        resolve_workspace(tmp_path / "ws")
    assert excinfo.value.code == "workspace_missing"


# TC-PERS-002: save → close → reopen 重启存活
def test_save_and_reopen_restores_semantics(tmp_path: Path) -> None:
    layout = create_workspace(tmp_path / "ws")
    migrate(layout.db_path)
    graph = valid_graph()
    save_course_graph(layout, graph)

    reopened = load_course_graph(layout)
    assert reopened["workspace_id"] == WORKSPACE_ID
    assert reopened["course_id"] == COURSE_ID
    assert reopened["revision_no"] == graph["revision_no"]
    assert reopened["concepts"] == graph["concepts"]


def test_reload_detects_revision_change(tmp_path: Path) -> None:
    layout = create_workspace(tmp_path / "ws")
    migrate(layout.db_path)
    graph = valid_graph()
    save_course_graph(layout, graph)

    changed = dict(graph)
    changed["revision_no"] = 3
    save_course_graph(layout, changed)

    reopened = load_course_graph(layout)
    assert reopened["revision_no"] == 3


# TC-PERS-003: migration v1 建库/重复/乱序/回滚
def test_migrate_creates_v1(tmp_path: Path) -> None:
    db_path = tmp_path / "ws.db"
    migrate(db_path)
    assert db_path.exists()


def test_migrate_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "ws.db"
    migrate(db_path)
    migrate(db_path)
    assert db_path.exists()


def test_migrate_rejects_unknown_version(tmp_path: Path) -> None:
    import sqlite3

    db_path = tmp_path / "ws.db"
    migrate(db_path)
    # Simulate a future/unknown schema version, then require explicit failure.
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA user_version = 99")
    with pytest.raises(WorkspaceError) as excinfo:
        migrate(db_path)
    assert excinfo.value.code == "migration_conflict"


def test_migrate_rollback_leaves_no_partial_db(tmp_path: Path) -> None:
    # Corrupt the db so migration DDL fails inside a transaction; the file must
    # not be left half-initialized.
    db_path = tmp_path / "ws.db"
    db_path.write_bytes(b"not a sqlite file")
    with pytest.raises(WorkspaceError):
        migrate(db_path)


# TC-PERS-004: backup/export/delete
def test_backup_and_restore_round_trip(tmp_path: Path) -> None:
    layout = create_workspace(tmp_path / "ws")
    migrate(layout.db_path)
    save_course_graph(layout, valid_graph())

    backup_path = backup_workspace(layout)
    assert backup_path.exists()
    checksum_file = backup_path.with_suffix(backup_path.suffix + ".sha256")
    assert checksum_file.exists()

    changed = dict(valid_graph())
    changed["revision_no"] = 9
    save_course_graph(layout, changed)

    restore_backup(layout, backup_path)
    restored = load_course_graph(layout)
    assert restored["revision_no"] == 0


def test_export_produces_valid_json(tmp_path: Path) -> None:
    layout = create_workspace(tmp_path / "ws")
    migrate(layout.db_path)
    save_course_graph(layout, valid_graph())

    out_path = tmp_path / "export.json"
    export_course_graph(layout, out_path)
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["workspace_id"] == WORKSPACE_ID
    assert payload["course_id"] == COURSE_ID


def test_purge_removes_data_and_writes_manifest(tmp_path: Path) -> None:
    layout = create_workspace(tmp_path / "ws")
    migrate(layout.db_path)
    save_course_graph(layout, valid_graph())
    backup_workspace(layout)

    manifest_path = purge_workspace(layout)
    assert manifest_path.exists()
    assert not layout.db_path.exists()
    assert not layout.backups_dir.exists() or not any(layout.backups_dir.iterdir())
    assert not layout.exports_dir.exists() or not any(layout.exports_dir.iterdir())


# TC-PERS-005: 故障注入（截断/垃圾字节/中断写入/重复 replay）
def test_load_truncated_db_fails_closed(tmp_path: Path) -> None:
    layout = create_workspace(tmp_path / "ws")
    migrate(layout.db_path)
    save_course_graph(layout, valid_graph())

    raw = layout.db_path.read_bytes()
    layout.db_path.write_bytes(raw[: len(raw) // 2])

    with pytest.raises(WorkspaceError) as excinfo:
        load_course_graph(layout)
    assert excinfo.value.code == "workspace_corrupt"


def test_load_garbage_db_fails_closed(tmp_path: Path) -> None:
    layout = create_workspace(tmp_path / "ws")
    layout.db_path.write_bytes(b"garbage-not-a-sqlite-database" * 32)
    with pytest.raises(WorkspaceError) as excinfo:
        load_course_graph(layout)
    assert excinfo.value.code == "workspace_corrupt"


def test_save_invalid_graph_fails_closed(tmp_path: Path) -> None:
    layout = create_workspace(tmp_path / "ws")
    migrate(layout.db_path)
    save_course_graph(layout, valid_graph())

    invalid = dict(valid_graph())
    invalid["concepts"] = [{"id": "not-valid"}]

    with pytest.raises(WorkspaceError):
        save_course_graph(layout, invalid)

    reopened = load_course_graph(layout)
    assert reopened["revision_no"] == 0


def test_duplicate_history_replay_fails_closed(tmp_path: Path) -> None:
    layout = create_workspace(tmp_path / "ws")
    migrate(layout.db_path)
    graph, record = history_with_one_record()

    save_course_graph(layout, graph)
    save_history_records(layout, [record, record])  # duplicate change_id

    records = load_history_records(layout)
    assert len(records) == 2
    with pytest.raises(GraphHistoryError) as excinfo:
        GraphHistory.replay(graph, records)
    assert excinfo.value.code == "validation_failed"
