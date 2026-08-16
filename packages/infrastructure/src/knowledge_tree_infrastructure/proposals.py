"""Pending external-proposal store (WORK-2026-050).

External AI clients (the MCP `propose_patch` tool) queue GraphPatch proposals
here as plain JSON files under `<workspace>/proposals/`. The store never
touches the graph database: settling a proposal to ``accepted`` only records
the outcome of an in-app human confirmation that itself went through the
protected commit gate (`apply_graph_patch`). Files are the cross-process
channel between the MCP server process and the sidecar API process.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Never

from knowledge_tree_domain.ai_draft import uuid7

from knowledge_tree_infrastructure.workspace import WorkspaceError, WorkspaceLayout

PROPOSAL_SCHEMA_VERSION = 1
_MAX_NOTE_CHARS = 500
_SETTLED_STATUSES = frozenset({"accepted", "rejected"})
_PROPOSAL_ID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

JsonObject = dict[str, Any]


def _reject(code: str, *, rule: str, **details: Any) -> Never:
    raise WorkspaceError(code, details={"rule": rule, **details})


def _now_iso() -> str:
    # Millisecond precision keeps same-second creations orderable (listing is
    # oldest-first) without giving up readability.
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _proposal_path(layout: WorkspaceLayout, proposal_id: str) -> Path:
    # proposal_id arrives from URL paths / MCP arguments: fail closed on
    # anything that is not a bare lowercase UUID before it reaches the path.
    if not isinstance(proposal_id, str) or not _PROPOSAL_ID_PATTERN.match(proposal_id):
        _reject("proposal_invalid", rule="proposal_id_malformed")
    return layout.root / "proposals" / f"{proposal_id}.json"


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    os.replace(tmp, path)


def _load_json(path: Path) -> JsonObject:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        _reject("proposal_invalid", rule="payload_unreadable", detail=str(error))
    if not isinstance(payload, dict):
        _reject("proposal_invalid", rule="payload_not_object")
    return payload


def save_proposal(
    layout: WorkspaceLayout,
    patch: Mapping[str, Any],
    *,
    origin: str = "mcp",
    note: str = "",
    id_factory: Callable[[], str] = uuid7,
) -> JsonObject:
    """Queue an untrusted external patch as a pending proposal file."""

    if not isinstance(patch, Mapping):
        _reject("proposal_invalid", rule="patch_missing")
    if not isinstance(note, str):
        _reject("proposal_invalid", rule="note_not_string")
    operations = patch.get("operations")
    operations_count = len(operations) if isinstance(operations, list) else 0
    record: JsonObject = {
        "schema_version": PROPOSAL_SCHEMA_VERSION,
        "proposal_id": id_factory(),
        "origin": origin,
        # External input: bound the note so a hostile client cannot balloon
        # the stored file.
        "note": note[:_MAX_NOTE_CHARS],
        "status": "pending",
        "created_at": _now_iso(),
        "status_at": None,
        "change_id": None,
        "summary": {"operations_count": operations_count},
        "patch": dict(patch),
    }
    _atomic_write_json(_proposal_path(layout, record["proposal_id"]), record)
    return record


def list_proposals(layout: WorkspaceLayout, *, status: str | None = "pending") -> list[JsonObject]:
    """List stored proposals (pending by default), oldest first.

    Unreadable or malformed files are skipped rather than failing the whole
    listing; they stay on disk for manual inspection and cannot be accepted.
    """

    proposals_dir = layout.root / "proposals"
    if not proposals_dir.is_dir():
        return []
    records: list[JsonObject] = []
    for path in sorted(proposals_dir.glob("*.json")):
        try:
            record = _load_json(path)
        except WorkspaceError:
            continue
        if status is None or record.get("status") == status:
            records.append(record)
    records.sort(key=lambda record: str(record.get("created_at", "")))
    return records


def read_proposal(layout: WorkspaceLayout, proposal_id: str) -> JsonObject:
    """Read one proposal, failing closed on traversal, absence or corruption."""

    path = _proposal_path(layout, proposal_id)
    if not path.is_file():
        _reject("proposal_missing", rule="proposal_file_absent")
    return _load_json(path)


def settle_proposal(
    layout: WorkspaceLayout,
    proposal_id: str,
    status: str,
    *,
    change_id: str | None = None,
) -> JsonObject:
    """Record the in-app human decision; only pending proposals may settle."""

    if status not in _SETTLED_STATUSES:
        _reject("proposal_invalid", rule="status_not_settleable", status=status)
    if status == "accepted" and not isinstance(change_id, str):
        _reject("proposal_invalid", rule="change_id_required")
    record = read_proposal(layout, proposal_id)
    if record.get("status") != "pending":
        _reject(
            "proposal_state_conflict",
            rule="not_pending",
            status=record.get("status"),
        )
    record["status"] = status
    record["status_at"] = _now_iso()
    record["change_id"] = change_id
    _atomic_write_json(_proposal_path(layout, proposal_id), record)
    return record
