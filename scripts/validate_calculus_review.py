"""Command-line gate for the calculus-v1 independent review packet."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts.calculus_dataset_validation import (
    DatasetValidationError,
    load_and_validate_dataset,
    validate_dataset_semantics,
)
from scripts.calculus_review_validation import (
    ReviewValidationError,
    load_and_validate_review,
    validate_review_semantics,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="fail until both independent subject and QA signoffs are complete",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    try:
        dataset = load_and_validate_dataset(root)
        validate_dataset_semantics(root, dataset)
        review = load_and_validate_review(root)
        validate_review_semantics(root, review, dataset, require_complete=args.require_complete)
    except (DatasetValidationError, ReviewValidationError) as error:
        print(f"FAIL [{error.code}]: {error}", file=sys.stderr)
        return 1

    subject = review["subject_signoff"]["status"]
    qa = review["qa_signoff"]["status"]
    print(
        "PASS: calculus-v1 independent review packet "
        f"(30 concepts, 40 relations, 50 anchors, subject={subject}, qa={qa})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
