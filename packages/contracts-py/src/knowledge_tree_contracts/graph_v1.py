"""Load and validate the canonical graph v1 JSON Schema without framework dependencies."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from copy import deepcopy
from functools import lru_cache
from typing import Any
from uuid import UUID

from jsonschema import Draft202012Validator, FormatChecker

from ._generated_graph_v1_schema import GRAPH_V1_SCHEMA_JSON

JsonObject = dict[str, Any]

_CONTRACT_DEFINITIONS = {
    "anchor": "Anchor",
    "course_graph": "CourseGraph",
    "graph_patch": "GraphPatch",
}
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


class ContractValidationError(ValueError):
    """A stable, content-safe contract rejection."""

    def __init__(self, *, contract: str, path: str, rule: str) -> None:
        self.code = "validation_failed"
        self.details: JsonObject = {"contract": contract, "path": path, "rule": rule}
        super().__init__(f"{self.code}: {contract} at {path} violates {rule}")


@lru_cache(maxsize=1)
def _load_graph_contract_document() -> JsonObject:
    try:
        value = json.loads(GRAPH_V1_SCHEMA_JSON)
    except json.JSONDecodeError as error:
        raise RuntimeError("generated graph schema artifact is invalid") from error
    if not isinstance(value, dict):
        raise RuntimeError("canonical graph schema must be an object")
    Draft202012Validator.check_schema(value)
    return value


def graph_contract_document() -> JsonObject:
    """Return an isolated copy of the canonical graph contract document."""

    return deepcopy(_load_graph_contract_document())


def contract_schema(contract: str) -> JsonObject:
    """Build a named validation view while retaining the canonical root definitions."""

    definition = _CONTRACT_DEFINITIONS.get(contract)
    if definition is None:
        raise ValueError(f"unknown graph contract: {contract}")
    root = graph_contract_document()
    return {
        "$schema": root["$schema"],
        "$id": f"{root['$id']}?contract={contract}",
        "$ref": f"#/$defs/{definition}",
        "$defs": deepcopy(root["$defs"]),
    }


def _is_uuidv7(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        identifier = UUID(value)
    except ValueError:
        return False
    return identifier.version == 7 and identifier.variant == "specified in RFC 4122"


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_PATTERN.fullmatch(value) is not None


def _format_checker() -> FormatChecker:
    checker = FormatChecker()
    checker.checks("uuidv7")(_is_uuidv7)
    checker.checks("sha256")(_is_sha256)
    return checker


def _path(parts: Any) -> str:
    rendered = ".".join(str(part) for part in parts)
    return rendered or "<root>"


def _semantic_anchor_validation(instance: Mapping[str, Any]) -> None:
    selectors = instance.get("selectors")
    if not isinstance(selectors, list):
        return
    for index, selector in enumerate(selectors):
        if not isinstance(selector, dict):
            continue
        if selector.get("type") == "page_bbox":
            bbox = selector.get("bbox_norm")
            if (
                isinstance(bbox, list)
                and len(bbox) == 4
                and all(isinstance(item, int | float) for item in bbox)
                and not isinstance(bbox[0], bool)
                and not isinstance(bbox[1], bool)
                and not isinstance(bbox[2], bool)
                and not isinstance(bbox[3], bool)
                and not (bbox[0] < bbox[2] and bbox[1] < bbox[3])
            ):
                raise ContractValidationError(
                    contract="anchor", path=f"selectors.{index}.bbox_norm", rule="ordered_bbox"
                )
        if selector.get("type") == "text_position":
            start = selector.get("start")
            end = selector.get("end")
            if isinstance(start, int) and isinstance(end, int) and start >= end:
                raise ContractValidationError(
                    contract="anchor",
                    path=f"selectors.{index}",
                    rule="ordered_text_position",
                )


def validate_contract(contract: str, instance: Mapping[str, Any]) -> None:
    """Validate a mapping against a named v1 contract without mutating the input."""

    schema = contract_schema(contract)
    validator = Draft202012Validator(schema, format_checker=_format_checker())
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path))
    if errors:
        first = errors[0]
        raise ContractValidationError(
            contract=contract,
            path=_path(first.absolute_path),
            rule=str(first.validator or "schema"),
        )
    if contract == "anchor":
        _semantic_anchor_validation(instance)
