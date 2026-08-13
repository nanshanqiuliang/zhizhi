"""Deterministic, offline repository and LLM configuration validation."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

JsonObject = dict[str, Any]


class RepositoryValidationError(ValueError):
    """Raised when a versioned repository contract is invalid."""


@dataclass(frozen=True, slots=True)
class SecretFinding:
    """A possible secret location without retaining the matching content."""

    path: Path
    line: int
    rule: str


REQUIRED_PATHS = (
    "AGENTS.md",
    "README.md",
    "pyproject.toml",
    "uv.lock",
    "package.json",
    "pnpm-workspace.yaml",
    "pnpm-lock.yaml",
    ".github/workflows/ci.yml",
    "apps/desktop",
    "apps/web",
    "apps/api",
    "apps/worker",
    "packages/domain/src/knowledge_tree_domain",
    "packages/application/src/knowledge_tree_application",
    "packages/contracts-py/src/knowledge_tree_contracts",
    "packages/contracts-ts/src",
    "docs/contracts/knowledge-tree-graph.v1.schema.json",
    "packages/infrastructure/src/knowledge_tree_infrastructure",
    "packages/algorithms/src/knowledge_tree_algorithms",
    "migrations/sqlite",
    "migrations/postgres",
    "tests/unit",
    "tests/contract",
    "tests/security",
    "evals/calculus-v1/gold.json",
    "evals/calculus-v1/independent-review.json",
    "evals/calculus-v1/review-policy.v2.json",
    "evals/calculus-v1/schema/gold.schema.json",
    "evals/calculus-v1/schema/independent-review.schema.json",
    "evals/calculus-v1/schema/machine-review.schema.json",
    "evals/calculus-v1/schema/review-policy.schema.json",
)

SECRET_RULES: Mapping[str, re.Pattern[str]] = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "api_token": re.compile(r"\b(?:sk-|sk_)[A-Za-z0-9_-]{20,}\b"),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
}

TEXT_SUFFIXES = {
    "",
    ".css",
    ".html",
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}

EXCLUDED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "dist",
    "node_modules",
    "target",
}


def _as_object(value: Any, source: Path) -> JsonObject:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise RepositoryValidationError(f"{source}: expected an object with string keys")
    return value


def _load_yaml(path: Path) -> JsonObject:
    try:
        return _as_object(yaml.safe_load(path.read_text(encoding="utf-8")), path)
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise RepositoryValidationError(f"{path}: cannot parse YAML: {error}") from error


def _load_json(path: Path) -> JsonObject:
    try:
        return _as_object(json.loads(path.read_text(encoding="utf-8")), path)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RepositoryValidationError(f"{path}: cannot parse JSON: {error}") from error


def _format_schema_path(parts: Iterable[object]) -> str:
    rendered = ".".join(str(part) for part in parts)
    return rendered or "<root>"


def _validate_schema(instance: JsonObject, schema: JsonObject, source: Path) -> None:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path))
    if errors:
        first = errors[0]
        location = _format_schema_path(first.absolute_path)
        raise RepositoryValidationError(f"{source}:{location}: {first.message}")


def load_and_validate_llm_config(root: Path) -> tuple[JsonObject, JsonObject]:
    """Load the two versioned LLM files and enforce their JSON Schemas."""

    llm_dir = root / "config/llm"
    providers_path = llm_dir / "providers.yaml"
    policies_path = llm_dir / "model-policies.yaml"
    providers = _load_yaml(providers_path)
    policies = _load_yaml(policies_path)
    provider_schema = _load_json(llm_dir / "schema/providers.schema.json")
    policy_schema = _load_json(llm_dir / "schema/model-policies.schema.json")
    _validate_schema(providers, provider_schema, providers_path)
    _validate_schema(policies, policy_schema, policies_path)
    return providers, policies


def load_graph_contract_schema(root: Path) -> JsonObject:
    """Load and self-validate the canonical graph contract source."""

    path = root / "docs/contracts/knowledge-tree-graph.v1.schema.json"
    schema = _load_json(path)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise RepositoryValidationError(f"{path}: invalid JSON Schema: {error}") from error
    return schema


def _deployment(
    providers: JsonObject, deployment_name: str
) -> tuple[JsonObject, JsonObject] | None:
    provider_name, separator, model_name = deployment_name.partition("/")
    if not separator:
        return None
    provider = providers.get("providers", {}).get(provider_name)
    if not isinstance(provider, dict):
        return None
    model = provider.get("models", {}).get(model_name)
    if not isinstance(model, dict):
        return None
    return provider, model


def validate_llm_semantics(providers: JsonObject, policies: JsonObject) -> None:
    """Enforce cross-file and security invariants JSON Schema cannot express."""

    configured_providers = providers.get("providers", {})
    if not isinstance(configured_providers, dict):
        raise RepositoryValidationError("providers must be an object")

    for provider_name, provider_value in configured_providers.items():
        if not isinstance(provider_value, dict):
            raise RepositoryValidationError(f"provider {provider_name} must be an object")
        endpoint = provider_value.get("endpoint")
        if endpoint is not None:
            if not isinstance(endpoint, dict):
                raise RepositoryValidationError(
                    f"provider {provider_name} endpoint must be an object"
                )
            base_url = endpoint.get("base_url")
            allowed_hosts = endpoint.get("allowed_hosts", [])
            if not isinstance(base_url, str) or urlparse(base_url).scheme != "https":
                raise RepositoryValidationError(f"provider {provider_name} base_url must use HTTPS")
            hostname = urlparse(base_url).hostname
            if hostname not in allowed_hosts:
                raise RepositoryValidationError(
                    f"provider {provider_name} host {hostname!r} is not allowlisted"
                )

    global_limits = policies.get("global_limits", {})
    if not isinstance(global_limits, dict):
        raise RepositoryValidationError("global_limits must be an object")
    global_fallbacks = global_limits.get("max_fallbacks_per_model_run")
    if not isinstance(global_fallbacks, int):
        raise RepositoryValidationError("global fallback limit must be an integer")

    task_profiles = policies.get("task_profiles", {})
    if not isinstance(task_profiles, dict):
        raise RepositoryValidationError("task_profiles must be an object")
    for task_name, task_value in task_profiles.items():
        if not isinstance(task_value, dict):
            raise RepositoryValidationError(f"task profile {task_name} must be an object")
        deployments = task_value.get("deployments", [])
        preferences = task_value.get("production_preference", [])
        required = set(task_value.get("required_capabilities", []))
        if not isinstance(deployments, list) or not all(
            isinstance(item, str) for item in deployments
        ):
            raise RepositoryValidationError(f"task profile {task_name} deployments are invalid")
        if not isinstance(preferences, list) or not set(preferences).issubset(deployments):
            raise RepositoryValidationError(
                f"task profile {task_name} production preference is not a deployment subset"
            )
        for deployment_name in deployments:
            resolved = _deployment(providers, deployment_name)
            if resolved is None:
                raise RepositoryValidationError(
                    f"task profile {task_name} references unknown deployment {deployment_name}"
                )
            _, model = resolved
            capabilities = model.get("capabilities", {})
            if not isinstance(capabilities, dict):
                raise RepositoryValidationError(
                    f"deployment {deployment_name} has no capability snapshot"
                )
            missing = sorted(name for name in required if capabilities.get(name) is not True)
            if missing:
                raise RepositoryValidationError(
                    f"deployment {deployment_name} lacks required capabilities: {missing}"
                )
        budget = task_value.get("budget")
        if isinstance(budget, dict):
            fallback_count = budget.get("max_fallbacks")
            if isinstance(fallback_count, int) and fallback_count > global_fallbacks:
                raise RepositoryValidationError(
                    f"task profile {task_name} exceeds global fallback limit"
                )


def missing_required_paths(root: Path) -> list[str]:
    """Return repository skeleton paths that have not been created."""

    return [relative for relative in REQUIRED_PATHS if not (root / relative).exists()]


def repository_text_files(root: Path) -> list[Path]:
    """Return text-like files while excluding build, cache, VCS, and local data trees."""

    result: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        if path.name in {"uv.lock", "pnpm-lock.yaml"} or path.suffix.lower() in TEXT_SUFFIXES:
            result.append(path)
    return sorted(result)


def find_suspected_secrets(paths: Iterable[Path]) -> list[SecretFinding]:
    """Find high-signal secret patterns without returning their values."""

    findings: list[SecretFinding] = []
    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            continue
        for line_number, line in enumerate(lines, start=1):
            for rule, pattern in SECRET_RULES.items():
                if pattern.search(line):
                    findings.append(SecretFinding(path=path, line=line_number, rule=rule))
    return findings
