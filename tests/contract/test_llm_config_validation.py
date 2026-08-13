from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from scripts.repository_validation import (
    RepositoryValidationError,
    load_and_validate_llm_config,
    validate_llm_semantics,
)

ROOT = Path(__file__).resolve().parents[2]


def test_versioned_llm_config_passes_schema_and_semantics() -> None:
    providers, policies = load_and_validate_llm_config(ROOT)

    validate_llm_semantics(providers, policies)


def test_unknown_provider_field_is_rejected_by_schema(tmp_path: Path) -> None:
    providers = (ROOT / "config/llm/providers.yaml").read_text(encoding="utf-8")
    policies = (ROOT / "config/llm/model-policies.yaml").read_text(encoding="utf-8")
    schemas = ROOT / "config/llm/schema"
    config = tmp_path / "config/llm"
    config.mkdir(parents=True)
    (config / "schema").mkdir()
    (config / "providers.yaml").write_text(
        providers.replace("    enabled: true", "    enabled: true\n    unknown_field: true", 1),
        encoding="utf-8",
    )
    (config / "model-policies.yaml").write_text(policies, encoding="utf-8")
    for name in ("providers.schema.json", "model-policies.schema.json"):
        (config / "schema" / name).write_text(
            (schemas / name).read_text(encoding="utf-8"), encoding="utf-8"
        )

    with pytest.raises(RepositoryValidationError, match="unknown_field"):
        load_and_validate_llm_config(tmp_path)


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda providers, policies: policies["task_profiles"]["concept_extract"][
                "deployments"
            ].insert(0, "missing/model"),
            "unknown deployment",
        ),
        (
            lambda providers, policies: policies["task_profiles"]["concept_extract"][
                "required_capabilities"
            ].append("image_input"),
            "lacks required capabilities",
        ),
        (
            lambda providers, policies: providers["providers"]["deepseek"]["endpoint"].update(
                {"base_url": "http://api.deepseek.com"}
            ),
            "must use HTTPS",
        ),
        (
            lambda providers, policies: policies["task_profiles"]["concept_extract"][
                "budget"
            ].update({"max_fallbacks": 2}),
            "exceeds global fallback limit",
        ),
    ],
)
def test_semantic_mutations_fail(mutator: object, message: str) -> None:
    providers, policies = load_and_validate_llm_config(ROOT)
    changed_providers = deepcopy(providers)
    changed_policies = deepcopy(policies)
    assert callable(mutator)
    mutator(changed_providers, changed_policies)

    with pytest.raises(RepositoryValidationError, match=message):
        validate_llm_semantics(changed_providers, changed_policies)
