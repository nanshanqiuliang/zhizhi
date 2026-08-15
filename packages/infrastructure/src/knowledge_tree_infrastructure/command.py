"""Natural-language command -> GraphPatch mapping (WORK-2026-029, Step 9 slice 2).

Deterministic, framework-free glue that turns an LLM-produced operation list
(which references concepts by *label*) into a `proposed` GraphPatch v1 that the
existing commit gate can preview and apply. This module never calls an LLM and
never persists anything; it only maps labels to ids and shapes operations.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from typing import Any

JsonObject = dict[str, Any]

_EDGE_TYPES = ("prerequisite_of", "related_to", "part_of", "example_of")
_DIMENSIONS = ("content", "position")


class CommandError(ValueError):
    """A stable, identifier-only rejection from command interpretation."""

    def __init__(self, code: str, *, details: Mapping[str, Any]) -> None:
        self.code = code
        self.details = dict(details)
        super().__init__(f"{code}: command rejected")


def _digest(value: Any) -> str:
    """Return a short hash for an LLM-emitted value, never the raw value."""
    raw = value if isinstance(value, str) else repr(value)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def build_command_patch(
    graph: JsonObject,
    operations: list[JsonObject],
    *,
    id_factory: Callable[[], str],
    reason: str,
) -> JsonObject:
    """Map label-based operations to a `proposed` GraphPatch v1.

    Supports `set_lock` (dimension content/position) and `create_edge` (the four
    edge types); every referenced label must exactly match a concept in the
    current graph (casefold) or the whole command fails closed. The resulting
    patch is `requires_confirmation=true` / `confirmed=false` / actor=user and
    is never applied here.
    """

    concepts = graph.get("concepts")
    if not isinstance(concepts, list):
        raise CommandError("command_invalid", details={"rule": "graph_concepts_missing"})

    by_label: dict[str, JsonObject] = {}
    for concept in concepts:
        if not isinstance(concept, dict) or not isinstance(concept.get("label"), str):
            continue
        by_label[str(concept["label"]).casefold()] = concept

    def resolve(label: Any, *, rule: str) -> JsonObject:
        if not isinstance(label, str) or not label:
            raise CommandError(
                "command_label_unknown", details={"rule": rule, "label_hash": _digest(label)}
            )
        concept = by_label.get(label.casefold())
        if concept is None:
            raise CommandError(
                "command_label_unknown", details={"rule": rule, "label_hash": _digest(label)}
            )
        return concept

    ops: list[JsonObject] = []
    for operation in operations:
        if not isinstance(operation, dict):
            raise CommandError("command_invalid", details={"rule": "operation_not_object"})
        op = operation.get("op")
        if op == "set_lock":
            concept = resolve(operation.get("target"), rule="target_unknown")
            dimension = operation.get("dimension")
            value = operation.get("value")
            if dimension not in _DIMENSIONS or not isinstance(value, bool):
                raise CommandError(
                    "command_invalid",
                    details={"rule": "set_lock_shape", "dimension_hash": _digest(dimension)},
                )
            ops.append(
                {
                    "op_id": id_factory(),
                    "op": "set_lock",
                    "target": {"type": "concept", "id": str(concept["id"])},
                    "expected_updated_revision_no": int(concept.get("revision_no", 0)),
                    "dimension": dimension,
                    "value": value,
                }
            )
        elif op == "create_edge":
            source = resolve(operation.get("source"), rule="source_unknown")
            target = resolve(operation.get("target"), rule="target_unknown")
            edge_type = operation.get("edge_type")
            if edge_type not in _EDGE_TYPES:
                raise CommandError(
                    "command_invalid",
                    details={"rule": "edge_type_invalid", "edge_type_hash": _digest(edge_type)},
                )
            ops.append(
                {
                    "op_id": id_factory(),
                    "op": "create_edge",
                    "expected_source_revision_no": int(source.get("revision_no", 0)),
                    "expected_target_revision_no": int(target.get("revision_no", 0)),
                    "edge": {
                        "id": id_factory(),
                        "course_id": graph["course_id"],
                        "source_concept_id": str(source["id"]),
                        "target_concept_id": str(target["id"]),
                        "edge_type": edge_type,
                        "origin": "user",
                        "review_state": "accepted",
                        "confidence": None,
                        "evidence_ids": [],
                        "locked": False,
                        "revision_no": 0,
                    },
                }
            )
        else:
            raise CommandError(
                "command_invalid", details={"rule": "op_unknown", "op_hash": _digest(op)}
            )

    return {
        "schema_version": 1,
        "patch_id": id_factory(),
        "workspace_id": graph["workspace_id"],
        "course_id": graph["course_id"],
        "base_revision_no": int(graph["revision_no"]),
        "actor": {"type": "user", "id": "local-user"},
        "reason": reason,
        "requires_confirmation": True,
        "confirmed": False,
        "operations": ops,
    }
