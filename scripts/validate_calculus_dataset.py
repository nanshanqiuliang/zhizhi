"""Command-line gate for the calculus-v1 gold fixture."""

from __future__ import annotations

import sys
from pathlib import Path

from scripts.calculus_dataset_validation import (
    DatasetValidationError,
    load_and_validate_dataset,
    validate_dataset_semantics,
)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        dataset = load_and_validate_dataset(root)
        validate_dataset_semantics(root, dataset)
    except DatasetValidationError as error:
        print(f"FAIL [{error.code}]: {error}", file=sys.stderr)
        return 1

    source = dataset["source"]
    print(
        "PASS: calculus-v1 dataset "
        f"({len(dataset['concepts'])} concepts, {len(dataset['relations'])} relations, "
        f"{len(dataset['anchors'])} anchors, {source['page_count']} PDF pages, "
        f"independent review={dataset['review']['independent']['status']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
