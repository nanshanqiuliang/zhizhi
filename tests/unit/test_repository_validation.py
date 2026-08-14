from pathlib import Path

import pytest

from scripts.repository_validation import (
    RepositoryValidationError,
    load_graph_contract_schema,
    load_llm_contract_schema,
    missing_required_paths,
)


def test_repository_skeleton_has_required_paths() -> None:
    root = Path(__file__).resolve().parents[2]

    assert missing_required_paths(root) == []


def test_missing_required_path_is_reported(tmp_path: Path) -> None:
    missing = missing_required_paths(tmp_path)

    assert "AGENTS.md" in missing
    assert "apps/web" in missing


def test_canonical_graph_schema_is_in_default_repository_gate() -> None:
    root = Path(__file__).resolve().parents[2]

    schema = load_graph_contract_schema(root)

    assert schema["$defs"]["GraphPatch"]["properties"]["schema_version"] == {"const": 1}


def test_invalid_graph_schema_fails_default_repository_gate(tmp_path: Path) -> None:
    contract_dir = tmp_path / "docs/contracts"
    contract_dir.mkdir(parents=True)
    (contract_dir / "knowledge-tree-graph.v1.schema.json").write_text(
        '{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"wrong"}',
        encoding="utf-8",
    )

    with pytest.raises(RepositoryValidationError):
        load_graph_contract_schema(tmp_path)


def test_canonical_llm_schema_is_in_default_repository_gate() -> None:
    root = Path(__file__).resolve().parents[2]

    schema = load_llm_contract_schema(root)

    assert schema["$defs"]["GenerationRequest"]["properties"]["schema_version"] == {"const": 1}


def test_llm_schema_without_generation_request_fails_gate(tmp_path: Path) -> None:
    contract_dir = tmp_path / "docs/contracts"
    contract_dir.mkdir(parents=True)
    (contract_dir / "llm.v1.schema.json").write_text(
        '{"$schema":"https://json-schema.org/draft/2020-12/schema","$defs":{}}',
        encoding="utf-8",
    )

    with pytest.raises(RepositoryValidationError, match="GenerationRequest"):
        load_llm_contract_schema(tmp_path)
