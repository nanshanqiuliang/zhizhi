"""Validation for the calculus-v1 independent review packet."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from scripts.calculus_dataset_validation import JsonObject

DATASET_DIR = Path("evals/calculus-v1")
REVIEW_PATH = DATASET_DIR / "independent-review.json"
REVIEW_SCHEMA_PATH = DATASET_DIR / "schema/independent-review.schema.json"


class ReviewValidationError(ValueError):
    """Raised when the independent review packet is invalid or incomplete."""

    code = "calculus_review_invalid"


def _load_object(path: Path) -> JsonObject:
    try:
        value: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReviewValidationError(f"{path}: cannot parse JSON: {error}") from error
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ReviewValidationError(f"{path}: expected an object with string keys")
    return value


def _validate_schema(root: Path, review: JsonObject) -> None:
    schema = _load_object(root / REVIEW_SCHEMA_PATH)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(review), key=lambda item: list(item.absolute_path))
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "<root>"
        raise ReviewValidationError(f"independent-review.json:{location}: {first.message}")


def load_and_validate_review(root: Path) -> JsonObject:
    """Load the pending review packet and validate its JSON Schema."""

    review = _load_object(root / REVIEW_PATH)
    _validate_schema(root, review)
    return review


def _review_ids(items: Any, kind: str) -> list[str]:
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        raise ReviewValidationError(f"{kind} reviews must be an object array")
    ids: list[str] = []
    for item in items:
        item_id = item.get("id")
        if not isinstance(item_id, str):
            raise ReviewValidationError(f"{kind} review has invalid id")
        if item_id in ids:
            raise ReviewValidationError(f"duplicate {kind} review id: {item_id}")
        ids.append(item_id)
    return ids


def _validate_coverage(review: JsonObject, dataset: JsonObject) -> None:
    mappings = (
        ("concept", "concept_reviews", "concepts"),
        ("relation", "relation_reviews", "relations"),
        ("anchor", "anchor_reviews", "anchors"),
    )
    for kind, review_key, dataset_key in mappings:
        actual = set(_review_ids(review.get(review_key), kind))
        expected = {item["id"] for item in dataset[dataset_key]}
        if actual != expected:
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            raise ReviewValidationError(
                f"{kind} review coverage mismatch: missing={missing}, extra={extra}"
            )


def _validate_item_decisions(review: JsonObject) -> None:
    for key in ("concept_reviews", "relation_reviews", "anchor_reviews"):
        for item in review[key]:
            decision = item["decision"]
            resolution = item.get("resolution")
            resolution_fields = (
                item.get("resolution_comment"),
                item.get("resolution_by"),
                item.get("resolved_at"),
            )
            if decision == "dispute":
                if not item.get("comment") or not item.get("proposed_change"):
                    raise ReviewValidationError(
                        f"dispute requires comment and proposed_change: {key}/{item['id']}"
                    )
                if resolution not in {"pending", "accept_proposed", "reject_proposed"}:
                    raise ReviewValidationError(
                        f"dispute has invalid resolution state: {key}/{item['id']}"
                    )
                if resolution == "pending" and any(
                    value is not None for value in resolution_fields
                ):
                    raise ReviewValidationError(
                        f"pending dispute cannot have resolution metadata: {key}/{item['id']}"
                    )
                if resolution in {"accept_proposed", "reject_proposed"} and not all(
                    resolution_fields
                ):
                    raise ReviewValidationError(
                        "resolved dispute requires complete resolution metadata: "
                        f"{key}/{item['id']}"
                    )
                continue
            if item.get("proposed_change") is not None:
                raise ReviewValidationError(
                    f"non-dispute cannot propose a change: {key}/{item['id']}"
                )
            if resolution != "not_applicable" or any(
                value is not None for value in resolution_fields
            ):
                raise ReviewValidationError(
                    f"non-dispute resolution must be not_applicable: {key}/{item['id']}"
                )


def _all_decided(review: JsonObject) -> bool:
    return all(
        item["decision"] in {"accept", "dispute"}
        for key in ("concept_reviews", "relation_reviews", "anchor_reviews")
        for item in review[key]
    )


def _all_disputes_resolved(review: JsonObject) -> bool:
    for key in ("concept_reviews", "relation_reviews", "anchor_reviews"):
        for item in review[key]:
            if item["decision"] == "dispute" and (
                item.get("resolution") not in {"accept_proposed", "reject_proposed"}
                or not item.get("resolution_comment")
                or not item.get("resolution_by")
                or not item.get("resolved_at")
            ):
                return False
    return True


def _parse_time(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise ReviewValidationError(f"{label} must be an RFC3339 timestamp")
    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise ReviewValidationError(f"{label} must be an RFC3339 timestamp") from error


def _validate_resolution_order(review: JsonObject, subject: JsonObject) -> None:
    subject_time = _parse_time(subject.get("completed_at"), "subject completed_at")
    for key in ("concept_reviews", "relation_reviews", "anchor_reviews"):
        for item in review[key]:
            if item["decision"] != "dispute":
                continue
            if item.get("resolution_by") == subject.get("reviewer"):
                raise ReviewValidationError(
                    f"subject reviewer cannot adjudicate own dispute: {key}/{item['id']}"
                )
            resolved_at = _parse_time(item.get("resolved_at"), f"{key}/{item['id']} resolved_at")
            if resolved_at > subject_time:
                raise ReviewValidationError(
                    f"dispute resolution cannot follow subject signoff: {key}/{item['id']}"
                )


def _validate_signoff(signoff: Any, role: str, expected_role: str) -> None:
    if not isinstance(signoff, dict):
        raise ReviewValidationError(f"{role} signoff must be an object")
    if signoff.get("reviewer_role") != expected_role:
        raise ReviewValidationError(f"{role} signoff has incorrect reviewer_role")
    status = signoff.get("status")
    reviewer = signoff.get("reviewer")
    completed_at = signoff.get("completed_at")
    if status == "complete" and (not reviewer or not completed_at):
        raise ReviewValidationError(f"complete {role} signoff requires reviewer and completed_at")
    if status == "in_progress" and not reviewer:
        raise ReviewValidationError(f"in_progress {role} signoff requires reviewer")
    if status == "pending" and reviewer is not None:
        raise ReviewValidationError(f"pending {role} signoff cannot name a reviewer")
    if status != "complete" and completed_at is not None:
        raise ReviewValidationError(f"incomplete {role} signoff cannot have completed_at")


def review_subject_sha256(dataset: JsonObject) -> str:
    """Hash reviewable dataset content while excluding mutable approval metadata."""

    subject = {key: value for key, value in dataset.items() if key not in {"status", "review"}}
    payload = json.dumps(subject, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def validate_review_semantics(
    root: Path,
    review: JsonObject,
    dataset: JsonObject,
    *,
    validate_schema: bool = False,
    require_complete: bool = False,
) -> None:
    """Validate dataset binding, item coverage, disputes, and separated signoffs."""

    if validate_schema:
        _validate_schema(root, review)

    actual_hash = review_subject_sha256(dataset)
    if review.get("review_subject_sha256") != actual_hash:
        raise ReviewValidationError(
            "review subject hash mismatch: "
            f"expected {review.get('review_subject_sha256')}, actual {actual_hash}"
        )
    if review.get("dataset_id") != dataset.get("dataset_id"):
        raise ReviewValidationError("review dataset_id does not match gold.json")
    if review.get("dataset_version") != dataset.get("dataset_version"):
        raise ReviewValidationError("review dataset_version does not match gold.json")

    _validate_coverage(review, dataset)
    _validate_item_decisions(review)
    subject = review.get("subject_signoff")
    qa = review.get("qa_signoff")
    _validate_signoff(subject, "subject", "independent_subject_reviewer")
    _validate_signoff(qa, "qa", "qa")

    if (
        isinstance(subject, dict)
        and subject.get("status") == "complete"
        and not _all_decided(review)
    ):
        raise ReviewValidationError("subject signoff requires all item decisions")
    if (
        isinstance(subject, dict)
        and subject.get("status") == "complete"
        and not _all_disputes_resolved(review)
    ):
        raise ReviewValidationError("subject signoff requires all disputes to be resolved")
    if isinstance(subject, dict) and subject.get("status") == "complete":
        _validate_resolution_order(review, subject)
    if isinstance(qa, dict) and qa.get("status") == "complete":
        if not isinstance(subject, dict) or subject.get("status") != "complete":
            raise ReviewValidationError("QA signoff requires complete subject signoff")
        if review.get("license_notice_seen") is not True:
            raise ReviewValidationError("QA signoff requires license notice acknowledgement")
        if qa.get("reviewer") == subject.get("reviewer"):
            raise ReviewValidationError("subject reviewer and QA must be different people")
        subject_time = _parse_time(subject.get("completed_at"), "subject completed_at")
        qa_time = _parse_time(qa.get("completed_at"), "QA completed_at")
        if qa_time < subject_time:
            raise ReviewValidationError("QA signoff cannot precede subject signoff")

    must_be_complete = (
        require_complete
        or dataset.get("status") == "approved"
        or (isinstance(qa, dict) and qa.get("status") == "complete")
    )
    if must_be_complete:
        if (
            not isinstance(subject, dict)
            or not isinstance(qa, dict)
            or subject.get("status") != "complete"
            or qa.get("status") != "complete"
        ):
            raise ReviewValidationError("independent review is incomplete")
        dataset_independent = dataset.get("review", {}).get("independent", {})
        if (
            dataset.get("status") != "approved"
            or dataset_independent.get("status") != "complete"
            or dataset_independent.get("reviewer") != subject.get("reviewer")
        ):
            raise ReviewValidationError(
                "complete review packet requires synchronized approved dataset metadata"
            )
