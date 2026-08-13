"""Red-light unit tests for GraphChangeRecord JSON round-trip persistence.

The serializer lives in `knowledge_tree_infrastructure.workspace` (WORK-2026-013)
and does not exist yet, so collection is expected to fail with ImportError.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from knowledge_tree_domain import GraphHistory
from knowledge_tree_infrastructure.workspace import (
    WorkspaceError,
    record_from_json,
    record_to_json,
)

from tests.contract.test_graph_contracts import valid_graph, valid_patch

JsonObject = dict[str, Any]
TRUSTED_USER = {"type": "user", "id": "local-user"}


def confirmed_patch() -> JsonObject:
    patch = valid_patch()
    patch["confirmed"] = True
    return patch


def one_record() -> Any:
    history = GraphHistory.start(valid_graph()).apply_patch(
        confirmed_patch(), trusted_actor=TRUSTED_USER
    )
    return history.undo_records[-1]


# TC-PERS-006: history record JSON 往返
def test_record_json_round_trip_preserves_fields() -> None:
    record = one_record()
    payload = record_to_json(record)
    parsed = json.loads(payload)
    assert parsed["change_id"] == record.change_id
    assert parsed["before_revision_no"] == record.before_revision_no
    assert parsed["after_revision_no"] == record.after_revision_no
    assert parsed["before_semantic_hash"] == record.before_semantic_hash
    assert parsed["after_semantic_hash"] == record.after_semantic_hash
    assert parsed["record_digest"] == record.record_digest

    restored = record_from_json(payload)
    assert restored == record


def test_record_json_round_trip_replay_equivalent() -> None:
    record = one_record()
    restored = record_from_json(record_to_json(record))
    assert restored.change_id == record.change_id
    assert restored.deltas == record.deltas
    assert restored.record_digest == record.record_digest


def test_record_from_json_rejects_tampered_digest() -> None:
    payload = record_to_json(one_record())
    parsed = json.loads(payload)
    parsed["after_revision_no"] = parsed["after_revision_no"] + 1
    with pytest.raises(WorkspaceError) as excinfo:
        record_from_json(json.dumps(parsed))
    assert excinfo.value.code == "record_tampered"


def test_record_from_json_rejects_malformed_payload() -> None:
    with pytest.raises(WorkspaceError) as excinfo:
        record_from_json("{not json")
    assert excinfo.value.code == "record_invalid"
