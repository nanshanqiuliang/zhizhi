"""Pure, deterministic preview validation for GraphPatch v1."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal, Never

from knowledge_tree_contracts import ContractValidationError, validate_contract

JsonObject = dict[str, Any]
PreviewStatus = Literal["requires_confirmation", "ready_to_apply"]


class GraphPatchError(ValueError):
    """A stable rejection that never includes note or source text."""

    def __init__(self, code: str, *, details: Mapping[str, Any]) -> None:
        self.code = code
        self.details = dict(details)
        super().__init__(f"{code}: graph patch rejected")


@dataclass(frozen=True, slots=True)
class GraphPatchPreview:
    """An isolated candidate snapshot; this object has no persistence capability."""

    status: PreviewStatus
    snapshot: JsonObject
    findings: tuple[JsonObject, ...] = ()


def _reject(code: str, *, rule: str, operation_id: str | None = None, **ids: Any) -> Never:
    details: JsonObject = {"rule": rule, **ids}
    if operation_id is not None:
        details["operation_id"] = operation_id
    raise GraphPatchError(code, details=details)


def _validate_schema(contract: str, value: Mapping[str, Any]) -> None:
    try:
        validate_contract(contract, value)
    except ContractValidationError as error:
        raise GraphPatchError(error.code, details=error.details) from error


def _index_by_id(items: list[JsonObject], *, kind: str) -> dict[str, JsonObject]:
    result: dict[str, JsonObject] = {}
    for item in items:
        item_id = str(item["id"])
        if item_id in result:
            _reject("validation_failed", rule=f"duplicate_{kind}_id", target_id=item_id)
        result[item_id] = item
    return result


def _path_between(adjacency: Mapping[str, set[str]], start: str, goal: str) -> list[str] | None:
    queue: deque[str] = deque([start])
    parent: dict[str, str | None] = {start: None}
    while queue:
        current = queue.popleft()
        if current == goal:
            path: list[str] = []
            cursor: str | None = current
            while cursor is not None:
                path.append(cursor)
                cursor = parent[cursor]
            return list(reversed(path))
        for neighbor in sorted(adjacency.get(current, set())):
            if neighbor not in parent:
                parent[neighbor] = current
                queue.append(neighbor)
    return None


def _prerequisite_adjacency(edges: list[JsonObject]) -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = {}
    for edge in edges:
        if edge["edge_type"] == "prerequisite_of":
            source = str(edge["source_concept_id"])
            target = str(edge["target_concept_id"])
            adjacency.setdefault(source, set()).add(target)
    return adjacency


def _validate_graph_semantics(graph: JsonObject) -> None:
    course_id = str(graph["course_id"])
    concepts: list[JsonObject] = graph["concepts"]
    edges: list[JsonObject] = graph["edges"]
    layouts: list[JsonObject] = graph["layout_items"]
    concept_index = _index_by_id(concepts, kind="concept")
    _index_by_id(edges, kind="edge")

    for concept in concepts:
        if concept["course_id"] != course_id:
            _reject(
                "validation_failed",
                rule="concept_course_mismatch",
                target_id=concept["id"],
            )
        _validate_origin_evidence(concept, kind="concept")

    edge_keys: set[tuple[str, str, str]] = set()
    prerequisite_adjacency: dict[str, set[str]] = {}
    for edge in edges:
        _validate_edge_semantics(edge, course_id=course_id, concepts=concept_index)
        edge_key = _edge_key(edge)
        if edge_key in edge_keys:
            _reject("validation_failed", rule="duplicate_edge", target_id=edge["id"])
        edge_keys.add(edge_key)
        if edge["edge_type"] == "prerequisite_of":
            source = str(edge["source_concept_id"])
            target = str(edge["target_concept_id"])
            path = _path_between(prerequisite_adjacency, target, source)
            if path is not None:
                raise GraphPatchError(
                    "graph_cycle_detected",
                    details={"rule": "existing_graph_cycle", "cycle_path": [source, *path]},
                )
            prerequisite_adjacency.setdefault(source, set()).add(target)

    layout_keys: set[tuple[str, str]] = set()
    for layout in layouts:
        concept_id = str(layout["concept_id"])
        if concept_id not in concept_index:
            _reject("validation_failed", rule="layout_target_missing", target_id=concept_id)
        key = (str(layout["view_id"]), concept_id)
        if key in layout_keys:
            _reject("validation_failed", rule="duplicate_layout_item", target_id=concept_id)
        layout_keys.add(key)


def _validate_origin_evidence(item: JsonObject, *, kind: str) -> None:
    origin = item["origin"]
    confidence = item["confidence"]
    evidence_ids = item["evidence_ids"]
    if origin == "user" and confidence is not None:
        _reject(
            "validation_failed",
            rule="user_confidence_must_be_null",
            target_id=item["id"],
        )
    if kind == "concept" and origin == "ai" and not evidence_ids:
        _reject("evidence_required", rule="ai_concept_evidence", target_id=item["id"])
    if (
        kind == "edge"
        and origin == "ai"
        and item["edge_type"] == "prerequisite_of"
        and not evidence_ids
    ):
        _reject("evidence_required", rule="ai_prerequisite_evidence", target_id=item["id"])


def _validate_edge_semantics(
    edge: JsonObject,
    *,
    course_id: str,
    concepts: Mapping[str, JsonObject],
    operation_id: str | None = None,
) -> None:
    source = str(edge["source_concept_id"])
    target = str(edge["target_concept_id"])
    if edge["course_id"] != course_id:
        _reject("validation_failed", rule="edge_course_mismatch", target_id=edge["id"])
    if source == target:
        details: JsonObject = {
            "rule": "self_edge",
            "target_id": edge["id"],
            "cycle_path": [source, source],
        }
        if operation_id is not None:
            details["operation_id"] = operation_id
        raise GraphPatchError("graph_cycle_detected", details=details)
    if source not in concepts or target not in concepts:
        missing_id = source if source not in concepts else target
        _reject("validation_failed", rule="edge_endpoint_missing", target_id=missing_id)
    if concepts[source]["course_id"] != course_id or concepts[target]["course_id"] != course_id:
        _reject("validation_failed", rule="edge_endpoint_course_mismatch", target_id=edge["id"])
    _validate_origin_evidence(edge, kind="edge")


def _edge_key(edge: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(edge["source_concept_id"]),
        str(edge["target_concept_id"]),
        str(edge["edge_type"]),
    )


def _concept_target(
    operation: JsonObject,
    concepts: Mapping[str, JsonObject],
    base_revisions: Mapping[str, int],
    *,
    operation_id: str,
) -> JsonObject:
    target_id = str(operation["target"]["id"])
    target = concepts.get(target_id)
    if target is None:
        _reject(
            "validation_failed",
            rule="target_missing",
            operation_id=operation_id,
            target_id=target_id,
        )
    base_revision = base_revisions.get(target_id)
    if base_revision is None:
        _reject(
            "validation_failed",
            rule="same_patch_created_target_not_supported",
            operation_id=operation_id,
            target_id=target_id,
        )
    if base_revision != operation["expected_updated_revision_no"]:
        _reject(
            "revision_conflict",
            rule="target_revision_mismatch",
            operation_id=operation_id,
            target_id=target_id,
            expected_revision_no=operation["expected_updated_revision_no"],
            actual_revision_no=base_revision,
        )
    return target


def _ensure_unlocked(
    concept: JsonObject,
    dimension: str,
    *,
    operation_id: str,
) -> None:
    if concept["locks"][dimension]:
        _reject(
            "target_locked",
            rule=f"{dimension}_lock",
            operation_id=operation_id,
            target_id=concept["id"],
            dimension=dimension,
        )


def _apply_create_concept(
    operation: JsonObject,
    graph: JsonObject,
    concepts: dict[str, JsonObject],
    base_revisions: dict[str, int],
    *,
    actor_type: str,
    next_revision: int,
) -> None:
    concept = operation["concept"]
    operation_id = str(operation["op_id"])
    concept_id = str(concept["id"])
    if concept_id in concepts:
        _reject(
            "validation_failed",
            rule="concept_already_exists",
            operation_id=operation_id,
            target_id=concept_id,
        )
    if concept["course_id"] != graph["course_id"]:
        _reject(
            "validation_failed",
            rule="concept_course_mismatch",
            operation_id=operation_id,
            target_id=concept_id,
        )
    if concept["revision_no"] != 0:
        _reject(
            "validation_failed",
            rule="new_concept_revision_must_be_zero",
            operation_id=operation_id,
            target_id=concept_id,
        )
    if concept["origin"] != actor_type:
        _reject(
            "validation_failed",
            rule="actor_origin_mismatch",
            operation_id=operation_id,
            target_id=concept_id,
        )
    _validate_origin_evidence(concept, kind="concept")
    concept["revision_no"] = next_revision
    graph["concepts"].append(concept)
    concepts[concept_id] = concept
    base_revisions[concept_id] = 0


def _apply_update_concept(
    operation: JsonObject,
    concepts: Mapping[str, JsonObject],
    base_revisions: Mapping[str, int],
    *,
    actor_type: str,
    next_revision: int,
) -> None:
    operation_id = str(operation["op_id"])
    target = _concept_target(operation, concepts, base_revisions, operation_id=operation_id)
    _ensure_unlocked(target, "content", operation_id=operation_id)
    if actor_type == "ai" and not operation["evidence_ids"]:
        _reject(
            "evidence_required",
            rule="ai_concept_update_evidence",
            operation_id=operation_id,
            target_id=target["id"],
        )
    target.update(operation["changes"])
    if operation["evidence_ids"]:
        target["evidence_ids"] = sorted(
            set(target["evidence_ids"]) | set(operation["evidence_ids"])
        )
    _validate_origin_evidence(target, kind="concept")
    target["revision_no"] = next_revision


def _apply_create_edge(
    operation: JsonObject,
    graph: JsonObject,
    concepts: Mapping[str, JsonObject],
    edges: dict[str, JsonObject],
    base_revisions: Mapping[str, int],
    *,
    actor_type: str,
    next_revision: int,
) -> None:
    operation_id = str(operation["op_id"])
    edge = operation["edge"]
    edge_id = str(edge["id"])
    if edge_id in edges:
        _reject(
            "validation_failed",
            rule="edge_already_exists",
            operation_id=operation_id,
            target_id=edge_id,
        )
    if edge["revision_no"] != 0:
        _reject(
            "validation_failed",
            rule="new_edge_revision_must_be_zero",
            operation_id=operation_id,
            target_id=edge_id,
        )
    if edge["origin"] != actor_type:
        _reject(
            "validation_failed",
            rule="actor_origin_mismatch",
            operation_id=operation_id,
            target_id=edge_id,
        )
    _validate_edge_semantics(
        edge,
        course_id=str(graph["course_id"]),
        concepts=concepts,
        operation_id=operation_id,
    )
    source = concepts[str(edge["source_concept_id"])]
    target = concepts[str(edge["target_concept_id"])]
    for role, concept, expected_field in (
        ("source", source, "expected_source_revision_no"),
        ("target", target, "expected_target_revision_no"),
    ):
        concept_id = str(concept["id"])
        actual_revision = base_revisions[concept_id]
        if actual_revision != operation[expected_field]:
            _reject(
                "revision_conflict",
                rule=f"{role}_revision_mismatch",
                operation_id=operation_id,
                target_id=concept_id,
                expected_revision_no=operation[expected_field],
                actual_revision_no=actual_revision,
            )
    _ensure_unlocked(source, "relations", operation_id=operation_id)
    _ensure_unlocked(target, "relations", operation_id=operation_id)

    edge_key = _edge_key(edge)
    if any(_edge_key(existing) == edge_key for existing in graph["edges"]):
        _reject(
            "validation_failed",
            rule="duplicate_edge",
            operation_id=operation_id,
            target_id=edge_id,
        )
    if edge["edge_type"] == "prerequisite_of":
        source_id, target_id, _ = edge_key
        path = _path_between(_prerequisite_adjacency(graph["edges"]), target_id, source_id)
        if path is not None:
            raise GraphPatchError(
                "graph_cycle_detected",
                details={"operation_id": operation_id, "cycle_path": [source_id, *path]},
            )
    edge["revision_no"] = next_revision
    graph["edges"].append(edge)
    edges[edge_id] = edge
    source["revision_no"] = next_revision
    target["revision_no"] = next_revision


def _apply_set_lock(
    operation: JsonObject,
    concepts: Mapping[str, JsonObject],
    base_revisions: Mapping[str, int],
    *,
    actor_type: str,
    next_revision: int,
) -> None:
    operation_id = str(operation["op_id"])
    target = _concept_target(operation, concepts, base_revisions, operation_id=operation_id)
    dimension = str(operation["dimension"])
    if actor_type != "user":
        _reject(
            "target_locked" if target["locks"][dimension] else "validation_failed",
            rule="only_user_may_set_lock",
            operation_id=operation_id,
            target_id=target["id"],
            dimension=dimension,
        )
    target["locks"][dimension] = operation["value"]
    target["revision_no"] = next_revision


def _apply_annotation(
    operation: JsonObject,
    concepts: Mapping[str, JsonObject],
    base_revisions: Mapping[str, int],
    *,
    next_revision: int,
) -> None:
    operation_id = str(operation["op_id"])
    target = _concept_target(operation, concepts, base_revisions, operation_id=operation_id)
    _ensure_unlocked(target, "annotations", operation_id=operation_id)
    annotation = operation["annotation"]
    target["annotations"] = [
        current for current in target["annotations"] if current["kind"] != annotation["kind"]
    ]
    target["annotations"].append(annotation)
    target["annotations"].sort(key=lambda current: str(current["kind"]))
    target["revision_no"] = next_revision


def _apply_layout(
    operation: JsonObject,
    graph: JsonObject,
    concepts: Mapping[str, JsonObject],
    base_revisions: Mapping[str, int],
    *,
    next_revision: int,
) -> None:
    operation_id = str(operation["op_id"])
    target = _concept_target(operation, concepts, base_revisions, operation_id=operation_id)
    _ensure_unlocked(target, "position", operation_id=operation_id)
    layout = operation["layout_item"]
    if layout["concept_id"] != target["id"]:
        _reject(
            "validation_failed",
            rule="layout_target_mismatch",
            operation_id=operation_id,
            target_id=target["id"],
        )
    key = (layout["view_id"], layout["concept_id"])
    graph["layout_items"] = [
        current
        for current in graph["layout_items"]
        if (current["view_id"], current["concept_id"]) != key
    ]
    layout["revision_no"] = next_revision
    graph["layout_items"].append(layout)
    graph["layout_items"].sort(key=lambda current: (current["view_id"], current["concept_id"]))
    target["revision_no"] = next_revision


def _apply_delete_concept(
    operation: JsonObject,
    graph: JsonObject,
    concepts: dict[str, JsonObject],
    base_revisions: dict[str, int],
    *,
    next_revision: int,
) -> None:
    operation_id = str(operation["op_id"])
    target = _concept_target(operation, concepts, base_revisions, operation_id=operation_id)
    for dimension in ("content", "relations", "position", "annotations"):
        if target["locks"][dimension]:
            _reject(
                "target_locked",
                rule=f"{dimension}_lock",
                operation_id=operation_id,
                target_id=target["id"],
                dimension=dimension,
            )
    concept_id = str(target["id"])
    graph["concepts"] = [concept for concept in graph["concepts"] if concept["id"] != concept_id]
    graph["edges"] = [
        edge
        for edge in graph["edges"]
        if edge["source_concept_id"] != concept_id and edge["target_concept_id"] != concept_id
    ]
    graph["layout_items"] = [
        item for item in graph["layout_items"] if item["concept_id"] != concept_id
    ]
    concepts.pop(concept_id, None)
    base_revisions.pop(concept_id, None)


def _apply_delete_edge(
    operation: JsonObject,
    graph: JsonObject,
    concepts: dict[str, JsonObject],
    *,
    next_revision: int,
) -> None:
    operation_id = str(operation["op_id"])
    edge_id = str(operation["target"]["id"])
    edge = next((item for item in graph["edges"] if item["id"] == edge_id), None)
    if edge is None:
        _reject(
            "validation_failed", rule="edge_missing", operation_id=operation_id, target_id=edge_id
        )
    source = concepts.get(str(edge["source_concept_id"]))
    target = concepts.get(str(edge["target_concept_id"]))
    if source is not None:
        _ensure_unlocked(source, "relations", operation_id=operation_id)
    if target is not None:
        _ensure_unlocked(target, "relations", operation_id=operation_id)
    graph["edges"] = [item for item in graph["edges"] if item["id"] != edge_id]
    if source is not None:
        source["revision_no"] = next_revision
    if target is not None:
        target["revision_no"] = next_revision


def _apply_operation(
    operation: JsonObject,
    graph: JsonObject,
    concepts: dict[str, JsonObject],
    edges: dict[str, JsonObject],
    base_revisions: dict[str, int],
    *,
    actor_type: str,
    next_revision: int,
) -> None:
    operation_name = operation["op"]
    if operation_name == "create_concept":
        _apply_create_concept(
            operation,
            graph,
            concepts,
            base_revisions,
            actor_type=actor_type,
            next_revision=next_revision,
        )
    elif operation_name == "update_concept":
        _apply_update_concept(
            operation,
            concepts,
            base_revisions,
            actor_type=actor_type,
            next_revision=next_revision,
        )
    elif operation_name == "create_edge":
        _apply_create_edge(
            operation,
            graph,
            concepts,
            edges,
            base_revisions,
            actor_type=actor_type,
            next_revision=next_revision,
        )
    elif operation_name == "set_lock":
        _apply_set_lock(
            operation,
            concepts,
            base_revisions,
            actor_type=actor_type,
            next_revision=next_revision,
        )
    elif operation_name == "upsert_annotation":
        _apply_annotation(
            operation,
            concepts,
            base_revisions,
            next_revision=next_revision,
        )
    elif operation_name == "set_layout_item":
        _apply_layout(
            operation,
            graph,
            concepts,
            base_revisions,
            next_revision=next_revision,
        )
    elif operation_name == "delete_concept":
        _apply_delete_concept(
            operation,
            graph,
            concepts,
            base_revisions,
            next_revision=next_revision,
        )
    elif operation_name == "delete_edge":
        _apply_delete_edge(
            operation,
            graph,
            concepts,
            next_revision=next_revision,
        )
    else:
        _reject(
            "validation_failed",
            rule="unsupported_operation",
            operation_id=str(operation["op_id"]),
        )


def preview_graph_patch(
    graph: Mapping[str, Any],
    patch: Mapping[str, Any],
    *,
    trusted_actor: Mapping[str, str],
) -> GraphPatchPreview:
    """Return a candidate graph using actor context supplied outside the untrusted patch."""

    _validate_schema("course_graph", graph)
    _validate_schema("graph_patch", patch)
    working_graph: JsonObject = deepcopy(dict(graph))
    working_patch: JsonObject = deepcopy(dict(patch))
    _validate_graph_semantics(working_graph)

    declared_actor = working_patch["actor"]
    if (
        trusted_actor.get("type") != declared_actor["type"]
        or trusted_actor.get("id") != declared_actor["id"]
    ):
        _reject("permission_denied", rule="actor_context_mismatch")

    for identity_field in ("workspace_id", "course_id"):
        if working_graph[identity_field] != working_patch[identity_field]:
            _reject("validation_failed", rule=f"{identity_field}_mismatch")
    if working_graph["revision_no"] != working_patch["base_revision_no"]:
        _reject(
            "revision_conflict",
            rule="base_revision_mismatch",
            expected_revision_no=working_patch["base_revision_no"],
            actual_revision_no=working_graph["revision_no"],
        )
    if working_patch["requires_confirmation"] is not True:
        _reject("validation_failed", rule="confirmation_required")

    operation_ids: set[str] = set()
    concepts = _index_by_id(working_graph["concepts"], kind="concept")
    edges = _index_by_id(working_graph["edges"], kind="edge")
    base_revisions = {
        concept_id: int(concept["revision_no"]) for concept_id, concept in concepts.items()
    }
    next_revision = int(working_graph["revision_no"]) + 1
    actor_type = str(working_patch["actor"]["type"])
    operation_targets: set[tuple[str, str]] = set()
    for operation in working_patch["operations"]:
        operation_id = str(operation["op_id"])
        if operation_id in operation_ids:
            _reject(
                "validation_failed",
                rule="duplicate_operation_id",
                operation_id=operation_id,
            )
        operation_ids.add(operation_id)
        operation_target = _operation_target_key(operation)
        if operation_target in operation_targets:
            _reject(
                "validation_failed",
                rule="duplicate_operation_target",
                operation_id=operation_id,
            )
        operation_targets.add(operation_target)
        _apply_operation(
            operation,
            working_graph,
            concepts,
            edges,
            base_revisions,
            actor_type=actor_type,
            next_revision=next_revision,
        )

    working_graph["revision_no"] = next_revision
    _validate_schema("course_graph", working_graph)
    _validate_graph_semantics(working_graph)
    status: PreviewStatus = (
        "ready_to_apply"
        if actor_type == "user" and working_patch["confirmed"] is True
        else "requires_confirmation"
    )
    return GraphPatchPreview(status=status, snapshot=working_graph)


def validate_course_graph(graph: Mapping[str, Any]) -> None:
    """Validate graph schema and cross-entity semantics without mutating the input."""

    _validate_schema("course_graph", graph)
    _validate_graph_semantics(deepcopy(dict(graph)))


def _operation_target_key(operation: Mapping[str, Any]) -> tuple[str, str]:
    operation_name = str(operation["op"])
    if operation_name == "create_concept":
        target = str(operation["concept"]["id"])
    elif operation_name == "create_edge":
        target = str(operation["edge"]["id"])
    else:
        target = str(operation["target"]["id"])
        if operation_name == "set_lock":
            target = f"{target}:{operation['dimension']}"
        elif operation_name == "upsert_annotation":
            target = f"{target}:{operation['annotation']['kind']}"
        elif operation_name == "set_layout_item":
            target = f"{target}:{operation['layout_item']['view_id']}"
    return operation_name, target
