"""Command-line entry point for the offline repository gate."""

from __future__ import annotations

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
from scripts.repository_validation import (
    RepositoryValidationError,
    find_suspected_secrets,
    load_and_validate_llm_config,
    missing_required_paths,
    repository_text_files,
    validate_llm_semantics,
)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        missing = missing_required_paths(root)
        if missing:
            raise RepositoryValidationError(f"required repository paths are missing: {missing}")

        providers, policies = load_and_validate_llm_config(root)
        validate_llm_semantics(providers, policies)

        dataset = load_and_validate_dataset(root)
        validate_dataset_semantics(root, dataset)
        review = load_and_validate_review(root)
        validate_review_semantics(root, review, dataset)

        findings = find_suspected_secrets(repository_text_files(root))
        if findings:
            locations = [
                f"{finding.path.relative_to(root)}:{finding.line} ({finding.rule})"
                for finding in findings
            ]
            raise RepositoryValidationError(f"suspected secrets found: {locations}")
    except (DatasetValidationError, RepositoryValidationError, ReviewValidationError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1

    profiles = len(policies["task_profiles"])
    provider_count = len(providers["providers"])
    print(
        "PASS: repository skeleton, secret scan, LLM contracts, and calculus review packet "
        f"({provider_count} providers, {profiles} task profiles, 30/40/50 review items)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
