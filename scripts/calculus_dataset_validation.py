"""Contract, provenance, license, and graph checks for calculus-v1."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from pypdf import PdfReader

JsonObject = dict[str, Any]
DATASET_DIR = Path("evals/calculus-v1")


class DatasetValidationError(ValueError):
    """Raised when the calculus gold dataset violates its frozen contract."""

    code = "calculus_dataset_invalid"


def _as_object(value: Any, source: Path) -> JsonObject:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise DatasetValidationError(f"{source}: expected an object with string keys")
    return value


def _load_json(path: Path) -> JsonObject:
    try:
        return _as_object(json.loads(path.read_text(encoding="utf-8")), path)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise DatasetValidationError(f"{path}: cannot parse JSON: {error}") from error


def _schema_error(dataset: JsonObject, schema: JsonObject) -> str | None:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(dataset), key=lambda item: list(item.absolute_path))
    if not errors:
        return None
    first = errors[0]
    location = ".".join(str(part) for part in first.absolute_path) or "<root>"
    return f"gold.json:{location}: {first.message}"


def _validate_schema(root: Path, dataset: JsonObject) -> None:
    schema = _load_json(root / DATASET_DIR / "schema/gold.schema.json")
    if message := _schema_error(dataset, schema):
        raise DatasetValidationError(message)


def load_and_validate_dataset(root: Path) -> JsonObject:
    """Load calculus-v1 and validate its JSON Schema."""

    dataset = _load_json(root / DATASET_DIR / "gold.json")
    _validate_schema(root, dataset)
    return dataset


def _unique_index(items: list[JsonObject], kind: str) -> dict[str, JsonObject]:
    result: dict[str, JsonObject] = {}
    for item in items:
        item_id = item.get("id")
        if not isinstance(item_id, str):
            raise DatasetValidationError(f"{kind} has a non-string id")
        if item_id in result:
            raise DatasetValidationError(f"duplicate {kind} id: {item_id}")
        result[item_id] = item
    return result


def _safe_source_path(root: Path, local_path: str) -> Path:
    dataset_root = (root / DATASET_DIR).resolve()
    candidate = (dataset_root / local_path).resolve()
    if dataset_root not in candidate.parents:
        raise DatasetValidationError("source local_path escapes the dataset directory")
    if candidate.suffix.lower() != ".pdf":
        raise DatasetValidationError("source local_path must point to a PDF")
    return candidate


def _validate_pdf(root: Path, source: JsonObject) -> None:
    local_path = source.get("local_path")
    if not isinstance(local_path, str):
        raise DatasetValidationError("source local_path is invalid")
    pdf_path = _safe_source_path(root, local_path)
    if not pdf_path.is_file():
        raise DatasetValidationError(f"source PDF is missing: {local_path}")
    payload = pdf_path.read_bytes()
    actual_hash = hashlib.sha256(payload).hexdigest()
    if actual_hash != source.get("sha256"):
        raise DatasetValidationError(
            f"PDF hash mismatch: expected {source.get('sha256')}, actual {actual_hash}"
        )
    if len(payload) != source.get("byte_size"):
        raise DatasetValidationError(
            f"PDF byte size mismatch: expected {source.get('byte_size')}, actual {len(payload)}"
        )

    reader = PdfReader(pdf_path)
    if reader.is_encrypted:
        raise DatasetValidationError("source PDF must not be encrypted")
    if len(reader.pages) != source.get("page_count"):
        raise DatasetValidationError(
            f"PDF page count mismatch: expected {source.get('page_count')}, "
            f"actual {len(reader.pages)}"
        )
    metadata: Any = reader.metadata or {}
    if metadata.get("/Author") != source.get("creator"):
        raise DatasetValidationError("PDF author metadata does not match source creator")
    if "Chapter 02: Derivatives" not in str(metadata.get("/Title", "")):
        raise DatasetValidationError("PDF title metadata does not identify Chapter 02")

    catalog = reader.root_object
    names = catalog.get("/Names")
    has_javascript = bool(names and "/JavaScript" in names)
    has_embedded_files = bool(names and "/EmbeddedFiles" in names)
    if has_javascript or "/OpenAction" in catalog or "/AA" in catalog:
        raise DatasetValidationError("source PDF contains active document actions")
    if has_embedded_files:
        raise DatasetValidationError("source PDF contains embedded files")


def _validate_notice(root: Path) -> None:
    notice_path = root / DATASET_DIR / "NOTICE.md"
    try:
        notice = notice_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise DatasetValidationError(f"cannot read license notice: {error}") from error
    required = (
        "Gilbert Strang",
        "MIT OpenCourseWare",
        "CC BY-NC-SA 4.0",
        "https://creativecommons.org/licenses/by-nc-sa/4.0/",
        "non-commercial",
        "No MIT logo",
        "no endorsement",
    )
    missing = [value for value in required if value not in notice]
    if missing:
        raise DatasetValidationError(f"license notice is missing required statements: {missing}")


def _validate_dag(concept_ids: set[str], relations: list[JsonObject]) -> None:
    adjacency: dict[str, set[str]] = defaultdict(set)
    indegree = {concept_id: 0 for concept_id in concept_ids}
    edge_ids: set[tuple[str, str]] = set()
    for relation in relations:
        source = relation["source_concept_id"]
        target = relation["target_concept_id"]
        if source not in concept_ids:
            raise DatasetValidationError(f"relation has unknown source concept: {source}")
        if target not in concept_ids:
            raise DatasetValidationError(f"relation has unknown target concept: {target}")
        if source == target:
            raise DatasetValidationError(f"relation self-loop is forbidden: {source}")
        edge = (source, target)
        if edge in edge_ids:
            raise DatasetValidationError(f"duplicate prerequisite edge: {source} -> {target}")
        edge_ids.add(edge)
        adjacency[source].add(target)
        indegree[target] += 1

    ready = deque(sorted(node for node, degree in indegree.items() if degree == 0))
    visited = 0
    while ready:
        node = ready.popleft()
        visited += 1
        for target in sorted(adjacency[node]):
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
    if visited != len(concept_ids):
        cyclic_nodes = sorted(node for node, degree in indegree.items() if degree > 0)
        raise DatasetValidationError(f"prerequisite graph contains a cycle: {cyclic_nodes}")


def validate_dataset_semantics(
    root: Path, dataset: JsonObject, *, validate_schema: bool = False
) -> None:
    """Validate source identity, license, references, evidence, counts, and DAG."""

    if validate_schema:
        _validate_schema(root, dataset)

    concepts = dataset.get("concepts")
    relations = dataset.get("relations")
    anchors = dataset.get("anchors")
    if not isinstance(concepts, list) or not all(isinstance(item, dict) for item in concepts):
        raise DatasetValidationError("concepts must be an object array")
    if not isinstance(relations, list) or not all(isinstance(item, dict) for item in relations):
        raise DatasetValidationError("relations must be an object array")
    if not isinstance(anchors, list) or not all(isinstance(item, dict) for item in anchors):
        raise DatasetValidationError("anchors must be an object array")
    if (len(concepts), len(relations), len(anchors)) != (30, 40, 50):
        raise DatasetValidationError(
            f"frozen counts must be 30/40/50, got {len(concepts)}/{len(relations)}/{len(anchors)}"
        )

    concept_index = _unique_index(concepts, "concept")
    relation_index = _unique_index(relations, "relation")
    anchor_index = _unique_index(anchors, "anchor")
    assert len(relation_index) == 40

    source = dataset.get("source")
    if not isinstance(source, dict):
        raise DatasetValidationError("source must be an object")
    _validate_pdf(root, source)
    _validate_notice(root)

    resource_id = source.get("resource_id")
    page_count = source.get("page_count")
    for anchor_id, anchor in anchor_index.items():
        if anchor.get("resource_id") != resource_id:
            raise DatasetValidationError(f"anchor {anchor_id} references another resource")
        selector = anchor.get("selector", {})
        page = selector.get("page") if isinstance(selector, dict) else None
        if (
            not isinstance(page, int)
            or not isinstance(page_count, int)
            or not 1 <= page <= page_count
        ):
            raise DatasetValidationError(f"anchor {anchor_id} page is outside the PDF")
        for concept_id in anchor.get("concept_ids", []):
            if concept_id not in concept_index:
                raise DatasetValidationError(
                    f"anchor {anchor_id} references unknown concept: {concept_id}"
                )

    for concept_id, concept in concept_index.items():
        for anchor_id in concept.get("anchor_ids", []):
            if anchor_id not in anchor_index:
                raise DatasetValidationError(
                    f"concept {concept_id} references unknown anchor: {anchor_id}"
                )
            if concept_id not in anchor_index[anchor_id].get("concept_ids", []):
                raise DatasetValidationError(
                    f"concept/anchor backlink mismatch: {concept_id} <-> {anchor_id}"
                )

    _validate_dag(set(concept_index), relations)

    for relation_id, relation in relation_index.items():
        source_id = relation.get("source_concept_id")
        target_id = relation.get("target_concept_id")
        if not isinstance(source_id, str) or not isinstance(target_id, str):
            raise DatasetValidationError(f"relation {relation_id} has invalid concept endpoints")
        evidence_concepts: set[str] = set()
        for anchor_id in relation.get("evidence_anchor_ids", []):
            if anchor_id not in anchor_index:
                raise DatasetValidationError(
                    f"relation {relation_id} references unknown evidence anchor: {anchor_id}"
                )
            evidence_concepts.update(anchor_index[anchor_id].get("concept_ids", []))
        missing_evidence = {source_id, target_id} - evidence_concepts
        if missing_evidence:
            missing = sorted(missing_evidence)
            raise DatasetValidationError(
                f"relation {relation_id} evidence does not cover concepts: {missing}"
            )

    review = dataset.get("review", {})
    dataset_status = dataset.get("status")
    author_status = review.get("author", {}).get("status")
    independent_status = review.get("independent", {}).get("status")
    if dataset_status in {"author_reviewed", "approved"} and author_status != "complete":
        raise DatasetValidationError("author_reviewed dataset requires complete author review")
    if dataset_status == "approved" and (author_status, independent_status) != (
        "complete",
        "complete",
    ):
        raise DatasetValidationError("approved dataset requires author and independent review")
