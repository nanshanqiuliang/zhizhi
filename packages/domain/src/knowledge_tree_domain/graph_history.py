"""Pure, immutable GraphPatch replay and LIFO undo/redo primitives."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Never

from .graph_patch import GraphPatchError, preview_graph_patch, validate_course_graph

JsonObject = dict[str, Any]
_COLLECTIONS = ("concepts", "edges", "layout_items")


class GraphHistoryError(ValueError):
    """A stable, content-safe history rejection."""

    def __init__(self, code: str, *, details: Mapping[str, Any]) -> None:
        self.code = code
        self.details = dict(details)
        super().__init__(f"{code}: graph history rejected")


@dataclass(frozen=True, slots=True)
class EntityDelta:
    """Canonical before/after values for one changed graph entity."""

    collection: str
    entity_key: str
    before_json: str | None
    after_json: str | None
    before_index: int | None
    after_index: int | None


@dataclass(frozen=True, slots=True)
class GraphChangeRecord:
    """A content-bound internal change record, not an external write DTO."""

    change_id: str
    before_revision_no: int
    after_revision_no: int
    before_semantic_hash: str
    after_semantic_hash: str
    deltas: tuple[EntityDelta, ...]
    record_digest: str


@dataclass(frozen=True, slots=True)
class GraphHistory:
    """An immutable in-memory graph snapshot plus LIFO history records."""

    _snapshot_json: str
    undo_records: tuple[GraphChangeRecord, ...] = ()
    redo_records: tuple[GraphChangeRecord, ...] = ()

    @classmethod
    def start(cls, graph: Mapping[str, Any]) -> GraphHistory:
        """Start an isolated history without taking ownership of caller data."""

        _validate_graph(graph)
        return cls(_snapshot_json=_canonical_json(dict(graph)))

    @classmethod
    def replay(
        cls,
        initial_graph: Mapping[str, Any],
        records: Iterable[GraphChangeRecord],
    ) -> GraphHistory:
        """Replay a complete ordered record sequence from its initial graph."""

        frozen_records = tuple(records)
        _reject_duplicate_change_ids(frozen_records)
        history = cls.start(initial_graph)
        for record in frozen_records:
            _validate_record(record)
            current = history.snapshot
            if current.get("revision_no") != record.before_revision_no:
                _reject(
                    "history_conflict",
                    rule="replay_revision_mismatch",
                    change_id=record.change_id,
                    expected_revision_no=record.before_revision_no,
                    actual_revision_no=current.get("revision_no"),
                )
            candidate = _apply_record(current, record, forward=True)
            if candidate["revision_no"] != record.after_revision_no:
                _reject(
                    "validation_failed",
                    rule="history_record_revision_invalid",
                    change_id=record.change_id,
                )
            history = cls(
                _snapshot_json=_canonical_json(candidate),
                undo_records=(*history.undo_records, record),
            )
        return history

    @property
    def snapshot(self) -> JsonObject:
        """Return an isolated copy of the current graph snapshot."""

        value: JsonObject = json.loads(self._snapshot_json)
        return value

    def apply_patch(
        self,
        patch: Mapping[str, Any],
        *,
        trusted_actor: Mapping[str, str],
    ) -> GraphHistory:
        """Apply a confirmed user GraphPatch and derive its trusted delta record."""

        actor = patch.get("actor")
        if not isinstance(actor, Mapping) or actor.get("type") != "user":
            _reject("permission_denied", rule="history_user_patch_required")

        current = self.snapshot
        preview = preview_graph_patch(current, patch, trusted_actor=trusted_actor)
        if preview.status != "ready_to_apply":
            _reject("permission_denied", rule="history_confirmed_patch_required")

        change_id = patch.get("patch_id")
        if not isinstance(change_id, str):
            _reject("validation_failed", rule="history_change_id_missing")
        if change_id in {record.change_id for record in (*self.undo_records, *self.redo_records)}:
            _reject(
                "validation_failed",
                rule="duplicate_change_id",
                change_id=change_id,
            )

        record = _build_record(change_id, current, preview.snapshot)
        return GraphHistory(
            _snapshot_json=_canonical_json(preview.snapshot),
            undo_records=(*self.undo_records, record),
            redo_records=(),
        )

    def undo(self) -> GraphHistory:
        """Undo the most recent applied record while keeping revisions monotonic."""

        if not self.undo_records:
            _reject("history_empty", rule="undo_stack_empty")
        record = self.undo_records[-1]
        _validate_record(record)
        candidate = _apply_record(self.snapshot, record, forward=False)
        return GraphHistory(
            _snapshot_json=_canonical_json(candidate),
            undo_records=self.undo_records[:-1],
            redo_records=(*self.redo_records, record),
        )

    def redo(self) -> GraphHistory:
        """Redo the most recently undone record in strict LIFO order."""

        if not self.redo_records:
            _reject("history_empty", rule="redo_stack_empty")
        record = self.redo_records[-1]
        _validate_record(record)
        candidate = _apply_record(self.snapshot, record, forward=True)
        return GraphHistory(
            _snapshot_json=_canonical_json(candidate),
            undo_records=(*self.undo_records, record),
            redo_records=self.redo_records[:-1],
        )


def semantic_graph_hash(graph: Mapping[str, Any]) -> str:
    """Hash graph business semantics while excluding all revision counters."""

    normalized = _semantic_value(dict(graph))
    digest = hashlib.sha256(_canonical_json(normalized).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _semantic_value(value: Any, *, parent_key: str | None = None) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _semantic_value(item, parent_key=str(key))
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if key != "revision_no"
        }
    if isinstance(value, list):
        items = [_semantic_value(item, parent_key=parent_key) for item in value]
        if parent_key == "concepts":
            return sorted(items, key=lambda item: str(item["id"]))
        if parent_key == "edges":
            return sorted(items, key=lambda item: str(item["id"]))
        if parent_key == "layout_items":
            return sorted(
                items,
                key=lambda item: (str(item["view_id"]), str(item["concept_id"])),
            )
        if parent_key == "annotations":
            return sorted(items, key=lambda item: str(item["kind"]))
        if parent_key == "evidence_ids":
            return sorted(items, key=str)
        return items
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _reject(code: str, *, rule: str, **safe_details: Any) -> Never:
    raise GraphHistoryError(code, details={"rule": rule, **safe_details})


def _validate_graph(graph: Mapping[str, Any]) -> None:
    try:
        validate_course_graph(graph)
    except GraphPatchError as error:
        raise GraphHistoryError(error.code, details=error.details) from error


def _entity_key(collection: str, entity: Mapping[str, Any]) -> str:
    if collection in {"concepts", "edges"}:
        return str(entity["id"])
    if collection == "layout_items":
        return f"{entity['view_id']}:{entity['concept_id']}"
    _reject("validation_failed", rule="history_collection_unsupported")


def _collection_index(
    graph: Mapping[str, Any], collection: str
) -> dict[str, tuple[int, JsonObject]]:
    items = graph.get(collection)
    if not isinstance(items, list):
        _reject("validation_failed", rule="history_graph_collection_invalid")
    return {
        _entity_key(collection, item): (index, item)
        for index, item in enumerate(items)
        if isinstance(item, dict)
    }


def _build_deltas(before: Mapping[str, Any], after: Mapping[str, Any]) -> tuple[EntityDelta, ...]:
    deltas: list[EntityDelta] = []
    for collection in _COLLECTIONS:
        before_index = _collection_index(before, collection)
        after_index = _collection_index(after, collection)
        for entity_key in sorted(set(before_index) | set(after_index)):
            previous = before_index.get(entity_key)
            following = after_index.get(entity_key)
            before_json = _canonical_json(previous[1]) if previous is not None else None
            after_json = _canonical_json(following[1]) if following is not None else None
            if before_json == after_json:
                continue
            deltas.append(
                EntityDelta(
                    collection=collection,
                    entity_key=entity_key,
                    before_json=before_json,
                    after_json=after_json,
                    before_index=previous[0] if previous is not None else None,
                    after_index=following[0] if following is not None else None,
                )
            )
    return tuple(deltas)


def _record_payload(
    *,
    change_id: str,
    before_revision_no: int,
    after_revision_no: int,
    before_semantic_hash: str,
    after_semantic_hash: str,
    deltas: tuple[EntityDelta, ...],
) -> JsonObject:
    return {
        "change_id": change_id,
        "before_revision_no": before_revision_no,
        "after_revision_no": after_revision_no,
        "before_semantic_hash": before_semantic_hash,
        "after_semantic_hash": after_semantic_hash,
        "deltas": [
            {
                "collection": delta.collection,
                "entity_key": delta.entity_key,
                "before_json": delta.before_json,
                "after_json": delta.after_json,
                "before_index": delta.before_index,
                "after_index": delta.after_index,
            }
            for delta in deltas
        ],
    }


def _digest_record_payload(payload: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _build_record(
    change_id: str,
    before: Mapping[str, Any],
    after: Mapping[str, Any],
) -> GraphChangeRecord:
    before_revision = before.get("revision_no")
    after_revision = after.get("revision_no")
    if not isinstance(before_revision, int) or not isinstance(after_revision, int):
        _reject("validation_failed", rule="history_graph_revision_invalid")
    deltas = _build_deltas(before, after)
    if not deltas:
        _reject("validation_failed", rule="history_change_empty", change_id=change_id)
    payload = _record_payload(
        change_id=change_id,
        before_revision_no=before_revision,
        after_revision_no=after_revision,
        before_semantic_hash=semantic_graph_hash(before),
        after_semantic_hash=semantic_graph_hash(after),
        deltas=deltas,
    )
    return GraphChangeRecord(
        change_id=change_id,
        before_revision_no=before_revision,
        after_revision_no=after_revision,
        before_semantic_hash=str(payload["before_semantic_hash"]),
        after_semantic_hash=str(payload["after_semantic_hash"]),
        deltas=deltas,
        record_digest=_digest_record_payload(payload),
    )


def _validate_record(record: GraphChangeRecord) -> None:
    payload = _record_payload(
        change_id=record.change_id,
        before_revision_no=record.before_revision_no,
        after_revision_no=record.after_revision_no,
        before_semantic_hash=record.before_semantic_hash,
        after_semantic_hash=record.after_semantic_hash,
        deltas=record.deltas,
    )
    if record.record_digest != _digest_record_payload(payload):
        _reject(
            "validation_failed",
            rule="history_record_digest_mismatch",
            change_id=record.change_id,
        )
    if record.after_revision_no != record.before_revision_no + 1:
        _reject(
            "validation_failed",
            rule="history_record_revision_invalid",
            change_id=record.change_id,
        )
    if not record.deltas:
        _reject(
            "validation_failed",
            rule="history_record_empty",
            change_id=record.change_id,
        )
    seen: set[tuple[str, str]] = set()
    for delta in record.deltas:
        key = (delta.collection, delta.entity_key)
        if delta.collection not in _COLLECTIONS or key in seen:
            _reject(
                "validation_failed",
                rule="history_delta_invalid",
                change_id=record.change_id,
            )
        seen.add(key)


def _reject_duplicate_change_ids(records: tuple[GraphChangeRecord, ...]) -> None:
    seen: set[str] = set()
    for record in records:
        if record.change_id in seen:
            _reject(
                "validation_failed",
                rule="duplicate_change_id",
                change_id=record.change_id,
            )
        seen.add(record.change_id)


def _same_entity_semantics(actual: Mapping[str, Any], expected_json: str) -> bool:
    expected: JsonObject = json.loads(expected_json)
    return bool(_semantic_value(actual) == _semantic_value(expected))


def _apply_delta(
    graph: JsonObject,
    delta: EntityDelta,
    *,
    forward: bool,
    next_revision: int,
    change_id: str,
) -> None:
    expected_json = delta.before_json if forward else delta.after_json
    replacement_json = delta.after_json if forward else delta.before_json
    replacement_index = delta.after_index if forward else delta.before_index
    items: list[JsonObject] = graph[delta.collection]
    actual_index = next(
        (
            index
            for index, item in enumerate(items)
            if _entity_key(delta.collection, item) == delta.entity_key
        ),
        None,
    )
    if expected_json is None:
        if actual_index is not None:
            _reject(
                "history_conflict",
                rule="history_entity_unexpected",
                change_id=change_id,
                entity_key=delta.entity_key,
            )
    else:
        if actual_index is None or not _same_entity_semantics(items[actual_index], expected_json):
            _reject(
                "history_conflict",
                rule="history_entity_mismatch",
                change_id=change_id,
                entity_key=delta.entity_key,
            )

    if actual_index is not None:
        items.pop(actual_index)
    if replacement_json is not None:
        replacement: JsonObject = json.loads(replacement_json)
        replacement["revision_no"] = next_revision
        index = len(items) if replacement_index is None else min(replacement_index, len(items))
        items.insert(index, replacement)


def _apply_record(
    graph: Mapping[str, Any],
    record: GraphChangeRecord,
    *,
    forward: bool,
) -> JsonObject:
    current_hash = semantic_graph_hash(graph)
    expected_hash = record.before_semantic_hash if forward else record.after_semantic_hash
    if current_hash != expected_hash:
        _reject(
            "history_conflict",
            rule="history_semantic_hash_mismatch",
            change_id=record.change_id,
            expected_semantic_hash=expected_hash,
            actual_semantic_hash=current_hash,
        )
    candidate: JsonObject = json.loads(_canonical_json(dict(graph)))
    revision = candidate.get("revision_no")
    if not isinstance(revision, int):
        _reject("validation_failed", rule="history_graph_revision_invalid")
    next_revision = revision + 1
    deltas = record.deltas if forward else tuple(reversed(record.deltas))
    for delta in deltas:
        _apply_delta(
            candidate,
            delta,
            forward=forward,
            next_revision=next_revision,
            change_id=record.change_id,
        )
    candidate["revision_no"] = next_revision
    actual_hash = semantic_graph_hash(candidate)
    expected_result_hash = record.after_semantic_hash if forward else record.before_semantic_hash
    if actual_hash != expected_result_hash:
        _reject(
            "validation_failed",
            rule="history_record_result_mismatch",
            change_id=record.change_id,
        )
    _validate_graph(candidate)
    return candidate


__all__ = [
    "EntityDelta",
    "GraphChangeRecord",
    "GraphHistory",
    "GraphHistoryError",
    "semantic_graph_hash",
]
