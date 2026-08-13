"""Command-line entry point for the offline repository gate."""

from __future__ import annotations

import sys
from pathlib import Path

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

        findings = find_suspected_secrets(repository_text_files(root))
        if findings:
            locations = [
                f"{finding.path.relative_to(root)}:{finding.line} ({finding.rule})"
                for finding in findings
            ]
            raise RepositoryValidationError(f"suspected secrets found: {locations}")
    except RepositoryValidationError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1

    profiles = len(policies["task_profiles"])
    provider_count = len(providers["providers"])
    print(
        "PASS: repository skeleton, secret scan, and LLM contracts "
        f"({provider_count} providers, {profiles} task profiles)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
