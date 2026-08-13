from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from scripts.calculus_dataset_validation import (
    DatasetValidationError,
    load_and_validate_dataset,
    validate_dataset_semantics,
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
