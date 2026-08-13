from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from scripts.calculus_dataset_validation import (
    DatasetValidationError,
    load_and_validate_dataset,
    validate_dataset_semantics,
)
from scripts.calculus_review_validation import (
    ReviewValidationError,
    load_and_validate_review,
    review_subject_sha256,
    validate_review_semantics,
)

ROOT = Path(__file__).resolve().parents[2]


def test_calculus_dataset_passes_contract_and_semantics() -> None:
    dataset = load_and_validate_dataset(ROOT)

    validate_dataset_semantics(ROOT, dataset)


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda data: data["concepts"].append(deepcopy(data["concepts"][0])),
            "too long",
        ),
        (
            lambda data: data["relations"][0].update({"target_concept_id": "missing"}),
            "unknown target concept",
        ),
        (
            lambda data: data["relations"][0].update(
                {"target_concept_id": data["relations"][0]["source_concept_id"]}
            ),
            "self-loop",
        ),
        (
            lambda data: data["relations"].append(
                {
                    **deepcopy(data["relations"][0]),
                    "id": "r999",
                    "source_concept_id": data["relations"][0]["target_concept_id"],
                    "target_concept_id": data["relations"][0]["source_concept_id"],
                }
            ),
            "too long",
        ),
        (
            lambda data: data["relations"][0].update({"source_concept_id": "dependent_variable"}),
            "duplicate prerequisite edge",
        ),
        (
            lambda data: data["relations"][-1].update(
                {
                    "source_concept_id": data["relations"][0]["target_concept_id"],
                    "target_concept_id": data["relations"][0]["source_concept_id"],
                    "evidence_anchor_ids": ["a005"],
                }
            ),
            "contains a cycle",
        ),
        (
            lambda data: data["relations"][0].update({"evidence_anchor_ids": ["a001"]}),
            "evidence does not cover concepts",
        ),
        (
            lambda data: data["source"].update({"sha256": "0" * 64}),
            "PDF hash mismatch",
        ),
        (
            lambda data: data["license"].update({"commercial_use": "allowed"}),
            "commercial_use",
        ),
        (
            lambda data: data["source"].update({"local_path": "source/../gold.json"}),
            "local_path",
        ),
        (
            lambda data: data["review"]["author"].update({"status": "pending"}),
            "requires complete author review",
        ),
        (
            lambda data: data.update({"status": "approved"}),
            "requires author and independent review",
        ),
    ],
)
def test_invalid_dataset_mutations_fail(mutator: object, message: str) -> None:
    dataset = load_and_validate_dataset(ROOT)
    changed = deepcopy(dataset)
    assert callable(mutator)
    mutator(changed)

    with pytest.raises(DatasetValidationError, match=message):
        validate_dataset_semantics(ROOT, changed, validate_schema=True)


def test_independent_review_must_remain_pending_until_assigned() -> None:
    dataset = load_and_validate_dataset(ROOT)

    assert dataset["review"]["independent"] == {
        "reviewer_role": "independent_subject_reviewer",
        "reviewer": "pending_assignment",
        "status": "pending",
    }
    assert dataset["status"] == "author_reviewed"


def test_pending_independent_review_packet_is_complete_but_unsigned() -> None:
    dataset = load_and_validate_dataset(ROOT)
    review = load_and_validate_review(ROOT)

    validate_review_semantics(ROOT, review, dataset)

    assert len(review["concept_reviews"]) == 30
    assert len(review["relation_reviews"]) == 40
    assert len(review["anchor_reviews"]) == 50
    assert review["subject_signoff"]["status"] == "pending"
    assert review["qa_signoff"]["status"] == "pending"


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda review: review.update({"review_subject_sha256": "0" * 64}),
            "review subject hash mismatch",
        ),
        (
            lambda review: review["concept_reviews"].pop(),
            "too short|review coverage",
        ),
        (
            lambda review: review["relation_reviews"][1].update(
                {"id": review["relation_reviews"][0]["id"]}
            ),
            "duplicate concept review id|duplicate relation review id",
        ),
        (
            lambda review: review["relation_reviews"][0].update(
                {"decision": "dispute", "comment": None, "proposed_change": None}
            ),
            "dispute requires",
        ),
        (
            lambda review: review["subject_signoff"].update(
                {
                    "status": "complete",
                    "reviewer": "subject-reviewer",
                    "completed_at": "2026-08-13T20:00:00+08:00",
                }
            ),
            "subject signoff requires all item decisions",
        ),
        (
            lambda review: review["subject_signoff"].update({"reviewer_role": "qa"}),
            "subject signoff has incorrect reviewer_role",
        ),
    ],
)
def test_invalid_independent_review_mutations_fail(mutator: object, message: str) -> None:
    dataset = load_and_validate_dataset(ROOT)
    review = load_and_validate_review(ROOT)
    changed = deepcopy(review)
    assert callable(mutator)
    mutator(changed)

    with pytest.raises(ReviewValidationError, match=message):
        validate_review_semantics(ROOT, changed, dataset, validate_schema=True)


def test_complete_review_gate_rejects_pending_signatures() -> None:
    dataset = load_and_validate_dataset(ROOT)
    review = load_and_validate_review(ROOT)

    with pytest.raises(ReviewValidationError, match="independent review is incomplete"):
        validate_review_semantics(ROOT, review, dataset, require_complete=True)


def test_complete_review_gate_accepts_separated_subject_and_qa_signoffs() -> None:
    dataset = deepcopy(load_and_validate_dataset(ROOT))
    review = deepcopy(load_and_validate_review(ROOT))
    for key in ("concept_reviews", "relation_reviews", "anchor_reviews"):
        for item in review[key]:
            item["decision"] = "accept"
    review["license_notice_seen"] = True
    review["subject_signoff"].update(
        {
            "reviewer": "independent-subject-reviewer",
            "status": "complete",
            "completed_at": "2026-08-13T20:00:00+08:00",
        }
    )
    review["qa_signoff"].update(
        {
            "reviewer": "independent-qa",
            "status": "complete",
            "completed_at": "2026-08-13T20:05:00+08:00",
        }
    )
    dataset["status"] = "approved"
    dataset["review"]["independent"].update(
        {"reviewer": "independent-subject-reviewer", "status": "complete"}
    )

    validate_review_semantics(ROOT, review, dataset, require_complete=True)


def test_complete_review_gate_rejects_unsynchronized_dataset_approval() -> None:
    dataset = load_and_validate_dataset(ROOT)
    review = deepcopy(load_and_validate_review(ROOT))
    for key in ("concept_reviews", "relation_reviews", "anchor_reviews"):
        for item in review[key]:
            item["decision"] = "accept"
    review["license_notice_seen"] = True
    review["subject_signoff"].update(
        {
            "reviewer": "independent-subject-reviewer",
            "status": "complete",
            "completed_at": "2026-08-13T20:00:00+08:00",
        }
    )
    review["qa_signoff"].update(
        {
            "reviewer": "independent-qa",
            "status": "complete",
            "completed_at": "2026-08-13T20:05:00+08:00",
        }
    )

    with pytest.raises(ReviewValidationError, match="requires synchronized approved dataset"):
        validate_review_semantics(ROOT, review, dataset)


def test_signoff_lifecycle_requires_clean_ownership_fields() -> None:
    dataset = load_and_validate_dataset(ROOT)
    review = deepcopy(load_and_validate_review(ROOT))
    review["subject_signoff"].update({"reviewer": "subject-reviewer", "status": "pending"})
    with pytest.raises(ReviewValidationError, match="pending subject signoff cannot name"):
        validate_review_semantics(ROOT, review, dataset)

    review["subject_signoff"].update({"reviewer": None, "status": "in_progress"})
    with pytest.raises(ReviewValidationError, match="in_progress subject signoff requires"):
        validate_review_semantics(ROOT, review, dataset)


def test_review_subject_hash_ignores_only_mutable_approval_metadata() -> None:
    dataset = load_and_validate_dataset(ROOT)
    changed_approval = deepcopy(dataset)
    changed_approval["status"] = "approved"
    changed_approval["review"]["independent"]["status"] = "complete"
    changed_content = deepcopy(dataset)
    changed_content["concepts"][0]["definition_zh"] += "变更"

    assert review_subject_sha256(changed_approval) == review_subject_sha256(dataset)
    assert review_subject_sha256(changed_content) != review_subject_sha256(dataset)


def test_qa_cannot_sign_before_subject_reviewer() -> None:
    dataset = load_and_validate_dataset(ROOT)
    review = deepcopy(load_and_validate_review(ROOT))
    review["qa_signoff"].update(
        {
            "reviewer": "independent-qa",
            "status": "complete",
            "completed_at": "2026-08-13T20:05:00+08:00",
        }
    )

    with pytest.raises(ReviewValidationError, match="requires complete subject signoff"):
        validate_review_semantics(ROOT, review, dataset)


def test_complete_subject_signoff_rejects_unresolved_dispute() -> None:
    dataset = load_and_validate_dataset(ROOT)
    review = deepcopy(load_and_validate_review(ROOT))
    for key in ("concept_reviews", "relation_reviews", "anchor_reviews"):
        for item in review[key]:
            item["decision"] = "accept"
    review["relation_reviews"][0].update(
        {
            "decision": "dispute",
            "comment": "方向需要复核。",
            "proposed_change": "反转关系方向。",
            "resolution": "pending",
            "resolution_comment": None,
            "resolution_by": None,
            "resolved_at": None,
        }
    )
    review["subject_signoff"].update(
        {
            "reviewer": "independent-subject-reviewer",
            "status": "complete",
            "completed_at": "2026-08-13T20:00:00+08:00",
        }
    )

    with pytest.raises(ReviewValidationError, match="requires all disputes to be resolved"):
        validate_review_semantics(ROOT, review, dataset)


def test_dispute_and_non_dispute_resolution_states_are_strict() -> None:
    dataset = load_and_validate_dataset(ROOT)
    review = deepcopy(load_and_validate_review(ROOT))
    review["relation_reviews"][0].update(
        {
            "decision": "dispute",
            "comment": "方向需要复核。",
            "proposed_change": "反转关系方向。",
        }
    )
    with pytest.raises(ReviewValidationError, match="invalid resolution state"):
        validate_review_semantics(ROOT, review, dataset)

    review = deepcopy(load_and_validate_review(ROOT))
    review["relation_reviews"][0]["proposed_change"] = "不应存在的建议"
    with pytest.raises(ReviewValidationError, match="non-dispute cannot propose"):
        validate_review_semantics(ROOT, review, dataset)


def test_third_party_resolved_dispute_can_pass_complete_gate() -> None:
    dataset = deepcopy(load_and_validate_dataset(ROOT))
    review = deepcopy(load_and_validate_review(ROOT))
    for key in ("concept_reviews", "relation_reviews", "anchor_reviews"):
        for item in review[key]:
            item["decision"] = "accept"
    review["relation_reviews"][0].update(
        {
            "decision": "dispute",
            "comment": "方向需要复核。",
            "proposed_change": "保留原方向并补充理由。",
            "resolution": "accept_proposed",
            "resolution_comment": "项目负责人接受补充理由。",
            "resolution_by": "project-owner",
            "resolved_at": "2026-08-13T19:55:00+08:00",
        }
    )
    review["license_notice_seen"] = True
    review["subject_signoff"].update(
        {
            "reviewer": "independent-subject-reviewer",
            "status": "complete",
            "completed_at": "2026-08-13T20:00:00+08:00",
        }
    )
    review["qa_signoff"].update(
        {
            "reviewer": "independent-qa",
            "status": "complete",
            "completed_at": "2026-08-13T20:05:00+08:00",
        }
    )
    dataset["status"] = "approved"
    dataset["review"]["independent"].update(
        {"reviewer": "independent-subject-reviewer", "status": "complete"}
    )

    validate_review_semantics(ROOT, review, dataset, require_complete=True)


@pytest.mark.parametrize(
    ("resolution_by", "resolved_at", "message"),
    [
        (
            "independent-subject-reviewer",
            "2026-08-13T19:55:00+08:00",
            "cannot adjudicate own dispute",
        ),
        (
            "project-owner",
            "2026-08-13T20:01:00+08:00",
            "cannot follow subject signoff",
        ),
    ],
)
def test_dispute_adjudication_is_independent_and_precedes_subject_signoff(
    resolution_by: str, resolved_at: str, message: str
) -> None:
    dataset = load_and_validate_dataset(ROOT)
    review = deepcopy(load_and_validate_review(ROOT))
    for key in ("concept_reviews", "relation_reviews", "anchor_reviews"):
        for item in review[key]:
            item["decision"] = "accept"
    review["relation_reviews"][0].update(
        {
            "decision": "dispute",
            "comment": "方向需要复核。",
            "proposed_change": "保留原方向并补充理由。",
            "resolution": "accept_proposed",
            "resolution_comment": "裁决意见。",
            "resolution_by": resolution_by,
            "resolved_at": resolved_at,
        }
    )
    review["subject_signoff"].update(
        {
            "reviewer": "independent-subject-reviewer",
            "status": "complete",
            "completed_at": "2026-08-13T20:00:00+08:00",
        }
    )

    with pytest.raises(ReviewValidationError, match=message):
        validate_review_semantics(ROOT, review, dataset)


def test_subject_and_qa_signoffs_require_distinct_ordered_reviewers() -> None:
    dataset = load_and_validate_dataset(ROOT)
    review = deepcopy(load_and_validate_review(ROOT))
    for key in ("concept_reviews", "relation_reviews", "anchor_reviews"):
        for item in review[key]:
            item["decision"] = "accept"
    review["license_notice_seen"] = True
    review["subject_signoff"].update(
        {
            "reviewer": "reviewer-a",
            "status": "complete",
            "completed_at": "2026-08-13T20:05:00+08:00",
        }
    )
    review["qa_signoff"].update(
        {
            "reviewer": "reviewer-a",
            "status": "complete",
            "completed_at": "2026-08-13T20:10:00+08:00",
        }
    )
    with pytest.raises(ReviewValidationError, match="must be different people"):
        validate_review_semantics(ROOT, review, dataset)

    review["qa_signoff"].update(
        {
            "reviewer": "reviewer-b",
            "completed_at": "2026-08-13T20:00:00+08:00",
        }
    )
    with pytest.raises(ReviewValidationError, match="cannot precede subject signoff"):
        validate_review_semantics(ROOT, review, dataset)
