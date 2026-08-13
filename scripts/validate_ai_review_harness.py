"""CLI for deterministic calculus v2 machine-review validation."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.ai_review_harness import (
    MachineReviewValidationError,
    ReplaySearchProvider,
    build_mock_machine_review,
    load_review_policy,
    validate_machine_review,
)
from scripts.calculus_dataset_validation import load_and_validate_dataset


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        dataset = load_and_validate_dataset(root)
        policy = load_review_policy(root)
        provider = ReplaySearchProvider.from_dataset(root, dataset)
        review = build_mock_machine_review(dataset, policy, provider)
        validate_machine_review(root, review, dataset, policy, provider)
    except MachineReviewValidationError as error:
        print(json.dumps({"code": error.code, "detail": str(error)}, ensure_ascii=False))
        return 1
    print(
        "PASS: calculus-machine-review.v2 deterministic mock/replay "
        f"state={review['machine_state']} correlation={review['correlation']['classification']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
